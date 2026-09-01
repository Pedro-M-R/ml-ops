from pathlib import Path

import pandas as pd

COLUNAS_OBRIGATORIAS = [
    "customerID",
    "tenure",
    "MonthlyCharges",
    "TotalCharges",
    "Churn",
]


def carregar_dados(caminho: Path) -> pd.DataFrame:
    if not Path(caminho).exists():
        raise FileNotFoundError(f"dataset nao encontrado: {caminho}")
    return pd.read_csv(caminho)


def validar_dados(df: pd.DataFrame) -> pd.DataFrame:
    ausentes = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if ausentes:
        raise ValueError(f"colunas ausentes: {ausentes}")
    if df.empty:
        raise ValueError("dataset vazio")
    return df
