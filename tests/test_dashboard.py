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


def test_customer_lookup_uses_existing_record_without_target(csv_frame):
    csv_frame["Churn"] = "Yes"
    customer = client.customer_from_id(csv_frame, " 001 ")
    assert customer["customerID"] == "001"
    assert "Churn" not in customer
    csv_frame["customerID"] = "7000-QFVW"
    assert client.customer_from_id(csv_frame, " 7000-qfvw ")["customerID"] == "7000-QFVW"
    with pytest.raises(client.DashboardError, match="não encontrado"):
        client.customer_from_id(csv_frame, "inexistente")
    with pytest.raises(client.DashboardError, match="Informe o código"):
        client.customer_from_id(csv_frame, " ")
    with pytest.raises(client.DashboardError, match="mais de um registro"):
        client.customer_from_id(pd.concat([csv_frame, csv_frame]), "7000-QFVW")


def test_existing_base_model_and_streamlit_match_fastapi(monkeypatch, tmp_path):
    """Usa o artefato treinado e os clientes reais, inclusive no pacote publicado."""
    import numpy as np
    from fastapi.testclient import TestClient
    from churn.api import create_app

    monkeypatch.delenv("CHURN_DATA_PATH", raising=False)
    root = Path(__file__).resolve().parents[1]
    published_base = tmp_path / "frontend/data/churn.csv"
    published_base.parent.mkdir(parents=True)
    published_base.write_bytes((root / "frontend/data/churn.csv").read_bytes())
    monkeypatch.setattr(client, "__file__", str(tmp_path / "src/churn/dashboard_client.py"))
    frame = client.load_customer_base()
    customers = client.customers_from_frame(frame)
    monkeypatch.setattr(client, "check_health", lambda: True)
    with TestClient(create_app()) as api:
        requests = []

        def handler(request):
            requests.append(json.loads(request.content))
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

        app = AppTest.from_file(str(root / "frontend/streamlit_app.py")).run(timeout=30)
        assert not app.exception
        assert app.title[0].value == "Qual a chance deste cliente cancelar?"
        assert len(app.json) == 0
        assert app.text_input(key="customer_id").value == ""
        assert [app.button(key=f"example_{index}").label for index in range(4)] == frame.customerID.head(4).tolist()
        for position, expected_class in [(int(np.argmin(probabilities)), 0), (int(np.argmax(probabilities)), 1)]:
            customer_id = customers[position]["customerID"]
            app.text_input(key="customer_id").set_value(" " + customer_id.lower() + " ")
            next(button for button in app.button if button.label == "Consultar").click().run(timeout=30)
            assert not app.exception
            expected = api.post("/predict", json={"customers": [customers[position]], "threshold": 0.5}).json()
            assert json.loads(app.json[0].value) == expected
            assert requests[-1]["customers"] == [customers[position]]
            assert "Churn" not in requests[-1]["customers"][0]
            assert expected["predictions"][0]["churn_prediction"] == expected_class
            assert app.metric[0].value == f"{probabilities[position]:.1%}"
            assert app.metric[1].value == f"{1 - probabilities[position]:.1%}"
            label = "SIM — tende a continuar pagando" if expected_class == 0 else "NÃO — tende a cancelar o serviço"
            assert any(label in element.value for element in app.markdown)

        # O exemplo é um cliente real e consulta o modelo com um único clique.
        app.button(key="example_0").click().run(timeout=30)
        assert not app.exception
        assert app.text_input(key="customer_id").value == customers[0]["customerID"]
        assert requests[-1]["customers"] == [customers[0]]
        assert json.loads(app.json[0].value) == api.post(
            "/predict", json={"customers": [customers[0]], "threshold": 0.5},
        ).json()

        app.button(key="classify_base").click().run(timeout=30)
        assert not app.exception
        assert json.loads(app.json[-1].value) == result.attrs["api_response"]
        assert set(app.dataframe[-1].value["Classificação"]) == {
            "SIM — tende a continuar pagando", "NÃO — tende a cancelar o serviço",
        }


def test_lookup_rejects_empty_and_unknown_ids_without_calling_api(monkeypatch):
    monkeypatch.setattr(client, "check_health", lambda: True)
    calls = []
    monkeypatch.setattr(client, "predict_customers", lambda *args: calls.append(args))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "src/churn/dashboard.py")).run()
    next(button for button in app.button if button.label == "Consultar").click().run()
    assert "Informe o código" in app.error[0].value
    app.text_input(key="customer_id").set_value("cliente-inexistente")
    next(button for button in app.button if button.label == "Consultar").click().run()
    assert "não encontrado no churn.csv" in app.error[0].value
    assert not app.exception
    assert not calls
    assert len(app.metric) == 0
    assert len(app.json) == 0


def test_form_displays_api_error_and_clears_previous_result(monkeypatch):
    monkeypatch.setattr(client, "check_health", lambda: True)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "src/churn/dashboard.py"))
    calls = []

    def predict(customers, threshold):
        calls.append(customers)
        if len(calls) > 1:
            raise client.DashboardError("A API não está disponível.")
        return pd.DataFrame([{
            "customerID": customers[0]["customerID"], "churn_probability": 0.7, "churn_prediction": 1,
        }])

    monkeypatch.setattr(client, "predict_customers", predict)
    app.run()
    app.button(key="example_0").click().run()
    assert len(app.metric) == 2
    app.button(key="example_1").click().run()
    assert not app.exception
    assert app.error[0].value == "A API não está disponível."
    assert len(app.metric) == 0
    assert len(app.json) == 0
