"""Pipeline autocontido: entradas brutas, imputação, one-hot e classificador."""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


class RawFeatures(TransformerMixin, BaseEstimator):
    def fit(self, X, y=None):
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        return self

    def transform(self, X):
        frame = X.loc[:, self.feature_names_in_].copy()
        for column in ("tenure", "SeniorCitizen", "MonthlyCharges", "TotalCharges"):
            if column in frame:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame


def build_pipeline(estimator):
    numeric = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ])
    categorical = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent")),
        ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    return Pipeline([
        ("raw", RawFeatures()),
        ("preprocess", ColumnTransformer([
            ("numeric", numeric, make_column_selector(dtype_include=np.number)),
            ("categorical", categorical, make_column_selector(dtype_exclude=np.number)),
        ])),
        ("classifier", estimator),
    ])
