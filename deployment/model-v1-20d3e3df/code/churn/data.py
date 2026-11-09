from pathlib import Path

import pandas as pd
import pandera.pandas as pa


ChurnSchema = pa.DataFrameSchema(
    {
        "customerID": pa.Column(str, nullable=False),
        "tenure": pa.Column(
            int, pa.Check.in_range(min_value=0, max_value=72), nullable=False
        ),
        "MonthlyCharges": pa.Column(float, pa.Check.ge(0), nullable=False),
        "TotalCharges": pa.Column(float, pa.Check.ge(0), nullable=True),
        "Churn": pa.Column(str, pa.Check.isin(["Yes", "No"]), nullable=False),
    },
    coerce=True,
    strict=False,
)


def carregar_dados(caminho: Path) -> pd.DataFrame:
    if not Path(caminho).exists():
        raise FileNotFoundError(f"dataset nao encontrado: {caminho}")
    return pd.read_csv(caminho)


def validar_dados(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("dataset vazio")
    df = df.copy()
    df["TotalCharges"] = df["TotalCharges"].replace(
        r"^\s*$", float("nan"), regex=True
    )
    return ChurnSchema.validate(df, lazy=True)
