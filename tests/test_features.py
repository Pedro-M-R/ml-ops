import pandas as pd

from churn.features import (
    DIVISORES_ESCALA,
    PREENCHIMENTO_TOTAL_CHARGES,
    adicionar_gasto_por_mes,
    codificar_categoricas,
    construir_features,
    escalar_numericas,
    limpar_total_charges,
    remover_id,
)


def test_remover_id(raw_df):
    assert "customerID" not in remover_id(raw_df, "customerID").columns


def test_limpar_total_charges_converte_e_preenche(raw_df):
    out = limpar_total_charges(raw_df)
    assert pd.api.types.is_numeric_dtype(out["TotalCharges"])
    assert out["TotalCharges"].notna().all()


def test_limpar_total_charges_usa_constante_do_original(raw_df):
    out = limpar_total_charges(raw_df)
    assert out["TotalCharges"].iloc[2] == PREENCHIMENTO_TOTAL_CHARGES


def test_escalar_numericas(raw_df):
    limpo = limpar_total_charges(raw_df)
    out = escalar_numericas(limpo)
    for coluna, divisor in DIVISORES_ESCALA.items():
        assert out[coluna].iloc[1] == limpo[coluna].iloc[1] / divisor


def test_adicionar_gasto_por_mes_nao_divide_por_zero(raw_df):
    out = adicionar_gasto_por_mes(limpar_total_charges(raw_df))
    assert out["gasto_por_mes"].iloc[3] == 0.0


def test_codificar_categoricas(raw_df):
    out = codificar_categoricas(raw_df)
    assert out.select_dtypes(include="object").empty


def test_transformacoes_nao_mutam_entrada(raw_df):
    antes = raw_df.copy()
    limpar_total_charges(raw_df)
    adicionar_gasto_por_mes(limpar_total_charges(raw_df))
    codificar_categoricas(raw_df)
    pd.testing.assert_frame_equal(raw_df, antes)


def test_construir_features(raw_df):
    X, y = construir_features(raw_df, alvo="Churn", coluna_id="customerID")
    assert "Churn" not in X.columns
    assert "customerID" not in X.columns
    assert "gasto_por_mes" in X.columns
    assert len(X) == len(y) == len(raw_df)
