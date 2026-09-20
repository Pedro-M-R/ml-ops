import hashlib
import pickle
import tempfile
from pathlib import Path

import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from churn.config import Settings, settings
from churn.data import carregar_dados, validar_dados
from churn.evaluate import avaliar
from churn.features import CategoricalEncoder, preparar_features
from churn.lineage import data_md5, git_commit, git_dirty
from churn.tracking import configure_tracking


def build_model(cfg: Settings) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=cfg.n_estimators, random_state=cfg.random_state,
    )


def lineage_tags(cfg: Settings) -> dict[str, str]:
    pointer = Path(str(cfg.data_path) + ".dvc")
    version = data_md5(pointer)
    actual = hashlib.md5(cfg.data_path.read_bytes()).hexdigest()
    if actual != version:
        raise ValueError(
            "O CSV difere do ponteiro DVC. Execute dvc add para versionar a alteração "
            "ou dvc checkout para restaurar o dado antes de treinar."
        )
    return {"data_md5": version, "git_commit": git_commit(), "git_dirty": git_dirty()}


def prepare_data(cfg: Settings):
    frame = validar_dados(carregar_dados(cfg.data_path))
    features, labels = preparar_features(
        frame, cfg.target, cfg.id_column, cfg.positive_label,
    )
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=cfg.test_size,
        random_state=cfg.random_state, stratify=labels,
    )
    encoder = CategoricalEncoder().fit(x_train)
    return encoder.transform(x_train), encoder.transform(x_test), y_train, y_test, encoder


def train(cfg: Settings = settings) -> tuple[RandomForestClassifier, dict[str, float]]:
    tags = lineage_tags(cfg)
    x_train, x_test, y_train, y_test, encoder = prepare_data(cfg)

    configure_tracking()
    with mlflow.start_run(run_name="rf") as run:
        mlflow.set_tags({**tags, "run_type": "train"})
        mlflow.log_params(cfg.model_dump())
        model = build_model(cfg).fit(x_train, y_train)
        metrics = avaliar(model, x_test, y_test)
        mlflow.log_metrics(metrics)
        info = mlflow.sklearn.log_model(
            model, name="model",  # MLflow 3.x, conforme a nota de versão do guia.
            serialization_format="cloudpickle",
            signature=infer_signature(x_train, model.predict(x_train)),
            input_example=x_train.head(3),
        )
        mlflow.set_tag("model_uri", info.model_uri)
        with tempfile.TemporaryDirectory() as tmp:
            encoder_path = Path(tmp) / "encoder.pkl"
            with encoder_path.open("wb") as stream:
                pickle.dump(encoder, stream)
            mlflow.log_artifact(str(encoder_path), artifact_path="preprocessing")
        print(f"MLflow run_id: {run.info.run_id}")
    return model, metrics


def save_model(model: RandomForestClassifier, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(model, f)


def load_model(path: Path) -> RandomForestClassifier:
    with open(path, "rb") as f:
        return pickle.load(f)


def main(config: Settings = settings) -> dict[str, float]:
    model, metrics = train(config)
    save_model(model, config.model_path)

    for name, value in metrics.items():
        print(f"{name}: {value:.4f}")
    return metrics


def cli() -> None:
    main()


if __name__ == "__main__":
    cli()
