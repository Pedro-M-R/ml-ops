# Churn

Projeto-fio-condutor do curso de MLOps: predição de churn (tabular).

## Estrutura

```
src/churn/
├── data.py       # carga + validação
├── features.py   # transformações puras
├── model.py      # treino
├── evaluate.py   # métricas
└── config.py     # Pydantic settings
tests/            # pytest
data/             # dataset (versionado depois: DVC)
pyproject.toml    # deps travadas (uv)
uv.lock
```

## Setup

```bash
uv sync
```

Cria o `.venv`, instala as dependências travadas no `uv.lock` e o próprio pacote
em modo editável.

## Uso

Coloque o dataset em `data/churn.csv` e rode:

```bash
uv run churn-train
```

Qualquer setting pode ser sobrescrito por variável de ambiente com o prefixo
`CHURN_` ou por um arquivo `.env`:

```bash
CHURN_DATA_PATH=data/outro.csv CHURN_N_ESTIMATORS=500 uv run churn-train
```

## Testes

```bash
uv run pytest
```
