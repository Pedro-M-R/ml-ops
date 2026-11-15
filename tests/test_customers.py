"""Contrato da consulta de clientes e falhas sem exposição de credenciais."""

import httpx
import importlib.util
from pathlib import Path
import pandas as pd
import psycopg
import pytest
from fastapi.testclient import TestClient

from churn import customers as store, dashboard_client as dashboard
from churn.api import CustomerInput, create_app


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr("mlflow.pyfunc.load_model", lambda uri: object())
    with TestClient(create_app("test-model")) as client:
        yield client


def test_customer_routes_preserve_ids_and_do_not_return_target(api, monkeypatch):
    customer = CustomerInput(customerID="001", **dashboard.EXAMPLE_CUSTOMER)
    monkeypatch.setattr(store, "list_customers", lambda limit, offset: {"total": 1, "customers": [customer]})
    monkeypatch.setattr(store, "find_customer", lambda code: customer if code == "001" else None)
    assert api.get("/customers").json() == {"total": 1, "customers": [customer.model_dump()]}
    assert api.get("/customers/001").json()["customerID"] == "001"
    assert api.get("/customers/missing").status_code == 404
    for query in ("limit=0", "limit=1001", "offset=-1"):
        assert api.get("/customers?" + query).status_code == 422


def test_fastapi_serves_csv_when_database_is_not_configured(api, monkeypatch, tmp_path):
    path = tmp_path / "customers.csv"
    pd.DataFrame([
        {"customerID": "002", **dashboard.EXAMPLE_CUSTOMER, "Churn": "Yes"},
        {"customerID": "001", **dashboard.EXAMPLE_CUSTOMER, "TotalCharges": " ", "Churn": "No"},
    ]).to_csv(path, index=False)
    monkeypatch.delenv("CHURN_DB_HOST", raising=False)
    monkeypatch.setenv("CHURN_DATA_PATH", str(path))
    page = api.get("/customers?limit=1&offset=0").json()
    assert page["total"] == 2
    assert page["customers"][0]["customerID"] == "001"
    assert page["customers"][0]["TotalCharges"] is None
    assert "Churn" not in page["customers"][0]
    assert api.get("/customers/002").json()["customerID"] == "002"
    assert api.get("/customers/missing").status_code == 404
    path.unlink()
    assert api.get("/customers").status_code == 503


def test_database_failure_is_sanitized_and_affects_readiness(api, monkeypatch):
    monkeypatch.setenv("CHURN_DB_HOST", "postgres")

    def unavailable(*args):
        raise store.CustomerStoreUnavailable("private-password-and-host")

    monkeypatch.setattr(store, "list_customers", unavailable)
    for path in ("/customers", "/ready"):
        response = api.get(path)
        assert response.status_code == 503
        assert "private-password" not in response.text
    assert api.get("/health").status_code == 200


def test_readiness_rejects_empty_database(api, monkeypatch):
    monkeypatch.setenv("CHURN_DB_HOST", "postgres")
    monkeypatch.setattr(store, "list_customers", lambda *args: {"total": 0, "customers": []})
    assert api.get("/ready").status_code == 503


def test_query_parameters_are_bound_and_password_file_is_used(monkeypatch, tmp_path):
    path = tmp_path / "password"
    path.write_text("test-secret\n", encoding="utf-8")
    monkeypatch.setenv("CHURN_DB_PASSWORD_FILE", str(path))
    monkeypatch.setenv("CHURN_DB_HOST", "postgres")
    calls = []

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, statement, parameters):
            calls.append((statement.as_string(), parameters))
            return self

        def fetchone(self):
            return None

    def connect(**kwargs):
        assert kwargs["password"] == "test-secret"
        assert kwargs["user"] == "churn_reader"
        return Connection()

    monkeypatch.setattr(store.psycopg, "connect", connect)
    malicious = "x' OR true --"
    assert store.find_customer(malicious) is None
    assert malicious not in calls[0][0]
    assert calls[0][1] == (malicious,)


def test_connection_failure_becomes_store_unavailable(monkeypatch):
    monkeypatch.setenv("CHURN_DB_HOST", "postgres")
    monkeypatch.setenv("CHURN_DB_PASSWORD", "test-secret")
    monkeypatch.delenv("CHURN_DB_PASSWORD_FILE", raising=False)

    def fail(**kwargs):
        raise psycopg.OperationalError("private details")

    monkeypatch.setattr(store.psycopg, "connect", fail)
    with pytest.raises(store.CustomerStoreUnavailable, match="indisponível"):
        store.find_customer("001")


def test_dashboard_reads_paginated_api_without_csv(monkeypatch):
    monkeypatch.delenv("CHURN_CUSTOMER_SOURCE", raising=False)
    monkeypatch.setattr(dashboard, "BATCH_SIZE", 1)
    client_type = httpx.Client
    offsets = []

    def handler(request):
        # Reproduz o orçamento de espera necessário para a retomada observada no Render.
        if request.extensions["timeout"]["read"] < 55:
            raise httpx.ReadTimeout("API starting", request=request)
        offset = int(request.url.params["offset"])
        offsets.append(offset)
        return httpx.Response(200, json={"total": 2, "customers": [
            {"customerID": f"00{offset}", **dashboard.EXAMPLE_CUSTOMER, "TotalCharges": None},
        ]})

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(dashboard.httpx, "Client", lambda **kwargs: client_type(transport=transport, **kwargs))
    frame = dashboard.load_customer_base()
    assert frame.customerID.tolist() == ["000", "001"]
    assert offsets == [0, 1]
    assert pd.isna(frame.TotalCharges).all()


def test_customer_timeout_explains_api_startup_without_exposing_details(monkeypatch):
    monkeypatch.setenv("CHURN_CUSTOMER_SOURCE", "api")
    client_type = httpx.Client

    def unavailable(request):
        raise httpx.ReadTimeout("private service details", request=request)

    transport = httpx.MockTransport(unavailable)
    monkeypatch.setattr(dashboard.httpx, "Client", lambda **kwargs: client_type(transport=transport, **kwargs))
    with pytest.raises(dashboard.DashboardError, match="pode estar iniciando") as error:
        dashboard.load_customer_base()
    assert "private service details" not in str(error.value)


@pytest.mark.parametrize("body", [
    {"total": 10, "customers": []}, {"total": 50001, "customers": []},
    {"total": 1, "customers": [{"customerID": "001"}]},
])
def test_dashboard_rejects_incomplete_database_pages(monkeypatch, body):
    monkeypatch.setenv("CHURN_CUSTOMER_SOURCE", "api")
    client_type = httpx.Client
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    monkeypatch.setattr(dashboard.httpx, "Client", lambda **kwargs: client_type(transport=transport, **kwargs))
    with pytest.raises(dashboard.DashboardError):
        dashboard.load_customer_base()


def test_secret_generation_uses_lf_and_preserves_existing_values(monkeypatch, tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts/preparar_postgres.py"
    spec = importlib.util.spec_from_file_location("prepare_postgres", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    module.main()
    directory = tmp_path / "runtime/secrets"
    original = {path.name: path.read_bytes() for path in directory.iterdir()}
    assert len(set(original.values())) == 2
    assert all(b"\r" not in value and len(value.strip()) >= 40 for value in original.values())
    module.main()
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == original
    (directory / "db_reader_password").write_bytes(b"already-configured\r\n")
    module.main()
    assert (directory / "db_reader_password").read_bytes() == b"already-configured\n"
