import pytest

from churn.data import carregar_dados, validar_dados


def test_carregar_dados_arquivo_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        carregar_dados(tmp_path / "nao_existe.csv")


def test_carregar_dados(tmp_path, raw_df):
    caminho = tmp_path / "churn.csv"
    raw_df.to_csv(caminho, index=False)
    assert len(carregar_dados(caminho)) == len(raw_df)


def test_validar_dados_ok(raw_df):
    assert validar_dados(raw_df) is raw_df


def test_validar_dados_coluna_ausente(raw_df):
    with pytest.raises(ValueError, match="colunas ausentes"):
        validar_dados(raw_df.drop(columns=["Churn"]))


def test_validar_dados_vazio(raw_df):
    with pytest.raises(ValueError, match="vazio"):
        validar_dados(raw_df.iloc[0:0])
