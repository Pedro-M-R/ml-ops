"""Teste HTTP da API FastAPI contra o modelo exportado, incluindo os dois contratos."""

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

    def api(path, payload=None, expected_status=200):
        request = Request(
            args.url.rstrip("/") + path,
            data=None if payload is None else json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            response = urlopen(request, timeout=30)
        except HTTPError as exc:
            response = exc
        with response:
            assert response.status == expected_status, (
                f"{path}: esperado HTTP {expected_status}, recebido {response.status}"
            )
            body = response.read().decode("utf-8")
            return json.loads(body) if response.headers.get_content_type() == "application/json" else body

    for attempt in range(30):
        try:
            assert api("/ping") == {"status": "ok"}
            break
        except URLError:
            if attempt == 29:
                raise
            time.sleep(1)

    assert api("/health") == {"status": "ok"}
    assert "swagger-ui" in api("/docs")
    schema = api("/openapi.json")
    assert {"/health", "/ping", "/predict", "/invocations"} <= schema["paths"].keys()

    request = json.loads((ROOT / "reports/example_request.json").read_text(encoding="utf-8"))
    actual = api("/invocations", request)["predictions"]
    selection = json.loads((ROOT / "reports/selection.json").read_text(encoding="utf-8"))
    model = mlflow.pyfunc.load_model(str(ROOT / selection["export_path"]))
    frame = pd.DataFrame(**request["dataframe_split"])
    expected = np.asarray(model.predict(frame), dtype=float)
    assert np.asarray(actual).shape == expected.shape
    np.testing.assert_allclose(actual, expected, rtol=1e-12)

    records = frame.to_dict(orient="records")
    record_predictions = api("/invocations", {"dataframe_records": records})["predictions"]
    assert np.asarray(record_predictions).shape == expected.shape
    np.testing.assert_allclose(record_predictions, expected, rtol=1e-12)

    customers = [dict(row) for row in records]
    customers[0]["customerID"] = "api-test-001"
    named_predictions = []
    for threshold in (0.5, 0.9):
        payload = {"customers": customers}
        if threshold != 0.5:
            payload["threshold"] = threshold
        result = api("/predict", payload)
        assert result["threshold"] == threshold
        predictions = result["predictions"]
        assert len(predictions) == len(customers)
        np.testing.assert_allclose(
            [row["churn_probability"] for row in predictions], expected[:, 1], rtol=1e-12,
        )
        np.testing.assert_array_equal(
            [row["churn_prediction"] for row in predictions], (expected[:, 1] >= threshold).astype(int),
        )
        assert predictions[0]["customerID"] == customers[0]["customerID"]
        assert all("customerID" not in row for row in predictions[1:])
        named_predictions.append(result)

    invalid = {"dataframe_records": [{"missing": 1}]}
    assert "detail" in api("/invocations", invalid, expected_status=400)
    assert "detail" in api("/predict", {"customers": [{"missing": 1}]}, expected_status=422)
    report = {
        "health_status": 200,
        "health_body": {"status": "ok"},
        "ping_status": 200,
        "docs_status": 200,
        "openapi_status": 200,
        "openapi_paths_verified": ["/health", "/ping", "/predict", "/invocations"],
        "prediction_rows_verified": len(actual),
        "probabilities": actual,
        "dataframe_records_rows_verified": len(record_predictions),
        "predict_rows_verified_per_threshold": len(customers),
        "predict_results": named_predictions,
        "customer_id_echo_verified": True,
        "invalid_input_status": 400,
        "predict_invalid_input_status": 422,
        "registered_version": selection["version"],
    }
    (ROOT / "reports/api_verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("SUCESSO: FastAPI saudável, documentação acessível e previsões equivalentes ao modelo exportado nos dois contratos.")


if __name__ == "__main__":
    main()
