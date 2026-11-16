# Mapa do repositório Permanência

Este documento explica os arquivos que aparecem no GitHub. Para a fala da apresentação, use o [roteiro completo](apresentacao_projeto.md). Para aprofundar decisões e resultados, use o [roteiro técnico](apresentacao_mlflow.md).

## O que está em uso e o que é histórico

- **Implantação principal:** Streamlit, FastAPI e PostgreSQL em Docker Compose na AWS EC2.
- **Treinamento atual do champion:** pipeline.py e tuning.py, executados por churn-tune.
- **Experimentos:** MLflow local, em SQLite e artefatos locais; o pipeline exportado acompanha a API.
- **Fluxo legado:** model.py, features.py, experiments.py e o pipeline DVC preservam os exercícios de Random Forest.
- **Alternativas:** Render e Streamlit Cloud têm arquivos próprios, mas não são a hospedagem principal atual.
- **Planejamento:** grade-mlops-60h.md contém a proposta do curso. Não foram encontrados DAGs Airflow nem workflows GitHub Actions versionados neste repositório. A grade não comprova essas implementações.

## Como ler a listagem do GitHub

O nome à esquerda identifica a pasta ou arquivo. A frase ao lado é a mensagem do último commit que alterou aquele caminho; ela não é o nome do arquivo. Uma nova alteração com commit descritivo pode atualizar a frase da listagem sem apagar ou reescrever o histórico anterior.

## Pastas que têm nomes parecidos

| Caminho | Função |
| --- | --- |
| `deploy/postgres/` | Scripts para criar e carregar o banco. |
| `deployment/model-v1-20d3e3df/` | Artefato treinado, pronto para a API carregar. |
| `src/churn/` | Código atual da aplicação e dos fluxos de treino. |
| `deployment/.../code/churn/` | Fotografia do código preservada junto ao modelo. |

O nome da pasta do modelo é referenciado em selection.json e no empacotamento. Ele foi preservado para manter o carregamento do artefato. Os nomes técnicos dos arquivos também foram mantidos; as descrições abaixo explicam sua função.

## Arquivos da raiz

Ambiente, regras de versionamento e execução.

| Arquivo | Explicação simples |
| --- | --- |
| [.dockerignore](../.dockerignore) | Define arquivos que não devem entrar no contexto da imagem da aplicação, incluindo dados locais e segredos. |
| [.dvcignore](../.dvcignore) | Define arquivos locais ignorados pelo DVC, como bytecode Python. |
| [.gitattributes](../.gitattributes) | Padroniza finais de linha de scripts e o tratamento do CSV no Git. |
| [.gitignore](../.gitignore) | Evita versionar ambientes, senhas, caches e experimentos locais; permite o artefato selecionado. |
| [.python-version](../.python-version) | Indica Python 3.13 para as ferramentas de ambiente. Não contém o nome do projeto nem uma mensagem de commit. |
| [Dockerfile](../Dockerfile) | Constrói a imagem da aplicação com dependências, código, modelo e base de consulta. |
| [Dockerfile.postgres](../Dockerfile.postgres) | Prepara PostgreSQL 17 e inclui os scripts de inicialização, sem incorporar senhas. |
| [Dockerfile.postgres.dockerignore](../Dockerfile.postgres.dockerignore) | Restringe o contexto da imagem do banco aos arquivos de inicialização necessários. |
| [README.md](../README.md) | Página inicial: objetivo, resultados, acesso e hospedagem atual na AWS. |
| [compose.ec2.yml](../compose.ec2.yml) | Adapta o Compose à EC2: publica o painel e remove o mapeamento externo da API. |
| [compose.postgres.yml](../compose.postgres.yml) | Acrescenta PostgreSQL, volume, secrets e dependências de prontidão. |
| [docker-compose.yml](../docker-compose.yml) | Define API, painel, verificações de saúde e um perfil opcional de treinamento. |
| [dvc.lock](../dvc.lock) | Registra hashes das dependências e da saída da última execução registrada do pipeline DVC legado. |
| [dvc.yaml](../dvc.yaml) | Descreve o estágio DVC legado que executa churn.model e produz models/model.pkl. Não seleciona o champion atual. |
| [grade-mlops-60h.md](../grade-mlops-60h.md) | Planejamento do curso de MLOps. É material didático, não comprovação de todas as funcionalidades mencionadas. |
| [pyproject.toml](../pyproject.toml) | Define pacote, dependências, configurações e comandos como churn-tune, churn-serve e churn-dashboard. |
| [render.yaml](../render.yaml) | Configuração preservada como alternativa para publicar a API no Render. A implantação principal é AWS. |
| [uv.lock](../uv.lock) | Fixa as versões resolvidas das dependências para reinstalar o ambiente. |

## .dvc

Versionamento e localização dos dados.

| Arquivo | Explicação simples |
| --- | --- |
| [.dvc/.gitignore](../.dvc/.gitignore) | Ignora cache, temporários e configuração local do DVC. |
| [.dvc/config](../.dvc/config) | Configura o remote DVC local em ../../dvc-remote; outra máquina precisa ter acesso aos dados ou ajustar o remote. |

## .streamlit

Configuração visual e exemplos para o painel separado.

| Arquivo | Explicação simples |
| --- | --- |
| [.streamlit/config.toml](../.streamlit/config.toml) | Define tema, aparência e opções do servidor Streamlit. |
| [.streamlit/secrets.example.toml](../.streamlit/secrets.example.toml) | Exemplo de variáveis para o painel hospedado separadamente; não contém credenciais reais. |

## aws

Infraestrutura e partida dos serviços na hospedagem principal.

| Arquivo | Explicação simples |
| --- | --- |
| [aws/bootstrap.sh](../aws/bootstrap.sh) | Instala Docker/Compose, prepara secrets e inicia banco, API e painel na EC2. |
| [aws/cloudformation.yaml](../aws/cloudformation.yaml) | Template da rede, permissões IAM, EC2, disco, regras de acesso e inicialização. |

## data

Ponteiro DVC da base original.

| Arquivo | Explicação simples |
| --- | --- |
| [data/.gitkeep](../data/.gitkeep) | Mantém a pasta data presente no Git mesmo sem o CSV materializado. |
| [data/churn.csv.dvc](../data/churn.csv.dvc) | Ponteiro com identificação do CSV original; o conteúdo dos dados é gerenciado pelo DVC. |

## deploy/postgres

Inicialização da carteira e das permissões no banco.

| Arquivo | Explicação simples |
| --- | --- |
| [deploy/postgres/10-customers.sh](../deploy/postgres/10-customers.sh) | Aciona a carga inicial SQL no entrypoint do PostgreSQL em um volume novo. |
| [deploy/postgres/customers.sql](../deploy/postgres/customers.sql) | Cria e carrega customers, define restrições e concede leitura ao churn_reader. |

## deployment

Pipeline selecionado e exportado, com sua fotografia de código e ambiente.

| Arquivo | Explicação simples |
| --- | --- |
| [deployment/model-v1-20d3e3df/MLmodel](../deployment/model-v1-20d3e3df/MLmodel) | Manifesto MLflow: formato, assinatura, método de previsão e localização dos componentes. |
| [deployment/model-v1-20d3e3df/code/churn/__init__.py](../deployment/model-v1-20d3e3df/code/churn/__init__.py) | Snapshot do código na exportação: Identifica o pacote Python churn. Esta cópia preserva o artefato e não deve ser confundida com o código atual em src/churn. |
| [deployment/model-v1-20d3e3df/code/churn/config.py](../deployment/model-v1-20d3e3df/code/churn/config.py) | Snapshot do código na exportação: Configura caminhos e parâmetros por Pydantic Settings, arquivo .env e variáveis CHURN_. Esta cópia preserva o artefato e não deve ser confundida com o código atual em src/churn. |
| [deployment/model-v1-20d3e3df/code/churn/data.py](../deployment/model-v1-20d3e3df/code/churn/data.py) | Snapshot do código na exportação: Leitura do CSV e validação Pandera dos tipos e regras dos dados de treinamento. Esta cópia preserva o artefato e não deve ser confundida com o código atual em src/churn. |
| [deployment/model-v1-20d3e3df/code/churn/deploy.py](../deployment/model-v1-20d3e3df/code/churn/deploy.py) | Snapshot do código na exportação: Comandos para servir a API, abrir a interface MLflow e prever por CSV com o artefato exportado. Esta cópia preserva o artefato e não deve ser confundida com o código atual em src/churn. |
| [deployment/model-v1-20d3e3df/code/churn/evaluate.py](../deployment/model-v1-20d3e3df/code/churn/evaluate.py) | Snapshot do código na exportação: Calcula acurácia, precisão, recall, F1 e ROC-AUC. Esta cópia preserva o artefato e não deve ser confundida com o código atual em src/churn. |
| [deployment/model-v1-20d3e3df/code/churn/experiments.py](../deployment/model-v1-20d3e3df/code/churn/experiments.py) | Snapshot do código na exportação: Grid histórico de nove Random Forests. O fluxo atual de seleção está em tuning.py. Esta cópia preserva o artefato e não deve ser confundida com o código atual em src/churn. |
| [deployment/model-v1-20d3e3df/code/churn/features.py](../deployment/model-v1-20d3e3df/code/churn/features.py) | Snapshot do código na exportação: Transformações e encoder usados nos exercícios e no treino legado; o champion utiliza pipeline.py. Esta cópia preserva o artefato e não deve ser confundida com o código atual em src/churn. |
| [deployment/model-v1-20d3e3df/code/churn/lineage.py](../deployment/model-v1-20d3e3df/code/churn/lineage.py) | Snapshot do código na exportação: Lê a versão DVC dos dados e identifica commit Git e alterações locais. Esta cópia preserva o artefato e não deve ser confundida com o código atual em src/churn. |
| [deployment/model-v1-20d3e3df/code/churn/model.py](../deployment/model-v1-20d3e3df/code/churn/model.py) | Snapshot do código na exportação: Treinamento Random Forest instrumentado no MLflow, linhagem e persistência do fluxo legado. Esta cópia preserva o artefato e não deve ser confundida com o código atual em src/churn. |
| [deployment/model-v1-20d3e3df/code/churn/pipeline.py](../deployment/model-v1-20d3e3df/code/churn/pipeline.py) | Snapshot do código na exportação: Pipeline atual: conversão numérica, imputação, escala, one-hot e classificador. Esta cópia preserva o artefato e não deve ser confundida com o código atual em src/churn. |
| [deployment/model-v1-20d3e3df/code/churn/tracking.py](../deployment/model-v1-20d3e3df/code/churn/tracking.py) | Snapshot do código na exportação: Configura o experimento MLflow, o backend SQLite local e o destino dos artefatos. Esta cópia preserva o artefato e não deve ser confundida com o código atual em src/churn. |
| [deployment/model-v1-20d3e3df/code/churn/tuning.py](../deployment/model-v1-20d3e3df/code/churn/tuning.py) | Snapshot do código na exportação: Compara candidatos por CV, escolhe o vencedor, avalia no teste, registra e exporta o pipeline. Esta cópia preserva o artefato e não deve ser confundida com o código atual em src/churn. |
| [deployment/model-v1-20d3e3df/conda.yaml](../deployment/model-v1-20d3e3df/conda.yaml) | Descrição do ambiente Conda associado ao artefato exportado. |
| [deployment/model-v1-20d3e3df/input_example.json](../deployment/model-v1-20d3e3df/input_example.json) | Exemplo das entradas do modelo. |
| [deployment/model-v1-20d3e3df/model.pkl](../deployment/model-v1-20d3e3df/model.pkl) | Pipeline treinado serializado. É o artefato utilizado para prever, não um script de treinamento. |
| [deployment/model-v1-20d3e3df/python_env.yaml](../deployment/model-v1-20d3e3df/python_env.yaml) | Descrição do ambiente Python associado ao artefato exportado. |
| [deployment/model-v1-20d3e3df/requirements.txt](../deployment/model-v1-20d3e3df/requirements.txt) | Dependências com versões registradas para carregar o artefato. |
| [deployment/model-v1-20d3e3df/serving_input_example.json](../deployment/model-v1-20d3e3df/serving_input_example.json) | Exemplo de entrada no formato de serving MLflow. |

## docs

Guias, decisões e roteiros de apresentação.

| Arquivo | Explicação simples |
| --- | --- |
| [docs/apresentacao_mlflow.md](../docs/apresentacao_mlflow.md) | Explicações técnicas por ferramenta, decisões, métricas e perguntas para revisão. |
| [docs/apresentacao_projeto.md](../docs/apresentacao_projeto.md) | Fala simples do projeto completo e ordem sugerida para navegar no GitHub. |
| [docs/deploy_aws.md](../docs/deploy_aws.md) | Guia da implantação principal: EC2, acesso, atualização e cuidados de operação. |
| [docs/deploy_render_postgres.md](../docs/deploy_render_postgres.md) | Alternativa de publicação da API e do PostgreSQL no Render. |
| [docs/deploy_render_streamlit.md](../docs/deploy_render_streamlit.md) | Alternativa de publicação com API no Render e painel separado no Streamlit Cloud. |
| [docs/guia_execucao.md](../docs/guia_execucao.md) | Guia de instalação e execução do modelo em outro computador; alguns exemplos refletem etapas anteriores do painel. |
| [docs/historico_exercicios.md](../docs/historico_exercicios.md) | Preserva instruções dos exercícios e do fluxo legado; diferencia esse fluxo da seleção atual. |
| [docs/mapa_repositorio.md](../docs/mapa_repositorio.md) | Este mapa: função de cada arquivo e distinção entre entrega atual, alternativas e histórico. |
| [docs/postgres.md](../docs/postgres.md) | Arquitetura do banco, carga, conta de leitura, Compose, persistência e procedimentos de backup. |
| [docs/relato_projeto.md](../docs/relato_projeto.md) | Narrativa do desenvolvimento e das decisões de publicação, incluindo a conclusão na AWS. |
| [docs/resumo_3_slides.md](../docs/resumo_3_slides.md) | Resumo histórico de seleção e empacotamento; não é o roteiro atualizado do projeto completo. |

## frontend

Entrada alternativa da interface e base distribuída.

| Arquivo | Explicação simples |
| --- | --- |
| [frontend/data/churn.csv](../frontend/data/churn.csv) | Cópia versionada dos 7.043 clientes, distribuída com a aplicação e utilizada na carga inicial do banco. |
| [frontend/requirements.txt](../frontend/requirements.txt) | Dependências do frontend separado: Streamlit, pandas e cliente HTTP. |
| [frontend/streamlit_app.py](../frontend/streamlit_app.py) | Entrada alternativa do painel para hospedagem separada, incluindo leitura de configurações do Streamlit. |

## reports

Resultados e evidências datadas do treinamento e das verificações.

| Arquivo | Explicação simples |
| --- | --- |
| [reports/api_verification.json](../reports/api_verification.json) | Registro de verificações HTTP da API, formatos de entrada, probabilidades e erros. |
| [reports/comparison.csv](../reports/comparison.csv) | Ranking das 22 configurações com médias, desvios e tempo de ajuste na validação cruzada. |
| [reports/dashboard_verification.json](../reports/dashboard_verification.json) | Registro datado de verificações do painel. O status de hospedagem descreve a etapa em que foi gerado. |
| [reports/example_request.json](../reports/example_request.json) | Exemplo de requisição no formato dataframe_split para consultar o modelo. |
| [reports/hosting_verification.json](../reports/hosting_verification.json) | Registro datado de verificações de empacotamento e hospedagem; não representa o estado atual da conta AWS. |
| [reports/selection.json](../reports/selection.json) | Resultado principal: modelo escolhido, parâmetros, métricas, matriz de confusão, versão, hashes e caminho exportado. |
| [reports/split.csv](../reports/split.csv) | Identifica quais linhas foram destinadas ao treino e ao teste. |
| [reports/verification.json](../reports/verification.json) | Registro histórico de portabilidade, ambiente limpo e conferência das previsões após realocação. |

## scripts

Tarefas auxiliares executadas conforme a necessidade.

| Arquivo | Explicação simples |
| --- | --- |
| [scripts/deploy_aws.py](../scripts/deploy_aws.py) | Prepara o pacote e conduz a publicação com S3 e CloudFormation; não é executado ao abrir o painel. |
| [scripts/empacotar.py](../scripts/empacotar.py) | Gera o ZIP transportável com código, dependências, artefato selecionado e configurações, sem senhas locais. |
| [scripts/gerar_resumo.py](../scripts/gerar_resumo.py) | Gera o resumo histórico de três partes a partir dos relatórios do treinamento. |
| [scripts/importar_clientes_render.py](../scripts/importar_clientes_render.py) | Importador da alternativa PostgreSQL no Render, usando as rotinas de database_setup.py. |
| [scripts/preparar_base_painel.py](../scripts/preparar_base_painel.py) | Valida e copia a base original para frontend/data/churn.csv, sem treinar o modelo. |
| [scripts/preparar_postgres.py](../scripts/preparar_postgres.py) | Gera e preserva senhas administrativas e de leitura nos arquivos locais de secrets. |
| [scripts/testar_api.py](../scripts/testar_api.py) | Executa chamadas HTTP e confere o comportamento da API. |
| [scripts/verificar_mlflow.py](../scripts/verificar_mlflow.py) | Verifica treino, registros, artefatos e recarga do modelo; pode verificar também o grid histórico. |
| [scripts/verificar_postgres.py](../scripts/verificar_postgres.py) | Compara clientes com o CSV, previsões e restrição real de escrita da conta da API. |

## src/churn

Código-fonte atual, com módulos atuais e exercícios legados.

| Arquivo | Explicação simples |
| --- | --- |
| [src/churn/__init__.py](../src/churn/__init__.py) | Identifica o pacote Python churn. |
| [src/churn/api.py](../src/churn/api.py) | Schemas Pydantic e rotas de cadastro, previsão, saúde e prontidão da FastAPI. |
| [src/churn/config.py](../src/churn/config.py) | Configura caminhos e parâmetros por Pydantic Settings, arquivo .env e variáveis CHURN_. |
| [src/churn/customers.py](../src/churn/customers.py) | Consulta clientes em PostgreSQL ou CSV pelo backend; fornece busca individual e paginação. |
| [src/churn/dashboard.py](../src/churn/dashboard.py) | Interface Streamlit Permanência: consulta, apresentação dos resultados e classificação em lote. |
| [src/churn/dashboard_client.py](../src/churn/dashboard_client.py) | Cliente HTTP do painel, validação dos registros, paginação, lotes e conferência das respostas. |
| [src/churn/data.py](../src/churn/data.py) | Leitura do CSV e validação Pandera dos tipos e regras dos dados de treinamento. |
| [src/churn/database_setup.py](../src/churn/database_setup.py) | Rotinas para importar clientes e configurar a conta de leitura em um PostgreSQL gerenciado. |
| [src/churn/deploy.py](../src/churn/deploy.py) | Comandos para servir a API, abrir a interface MLflow e prever por CSV com o artefato exportado. |
| [src/churn/evaluate.py](../src/churn/evaluate.py) | Calcula acurácia, precisão, recall, F1 e ROC-AUC. |
| [src/churn/experiments.py](../src/churn/experiments.py) | Grid histórico de nove Random Forests. O fluxo atual de seleção está em tuning.py. |
| [src/churn/features.py](../src/churn/features.py) | Transformações e encoder usados nos exercícios e no treino legado; o champion utiliza pipeline.py. |
| [src/churn/lineage.py](../src/churn/lineage.py) | Lê a versão DVC dos dados e identifica commit Git e alterações locais. |
| [src/churn/model.py](../src/churn/model.py) | Treinamento Random Forest instrumentado no MLflow, linhagem e persistência do fluxo legado. |
| [src/churn/pipeline.py](../src/churn/pipeline.py) | Pipeline atual: conversão numérica, imputação, escala, one-hot e classificador. |
| [src/churn/tracking.py](../src/churn/tracking.py) | Configura o experimento MLflow, o backend SQLite local e o destino dos artefatos. |
| [src/churn/tuning.py](../src/churn/tuning.py) | Compara candidatos por CV, escolhe o vencedor, avalia no teste, registra e exporta o pipeline. |

## tests

Testes automatizados das partes do projeto.

| Arquivo | Explicação simples |
| --- | --- |
| [tests/conftest.py](../tests/conftest.py) | Fornece dados de exemplo compartilhados pelos testes. |
| [tests/test_api.py](../tests/test_api.py) | Testa contratos, entradas inválidas, limites, formatos e respostas da API. |
| [tests/test_customers.py](../tests/test_customers.py) | Testa o acesso aos clientes, SQL parametrizado, paginação e reaproveitamento no modo CSV. |
| [tests/test_dashboard.py](../tests/test_dashboard.py) | Testa a consulta e a apresentação do painel e a integração com o cliente HTTP. |
| [tests/test_data.py](../tests/test_data.py) | Testa carga e regras de validação dos dados. |
| [tests/test_database_setup.py](../tests/test_database_setup.py) | Testa as rotinas de importação e preparação do PostgreSQL gerenciado. |
| [tests/test_features.py](../tests/test_features.py) | Testa transformações do fluxo de features legado. |
| [tests/test_hosting.py](../tests/test_hosting.py) | Testa configurações e comportamentos necessários à hospedagem e ao empacotamento. |
| [tests/test_model.py](../tests/test_model.py) | Testa treinamento, métricas e persistência do modelo do fluxo legado. |
| [tests/test_pipeline.py](../tests/test_pipeline.py) | Testa o pipeline atual, categorias inéditas, ausências e transformações aprendidas no treino. |
| [tests/test_tracking.py](../tests/test_tracking.py) | Testa tracking e identificação da origem do código e dos dados. |

## O que pode existir localmente sem estar no Git

| Caminho | Papel |
| --- | --- |
| `.venv/` | Ambiente instalado; deve ser recriado, não copiado para publicação. |
| `data/churn.csv` | CSV materializado a partir do dado versionado; não aparece como conteúdo rastreado nesta listagem. |
| `mlflow.db`, `mlartifacts/`, `mlruns/` | Histórico atual e/ou legado de experimentos locais. |
| `models/model.pkl` | Saída do fluxo de treino legado. |
| `runtime/` | Senhas e arquivos de execução, excluídos do Git. |
| `dist/` | Pacotes transportáveis gerados pelos scripts. |

O volume PostgreSQL é administrado pelo Docker e não é um arquivo de banco versionado no repositório. Os relatórios são registros de verificações anteriores; para o estado da implantação, consulte também o guia AWS e o relato do projeto.
