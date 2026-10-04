# Churn: tuning, registro e deploy

Projeto de predição de churn com seleção por validação cruzada, MLflow Model Registry e API.

**Documentação atual:** [como executar em outro PC](docs/guia_execucao.md) e
[resumo para até 3 slides](docs/resumo_3_slides.md). Resultados reais:
`reports/selection.json` e `reports/comparison.csv`. Pacote transportável:
`dist/churn-portatil.zip`.

```bash
python -m pip install uv==0.12.17
python -m uv sync --locked --python 3.13
python -m uv run churn-tune --jobs 2
python -m uv run churn-ui
```

Em outro terminal, `python -m uv run churn-serve` inicia a API em
http://127.0.0.1:8000 com o modelo selecionado. Para usar o modelo do ZIP,
o retreino é opcional. O tracking atual usa `mlflow.db` (SQLite) e
`mlartifacts/`; os runs antigos em `mlruns/` foram preservados.

## Material anterior (histórico)

O restante desta página documenta os exercícios legados. Para seleção e deploy,
use o guia atual acima: `churn-tune` substitui o grid que comparava candidatos
no teste. O `dvc repro` legado ainda produz `models/model.pkl`, não o champion.
As instruções abaixo sobre tracking em `mlruns/` descrevem o backend antigo.

## Estrutura

```
src/churn/
├── data.py       # carga + validação
├── features.py   # transformações puras
├── model.py      # treino instrumentado com MLflow
├── lineage.py    # hash do DVC e commit do Git
├── experiments.py # grid de 9 runs e consulta do melhor
├── tracking.py   # destino único dos experimentos
├── evaluate.py   # métricas
└── config.py     # Pydantic settings
tests/            # pytest
data/             # dataset versionado pelo DVC
scripts/verificar_mlflow.py # verificação de ponta a ponta
dvc.yaml          # pipeline de treino
mlruns/           # tracking local (ignorado pelo Git)
pyproject.toml    # deps travadas (uv)
uv.lock
```

## Setup

```bash
python -m pip install uv  # apenas se uv ainda não estiver instalado
python -m uv sync --locked
```

Cria o `.venv`, instala as dependências travadas no `uv.lock` e o próprio pacote
em modo editável.

## Uso

Na raiz deste repositório (`ml-ops`), com `data/churn.csv` e seu ponteiro
`data/churn.csv.dvc`, rode:

```bash
python -m uv run churn-train
```

Qualquer setting pode ser sobrescrito por variável de ambiente com o prefixo
`CHURN_` ou por um arquivo `.env`:

```powershell
$env:CHURN_N_ESTIMATORS = "500"
python -m uv run churn-train
Remove-Item Env:CHURN_N_ESTIMATORS
```

O treino cria um run `rf` no experimento `churn`, com todos os parâmetros de
`Settings`, cinco métricas, tags `data_md5`, `git_commit` e `git_dirty`, modelo com
assinatura/exemplo de entrada e o encoder em `preprocessing/encoder.pkl`.
O modelo local continua em `models/model.pkl`. `train(cfg)` retorna `(model, metrics)`;
para ajustar apenas um classificador em matrizes já preparadas, use `build_model(cfg).fit(X, y)`.

A divisão é estratificada, com `random_state=42`; o encoder aprende categorias
somente no treino. O modelo recebe as features numéricas transformadas, não o CSV
bruto. Para inferência, aplique `preparar_features` e o encoder salvo antes de prever.
O treino verifica se o hash do CSV corresponde ao ponteiro DVC. Para outro dataset,
configure `CHURN_DATA_PATH` e versione também seu ponteiro `<arquivo>.dvc`.

## Grid rastreado e melhor execução

```powershell
python -m uv run python -m churn.experiments
```

Executa exatamente as nove combinações de `n_estimators=(100, 200, 500)` e
`max_depth=(None, 8, 16)`. Registra parâmetros, métricas e linhagem em cada run e
usa `search_runs`, ordenado por `roc_auc`, para imprimir o melhor desse grid.
Como no exemplo do guia, os runs do grid guardam métricas; o modelo e o encoder
são registrados pelo treino `rf`.

Para consultar todos os grids já executados:

```python
import mlflow
from churn.tracking import configure_tracking

configure_tracking()
runs = mlflow.search_runs(
    experiment_names=["churn"],
    filter_string="tags.run_type = 'grid' AND attributes.status = 'FINISHED'",
    order_by=["metrics.roc_auc DESC"],
)
if not runs.empty:
    print(runs.iloc[0][["run_id", "params.n_estimators", "params.max_depth", "metrics.roc_auc"]])
```

## Verificar se o MLflow está funcionando

```powershell
python -m uv run python scripts/verificar_mlflow.py --grid
```

O script executa um treino real, consulta seu run, confere parâmetros, métricas e
linhagem, baixa o encoder, recarrega o modelo e compara suas predições com as do
original. Com `--grid`, também executa e verifica as nove combinações.
Se tudo passar, imprime `SUCESSO: MLflow está funcionando.`; qualquer falha encerra
o comando com código diferente de zero. Sem `--grid`, verifica apenas o treino.

Para abrir a interface no PowerShell, a partir da raiz `ml-ops`:

```powershell
$env:MLFLOW_ALLOW_FILE_STORE = "true"
python -m uv run mlflow ui --backend-store-uri ./mlruns --host 127.0.0.1 --port 5000
```

Acesse http://127.0.0.1:5000 e selecione `churn`. Encerre com `Ctrl+C`.
O projeto usa uma URI absoluta para `mlruns/`, evitando criar stores ao mudar de
pasta. `MLFLOW_TRACKING_URI` pode apontar para um servidor; nesse caso, abra a UI
desse servidor. A variável `MLFLOW_ALLOW_FILE_STORE` habilita o backend de arquivos
do guia nas versões recentes. O MLflow instalado é 3.x, portanto usamos
[`name="model"`](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.sklearn.html),
conforme a nota de versão do material. As versões resolvidas estão no `uv.lock`.
O formato de serialização é explicitamente `cloudpickle`, compatível com o modelo
do projeto e com a linha 3.x do MLflow.

## Pipeline DVC

```powershell
python -m uv run dvc repro
```

O estágio `treino` executa o treino instrumentado e versiona `models/model.pkl`.
Se as dependências não mudarem, o DVC reutiliza o resultado sem criar outro run;
use `python -m uv run dvc repro --force` para refazer o treino.
O DVC está incluído nas dependências de desenvolvimento. Se o CSV estiver ausente,
use `python -m uv run dvc pull data/churn.csv.dvc` com o remote configurado.
O remote atual é local (`../../dvc-remote`); outro computador precisa ter acesso
ao dado ou configurar seu próprio remote. Para publicar os artefatos nesse remote,
execute `python -m uv run dvc push` separadamente do Git.

## Atualizar no Git (PowerShell)

```powershell
git status --short
git add .gitignore .dockerignore .dvcignore README.md pyproject.toml uv.lock docker-compose.yml dvc.yaml dvc.lock src/churn scripts/verificar_mlflow.py tests
git diff --cached --stat
git commit -m "Implementa tracking MLflow, linhagem DVC e grid de churn"
git push origin main
```

Os dados, modelos, ambiente virtual e experimentos locais não são enviados ao Git.
`git_dirty=true` identifica execuções feitas antes de consolidar as alterações em
um commit; execute o treino novamente após o commit para registrar essa revisão.

## Testes

```bash
python -m uv run pytest -q
```
