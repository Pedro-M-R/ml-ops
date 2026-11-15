"""Verifica o caminho PostgreSQL -> API -> previsão dentro do contêiner da API."""

import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd
import psycopg

from churn.customers import connection
from churn.dashboard_client import customers_from_frame


def request(path, body=None):
    payload = json.dumps(body).encode() if body is not None else None
    req = Request("http://127.0.0.1:8000" + path, data=payload,
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=30) as response:
        return json.load(response)


def main():
    request("/ready")
    root = Path(__file__).resolve().parents[1]
    csv_customers = customers_from_frame(pd.read_csv(root / "frontend/data/churn.csv", dtype=str))
    expected = sorted(csv_customers, key=lambda row: row["customerID"])
    actual = []
    while len(actual) < len(expected):
        page = request(f"/customers?limit=1000&offset={len(actual)}")
        assert page["total"] == len(expected), "Contagem diverge do CSV"
        assert page["customers"], "Página vazia antes do fim"
        actual.extend(page["customers"])
    assert actual == expected, "Registros do banco divergem do CSV"
    for start in range(0, len(actual), 1000):
        batch = actual[start:start + 1000]
        from_db = request("/predict", {"customers": batch})
        from_csv = request("/predict", {"customers": expected[start:start + 1000]})
        assert from_db == from_csv, "Previsões divergentes"
    code = actual[0]["customerID"]
    assert request("/customers/" + quote(code.lower())) == actual[0]
    with connection() as conn:
        # Desliga o padrão read-only para testar também a permissão SQL real.
        conn.execute("SET TRANSACTION READ WRITE")
        try:
            conn.execute("DELETE FROM public.customers WHERE false")
        except psycopg.errors.InsufficientPrivilege:
            conn.rollback()
        else:
            conn.rollback()
            raise AssertionError("O usuário da API conseguiu escrever na tabela")
    print(json.dumps({"status": "ok", "customers": len(actual),
                      "predictions_match_csv": True, "reader_cannot_write": True}, indent=2))


if __name__ == "__main__":
    main()
