from pathlib import Path

import pandas as pd

from churn.schema import ChurnSchema


def carregar_dados(caminho: Path) -> pd.DataFrame:
    if not Path(caminho).exists():
        raise FileNotFoundError(
            f"dataset nao encontrado: {caminho}"
        )

    return pd.read_csv(caminho)


def validar_dados(df: pd.DataFrame) -> pd.DataFrame:
    dados = df.copy()

    # TotalCharges possui valores vazios representados
    # por espaços no dataset original.
    if "TotalCharges" in dados.columns:
        dados["TotalCharges"] = dados["TotalCharges"].replace(
            r"^\s*$",
            None,
            regex=True,
        )

    return ChurnSchema.validate(
        dados,
        lazy=True,
    )

