import hashlib

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
import pytest
import yaml
from mlflow.tracking import MlflowClient

from churn.config import Settings
from churn.features import CategoricalEncoder
from churn.lineage import data_md5
from churn.model import lineage_tags, prepare_data, train


@pytest.fixture
def training_config(tmp_path, raw_df, monkeypatch):
    path = tmp_path / "churn.csv"
    pd.concat([raw_df] * 5, ignore_index=True).to_csv(path, index=False)
    pointer = {"outs": [{"md5": hashlib.md5(path.read_bytes()).hexdigest()}]}
    path.with_suffix(".csv.dvc").write_text(yaml.safe_dump(pointer), encoding="utf-8")
    previous = mlflow.get_tracking_uri()
    monkeypatch.setenv("MLFLOW_TRACKING_URI", (tmp_path / "mlruns").as_uri())
    yield Settings(data_path=path, model_path=tmp_path / "model.pkl", n_estimators=3)
    mlflow.set_tracking_uri(previous)


def test_train_registra_e_recarrega_modelo(training_config):
    model, metrics = train(training_config)
    run = MlflowClient().get_run(mlflow.last_active_run().info.run_id)
    assert run.info.status == "FINISHED"
    assert run.data.params["n_estimators"] == "3"
    assert run.data.metrics == metrics
    assert run.data.tags["data_md5"] == data_md5(
        training_config.data_path.with_suffix(".csv.dvc")
    )
    loaded = mlflow.sklearn.load_model(run.data.tags["model_uri"])
    _, x_test, _, _, _ = prepare_data(training_config)
    np.testing.assert_array_equal(loaded.predict(x_test), model.predict(x_test))
    artifacts = MlflowClient().list_artifacts(run.info.run_id, "preprocessing")
    assert any(a.path == "preprocessing/encoder.pkl" for a in artifacts)


def test_recusa_dado_diferente_do_dvc(training_config):
    training_config.data_path.write_text("alterado", encoding="utf-8")
    with pytest.raises(ValueError, match="difere do ponteiro DVC"):
        lineage_tags(training_config)


def test_encoder_nao_aprende_categorias_do_teste():
    encoder = CategoricalEncoder().fit(pd.DataFrame({"tipo": ["A", "B"]}))
    actual = encoder.transform(pd.DataFrame({"tipo": ["B", "C"]}))
    assert actual["tipo"].tolist() == [1.0, -1.0]


def test_split_reproduzivel(training_config):
    first = prepare_data(training_config)
    second = prepare_data(training_config)
    pd.testing.assert_frame_equal(first[0], second[0])
    pd.testing.assert_frame_equal(first[1], second[1])
    assert set(first[2]) == set(first[3]) == {0, 1}
