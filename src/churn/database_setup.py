"""Carga inicial do PostgreSQL gerenciado, sem depender do entrypoint Docker."""

from pathlib import Path

import pandas as pd
import psycopg
from psycopg import sql

from churn.dashboard_client import EXAMPLE_CUSTOMER, NUMERIC_COLUMNS, customers_from_frame

COLUMNS = ("customerID", *EXAMPLE_CUSTOMER)
READER = "churn_reader"


def read_customers(csv_path: Path) -> list[dict]:
    frame = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if "customerID" not in frame:
        raise ValueError("CSV sem customerID.")
    rows = customers_from_frame(frame)
    ids = [str(row.get("customerID") or "").casefold() for row in rows]
    if not all(ids) or len(set(ids)) != len(ids):
        raise ValueError("customerID vazio ou duplicado.")
    return rows


def initialize_database(admin_url: str, reader_password: str, rows: list[dict], *, sslmode="require") -> dict:
    if len(reader_password) < 20 or reader_password != reader_password.strip():
        raise ValueError("Use uma senha de leitura com pelo menos 20 caracteres, sem espaços nas extremidades.")
    if not rows:
        raise ValueError("A carteira está vazia.")
    identifiers = sql.SQL(", ").join(map(sql.Identifier, COLUMNS))
    definitions = []
    for name in COLUMNS:
        kind = "integer" if name == "SeniorCitizen" else "double precision" if name in NUMERIC_COLUMNS else "text"
        definitions.append(sql.SQL("{} {}").format(sql.Identifier(name), sql.SQL(kind)))
    with psycopg.connect(admin_url, sslmode=sslmode, connect_timeout=15) as conn:
        conn.execute("SET LOCAL statement_timeout = '30s'")
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('churn-customer-import'))")
        current_user = conn.execute("SELECT current_user").fetchone()[0]
        if current_user == READER:
            raise ValueError("A importação precisa do usuário proprietário do banco, não do churn_reader.")
        conn.execute(sql.SQL('CREATE TABLE IF NOT EXISTS public.customers ({}, PRIMARY KEY ("customerID"), '
                             'CHECK ("customerID" <> \'\'), CHECK ("SeniorCitizen" IN (0, 1)), '
                             'CHECK (tenure >= 0 AND "MonthlyCharges" >= 0 AND "TotalCharges" >= 0))')
                     .format(sql.SQL(", ").join(definitions)))
        conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS customers_normalized_id ON public.customers (lower("customerID"))')
        before = conn.execute("SELECT count(*) FROM public.customers").fetchone()[0]
        conn.execute("CREATE TEMP TABLE customer_import (LIKE public.customers) ON COMMIT DROP")
        with conn.cursor().copy(sql.SQL("COPY customer_import ({}) FROM STDIN").format(identifiers)) as copy:
            for row in rows:
                copy.write_row([row[name] for name in COLUMNS])
        conn.execute(sql.SQL('INSERT INTO public.customers ({0}) SELECT {0} FROM customer_import '
                             'ON CONFLICT ("customerID") DO NOTHING').format(identifiers))
        total = conn.execute("SELECT count(*) FROM public.customers").fetchone()[0]
        if conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (READER,)).fetchone() is None:
            conn.execute(sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(READER)))
        # Executar novamente atualiza a senha de leitura escolhida, sem alterar registros existentes.
        conn.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(sql.Identifier(READER), sql.Literal(reader_password)))
        conn.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        conn.execute("REVOKE ALL ON public.customers FROM PUBLIC")
        conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(READER)))
        conn.execute(sql.SQL("GRANT SELECT ON public.customers TO {}").format(sql.Identifier(READER)))
        conn.execute(sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(sql.Identifier(READER)))
    return {"customers": total, "inserted": total - before, "reader": READER}
