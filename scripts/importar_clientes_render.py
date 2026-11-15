"""Importa o CSV no Render Postgres; solicita as credenciais sem exibi-las."""

import argparse
import getpass
import json
import sys
from pathlib import Path

import psycopg

from churn.dashboard_client import DashboardError
from churn.database_setup import initialize_database, read_customers

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=ROOT / "frontend/data/churn.csv")
    parser.add_argument("--check-only", action="store_true", help="Valida o CSV sem conectar a nenhum banco.")
    args = parser.parse_args()
    rows = read_customers(args.csv)
    if args.check_only:
        print(f"CSV válido: {len(rows)} clientes. Nenhum banco foi acessado.")
        return
    print(f"CSV validado: {len(rows)} clientes. As próximas entradas não aparecem na tela.")
    admin_url = getpass.getpass("Cole a External Database URL do Render e pressione Enter: ").strip()
    if not admin_url.startswith(("postgresql://", "postgres://")):
        raise ValueError("Use a External Database URL completa fornecida pelo Render.")
    password = getpass.getpass("Escolha a senha de churn_reader (mínimo 20 caracteres): ")
    if password != getpass.getpass("Repita a senha de churn_reader: "):
        raise ValueError("As senhas de leitura são diferentes.")
    result = initialize_database(admin_url, password, rows)
    print(json.dumps(result, indent=2))
    print("Importação concluída. Configure a mesma senha em CHURN_DB_PASSWORD na API do Render.")


if __name__ == "__main__":
    try:
        main()
    except psycopg.Error:
        # Erros do driver podem conter usuário/host: não imprimir o DSN nem traceback.
        print("Falha no PostgreSQL. Confira a URL externa, o IP autorizado e as permissões do proprietário do banco.", file=sys.stderr)
        sys.exit(1)
    except (ValueError, OSError, DashboardError) as exc:
        print(f"Importação não concluída: {exc}", file=sys.stderr)
        sys.exit(1)
