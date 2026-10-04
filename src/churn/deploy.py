"""Comandos portáveis de UI, API HTTP e previsão via artefato exportado."""

import argparse
import json
import os
import subprocess
import sys
import sysconfig
from pathlib import Path

import pandas as pd

from churn.config import PROJECT_ROOT


def selected_path():
    selection = PROJECT_ROOT / "reports/selection.json"
    if not selection.exists():
        raise FileNotFoundError("Execute churn-tune ou copie deployment/ e reports/selection.json.")
    return str(PROJECT_ROOT / json.loads(selection.read_text(encoding="utf-8"))["export_path"])


def serve():
    parser = argparse.ArgumentParser(description="Serve o pipeline exportado, sem depender do banco MLflow.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model", help="Pasta exportada ou URI models:/nome/versão")
    args = parser.parse_args()
    environment = os.environ.copy()
    environment["PATH"] = sysconfig.get_path("scripts") + os.pathsep + environment.get("PATH", "")
    if args.model and args.model.startswith("models:"):
        from churn.tracking import configure_tracking
        environment["MLFLOW_TRACKING_URI"] = configure_tracking()
    raise SystemExit(subprocess.call([
        sys.executable, "-m", "mlflow", "models", "serve", "-m", args.model or selected_path(),
        "--env-manager", "local", "--host", args.host, "--port", str(args.port),
    ], env=environment))


def ui():
    from churn.tracking import configure_tracking
    uri = configure_tracking()
    raise SystemExit(subprocess.call([
        sys.executable, "-m", "mlflow", "ui", "--backend-store-uri", uri,
        "--host", "127.0.0.1", "--port", "5000",
    ]))


def predict():
    import mlflow.pyfunc
    parser = argparse.ArgumentParser(description="Prevê probabilidades de churn de um CSV bruto.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("predictions.csv"))
    parser.add_argument("--model")
    args = parser.parse_args()
    frame = pd.read_csv(args.input)
    for col in ("SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"):
        if col in frame:
            frame[col] = pd.to_numeric(frame[col], errors="coerce").astype(float)
    features = frame.drop(columns=["Churn", "customerID"], errors="ignore")
    probabilities = mlflow.pyfunc.load_model(args.model or selected_path()).predict(features)[:, 1]
    result = pd.DataFrame({"churn_probability": probabilities, "churn_prediction": (probabilities >= 0.5).astype(int)})
    if "customerID" in frame:
        result.insert(0, "customerID", frame["customerID"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"{len(result)} previsões salvas em {args.output}")
