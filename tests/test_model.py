from churn.config import Settings
from churn.evaluate import avaliar
from churn.features import construir_features
from churn.model import load_model, save_model, train


def test_treina_e_avalia(raw_df):
    config = Settings()
    X, y = construir_features(raw_df, config.target, config.id_column)
    model = train(X, y, config)
    metricas = avaliar(model, X, y)
    assert set(metricas) == {"accuracy", "precision", "recall", "f1", "roc_auc"}
    assert all(0.0 <= v <= 1.0 for v in metricas.values())


def test_salva_e_carrega_modelo(tmp_path, raw_df):
    config = Settings()
    X, y = construir_features(raw_df, config.target, config.id_column)
    model = train(X, y, config)
    path = tmp_path / "models" / "model.pkl"
    save_model(model, path)
    assert (load_model(path).predict(X) == model.predict(X)).all()
