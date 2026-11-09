# Publicar a API no Render e a tela no Streamlit Cloud

Esta opção usa o repositório `https://github.com/Pedro-M-R/ml-ops` na branch
`main`. A FastAPI e o modelo ficam no Render; o Streamlit Community Cloud
serve a tela e consulta a API por HTTPS. Não depende da conta AWS nem dos
servidores em execução no seu computador.

Os arquivos de publicação já estão preparados:

| Arquivo | Função |
| --- | --- |
| `render.yaml` | Cria o serviço Docker `churn-api`, plano Free, com health check `/health`. |
| `Dockerfile` | Instala o projeto com `uv.lock` e copia o modelo treinado. |
| `frontend/streamlit_app.py` | Entrada da tela no Streamlit Cloud. |
| `frontend/requirements.txt` | Instala só Streamlit, pandas e httpx para a tela. |
| `frontend/data/churn.csv` | Cópia da sua base existente para escolher clientes no site, sem reenviar CSV. |
| `.streamlit/secrets.example.toml` | Exemplo de configuração da URL da API. |

## 1. Enviar o projeto atualizado ao GitHub

Abra um terminal livre do PowerShell e entre na pasta correta:

```powershell
cd "C:\Users\Pedro\OneDrive\Área de Trabalho\trabalhojose\ml-ops"
git remote -v
git branch --show-current
git status --short
```

O remote deve apontar para `Pedro-M-R/ml-ops` e a branch deve ser `main`.
Revise os arquivos mostrados por `git status`. O modelo selecionado agora aparece
em `deployment/model-v1-20d3e3df/`; é necessário enviá-lo para o Render poder
construir a imagem. Outros modelos, `.venv`, logs, bancos MLflow e os arquivos
de credenciais locais continuam ignorados. A base original em `data/churn.csv`
é gerenciada pelo DVC e não acompanha o Git. A cópia em
`frontend/data/churn.csv` acompanha a publicação do painel e a imagem Docker.
Ela contém os mesmos 7.043 clientes da base existente, sem gerar novos dados.
Se atualizar a base original, atualize a cópia antes de publicar:

```powershell
python -m uv run python scripts/preparar_base_painel.py
```

Envie as alterações do projeto:

```powershell
git add .streamlit/config.toml Dockerfile frontend/streamlit_app.py frontend/requirements.txt frontend/data/churn.csv scripts/preparar_base_painel.py src/churn/dashboard.py src/churn/dashboard_client.py tests/test_dashboard.py tests/test_hosting.py README.md docs/deploy_aws.md docs/deploy_render_streamlit.md .gitattributes
git diff --cached --stat
git commit -m "Prepara FastAPI no Render e painel no Streamlit Cloud"
git push origin main
```

O `git add` precisa incluir `frontend/data/churn.csv`. Enviar apenas os arquivos
Python atualiza a interface, mas deixa os dados fora do site. Para confirmar que
a base entrou no commit, rode `git ls-files frontend/data/churn.csv`: deve aparecer
o caminho do CSV. O arquivo `data/churn.csv.dvc` é apenas um ponteiro, não contém
os registros. O remote DVC deste projeto é local e não está acessível ao Streamlit
Cloud; por isso o painel utiliza a cópia do CSV incluída na publicação.

Complete a autenticação do GitHub se solicitada. Se já tiver feito commit e
não houver mudanças, basta o `git push`. Se ele retornar conflito ou rejeição,
resolva a sincronização antes de continuar; não use `--force`.

Abra o repositório no GitHub e confira, na branch `main`, estes arquivos:

- `render.yaml`
- `frontend/streamlit_app.py`
- `frontend/requirements.txt`
- `frontend/data/churn.csv`
- `src/churn/dashboard.py`
- `reports/selection.json`
- `deployment/model-v1-20d3e3df/MLmodel`
- `deployment/model-v1-20d3e3df/model.pkl`

O arquivo de modelo é pequeno e pode ser enviado pelo Git normal. Se treinar um
modelo novo, atualize a exceção correspondente em `.gitignore`, envie a nova
pasta selecionada e o `reports/selection.json` atualizado juntos.

## 2. Criar a API no Render

1. Acesse [dashboard.render.com](https://dashboard.render.com/) e entre com sua conta.
2. Conecte o GitHub e autorize o acesso ao repositório `Pedro-M-R/ml-ops`.
3. Escolha **New → Blueprint** e selecione o repositório.
4. Selecione a branch `main` e o arquivo `render.yaml`, caso seja solicitado.
5. Confira o serviço `churn-api` com plano **Free** e runtime **Docker**.
6. Clique em **Deploy Blueprint** ou no botão equivalente de criação.
7. Aguarde a conclusão do build e a indicação de que o serviço está **Live**.

O Blueprint usa a raiz do repositório: **não informe `ml-ops` como Root Directory**.
`ml-ops` já é o próprio repositório, não uma subpasta dele no GitHub.
O Docker é construído no Render; não é preciso iniciar o Docker Desktop local.

O endereço exibido será semelhante a `https://churn-api-xxxx.onrender.com`.
Use o endereço exato informado pelo painel, pois o nome pode receber um sufixo.

Se preferir criar manualmente por **New → Web Service**, use:

| Campo | Valor |
| --- | --- |
| Repository | `Pedro-M-R/ml-ops` |
| Branch | `main` |
| Language / Runtime | `Docker` |
| Root Directory | vazio |
| Dockerfile Path | `./Dockerfile` |
| Docker Build Context | `.` |
| Docker Command | vazio; utiliza o CMD da imagem |
| Health Check Path | `/health` |
| Instance Type | `Free`, para tentativa inicial de demonstração |

O comando `churn-serve` lê a variável `PORT` do Render e escuta em `0.0.0.0`.
O template configura `PORT=10000`. Na criação manual, o Render fornece `PORT`.

## 3. Conferir a API publicada

Abra no navegador, substituindo pelo endereço real:

```text
https://SUA-API.onrender.com/health
https://SUA-API.onrender.com/docs
```

`/health` deve retornar `{"status":"ok"}`; `/docs` deve abrir o Swagger.
A API só fica pronta depois de carregar o modelo. Se o log mostrar erro de
arquivo ausente em `deployment/`, confirme que a pasta selecionada foi enviada
ao GitHub com todos os arquivos, incluindo `code/churn/`.

Para testar uma previsão no PowerShell, na pasta `ml-ops`:

```powershell
$apiPublica = 'https://SUA-API.onrender.com'
Invoke-RestMethod -Uri "$apiPublica/invocations" -Method Post -ContentType 'application/json' -InFile reports/example_request.json -TimeoutSec 180
```

## 4. Publicar a tela no Streamlit Community Cloud

1. Acesse [share.streamlit.io](https://share.streamlit.io/) e conecte seu GitHub.
2. Escolha **Create app / New app → Deploy from GitHub**.
3. Preencha:

   | Campo | Valor |
   | --- | --- |
   | Repository | `Pedro-M-R/ml-ops` |
   | Branch | `main` |
   | Main file path | `frontend/streamlit_app.py` |

4. Abra **Advanced settings** e selecione **Python 3.13**.
5. No campo **Secrets**, cole as duas linhas abaixo, trocando a URL pelo
   endereço real da API criada no Render:

   ```toml
   CHURN_API_URL = "https://SUA-API.onrender.com"
   CHURN_API_PUBLIC_URL = "https://SUA-API.onrender.com"
   ```

6. Clique em **Deploy** e aguarde o endereço `https://SEU-APP.streamlit.app`.

Use apenas a URL base nos Secrets, sem `/docs`, `/health` ou `/predict`.
`CHURN_API_URL` é o endereço que a tela consulta; `CHURN_API_PUBLIC_URL` habilita
o link da documentação em **Ver resposta original da API**.

O Streamlit usa `frontend/requirements.txt` porque está junto do arquivo de
entrada. Assim, a tela não instala as dependências de treino e MLflow da API.
A entrada importa a interface existente em `src/churn/dashboard.py`.

Se o app já existe, altere os valores em **Settings → Secrets**, salve e reinicie
o app se necessário. A configuração local de PowerShell não é enviada à nuvem.
Não envie `.streamlit/secrets.toml` ao GitHub; o exemplo pode ser versionado.

## 5. Testar os dois serviços juntos

1. Abra `/health` da API e aguarde `status: ok`.
2. Abra o link `streamlit.app` e confira o painel **Permanência**, com apresentação à esquerda e consulta à direita.
3. Confira **Modelo disponível** e a contagem de clientes da base `churn.csv`.
4. Digite um `customerID` existente e clique em **Consultar**, ou clique em um dos códigos de exemplo. O perfil é buscado automaticamente na base.
5. Confira **SIM — tende a continuar pagando** (classe 0) ou **NÃO — tende a cancelar o serviço** (classe 1), com a probabilidade e o JSON retornados pela API.
6. Em **Ver resposta original da API**, confira o JSON. Em **Consultar a base completa**, use **Classificar toda a base** para analisar os clientes e baixar o CSV.

Se funcionar após desligar os servidores locais, as chamadas estão passando
pelos serviços publicados. Na nuvem, não use `localhost`, `127.0.0.1` ou
`http://api:8000`: esses endereços não apontam para o Render a partir do Streamlit.

## Limites, diagnóstico e alterações

O plano gratuito do Render tem 512 MB de RAM e suspende após 15 minutos sem
tráfego de entrada. A primeira consulta após esse período pode demorar cerca de
um minuto, mais o carregamento do modelo. Abra `/health`, aguarde e consulte a
tela novamente. O painel permite até 120 segundos para cada requisição de previsão.

O limite de RAM pode não ser suficiente para o MLflow e as dependências durante
a execução. Se os logs indicarem encerramento por memória, será necessário
aumentar o plano ou preparar uma API com dependências menores. A configuração
Free é uma tentativa para demonstração, não uma garantia de capacidade.

Use dados de demonstração: a API publicada e a tela não têm autenticação neste
fluxo inicial. Os CSVs não são persistidos em disco pela aplicação.

| Sintoma | O que conferir |
| --- | --- |
| Render não encontra `Dockerfile` | Root Directory vazio e arquivo na raiz da branch publicada. |
| Modelo ausente no build | Pasta `deployment/model-v1-20d3e3df/` enviada no mesmo commit da seleção. |
| `No module named churn` | Main file path deve ser `frontend/streamlit_app.py`. |
| API funciona no navegador, tela não conecta | Secrets com URL base HTTPS exata e sem sufixo de endpoint. |
| Primeira consulta demora | Retomada da instância gratuita; aguarde `/health` ficar pronto. |
| Processo encerrado por memória | Limite de RAM do serviço Render; examine os logs antes de mudar o plano. |

Depois de publicar, commits na branch conectada acionam novas versões nos
serviços. Confira o status do deploy antes de testar alterações.

## Referências

- [Render: publicação com Docker](https://render.com/docs/docker)
- [Render: campos do Blueprint](https://render.com/docs/blueprint-spec)
- [Render: limites do plano gratuito](https://render.com/docs/free)
- [Streamlit: dependências e prioridade dos arquivos](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
- [Streamlit: Secrets na Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
