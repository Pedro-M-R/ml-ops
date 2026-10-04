# Slide 1 — Do MLflow ao ajuste dos modelos

- Base: **7.043 clientes**; divisão estratificada em 5.282 para treino e 1.761 para teste.
- **21 configurações + 1 referência**, comparadas com validação cruzada de 5 partes: 110 ajustes.
- MLflow registrou parâmetros, métricas, versão dos dados, código e artefatos de cada experimento.
- Pré-processamento dentro de cada fold; escolha pela **ROC-AUC média**, sem usar o teste para ajustar os candidatos.

# Slide 2 — Melhor modelo e motivo da escolha

| Melhor configuração de cada família | ROC-AUC na validação cruzada |
|---|---:|
| Regressão Logística | 0,82654 |
| HistGradientBoosting | 0,82649 |
| Random Forest | 0,82052 |
| Referência simples | 0,50000 |

- Selecionado: **Regressão Logística**, parâmetros `C=0,1, regularização L2, class_weight=None`.
- Teve a maior ROC-AUC média entre as configurações testadas. A simplicidade e a interpretação dos coeficientes reforçam a escolha.
- A vantagem para o segundo colocado foi de apenas **0,00006**: diferença pequena, sem evidência de superioridade estatística.
- No teste: **ROC-AUC 0,8467**, acurácia **77,9%**, precisão **70,3%**, recall **55,7%** e F1 **62,1%**.

# Slide 3 — Registro, deploy e uso em outro PC

- Pipeline completo registrado como **`churn-champion`**, versão **1**, alias **`champion`**.
- Modelo original, versão registrada e exportação reproduziram as probabilidades dos **1.761 clientes de teste**.
- API local testada em `http://127.0.0.1:8000`; pacote transportável com código, dependências fixadas e modelo.
- Em outro PC: Python 3.13 → `python -m uv sync --locked` → `python -m uv run churn-serve` (instalar `uv` antes).
- Limites: validado em Windows; Docker preparado, sem teste de execução. Limiar 0,5; custos da campanha e validação em novos clientes ainda precisam ser definidos antes do uso operacional.
