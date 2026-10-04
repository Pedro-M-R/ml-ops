import numpy as np
from sklearn.linear_model import LogisticRegression

from churn.pipeline import build_pipeline


def test_pipeline_handles_unknown_categories_and_missing_charges(raw_df):
    features = raw_df.drop(columns=["Churn", "customerID"])
    labels = (raw_df.Churn == "Yes").astype(int)
    pipeline = build_pipeline(LogisticRegression()).fit(features, labels)
    inference = features.iloc[[0]].copy()
    inference["gender"] = "never_seen_in_training"
    inference["TotalCharges"] = " "
    result = pipeline.predict_proba(inference)
    assert result.shape == (1, 2)
    assert np.isfinite(result).all()
    np.testing.assert_allclose(result.sum(axis=1), 1)
    encoder = pipeline.named_steps["preprocess"].named_transformers_["categorical"].named_steps["encode"]
    assert "never_seen_in_training" not in encoder.categories_[0]


def test_pipeline_preserves_rows_and_uses_training_median(raw_df):
    features = raw_df.drop(columns=["Churn", "customerID"])
    pipeline = build_pipeline(LogisticRegression()).fit(features, [0, 1, 0, 1])
    imputer = pipeline.named_steps["preprocess"].named_transformers_["numeric"].named_steps["impute"]
    # TotalCharges: mediana de 29.9, 718.8 e 0; a célula vazia não entra.
    assert np.isclose(imputer.statistics_[-1], 29.9)
    assert len(pipeline.predict(features)) == len(features)
