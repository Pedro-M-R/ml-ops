"""Valida CSV, lotes HTTP e o fluxo real do formulário Streamlit."""

import json
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


def test_response_keeps_exact_api_values_and_optional_ids(monkeypatch):
    response = {"predictions": [
        {"customerID": "001", "churn_probability": 0.2042808166952596, "churn_prediction": 0},
        {"churn_probability": 0.8, "churn_prediction": 1},
    ], "threshold": 0.5}
    mock_api(monkeypatch, lambda request: httpx.Response(200, json=response))
    result = client.predict_customers([client.EXAMPLE_CUSTOMER] * 2, 0.5)
    assert result.attrs["api_response"] == response


def test_customer_base_loads_configured_csv_and_keeps_history(monkeypatch, tmp_path, csv_frame):
    path = tmp_path / "customers.csv"
    csv_frame["Churn"] = "Yes"
    csv_frame.to_csv(path, index=False)
    monkeypatch.setenv("CHURN_DATA_PATH", str(path))
    frame = client.load_customer_base()
    assert frame.customerID.tolist() == ["001"]
    assert frame.Churn.tolist() == ["Yes"]
    assert "Churn" not in client.customers_from_frame(frame)[0]
    path.unlink()
    with pytest.raises(client.DashboardError, match="Base não encontrada"):
        client.load_customer_base()


def test_existing_base_model_and_streamlit_match_fastapi(monkeypatch):
    """Usa o artefato já treinado e a base do projeto, sem modelo simulado."""
    import numpy as np
    from fastapi.testclient import TestClient
    from churn.api import create_app

    monkeypatch.delenv("CHURN_DATA_PATH", raising=False)
    frame = client.load_customer_base()
    customers = client.customers_from_frame(frame)
    monkeypatch.setattr(client, "check_health", lambda: True)
    with TestClient(create_app()) as api:
        def handler(request):
            response = api.post("/predict", content=request.content, headers={"Content-Type": "application/json"})
            return httpx.Response(response.status_code, json=response.json())

        mock_api(monkeypatch, handler)
        result = client.predict_customers(customers, 0.5)
        features = frame.drop(columns=["customerID", "Churn"]).copy()
        for column in client.NUMERIC_COLUMNS:
            features[column] = pd.to_numeric(features[column].replace(r"^\s*$", None, regex=True)).astype(float)
        probabilities = api.app.state.model.predict(features)[:, 1]
        np.testing.assert_array_equal(result.churn_probability, probabilities)
        np.testing.assert_array_equal(result.churn_prediction, (probabilities >= 0.5).astype(int))
        assert result.customerID.tolist() == frame.customerID.tolist()

        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "frontend/streamlit_app.py"))
        app.run(timeout=30)
        assert not app.exception
        for position, expected_class in [(int(np.argmin(probabilities)), 0), (int(np.argmax(probabilities)), 1)]:
            app.selectbox(key="base_customer").set_value(position).run()
            next(button for button in app.button if button.label == "Classificar cliente da base").click().run(timeout=30)
            assert not app.exception
            expected = api.post("/predict", json={"customers": [customers[position]], "threshold": 0.5}).json()
            assert json.loads(app.json[0].value) == expected
            assert expected["predictions"][0]["churn_prediction"] == expected_class
            messages = app.success if expected_class == 0 else app.warning
            assert any(f"Classificação {expected_class}" in message.value for message in messages)
        # As abas podem ter resultados ao mesmo tempo, sem colisão de widgets.
        next(button for button in app.button if button.label == "Analisar cliente").click().run(timeout=30)
        assert not app.exception
        assert len(app.json) == 2
        next(button for button in app.button if button.label == "Classificar toda a base").click().run(timeout=30)
        assert not app.exception
        assert json.loads(app.json[0].value) == result.attrs["api_response"]


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
