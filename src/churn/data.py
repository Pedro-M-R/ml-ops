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

from pandera.errors import SchemaErrors


def test_validar_dados_lazy_encontra_varios_erros(raw_df):
    quebrado = raw_df.copy()

    quebrado.loc[0, "gender"] = "Alien"
    quebrado.loc[0, "tenure"] = 500
    quebrado.loc[0, "MonthlyCharges"] = -100
    quebrado.loc[0, "Churn"] = "Talvez"

    with pytest.raises(SchemaErrors) as exc_info:
        validar_dados(quebrado)

    erros = exc_info.value.failure_cases

    print("\nERROS ENCONTRADOS:")
    print(erros)

    colunas_com_erro = set(
        erros["column"].dropna()
    )

    assert "gender" in colunas_com_erro
    assert "tenure" in colunas_com_erro
    assert "MonthlyCharges" in colunas_com_erro
    assert "Churn" in colunas_com_erro