"""Valida CSV, lotes HTTP e o fluxo real do formulário Streamlit."""

from pathlib import Path

import httpx
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from churn import dashboard_client as client


@pytest.fixture
def csv_frame():
    return pd.DataFrame([{"customerID": "001", **client.EXAMPLE_CUSTOMER}])


def mock_api(monkeypatch, handler):
    original_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(client.httpx, "Client", lambda **kwargs: original_client(transport=transport, **kwargs))


def test_csv_preserves_id_missing_numbers_and_ignores_target(csv_frame):
    csv_frame["TotalCharges"] = " "
    csv_frame["Churn"] = "Yes"
    customer = client.customers_from_frame(csv_frame)[0]
    assert customer["customerID"] == "001"
    assert customer["TotalCharges"] is None
    assert "Churn" not in customer


@pytest.mark.parametrize("column,value", [
    ("MonthlyCharges", "abc"), ("tenure", -1), ("TotalCharges", "inf"),
    ("TotalCharges", "NaN"), ("SeniorCitizen", 2), ("SeniorCitizen", 0.5), ("gender", " "),
])
def test_csv_rejects_invalid_values(csv_frame, column, value):
    csv_frame[column] = value
    with pytest.raises(client.DashboardError):
        client.customers_from_frame(csv_frame)


def test_csv_rejects_missing_or_unknown_columns(csv_frame):
    with pytest.raises(client.DashboardError, match="ausentes"):
        client.customers_from_frame(csv_frame.drop(columns="gender"))
    with pytest.raises(client.DashboardError, match="desconhecidas"):
        client.customers_from_frame(csv_frame.assign(unexpected="x"))
    with pytest.raises(client.DashboardError, match="clientes por arquivo"):
        client.customers_from_frame(csv_frame.iloc[:0])


def test_large_csv_batches_requests_and_preserves_order(monkeypatch):
    import json

    batch_lengths = []

    def handler(request):
        body = json.loads(request.content)
        batch_lengths.append(len(body["customers"]))
        assert body["threshold"] == 0.7
        return httpx.Response(200, json={"threshold": 0.7, "predictions": [
            {"customerID": c["customerID"], "churn_probability": 0.6, "churn_prediction": 0}
            for c in body["customers"]
        ]})

    mock_api(monkeypatch, handler)
    customers = [{"customerID": str(i), **client.EXAMPLE_CUSTOMER} for i in range(2001)]
    result = client.predict_customers(customers, 0.7)
    assert batch_lengths == [1000, 1000, 1]
    assert result.customerID.tolist() == [str(i) for i in range(2001)]


@pytest.mark.parametrize("status", [400, 422, 500])
def test_api_failures_become_actionable_messages(monkeypatch, status):
    mock_api(monkeypatch, lambda request: httpx.Response(status, json={"detail": "private-customer-data"}))
    with pytest.raises(client.DashboardError) as error:
        client.predict_customers([client.EXAMPLE_CUSTOMER], 0.5)
    assert "private-customer-data" not in str(error.value)


@pytest.mark.parametrize("payload", [
    {}, {"predictions": [], "threshold": 0.5},
    {"predictions": [{"churn_probability": 1.1, "churn_prediction": 1}], "threshold": 0.5},
    {"predictions": [{"churn_probability": 0.6, "churn_prediction": 0}], "threshold": 0.5},
])
def test_invalid_api_response_is_not_shown_as_prediction(monkeypatch, payload):
    mock_api(monkeypatch, lambda request: httpx.Response(200, json=payload))
    with pytest.raises(client.DashboardError, match="inesperada"):
        client.predict_customers([client.EXAMPLE_CUSTOMER], 0.5)


def test_timeout_becomes_actionable_message(monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("timeout", request=request)

    mock_api(monkeypatch, handler)
    with pytest.raises(client.DashboardError, match="demorou"):
        client.predict_customers([client.EXAMPLE_CUSTOMER], 0.5)


def test_form_consumes_fastapi_contract_and_retains_applied_threshold(monkeypatch):
    from fastapi.testclient import TestClient
    import numpy as np
    from churn.api import create_app

    class Model:
        def predict(self, frame):
            return np.array([[0.3, 0.7]] * len(frame))

    monkeypatch.setattr("mlflow.pyfunc.load_model", lambda uri: Model())
    monkeypatch.setattr(client, "check_health", lambda: True)
    with TestClient(create_app(model_uri="test-model")) as api:
        mock_api(monkeypatch, lambda request: httpx.Response(
            200, json=api.post("/predict", content=request.content, headers={"Content-Type": "application/json"}).json()
        ))
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "src/churn/dashboard.py"))
        app.run(timeout=30)
        assert not app.exception
        next(button for button in app.button if button.label == "Analisar cliente").click().run(timeout=30)
        assert not app.exception
        assert app.metric[0].value == "1"
        assert app.metric[1].value == "1"
        assert app.metric[2].value == "70.0%"
        app.slider[0].set_value(0.9).run()
        assert any("Limiar aplicado: 50%" in caption.value for caption in app.caption)
        next(button for button in app.button if button.label == "Analisar cliente").click().run(timeout=30)
        assert not app.exception
        assert app.metric[1].value == "0"


def test_form_displays_api_error(monkeypatch):
    monkeypatch.setattr(client, "check_health", lambda: False)

    def fail(customers, threshold):
        raise client.DashboardError("A API não está disponível.")

    monkeypatch.setattr(client, "predict_customers", fail)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "src/churn/dashboard.py")).run()
    next(button for button in app.button if button.label == "Analisar cliente").click().run()
    assert not app.exception
    assert app.error[0].value == "A API não está disponível."
    assert len(app.metric) == 0
