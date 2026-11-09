"""Entradas de hospedagem: porta da plataforma e Secrets do Streamlit Cloud."""

import json
import os
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("platform_port,extra_args,expected", [
    (None, [], 8000), ("10000", [], 10000), ("10000", ["--port", "8080"], 8080),
])
def test_serve_respects_platform_port_and_explicit_override(monkeypatch, platform_port, extra_args, expected):
    from churn.deploy import serve

    if platform_port is None:
        monkeypatch.delenv("PORT", raising=False)
    else:
        monkeypatch.setenv("PORT", platform_port)
    monkeypatch.setattr("sys.argv", ["churn-serve", *extra_args])
    calls = []
    monkeypatch.setattr("uvicorn.run", lambda app, **kwargs: calls.append(kwargs))
    serve()
    assert calls[0]["port"] == expected


@pytest.mark.parametrize("explicit_url", ["", "https://explicit.example"])
def test_cloud_entry_uses_secrets_without_replacing_explicit_environment(monkeypatch, explicit_url):
    from churn import dashboard_client

    monkeypatch.setenv("CHURN_API_URL", explicit_url)
    monkeypatch.setenv("CHURN_API_PUBLIC_URL", "")
    monkeypatch.setattr("streamlit.secrets", {
        "CHURN_API_URL": "https://churn-api.example",
        "CHURN_API_PUBLIC_URL": "https://churn-api.example",
    })
    monkeypatch.setattr(dashboard_client, "check_health", lambda: True)
    called_urls = []

    def predict(customers, threshold):
        called_urls.append(dashboard_client.api_url())
        return pd.DataFrame([{"churn_probability": 0.7, "churn_prediction": 1}])

    monkeypatch.setattr(dashboard_client, "predict_customers", predict)
    monkeypatch.setattr("churn.dashboard.predict_customers", predict)
    monkeypatch.setattr("churn.dashboard.check_health", lambda: True)
    app = AppTest.from_file(str(ROOT / "frontend/streamlit_app.py")).run(timeout=30)
    assert not app.exception
    app.button(key="example_0").click().run()
    assert not app.exception
    assert called_urls == [explicit_url or "https://churn-api.example"]
    assert os.environ["CHURN_API_PUBLIC_URL"] == "https://churn-api.example"
    assert json.loads(app.json[0].value)["predictions"][0] == {"churn_probability": 0.7, "churn_prediction": 1}
