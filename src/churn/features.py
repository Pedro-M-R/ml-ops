import pandas as pd

PREENCHIMENTO_TOTAL_CHARGES = 2200.0
DIVISORES_ESCALA = {
    "MonthlyCharges": 118.0,
    "TotalCharges": 8600.0,
    "tenure": 72.0,
}


def remover_id(df: pd.DataFrame, coluna_id: str) -> pd.DataFrame:
    return df.drop(columns=[coluna_id], errors="ignore")


def limpar_total_charges(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    df["TotalCharges"] = df["TotalCharges"].fillna(PREENCHIMENTO_TOTAL_CHARGES)
    return df


def escalar_numericas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for coluna, divisor in DIVISORES_ESCALA.items():
        df[coluna] = df[coluna] / divisor
    return df


def adicionar_gasto_por_mes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["gasto_por_mes"] = df["TotalCharges"] / (df["tenure"] + 1)
    return df


def codificar_categoricas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for coluna in df.select_dtypes(include="object").columns:
        df[coluna] = df[coluna].astype("category").cat.codes
    return df


def construir_features(
    df: pd.DataFrame, alvo: str, coluna_id: str
) -> tuple[pd.DataFrame, pd.Series]:
    df = remover_id(df, coluna_id)
    df = limpar_total_charges(df)
    df = adicionar_gasto_por_mes(df)
    df = df.dropna()
    df = codificar_categoricas(df)
    return escalar_numericas(df.drop(columns=[alvo])), df[alvo]
