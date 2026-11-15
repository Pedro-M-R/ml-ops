"""Validação antes da carga: IDs, valores ausentes e senha de leitura."""

import pandas as pd
import pytest

from churn.dashboard_client import EXAMPLE_CUSTOMER
from churn.database_setup import initialize_database, read_customers


def test_seed_preserves_text_id_and_missing_numbers_and_removes_target(tmp_path):
    path = tmp_path / "seed.csv"
    pd.DataFrame([{"customerID": "001", **EXAMPLE_CUSTOMER, "TotalCharges": " ", "Churn": "Yes"}]).to_csv(path, index=False)
    row = read_customers(path)[0]
    assert row["customerID"] == "001"
    assert row["TotalCharges"] is None
    assert "Churn" not in row


@pytest.mark.parametrize("ids", [[""], ["001", "001"], ["ABC", "abc"]])
def test_seed_rejects_blank_or_duplicate_ids(tmp_path, ids):
    path = tmp_path / "seed.csv"
    pd.DataFrame([{"customerID": code, **EXAMPLE_CUSTOMER} for code in ids]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="vazio ou duplicado"):
        read_customers(path)


def test_seed_rejects_short_password_before_connecting(monkeypatch):
    monkeypatch.setattr("churn.database_setup.psycopg.connect", lambda *args, **kwargs: pytest.fail("Não deveria conectar"))
    with pytest.raises(ValueError, match="20 caracteres"):
        initialize_database("postgresql://unused", "short", [{"customerID": "001"}])
