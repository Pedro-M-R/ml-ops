"""Verifica gravação, consulta, artefatos e predições; --grid executa os 9 runs."""

import argparse
import pickle
import tempfile
from pathlib import Path

import mlflow
import mlflow.sklearn
import numpy as np
from mlflow.tracking import MlflowClient

from churn.config import settings
from churn.experiments import run_grid
from churn.lineage import data_md5, git_commit
from churn.model import prepare_data, save_model, train
from churn.tracking import configure_tracking


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verify(include_grid: bool = False) -> None:
    uri = configure_tracking()
    print(f"MLflow {mlflow.__version__} | Tracking: {uri}")
    model, metrics = train(settings)
    save_model(model, settings.model_path)
    last_run = mlflow.last_active_run()
    require(last_run is not None, "Nenhum run foi criado.")
    client = MlflowClient()
    run = client.get_run(last_run.info.run_id)
    require(run.info.status == "FINISHED", "O run não terminou com sucesso.")
    for key, value in settings.model_dump().items():
        require(run.data.params.get(key) == str(value), f"Parâmetro incorreto: {key}")
    for key, value in metrics.items():
        require(np.isclose(run.data.metrics.get(key, np.nan), value), f"Métrica incorreta: {key}")
    require(
        run.data.tags.get("data_md5") == data_md5(Path(str(settings.data_path) + ".dvc")),
        "Tag data_md5 incorreta.",
    )
    require(run.data.tags.get("git_commit") == git_commit(), "Tag git_commit incorreta.")

    loaded = mlflow.sklearn.load_model(run.data.tags["model_uri"])
    _, x_test, _, _, encoder = prepare_data(settings)
    np.testing.assert_array_equal(model.predict(x_test), loaded.predict(x_test))
    np.testing.assert_allclose(model.predict_proba(x_test), loaded.predict_proba(x_test))
    info = mlflow.models.get_model_info(run.data.tags["model_uri"])
    require(info.signature is not None, "O modelo está sem assinatura.")
    require(info.saved_input_example_info is not None, "Falta o exemplo de entrada.")
    with tempfile.TemporaryDirectory() as tmp:
        artifact = client.download_artifacts(
            run.info.run_id, "preprocessing/encoder.pkl", dst_path=tmp,
        )
        with open(artifact, "rb") as stream:
            saved_encoder = pickle.load(stream)
        require(saved_encoder.columns_ == encoder.columns_, "Encoder salvo incorreto.")
    print(f"OK: run {run.info.run_id}, parâmetros, métricas, linhagem, modelo e encoder.")
    print(f"OK: modelo recarregado reproduz as predições de {len(x_test)} exemplos.")

    if include_grid:
        runs = run_grid()
        expected = {(str(n), str(d)) for n in (100, 200, 500) for d in (None, 8, 16)}
        actual = set(zip(runs["params.n_estimators"], runs["params.max_depth"]))
        require(len(runs) == 9 and actual == expected, "O grid não contém as 9 combinações.")
        for key in metrics:
            require(runs[f"metrics.{key}"].between(0, 1).all(), f"Métrica inválida no grid: {key}")
        require((runs["tags.data_md5"] == run.data.tags["data_md5"]).all(), "Linhagem do grid incorreta.")
        print("OK: 9 runs do grid concluídos e consultados com search_runs.")
    print("SUCESSO: MLflow está funcionando.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", action="store_true", help="Executa e verifica também o grid completo.")
    args = parser.parse_args()
    verify(include_grid=args.grid)
