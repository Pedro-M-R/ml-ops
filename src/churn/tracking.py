"""Configuração compartilhada pelo treino, grid e verificação."""

import os

import mlflow

from churn.config import PROJECT_ROOT


def configure_tracking() -> str:
    # URI absoluta evita stores diferentes ao executar a partir de outra pasta.
    uri = os.environ.get("MLFLOW_TRACKING_URI") or (PROJECT_ROOT / "mlruns").as_uri()
    # Versões recentes do MLflow exigem opt-in para o file store usado no guia.
    if uri.startswith("file:"):
        os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment("churn")
    return uri
