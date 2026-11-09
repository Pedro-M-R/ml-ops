import pandas as pd
from sklearn.preprocessing import OrdinalEncoder

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


def preparar_features(
    df: pd.DataFrame, alvo: str, coluna_id: str, positive_label: str = "Yes",
) -> tuple[pd.DataFrame, pd.Series]:
    """Transformações determinísticas; categorias são aprendidas após o split."""
    df = remover_id(df, coluna_id)
    df = adicionar_gasto_por_mes(limpar_total_charges(df)).dropna()
    return (
        escalar_numericas(df.drop(columns=[alvo])),
        (df[alvo] == positive_label).astype(int),
    )


class CategoricalEncoder:
    """Aprende categorias só no treino; valores desconhecidos viram -1."""

    def fit(self, frame: pd.DataFrame) -> "CategoricalEncoder":
        self.columns_ = frame.columns.tolist()
        self.categorical_ = frame.select_dtypes(
            include=["object", "string", "category"]
        ).columns.tolist()
        self.encoder_ = OrdinalEncoder(
            handle_unknown="use_encoded_value", unknown_value=-1,
        )
        if self.categorical_:
            self.encoder_.fit(frame[self.categorical_])
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        result = frame.loc[:, self.columns_].copy()
        if self.categorical_:
            result[self.categorical_] = self.encoder_.transform(result[self.categorical_])
        return result.astype(float)
