"""Seleção por CV no treino; teste final, registro e exportação do vencedor."""

import argparse
import hashlib
import importlib.metadata
import json
import tempfile
import time
from pathlib import Path

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, make_scorer, precision_score
from sklearn.model_selection import ParameterGrid, StratifiedKFold, cross_validate, train_test_split

from churn.config import PROJECT_ROOT, Settings
from churn.data import carregar_dados, validar_dados
from churn.evaluate import avaliar
from churn.model import lineage_tags
from churn.pipeline import build_pipeline
from churn.tracking import configure_tracking

SEED = 2026
REGISTERED_NAME = "churn-champion"


def candidates():
    yield "baseline", DummyClassifier(strategy="prior"), {}
    for params in ParameterGrid({"C": [0.1, 1.0, 10.0], "class_weight": [None, "balanced"]}):
        yield "logistic_regression", LogisticRegression(max_iter=2000, random_state=SEED), params
    for params in ParameterGrid({"n_estimators": [100, 200, 500], "max_depth": [None, 8, 16]}):
        yield "random_forest", RandomForestClassifier(random_state=SEED, n_jobs=1), params
    for params in ParameterGrid({"learning_rate": [0.05, 0.1], "max_leaf_nodes": [7, 15, 31]}):
        yield "hist_gradient_boosting", HistGradientBoostingClassifier(
            random_state=SEED, max_iter=150, l2_regularization=1.0
        ), params


def run_tuning(cfg=None, folds=5, jobs=2, output=None):
    cfg = cfg or Settings()
    output = Path(output or PROJECT_ROOT / "reports")
    output.mkdir(parents=True, exist_ok=True)
    tags = lineage_tags(cfg)
    frame = validar_dados(carregar_dados(cfg.data_path))
    if frame[cfg.id_column].duplicated().any():
        raise ValueError("IDs duplicados: use uma divisão por grupos antes de treinar.")
    X = frame.drop(columns=[cfg.target, cfg.id_column])
    # Assinatura homogênea para JSON e CSV em qualquer plataforma.
    for col in X.select_dtypes(include="number"):
        X[col] = X[col].astype(float)
    y = (frame[cfg.target] == cfg.positive_label).astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=SEED, stratify=y
    )
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=SEED)
    configure_tracking()
    scoring = {"roc_auc": "roc_auc", "average_precision": "average_precision",
               "accuracy": "accuracy", "precision": make_scorer(precision_score, zero_division=0),
               "recall": "recall", "f1": "f1"}
    rows, pipelines = [], {}
    source_hash = hashlib.sha256()
    for path in sorted((PROJECT_ROOT / "src/churn").glob("*.py")):
        source_hash.update(path.name.encode())
        source_hash.update(path.read_bytes())
    with mlflow.start_run(run_name="tuning-selection") as parent, tempfile.TemporaryDirectory() as code_tmp:
        # Copiar conteúdo sem atributos readonly do OneDrive: MLflow precisa limpar
        # sua cópia temporária após log_model no Windows.
        staged_code = Path(code_tmp) / "churn"
        staged_code.mkdir()
        for source in (PROJECT_ROOT / "src/churn").glob("*.py"):
            (staged_code / source.name).write_bytes(source.read_bytes())
        mlflow.set_tags({**tags, "run_type": "tuning", "source_sha256": source_hash.hexdigest()})
        mlflow.log_params({"seed": SEED, "folds": folds, "selection_metric": "cv_roc_auc_mean",
                           "test_size": 0.25, "train_rows": len(X_train), "test_rows": len(X_test),
                           "threshold": 0.5, "n_candidates": 22, "jobs": jobs})
        mlflow.log_artifacts(str(PROJECT_ROOT / "src/churn"), "source/churn")
        mlflow.log_artifact(str(PROJECT_ROOT / "uv.lock"), "source")
        split = pd.DataFrame({"row_index": frame.index, "partition": "train"})
        split.loc[X_test.index, "partition"] = "test"
        split.to_csv(output / "split.csv", index=False)
        for number, (family, estimator, params) in enumerate(candidates()):
            pipeline = build_pipeline(estimator.set_params(**params))
            with mlflow.start_run(run_name=f"{number:02d}-{family}", nested=True) as child:
                mlflow.set_tags({**tags, "run_type": "cv_candidate", "family": family})
                mlflow.log_params({"family": family, **params})
                scores = cross_validate(pipeline, X_train, y_train, cv=cv, scoring=scoring,
                                        n_jobs=jobs, error_score="raise")
                metrics = {}
                for name in scoring:
                    values = scores[f"test_{name}"]
                    metrics[f"cv_{name}_mean"] = float(np.mean(values))
                    metrics[f"cv_{name}_std"] = float(np.std(values, ddof=1))
                    for fold, value in enumerate(values):
                        mlflow.log_metric(f"fold_{name}", float(value), step=fold)
                metrics["fit_seconds_mean"] = float(np.mean(scores["fit_time"]))
                mlflow.log_metrics(metrics)
                row = {"candidate": number, "family": family, "params": json.dumps(params),
                       "run_id": child.info.run_id, **metrics}
                rows.append(row)
                pipelines[number] = pipeline
                print(f"[{number + 1}/22] {family} {params}: AUC={metrics['cv_roc_auc_mean']:.6f}", flush=True)
        ranking = pd.DataFrame(rows).sort_values(
            ["cv_roc_auc_mean", "candidate"], ascending=[False, True]
        ).reset_index(drop=True)
        ranking.to_csv(output / "comparison.csv", index=False)
        best = ranking.iloc[0]
        winner = clone(pipelines[int(best.candidate)]).fit(X_train, y_train)
        # O teste é usado somente após congelar a escolha; não altera ranking/hiperparâmetros.
        metrics = avaliar(winner, X_test, y_test)
        metrics["average_precision"] = average_precision_score(y_test, winner.predict_proba(X_test)[:, 1])
        matrix = confusion_matrix(y_test, winner.predict(X_test)).tolist()
        started = time.perf_counter()
        expected = winner.predict_proba(X_test)
        batch_seconds = time.perf_counter() - started
        mlflow.log_metrics({f"test_{k}": v for k, v in metrics.items()})
        mlflow.set_tags({"selected_family": best.family, "selected_cv_run_id": best.run_id})
        requirements = [f"{name}=={importlib.metadata.version(name)}" for name in
                        ("mlflow", "scikit-learn", "pandas", "numpy", "scipy", "cloudpickle")]
        model_args = dict(
            serialization_format="cloudpickle",
            signature=infer_signature(X_train, winner.predict_proba(X_train)),
            input_example=X_train.head(3),
            code_paths=[str(staged_code)],
            pip_requirements=requirements, pyfunc_predict_fn="predict_proba",
        )
        info = mlflow.sklearn.log_model(winner, name="champion", **model_args)
        version = mlflow.register_model(info.model_uri, REGISTERED_NAME)
        client = MlflowClient()
        registry_uri = f"models:/{REGISTERED_NAME}/{version.version}"
        loaded = mlflow.sklearn.load_model(registry_uri)
        np.testing.assert_allclose(expected, loaded.predict_proba(X_test), rtol=1e-12)
        export = PROJECT_ROOT / "deployment" / f"model-v{version.version}-{parent.info.run_id[:8]}"
        mlflow.sklearn.save_model(winner, path=str(export), **model_args)
        portable = mlflow.pyfunc.load_model(str(export))
        np.testing.assert_allclose(expected, portable.predict(X_test), rtol=1e-12)
        client.set_registered_model_alias(REGISTERED_NAME, "champion", version.version)
        client.set_model_version_tag(REGISTERED_NAME, version.version, "validation", "registry_and_export_roundtrip_passed")
        client.update_model_version(REGISTERED_NAME, version.version, description=(
            f"{best.family}; seleção por ROC-AUC CV {folds} folds={best.cv_roc_auc_mean:.6f}; "
            f"teste ROC-AUC={metrics['roc_auc']:.6f}; pipeline completo; probabilidades [No, Yes]."
        ))
        result = {
            "run_id": parent.info.run_id, "selected_cv_run_id": best.run_id,
            "family": best.family, "params": json.loads(best.params),
            "cv_roc_auc_mean": best.cv_roc_auc_mean, "cv_roc_auc_std": best.cv_roc_auc_std,
            "test_metrics": metrics, "confusion_matrix": matrix,
            "registered_name": REGISTERED_NAME, "version": version.version,
            "alias": "champion", "model_uri": registry_uri,
            "export_path": export.relative_to(PROJECT_ROOT).as_posix(),
            "train_rows": len(X_train), "test_rows": len(X_test), "total_rows": len(X),
            "positive_rows": int(y.sum()), "seed": SEED, "folds": folds,
            "threshold": 0.5, "n_candidates": len(rows), "data_md5": tags["data_md5"],
            "source_sha256": source_hash.hexdigest(), "git_commit": tags["git_commit"],
            "git_dirty": tags["git_dirty"], "test_batch_seconds": batch_seconds,
            "roundtrip_verified_rows": len(X_test),
        }
        (output / "selection.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        request = {"dataframe_split": json.loads(X_test.head(3).to_json(orient="split", index=False))}
        (output / "example_request.json").write_text(json.dumps(request, indent=2), encoding="utf-8")
        for report_name in ("split.csv", "comparison.csv", "selection.json", "example_request.json"):
            mlflow.log_artifact(str(output / report_name), "reports")
        mlflow.set_tag("registered_model_uri", registry_uri)
    print(json.dumps(result, indent=2), flush=True)
    return result


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=2, help="Processos de CV; use 1 em PCs menores.")
    args = parser.parse_args()
    run_tuning(jobs=args.jobs)


if __name__ == "__main__":
    cli()
