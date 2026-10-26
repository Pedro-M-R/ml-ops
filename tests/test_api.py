"""Contratos HTTP da API, sem depender de um modelo exportado no disco."""

import json
from pathlib import Path

import mlflow.pyfunc
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from mlflow.exceptions import MlflowException

from churn.api import create_app


class StubModel:
    def __init__(self):
        self.frames = []
        self.error = None

    def predict(self, frame):
        self.frames.append(frame.copy(deep=True))
        if self.error is not None:
            raise self.error
        positive = np.resize(np.array([0.2, 0.9, 0.5]), len(frame))
        return np.column_stack((1.0 - positive, positive))


@pytest.fixture
def example():
    path = Path(__file__).resolve().parents[1] / "reports" / "example_request.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def customers(example):
    split = example["dataframe_split"]
    return [dict(zip(split["columns"], row)) for row in split["data"]]


@pytest.fixture
def model_loader(monkeypatch):
    model = StubModel()
    loaded_uris = []

    def load_model(uri):
        loaded_uris.append(uri)
        return model

    monkeypatch.setattr(mlflow.pyfunc, "load_model", load_model)
    return model, loaded_uris


@pytest.fixture
def api(model_loader):
    model, loaded_uris = model_loader
    with TestClient(create_app(model_uri="test-model")) as client:
        yield client, model, loaded_uris


def test_model_loads_once_during_startup(model_loader, customers):
    model, loaded_uris = model_loader
    application = create_app(model_uri="test-model")
    assert loaded_uris == []

    with TestClient(application) as client:
        assert loaded_uris == ["test-model"]
        for _ in range(2):
            assert client.post("/predict", json={"customers": customers}).status_code == 200
        assert loaded_uris == ["test-model"]
    assert len(model.frames) == 2


def test_startup_uses_selected_model_by_default(monkeypatch, model_loader):
    _, loaded_uris = model_loader
    selections = []

    def selected_path():
        selections.append("selected")
        return "deployment/selected-model"

    monkeypatch.setattr("churn.api.selected_path", selected_path)
    application = create_app()
    assert selections == []
    assert loaded_uris == []
    with TestClient(application) as client:
        assert client.get("/health").status_code == 200
        assert selections == ["selected"]
        assert loaded_uris == ["deployment/selected-model"]


def test_startup_fails_without_selected_model(monkeypatch, model_loader):
    _, loaded_uris = model_loader

    def missing_selection():
        raise FileNotFoundError("No selected model is available")

    monkeypatch.setattr("churn.api.selected_path", missing_selection)
    with pytest.raises(FileNotFoundError, match="No selected model"):
        with TestClient(create_app()):
            pytest.fail("The application must not start without a model")
    assert loaded_uris == []


def test_startup_propagates_model_loading_failure(monkeypatch):
    def missing_model(uri):
        raise MlflowException(f"Model artifact not found: {uri}")

    monkeypatch.setattr(mlflow.pyfunc, "load_model", missing_model)
    with pytest.raises(MlflowException, match="Model artifact not found"):
        with TestClient(create_app(model_uri="missing-model")):
            pytest.fail("The application must not start without a model")


def test_registry_model_configures_tracking_during_startup(monkeypatch, model_loader):
    _, loaded_uris = model_loader
    configured = []

    def configure_tracking():
        configured.append("configured")
        return "sqlite:///unused-test.db"

    monkeypatch.setattr("churn.tracking.configure_tracking", configure_tracking)
    application = create_app(model_uri="models:/test-churn/42")
    assert configured == []
    with TestClient(application) as client:
        assert client.get("/health").status_code == 200
        assert configured == ["configured"]
        assert loaded_uris == ["models:/test-churn/42"]


@pytest.mark.parametrize("path", ["/health", "/ping"])
def test_health(api, path):
    client, model, _ = api
    response = client.get(path)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert model.frames == []


def test_interactive_api_documentation(api):
    client, _, _ = api
    assert client.get("/docs").status_code == 200
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/predict" in response.json()["paths"]


def test_openapi_documents_route_specific_validation_errors(api):
    client, _, _ = api
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    invocations_responses = paths["/invocations"]["post"]["responses"]
    assert "400" in invocations_responses
    assert "422" not in invocations_responses
    assert "422" in paths["/predict"]["post"]["responses"]


def test_predict_probabilities_threshold_and_customer_ids(api, customers, example):
    client, model, _ = api
    customers[0]["customerID"] = "customer-001"
    customers[1]["customerID"] = None
    response = client.post("/predict", json={"customers": customers})
    assert response.status_code == 200
    result = response.json()
    assert result["threshold"] == 0.5
    predictions = result["predictions"]
    assert [p["churn_probability"] for p in predictions] == pytest.approx([0.2, 0.9, 0.5])
    assert [p["churn_prediction"] for p in predictions] == [0, 1, 1]
    assert predictions[0]["customerID"] == "customer-001"
    assert "customerID" not in predictions[1]
    assert "customerID" not in predictions[2]
    assert all(type(p["churn_prediction"]) is int for p in predictions)
    assert list(model.frames[0].columns) == example["dataframe_split"]["columns"]
    assert "customerID" not in model.frames[0]


@pytest.mark.parametrize("threshold, expected", [(0.0, [1, 1, 1]), (0.95, [0, 0, 0]), (1.0, [0, 0, 0])])
def test_predict_custom_threshold(api, customers, threshold, expected):
    client, _, _ = api
    response = client.post("/predict", json={"customers": customers, "threshold": threshold})
    assert response.status_code == 200
    assert response.json()["threshold"] == threshold
    assert [p["churn_prediction"] for p in response.json()["predictions"]] == expected


def test_predict_accepts_new_categories_and_missing_numeric_values(api, customers):
    client, model, _ = api
    customer = customers[0]
    customer["InternetService"] = "New satellite offering"
    for feature in ("SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"):
        customer[feature] = None
    response = client.post("/predict", json={"customers": [customer]})
    assert response.status_code == 200
    assert model.frames[0].iloc[0]["InternetService"] == "New satellite offering"
    assert model.frames[0][["SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"]].isna().all().all()


def test_predict_requires_every_model_feature(api, customers):
    client, model, _ = api
    for feature in customers[0]:
        customer = {name: value for name, value in customers[0].items() if name != feature}
        response = client.post("/predict", json={"customers": [customer]})
        assert response.status_code == 422, feature
    assert model.frames == []


@pytest.mark.parametrize("feature", [
    "gender", "Partner", "Dependents", "PhoneService", "MultipleLines", "InternetService",
    "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV",
    "StreamingMovies", "Contract", "PaperlessBilling", "PaymentMethod",
])
def test_predict_rejects_null_categories(api, customers, feature):
    client, model, _ = api
    customers[0][feature] = None
    assert client.post("/predict", json={"customers": customers}).status_code == 422
    assert model.frames == []


@pytest.mark.parametrize("feature, value", [
    ("SeniorCitizen", -1), ("SeniorCitizen", 2), ("SeniorCitizen", 0.5),
    ("tenure", -1), ("MonthlyCharges", -0.01), ("TotalCharges", -1),
    ("tenure", "invalid"), ("MonthlyCharges", "invalid"), ("TotalCharges", "invalid"),
])
def test_predict_rejects_invalid_numeric_features(api, customers, feature, value):
    client, model, _ = api
    customers[0][feature] = value
    assert client.post("/predict", json={"customers": customers}).status_code == 422
    assert model.frames == []


@pytest.mark.parametrize("feature", ["SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_predict_rejects_non_finite_features(api, customers, feature, value):
    client, model, _ = api
    customers[0][feature] = value
    response = client.post(
        "/predict", content=json.dumps({"customers": customers}), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert model.frames == []


@pytest.mark.parametrize("threshold", [-0.01, 1.01, None, "invalid", float("nan"), float("inf")])
def test_predict_rejects_invalid_threshold(api, customers, threshold):
    client, model, _ = api
    response = client.post(
        "/predict", content=json.dumps({"customers": customers, "threshold": threshold}),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert model.frames == []


@pytest.mark.parametrize("size", [0, 1001])
def test_predict_rejects_invalid_batch_size(api, customers, size):
    client, model, _ = api
    response = client.post("/predict", json={"customers": [customers[0]] * size})
    assert response.status_code == 422
    assert model.frames == []


@pytest.mark.parametrize("extra_location", ["request", "customer"])
def test_predict_rejects_unknown_fields(api, customers, extra_location):
    client, model, _ = api
    payload = {"customers": customers}
    if extra_location == "request":
        payload["unexpected"] = "value"
    else:
        customers[0]["unexpected"] = "value"
    assert client.post("/predict", json=payload).status_code == 422
    assert model.frames == []


def test_predict_accepts_maximum_batch(api, customers):
    client, _, _ = api
    response = client.post("/predict", json={"customers": [customers[0]] * 1000})
    assert response.status_code == 200
    assert len(response.json()["predictions"]) == 1000


def test_invocations_supports_existing_example(api, example):
    client, model, _ = api
    response = client.post("/invocations", json=example)
    assert response.status_code == 200
    np.testing.assert_allclose(response.json()["predictions"], [[0.8, 0.2], [0.1, 0.9], [0.5, 0.5]])
    split = example["dataframe_split"]
    pd.testing.assert_frame_equal(model.frames[0], pd.DataFrame(split["data"], columns=split["columns"]))


def test_invocations_supports_records(api, customers):
    client, model, _ = api
    response = client.post("/invocations", json={"dataframe_records": customers})
    assert response.status_code == 200
    np.testing.assert_allclose(response.json()["predictions"], [[0.8, 0.2], [0.1, 0.9], [0.5, 0.5]])
    pd.testing.assert_frame_equal(model.frames[0], pd.DataFrame(customers))


def test_invocations_supports_split_index(api, example):
    client, model, _ = api
    example["dataframe_split"]["index"] = ["one", "two", "three"]
    assert client.post("/invocations", json=example).status_code == 200
    assert list(model.frames[0].index) == ["one", "two", "three"]


@pytest.mark.parametrize("format_name", ["dataframe_records", "dataframe_split"])
def test_invocations_normalizes_json_integers_for_mlflow_signature(api, customers, format_name):
    client, model, _ = api
    numeric_columns = ["SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"]
    for customer in customers:
        for column in numeric_columns:
            customer[column] = int(customer[column])
    if format_name == "dataframe_records":
        payload = {format_name: customers}
    else:
        payload = {format_name: {
            "columns": list(customers[0]),
            "data": [list(customer.values()) for customer in customers],
        }}
    assert client.post("/invocations", json=payload).status_code == 200
    frame = model.frames[0]
    for column in numeric_columns:
        assert frame[column].dtype == np.dtype("float64")
        assert frame[column].tolist() == [float(customer[column]) for customer in customers]
    assert frame["gender"].tolist() == [customer["gender"] for customer in customers]


@pytest.mark.parametrize("format_name", ["dataframe_records", "dataframe_split"])
@pytest.mark.parametrize("mixed_rows", [False, True], ids=["single-row", "mixed-with-floats"])
def test_invocations_rejects_integers_too_large_for_numeric_conversion(api, customers, format_name, mixed_rows):
    client, model, _ = api
    records = customers if mixed_rows else customers[:1]
    records[0]["tenure"] = 10**400
    if format_name == "dataframe_records":
        payload = {format_name: records}
    else:
        payload = {format_name: {
            "columns": list(records[0]),
            "data": [list(customer.values()) for customer in records],
        }}
    response = client.post("/invocations", json=payload)
    assert response.status_code == 400
    assert model.frames == []


@pytest.mark.parametrize("payload", [
    {}, [], None,
    {"dataframe_records": []},
    {"dataframe_records": "invalid"},
    {"dataframe_records": [1]},
    {"dataframe_records": [{"gender": ["Male"]}]},
    {"dataframe_split": {"columns": [], "data": []}},
    {"dataframe_split": {"columns": ["gender", "gender"], "data": [["Male", "Male"]]}},
    {"dataframe_split": {"columns": ["gender"], "data": [["Male", "extra"]]}},
    {"dataframe_split": {"columns": ["gender"], "data": [["Male"]], "index": []}},
    {"dataframe_split": {"columns": ["gender"], "data": ["Male"]}},
    {"dataframe_split": {"columns": [1], "data": [["Male"]]}},
    {"dataframe_split": {"columns": ["gender"], "data": [[{"nested": "value"}]]}},
    {"dataframe_split": {"columns": ["gender"], "data": [["Male"]]}, "dataframe_records": [{"gender": "Male"}]},
])
def test_invocations_rejects_invalid_payload(api, payload):
    client, model, _ = api
    response = client.post("/invocations", json=payload)
    assert response.status_code == 400
    assert model.frames == []


@pytest.mark.parametrize("path, expected_status", [("/predict", 422), ("/invocations", 400)])
def test_malformed_json_returns_client_error(api, path, expected_status):
    client, _, _ = api
    response = client.post(path, content='{"unfinished":', headers={"Content-Type": "application/json"})
    assert response.status_code == expected_status


@pytest.mark.parametrize("format_name", ["dataframe_records", "dataframe_split"])
def test_invocations_rejects_oversized_batches(api, customers, example, format_name):
    client, model, _ = api
    if format_name == "dataframe_records":
        payload = {format_name: [customers[0]] * 1001}
    else:
        split = example[format_name]
        payload = {format_name: {"columns": split["columns"], "data": [split["data"][0]] * 1001}}
    assert client.post("/invocations", json=payload).status_code == 400
    assert model.frames == []


@pytest.mark.parametrize("error_type", [MlflowException, ValueError, TypeError])
@pytest.mark.parametrize("path", ["/predict", "/invocations"])
def test_model_schema_failures_return_bad_request(api, customers, example, error_type, path):
    client, model, _ = api
    model.error = error_type("Input is incompatible with the model signature")
    payload = {"customers": customers} if path == "/predict" else example
    assert client.post(path, json=payload).status_code == 400


@pytest.mark.parametrize("probabilities", [
    np.array([0.2, 0.9, 0.5]),
    np.array([[0.2, 0.8]]),
    np.array([[0.4, 0.2, 0.4]] * 3),
    np.array([[float("nan"), 0.8]] * 3),
    np.array([[float("inf"), 0.8]] * 3),
    np.array([[-0.1, 1.1]] * 3),
    np.array([[0.2, 0.3]] * 3),
], ids=["one-dimensional", "wrong-row-count", "wrong-column-count", "nan", "infinity", "out-of-range", "not-normalized"])
@pytest.mark.parametrize("path", ["/predict", "/invocations"])
def test_invalid_model_probabilities_return_server_error(api, customers, example, monkeypatch, probabilities, path):
    client, model, _ = api
    monkeypatch.setattr(model, "predict", lambda frame: probabilities)
    payload = {"customers": customers} if path == "/predict" else example
    assert client.post(path, json=payload).status_code == 500
