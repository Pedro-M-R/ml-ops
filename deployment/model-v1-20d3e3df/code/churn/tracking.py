"""Configuração compartilhada pelo treino, grid e verificação."""

import os

import mlflow

from churn.config import PROJECT_ROOT


def configure_tracking() -> str:
    # URI absoluta evita stores diferentes ao executar a partir de outra pasta.
    uri = os.environ.get("MLFLOW_TRACKING_URI") or (
        "sqlite:///" + (PROJECT_ROOT / "mlflow.db").as_posix()
    )
    # Versões recentes do MLflow exigem opt-in para o file store usado no guia.
    if uri.startswith("file:"):
        os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
    mlflow.set_tracking_uri(uri)
    if mlflow.get_experiment_by_name("churn") is None:
        if uri.startswith(("sqlite:", "file:")):
            mlflow.create_experiment(
                "churn", artifact_location=(PROJECT_ROOT / "mlartifacts").as_uri()
            )
        else:
            mlflow.create_experiment("churn")
    mlflow.set_experiment("churn")
    return uri
