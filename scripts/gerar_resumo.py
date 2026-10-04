"""Resumo de três slides, sempre derivado dos resultados reais da execução."""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NAMES = {"logistic_regression": "Regressão Logística", "random_forest": "Random Forest",
         "hist_gradient_boosting": "HistGradientBoosting", "baseline": "Referência simples"}


def fmt(value, digits=0):
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def main():
    result = json.loads((ROOT / "reports/selection.json").read_text(encoding="utf-8"))
    ranking = pd.read_csv(ROOT / "reports/comparison.csv")
    families = ranking.groupby("family", sort=False).head(1)
    table = "\n".join(f"| {NAMES[row.family]} | {fmt(row.cv_roc_auc_mean, 5)} |"
                      for row in families.itertuples())
    metrics = result["test_metrics"]
    winner = NAMES[result["family"]]
    gap = ranking.iloc[0].cv_roc_auc_mean - ranking.iloc[1].cv_roc_auc_mean
    reason = "Teve a maior ROC-AUC média entre as configurações testadas."
    if result["family"] == "logistic_regression":
        reason += " A simplicidade e a interpretação dos coeficientes reforçam a escolha."
    parameters = json.dumps(result["params"], ensure_ascii=False)
    if result["family"] == "logistic_regression":
        parameters = f"C={fmt(result['params']['C'], 1)}, regularização L2, class_weight={result['params']['class_weight']}"
    comparison = (f"A vantagem para o segundo colocado foi de apenas **{fmt(gap, 5)}**: diferença pequena, sem evidência de superioridade estatística."
                  if gap < 0.001 else f"Vantagem de **{fmt(gap, 5)}** sobre o segundo colocado; não foi realizado teste de significância.")
    text = f"""# Slide 1 — Do MLflow ao ajuste dos modelos

- Base: **{fmt(result['total_rows'])} clientes**; divisão estratificada em {fmt(result['train_rows'])} para treino e {fmt(result['test_rows'])} para teste.
- **21 configurações + 1 referência**, comparadas com validação cruzada de 5 partes: 110 ajustes.
- MLflow registrou parâmetros, métricas, versão dos dados, código e artefatos de cada experimento.
- Pré-processamento dentro de cada fold; escolha pela **ROC-AUC média**, sem usar o teste para ajustar os candidatos.

# Slide 2 — Melhor modelo e motivo da escolha

| Melhor configuração de cada família | ROC-AUC na validação cruzada |
|---|---:|
{table}

- Selecionado: **{winner}**, parâmetros `{parameters}`.
- {reason}
- {comparison}
- No teste: **ROC-AUC {fmt(metrics['roc_auc'], 4)}**, acurácia **{fmt(metrics['accuracy'] * 100, 1)}%**, precisão **{fmt(metrics['precision'] * 100, 1)}%**, recall **{fmt(metrics['recall'] * 100, 1)}%** e F1 **{fmt(metrics['f1'] * 100, 1)}%**.

# Slide 3 — Registro, deploy e uso em outro PC

- Pipeline completo registrado como **`{result['registered_name']}`**, versão **{result['version']}**, alias **`champion`**.
- Modelo original, versão registrada e exportação reproduziram as probabilidades dos **{fmt(result['roundtrip_verified_rows'])} clientes de teste**.
- API local testada em `http://127.0.0.1:8000`; pacote transportável com código, dependências fixadas e modelo.
- Em outro PC: Python 3.13 → `python -m uv sync --locked` → `python -m uv run churn-serve` (instalar `uv` antes).
- Limites: validado em Windows; Docker preparado, sem teste de execução. Limiar 0,5; custos da campanha e validação em novos clientes ainda precisam ser definidos antes do uso operacional.
"""
    destination = ROOT / "docs/resumo_3_slides.md"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
