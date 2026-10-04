"""Teste real da API: saúde, probabilidades, equivalência e entrada inválida."""

import argparse
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import mlflow.pyfunc
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    for attempt in range(30):
        try:
            with urlopen(args.url + "/ping", timeout=2) as response:
                assert response.status == 200
            break
        except URLError:
            if attempt == 29:
                raise
            time.sleep(1)
    request = json.loads((ROOT / "reports/example_request.json").read_text(encoding="utf-8"))
    req = Request(args.url + "/invocations", data=json.dumps(request).encode(), headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=30) as response:
        actual = json.load(response)["predictions"]
    selection = json.loads((ROOT / "reports/selection.json").read_text(encoding="utf-8"))
    model = mlflow.pyfunc.load_model(str(ROOT / selection["export_path"]))
    frame = pd.DataFrame(**request["dataframe_split"])
    np.testing.assert_allclose(actual, model.predict(frame), rtol=1e-12)
    invalid = Request(args.url + "/invocations", data=b'{"dataframe_records": [{"missing": 1}]}', headers={"Content-Type": "application/json"})
    try:
        urlopen(invalid, timeout=30)
    except HTTPError as exc:
        assert exc.code == 400
    else:
        raise AssertionError("A API aceitou uma entrada sem as colunas obrigatórias.")
    report = {"health_status": 200, "prediction_rows_verified": len(actual),
              "probabilities": actual, "invalid_input_status": 400,
              "registered_version": selection["version"]}
    (ROOT / "reports/api_verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("SUCESSO: API saudável, probabilidades equivalentes ao modelo exportado e schema validado.")


if __name__ == "__main__":
    main()
