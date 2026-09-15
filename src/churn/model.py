import pickle
import subprocess
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from churn.config import Settings, settings
from churn.data import carregar_dados, validar_dados
from churn.evaluate import avaliar
from churn.features import construir_features


def split(X: pd.DataFrame, y: pd.Series, config: Settings):
    return train_test_split(
        X,
        y,
        test_size=config.test_size,
    )


def train(
    X: pd.DataFrame,
    y: pd.Series,
    config: Settings,
) -> RandomForestClassifier:

    model = RandomForestClassifier(
        n_estimators=config.n_estimators
    )

    model.fit(X, y)

    return model


def save_model(model: RandomForestClassifier, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    with open(path, "wb") as f:
        pickle.dump(model, f)


def load_model(path: Path) -> RandomForestClassifier:
    with open(path, "rb") as f:
        return pickle.load(f)


def get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
        ).strip()
    except Exception:
        return "unknown"

def main(config: Settings = settings) -> dict[str, float]:

    mlflow.set_tracking_uri("http://127.0.0.1:5000")

    mlflow.set_experiment("churn")

def main(config: Settings = settings) -> dict[str, float]:

    
    mlflow.set_experiment("churn")

    df = validar_dados(
        carregar_dados(config.data_path)
    )

    X, y = construir_features(
        df,
        config.target,
        config.id_column,
    )

    X_train, X_test, y_train, y_test = split(
        X,
        y,
        config,
    )

    
    with mlflow.start_run(
    run_name=f"rf-{config.n_estimators}"
    ):

       
        mlflow.log_params({
            "n_estimators": config.n_estimators,
            "test_size": config.test_size,
        })

        
        model = train(
            X_train,
            y_train,
            config,
        )

        
        metrics = avaliar(
            model,
            X_test,
            y_test,
        )

        
        mlflow.log_metrics(metrics)

        
        mlflow.set_tag(
            "git_commit",
            get_git_commit(),
        )

        
        mlflow.sklearn.log_model(
            model,
            name="model",
        )

        
        save_model(
            model,
            config.model_path,
        )

        for name, value in metrics.items():
            print(f"{name}: {value:.4f}")

    return metrics


def cli() -> None:
    main()


if __name__ == "__main__":
    cli()