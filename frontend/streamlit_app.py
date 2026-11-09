"""Entrada para Streamlit Community Cloud, sem instalar as dependências da API."""

import os
import sys
from pathlib import Path

import streamlit as st

# Community Cloud executa na raiz do repositório, sem instalar o pacote churn.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from churn.dashboard import main


def configure_api():
    # Carrega os Secrets antes da primeira consulta HTTP e respeita env explícito.
    try:
        for key in ("CHURN_API_URL", "CHURN_API_PUBLIC_URL"):
            if not os.environ.get(key) and key in st.secrets:
                os.environ[key] = str(st.secrets[key])
    except FileNotFoundError:
        pass  # Execução local sem secrets.toml usa CHURN_API_URL ou localhost.


if __name__ == "__main__":
    configure_api()
    main()
