# Executar o modelo em outro computador

Use **Python 3.13 de 64 bits** e internet para instalar dependências. Não precisa
de GPU. Foi verificado em Windows; caminhos e comandos também foram preparados
para Linux/macOS, mas esses sistemas não foram executados nesta entrega.
Não significa literalmente qualquer PC: sistema e arquitetura devem suportar
Python e as versões de `uv.lock`. Não copie o ambiente `.venv`.

## Usar o modelo pronto

Extraia `dist/churn-portatil.zip`, abra um terminal na pasta `churn-portatil`:

```bash
python -m pip install uv==0.12.17
python -m uv sync --locked --python 3.13
python -m uv run churn-serve
```

Em Linux/macOS use `python3` se `python` não existir. A API fica em
http://127.0.0.1:8000; mantenha o terminal aberto e use Ctrl+C para encerrar.
O comando inicia **FastAPI com Uvicorn** e carrega o modelo uma vez na
inicialização. Por padrão, usa o pipeline indicado em `reports/selection.json`.
Para alterar endereço e porta, use, por exemplo,
`python -m uv run churn-serve --host 127.0.0.1 --port 8080`.
O ZIP contém código, dependências fixadas, pipeline treinado, relatórios e,
quando criado com `--include-data`, CSV e ponteiro DVC para retreino.
O banco original do MLflow não é necessário para o modelo exportado.

## Usar a API FastAPI

A documentação interativa está em http://127.0.0.1:8000/docs (Swagger UI) e
http://127.0.0.1:8000/redoc (ReDoc), com os esquemas de entrada e saída.
`GET /health` e `GET /ping` retornam HTTP 200 e `{"status":"ok"}` quando
a aplicação está pronta.

Em outro terminal, faça um teste real da API:

```bash
python -m uv run python scripts/testar_api.py
```

Ou faça a requisição no PowerShell:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/invocations -Method Post -ContentType 'application/json' -InFile reports/example_request.json
```

Com curl:

```bash
curl -X POST http://127.0.0.1:8000/invocations -H "Content-Type: application/json" --data-binary @reports/example_request.json
```

`POST /invocations` mantém os formatos `dataframe_split` (como no exemplo) e
`dataframe_records` (lista de objetos com nomes de colunas). O lote deve ter de
1 a 1.000 linhas; em `dataframe_records`, todos os registros devem conter as
mesmas colunas. Cada linha de `predictions` retorna `[P(não churn), P(churn)]`.
Entradas inválidas retornam HTTP 400.

Para obter probabilidade e classe em campos nomeados, use `POST /predict`.
O corpo contém `customers`, uma lista de 1 a 1.000 clientes, e `threshold`,
opcional, entre 0 e 1 inclusive (padrão: `0.5`). Cada cliente contém as 19 entradas
de `reports/example_request.json`. Os campos numéricos são obrigatórios e
aceitam `null`: `SeniorCitizen` aceita apenas `0` ou `1` quando preenchido;
`tenure`, `MonthlyCharges` e `TotalCharges` aceitam números finitos não negativos.
Os demais campos são strings obrigatórias e aceitam categorias novas.
`customerID` é opcional, não participa do cálculo e só aparece na resposta
quando foi enviado com valor não nulo. Erros de validação retornam HTTP 422 com
detalhes; incompatibilidades entre a entrada e o artefato do modelo retornam
HTTP 400.

Este exemplo no PowerShell converte as linhas do JSON existente para `/predict`:

```powershell
$example = Get-Content reports/example_request.json -Raw | ConvertFrom-Json
$customers = @(foreach ($row in $example.dataframe_split.data) {
    $customer = [ordered]@{}
    for ($i = 0; $i -lt $example.dataframe_split.columns.Count; $i++) {
        $customer[$example.dataframe_split.columns[$i]] = $row[$i]
    }
    $customer
})
$body = @{ customers = $customers; threshold = 0.5 } | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri http://127.0.0.1:8000/predict -Method Post -ContentType 'application/json' -Body $body
```

A resposta contém `predictions`, com `churn_probability` e `churn_prediction`
(`0` ou `1`) para cada cliente, na ordem enviada, e o `threshold` aplicado.
A classe é `1` quando a probabilidade de churn é maior ou igual ao limiar.
Por exemplo, uma probabilidade de `0.7` com limiar `0.5` produz:

```json
{"predictions":[{"churn_probability":0.7,"churn_prediction":1}],"threshold":0.5}
```

## Prever um CSV

Para prever diretamente um CSV, sem API:

```bash
python -m uv run churn-predict --input data/churn.csv --output predictions.csv
```

O CSV deve ter as mesmas entradas do treino. `Churn` e `customerID` são opcionais
e não são preditores. O resultado contém probabilidade e classe no limiar 0,5.
O limiar é inicial: custos de campanha e de perda de clientes não foram fornecidos
para otimizar uma decisão de negócio.

## Treinar, ajustar e registrar

Com CSV e ponteiro `.dvc` na pasta `data/`:

```bash
python -m uv run churn-tune --jobs 2
python -m uv run python scripts/gerar_resumo.py
```

Use `--jobs 1` em PCs menores. São 22 candidatos: baseline, 6 configurações de
Regressão Logística, 9 de Random Forest e 6 de HistGradientBoosting. Cada candidato
usa 5 folds estratificados: 110 ajustes, mais um ajuste final do vencedor.
Seed 2026. A seleção usa a maior ROC-AUC média de CV nos 75% de treino.
Empates exatos seguem a ordem fixa dos candidatos. Os 25% de teste são usados
apenas depois da escolha e não orientam a busca ou o limiar.

O pipeline inclui conversão numérica, imputação por mediana/moda, padronização
e one-hot. Tudo que aprende é ajustado dentro de cada fold. ID e alvo ficam fora
das entradas. O modelo exportado é o mesmo avaliado no teste: não é reajustado
nos 100% depois da avaliação. A base já tinha sido usada nos exercícios antigos;
o teste reservado nesta execução não substitui uma validação externa futura.

No MLflow são salvos parâmetros, métricas por fold, médias/desvios, tempos,
hash DVC, commit/estado Git, hash e cópia do código, lock, assinatura e exemplo.
`reports/comparison.csv` é o ranking; `reports/selection.json` identifica o vencedor;
`reports/split.csv` registra a divisão. O pipeline fica em `deployment/`.
O Model Registry recebe uma versão de `churn-champion` e o alias `champion`
após confirmar que o modelo registrado e o exportado reproduzem as previsões.
Cada execução concluída atualiza esse alias local. O resultado vale para os
candidatos e dados avaliados, sem afirmar que é o melhor modelo universal.

## Abrir o MLflow

```bash
python -m uv run churn-ui
```

Abra http://127.0.0.1:5000, experimento `churn`. Em Models, procure
`churn-champion` e `champion`. O backend é SQLite (`mlflow.db`), com artefatos
em `mlartifacts/`. `MLFLOW_TRACKING_URI` permite usar um servidor configurado.

Para servir pelo registry no computador onde ele está disponível:

```bash
python -m uv run churn-serve --model models:/churn-champion@champion
```

Os runs antigos em `mlruns/` foram preservados, sem migração. Para consultá-los,
em PowerShell:

```powershell
$env:MLFLOW_ALLOW_FILE_STORE = 'true'
python -m uv run mlflow ui --backend-store-uri ./mlruns --host 127.0.0.1 --port 5001
```

## Docker

Com Docker Engine/Desktop em execução e o modelo exportado presente:

```bash
docker compose up --build api
```

A imagem inclui o modelo e expõe a API na porta 8000. Usa Python 3.13 e `uv.lock`.
O serviço Docker estava desligado nesta máquina: build e execução em contêiner
**não foram validados**. A rota Python é a rota de validação desta entrega.
Não houve publicação em nuvem nem exposição pública da API.

Para retreinar em Docker:

```bash
docker compose --profile treino run --rm treino
```

Os dados devem estar em `data/`. O banco do contêiner fica em `runtime/mlflow.db`.
Depois, reconstrua a imagem da API para incorporar o modelo novo.

## Dados, DVC e comandos legados

O remote DVC existente (`../../dvc-remote`) é local e não estará automaticamente
disponível em outro computador. O ZIP com dados permite retreino sem esse remote.
Se usar só um clone Git, obtenha o CSV pelo remote ou copie CSV e ponteiro `.dvc`.
O treino verifica se o hash do CSV corresponde ao ponteiro antes de começar.

`churn-train`, `python -m churn.experiments`, `scripts/verificar_mlflow.py` e
`dvc repro` permanecem para os exercícios antigos. O grid legado compara
candidatos no teste: não o use para selecionar o deploy. `dvc repro` ainda gera
`models/model.pkl`; o fluxo atual de seleção/registro é `churn-tune`.

## Testes e pacote

A atualização FastAPI foi validada com **132 testes aprovados** e requisições
HTTP reais: saúde, documentação, os dois formatos de `/invocations`, `/predict`
com limiares 0,5 e 0,9 e rejeição de entradas inválidas. As probabilidades dos
três clientes de exemplo coincidiram com as do pipeline exportado. O relatório
atual está em `reports/api_verification.json`.

Antes da migração, um ambiente novo instalado a partir do lock, em outra pasta,
reproduziu exatamente as 7.043 previsões; essa verificação histórica está em
`reports/verification.json`. Para executar a suíte atual e atualizar o pacote:

```bash
python -m uv run pytest -q
python -m uv run python scripts/empacotar.py --include-data
```

O ZIP fica em `dist/churn-portatil.zip`. Não inclui `.venv` nem o banco com caminhos
locais absolutos; para inferência basta o pipeline. Retreinar cria um novo
histórico MLflow local e registra a nova versão.

## Fontes técnicas

- [FastAPI: inicialização e encerramento com lifespan](https://fastapi.tiangolo.com/advanced/events/)
- [MLflow: Model Registry e aliases](https://www.mlflow.org/docs/latest/ml/model-registry/workflow/)
- [MLflow: pipelines sklearn e dependências](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.sklearn.html)
- [Scikit-learn: validação cruzada e teste](https://scikit-learn.org/stable/modules/cross_validation.html)
