"""Comandos portáveis de UI, API HTTP e previsão via artefato exportado."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from churn.config import PROJECT_ROOT


def selected_path():
    selection = PROJECT_ROOT / "reports/selection.json"
    if not selection.exists():
        raise FileNotFoundError("Execute churn-tune ou copie deployment/ e reports/selection.json.")
    return str(PROJECT_ROOT / json.loads(selection.read_text(encoding="utf-8"))["export_path"])


def serve():
    import uvicorn

    from churn.api import create_app

    parser = argparse.ArgumentParser(description="Inicia a API FastAPI com o pipeline exportado de churn.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model", help="Pasta exportada ou URI models:/nome/versão")
    args = parser.parse_args()
    uvicorn.run(create_app(model_uri=args.model), host=args.host, port=args.port)


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
