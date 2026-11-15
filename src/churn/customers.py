"""Consulta somente de leitura à carteira armazenada no PostgreSQL."""

import os
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from threading import Lock

import psycopg
import pandas as pd
from psycopg import sql
from psycopg.rows import dict_row

class CustomerStoreUnavailable(Exception):
    pass


_csv_lock = Lock()


@lru_cache(maxsize=1)
def _read_csv_dataset(path: Path, mtime_ns: int, size: int):
    """Prepara o CSV uma vez; modificação ou substituição do arquivo invalida a cópia."""
    from churn.api import CustomerInput
    from churn.dashboard_client import customers_from_frame

    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig", nrows=50_001)
    rows = customers_from_frame(frame)
    ids = [str(row.get("customerID") or "").casefold() for row in rows]
    if not all(ids) or len(set(ids)) != len(ids):
        raise ValueError("Identificadores inválidos.")
    customers = tuple(sorted((CustomerInput.model_validate(row) for row in rows), key=lambda row: row.customerID))
    return customers, {row.customerID.casefold(): row for row in customers}


def _csv_dataset():
    from churn.config import PROJECT_ROOT
    from churn.dashboard_client import DashboardError

    path = Path(os.environ.get("CHURN_DATA_PATH") or PROJECT_ROOT / "frontend/data/churn.csv").resolve()
    try:
        stamp = path.stat()
        # Evita preparar o mesmo CSV em paralelo na primeira requisição.
        with _csv_lock:
            return _read_csv_dataset(path, stamp.st_mtime_ns, stamp.st_size)
    except (OSError, ValueError, DashboardError) as exc:
        raise CustomerStoreUnavailable("Base de clientes indisponível.") from exc


@contextmanager
def connection():
    password_file = os.environ.get("CHURN_DB_PASSWORD_FILE")
    try:
        password = (Path(password_file).read_text(encoding="utf-8").strip()
                    if password_file else os.environ.get("CHURN_DB_PASSWORD"))
        if not os.environ.get("CHURN_DB_HOST") or not password:
            raise CustomerStoreUnavailable("Banco de clientes não configurado.")
        with psycopg.connect(
            host=os.environ["CHURN_DB_HOST"],
            port=int(os.environ.get("CHURN_DB_PORT", "5432")),
            dbname=os.environ.get("CHURN_DB_NAME", "churn"),
            user=os.environ.get("CHURN_DB_USER", "churn_reader"),
            password=password, connect_timeout=5, row_factory=dict_row,
            sslmode=os.environ.get("CHURN_DB_SSLMODE", "prefer"),
            options="-c default_transaction_read_only=on -c statement_timeout=5000",
        ) as conn:
            yield conn
    except (psycopg.Error, OSError, ValueError) as exc:
        raise CustomerStoreUnavailable("Banco de clientes indisponível.") from exc


def _columns():
    from churn.api import CustomerInput

    return sql.SQL(", ").join(sql.Identifier(name) for name in CustomerInput.model_fields)


def find_customer(customer_id: str):
    from churn.api import CustomerInput

    if not os.environ.get("CHURN_DB_HOST"):
        _, by_id = _csv_dataset()
        return by_id.get(customer_id.strip().casefold())
    with connection() as conn:
        row = conn.execute(
            sql.SQL('SELECT {} FROM public.customers WHERE lower("customerID") = lower(%s)').format(_columns()),
            (customer_id.strip(),),
        ).fetchone()
    return CustomerInput.model_validate(row) if row is not None else None


def list_customers(limit: int, offset: int):
    from churn.api import CustomerInput

    if not os.environ.get("CHURN_DB_HOST"):
        rows, _ = _csv_dataset()
        return {"total": len(rows), "customers": rows[offset:offset + limit]}
    with connection() as conn:
        # Uma transação/snapshot mantém contagem e página coerentes.
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        total = conn.execute("SELECT count(*) AS total FROM public.customers").fetchone()["total"]
        rows = conn.execute(
            sql.SQL('SELECT {} FROM public.customers ORDER BY "customerID" LIMIT %s OFFSET %s').format(_columns()),
            (limit, offset),
        ).fetchall()
    return {"total": total, "customers": [CustomerInput.model_validate(row) for row in rows]}
