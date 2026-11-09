"""Grid do Encontro 6: 3 números de árvores x 3 profundidades = 9 runs."""

from uuid import uuid4

import mlflow
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from churn.config import Settings, settings
from churn.evaluate import avaliar
from churn.model import lineage_tags, prepare_data
from churn.tracking import configure_tracking


def run_grid(cfg: Settings = settings) -> pd.DataFrame:
    tags = lineage_tags(cfg)
    x_train, x_test, y_train, y_test, _ = prepare_data(cfg)
    configure_tracking()
    grid_id = uuid4().hex
    for n in (100, 200, 500):
        for depth in (None, 8, 16):
            with mlflow.start_run(run_name=f"rf-n{n}-d{depth}"):
                mlflow.set_tags({**tags, "run_type": "grid", "grid_id": grid_id})
                mlflow.log_params({
                    **cfg.model_dump(), "n_estimators": n, "max_depth": depth,
                })
                model = RandomForestClassifier(
                    n_estimators=n, max_depth=depth, random_state=cfg.random_state,
                ).fit(x_train, y_train)
                metrics = avaliar(model, x_test, y_test)
                mlflow.log_metrics(metrics)
                print(f"rf-n{n}-d{depth}: roc_auc={metrics['roc_auc']:.6f}")

    runs = mlflow.search_runs(
        experiment_names=["churn"],
        filter_string=f"tags.grid_id = '{grid_id}' AND attributes.status = 'FINISHED'",
        order_by=["metrics.roc_auc DESC"],
    )
    best = runs.iloc[0]
    print("Melhor run do grid:")
    print(best[["run_id", "params.n_estimators", "params.max_depth", "metrics.roc_auc"]])
    return runs


if __name__ == "__main__":
    run_grid()
