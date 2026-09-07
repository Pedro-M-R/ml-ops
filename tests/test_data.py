import pytest
from pandera.errors import SchemaErrors

from churn.data import carregar_dados, validar_dados


def test_carregar_dados_arquivo_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        carregar_dados(tmp_path / "nao_existe.csv")


def test_carregar_dados(tmp_path, raw_df):
    caminho = tmp_path / "churn.csv"
    raw_df.to_csv(caminho, index=False)
    assert len(carregar_dados(caminho)) == len(raw_df)


def test_validar_dados_ok(raw_df):
    validado = validar_dados(raw_df)
    assert validado["TotalCharges"].isna().sum() == 1
    assert validado["Churn"].tolist() == ["No", "Yes", "No", "Yes"]


def test_validar_dados_coluna_ausente(raw_df):
    with pytest.raises(SchemaErrors, match="column 'Churn'"):
        validar_dados(raw_df.drop(columns=["Churn"]))


def test_validar_dados_vazio(raw_df):
    with pytest.raises(ValueError, match="vazio"):
        validar_dados(raw_df.iloc[0:0])


def test_validar_dados_captura_adulteracoes_com_lazy(raw_df):
    adulterado = raw_df.copy()
    adulterado.loc[0, "tenure"] = 999
    adulterado.loc[1, "Churn"] = "Maybe"

    with pytest.raises(SchemaErrors) as erro:
        validar_dados(adulterado)

    mensagem = str(erro.value)
    assert "tenure" in mensagem
    assert "Churn" in mensagem
