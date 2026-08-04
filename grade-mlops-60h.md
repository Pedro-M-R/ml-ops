# Curso de MLOps — Grade Estrutural

> **Status deste documento:** grade estrutural (objetivo, dor motivadora, o que se constrói, tarefa de casa e ponto de atrito por encontro). Os **textos teóricos** de cada módulo — baseados no ml-ops.org — serão gerados depois, módulo a módulo, com a fonte verificada na hora da escrita. Este é o mapa; o conteúdo redacional vem em cima dele.

---

## 1. Dados do curso

| Item | Definição |
|---|---|
| **Público** | Último semestre de graduação (4 anos) em IA / Ciência de Dados. Sabem ML, Python e treinar modelos. Têm buracos em engenharia de software (Git, Docker, estrutura de projeto). |
| **Carga** | 15 encontros × 4h = **60h síncronas**  |
| **Objetivo terminal** | Ao fim do curso, o aluno é capaz de desenvolver um projeto de ML **de ponta a ponta**, atravessando os três pipelines (Dados, ML, Código) e implementando as principais ferramentas open-source de gestão de cada etapa. |
| **Escopo** | ML clássico (tabular). LLMOps/Agentes são apenas **citados** como extensão. Kubeflow/Kubernetes ficam no material assíncrono. |

---

## 2. Princípios de design (ler antes de aplicar a grade)

1. **Dor → ferramenta.** Nenhuma ferramenta é introduzida antes de o aluno sentir a dor que ela resolve. Docker entra quando "na minha máquina funciona" vira problema real; MLflow entra quando eles perdem qual experimento foi o melhor; Airflow entra quando rodar as etapas na mão fica insuportável. A ferramenta é a resposta a uma frustração já vivida, nunca um tópico solto.

2. **Projeto fixo, deliberadamente chato.** Todos constroem o **mesmo** sistema (churn tabular). Dataset e modelo são **fixados pelo professor** — os alunos não escolhem. O ponto pedagógico nunca é a acurácia; é o encanamento ao redor do modelo. Tirar essa liberdade é intencional: evita que a turma gaste tempo tunando modelo em vez de aprender MLOps.

3. **Sala invertida parcial.** Casa = **preparação de ambiente** (antes do encontro) + **consolidação/extensão** (depois) + **leitura teórica**. Sala = **construção assistida e desbloqueio ao vivo**. Setup acontece fora da sala; a sala fica livre para o que só o professor presencial resolve. Sem isso, ~35% de cada encontro evapora em "esperem, vou ajudar o fulano com o Docker".

4. **Checkpoint de sanidade** nos primeiros ~15min de cada encontro: o aluno chega com o ambiente da tarefa de casa de pé, ou com um erro específico para ser resolvido rápido. Isso é o que torna viável uma turma de 30+ sem o pesadelo de setup coletivo.
---

## 3. Fontes e vocabulário

| Uso | Fonte primária |
|---|---|
| Teoria, princípios, ciclo de vida, os 3 pipelines | **ml-ops.org** (INNOQ) |
| Vocabulário oficial de fases | **AWS Well-Architected ML Lens** |
| Ferramentas hands-on | Docs oficiais de cada ferramenta (open-source) |
| "Como isso vira serviço gerenciado" | **AWS** (análogos SageMaker etc.) |

**Tabela de tradução de vocabulário** (apresentar no Encontro 1 para evitar confusão terminológica):

| ml-ops.org (teoria) | AWS Well-Architected (fases) | Ferramenta do curso (open-source) | Análogo gerenciado AWS |
|---|---|---|---|
| Data Pipeline | Data Processing | DVC + Great Expectations/pandera | SageMaker Processing / Feature Store |
| ML Pipeline | Model Development | MLflow (tracking + registry) | SageMaker Experiments / Model Registry |
| (Orquestração — implícita) | (transversal) | Airflow | SageMaker Pipelines / Step Functions |
| Software Code Pipeline | Model Deployment | GitHub Actions + FastAPI + Docker | CodePipeline / SageMaker Endpoints |
| Monitoring & Logging | Model Monitoring | conceito + demo (Evidently) | SageMaker Model Monitor / Clarify |

> **Nota de coerência:** o diagrama-mapa do curso é o dos **três pipelines do ml-ops.org**. A âncora conceitual é *o modelo de três pipelines*, não "é da AWS". A AWS entra como vocabulário de fase e como catálogo de análogos gerenciados — não invocar "é o material da AWS" como justificativa para o diagrama, porque ele não é.

---

## 4. Kit de ferramentas (hands-on, presencial)

Git · Docker · DVC · MLflow · Airflow · GitHub Actions · FastAPI

Deliberadamente **open-source**: o aluno aprende o conceito onde vê o encanamento, e depois reconhece o serviço gerenciado AWS como "a mesma coisa, terceirizada". Isso também elimina o pesadelo logístico de contas AWS para 30+ alunos.

---

## 5. Projeto-fio-condutor

**Previsão de churn** (classificação binária tabular). Dataset e baseline fixados pelo professor.

**Arco:** o aluno começa no Encontro 1 com um notebook vergonhoso que "funciona na minha máquina" e termina no Encontro 15 com:

`dados versionados (DVC)` → `experimentos rastreados (MLflow)` → `pipeline orquestrado (Airflow)` → `modelo servido via API (FastAPI + Docker)` → `CI/CD automatizado (GitHub Actions)` → `monitoramento de drift (conceitual)`.

Cada encontro adiciona **uma** peça, motivada por uma dor sentida no encontro anterior. O diagrama do ml-ops.org é mostrado progressivamente — cada pipeline colorido "acende" quando a turma chega naquele módulo.

---

## 6. Grade dos 15 encontros

### BLOCO 0 — Fundação (Encontros 1–3)
*Não se toca em ML novo. Arruma-se a engenharia que falta.*

---

**Encontro 1 — Por que MLOps existe**
- **Objetivo:** enquadrar a disciplina e criar a primeira dor.
- **Dor motivadora (ao vivo):** cada aluno entrega seu notebook de churn para o colega ao lado rodar. Não roda. A dor de reprodutibilidade motiva todo o resto do curso.
- **Em sala (4h):** dinâmica do notebook quebrado (~45min) · o ciclo de vida de ML e o problema da dívida técnica em ML · os **três pipelines** do ml-ops.org (diagrama-mapa) · níveis de maturidade MLOps como mapa do que virá · tabela de tradução de vocabulário (§3).
- **Casa:** instalar o toolchain (Git, Docker, Python/venv) seguindo roteiro; **checkpoint no Encontro 2**. Leitura teórica: introdução do ml-ops.org.
- ** Atrito:** baixo (é o dia mais conceitual). O atrito real migra para a instalação em casa — por isso o checkpoint no início do Encontro 2.

---

**Encontro 2 — Git sério e estrutura de projeto**
- **Objetivo:** tirar o aluno do notebook e colocá-lo em um projeto versionável.
- **Dor motivadora:** "funciona no meu notebook" — mas ninguém consegue rodar, revisar ou colaborar.
- **Em sala (4h):** checkpoint de ambiente (~15min) · Git além do `git push` (branch, PR, resolução de conflito, revisão) · estrutura de projeto Python (sair do `.ipynb` → módulos `.py`, `pyproject`/deps travadas, separação código/config/dados) · migrar o notebook de churn para essa estrutura.
- **Casa:** finalizar a migração do projeto para estrutura modular; abrir um PR. Leitura: seção "Software Code Pipeline" do ml-ops.org.
- ** Atrito:** médio. Formandos de ciência de dados frequentemente têm buraco em Git colaborativo. **Não pule este encontro** achando que "são formandos" — é a causa nº1 de descarrilamento adiante.

---

**Encontro 3 — Docker: a camada de reprodutibilidade**
- **Objetivo:** matar "na minha máquina funciona".
- **Dor motivadora:** o PR do colega do Encontro 2 não roda na máquina de outro. Ambiente é o problema.
- **Em sala (4h):** por que containers (isolamento, reprodutibilidade) · imagem vs. container · Dockerfile do projeto churn · volumes e o loop de desenvolvimento · docker-compose introdutório.
- **Casa:** containerizar o projeto de churn (rodar treino dentro do container); **checkpoint no Encontro 4**. Leitura conceitual sobre reprodutibilidade.
- ** Atrito:** ALTO. É a fundação de Airflow e deploy — vale tempo generoso. A migração de setup para casa (com checkpoint) é o que evita perder a aula inteira aqui.

---

### BLOCO 1 — Data Pipeline / amarelo (Encontros 4–5)

---

**Encontro 4 — Coleta, limpeza e validação de dados**
- **Objetivo:** transformar limpeza ad-hoc em etapa versionável e testável.
- **Dor motivadora:** um dado sujo quebra o treino silenciosamente — e ninguém percebe até a métrica despencar.
- **Em sala (4h):** o Data Pipeline no diagrama (exploration → validation → wrangling) · profiling de dados · validação como teste ("JUnit4Data" → Great Expectations ou pandera) · o `DATA` como artefato.
- **Casa:** escrever validações para o dataset de churn (schema, ranges, nulos); quebrar de propósito e ver o teste pegar. Leitura: "Data Pipeline" no ml-ops.org.
- ** Atrito:** médio.

---

**Encontro 5 — Versionamento de dados (DVC)**
- **Objetivo:** rastrear qual dado gerou qual modelo.
- **Dor motivadora:** "mudei o dataset e não sei mais qual modelo veio de qual versão dos dados."
- **Em sala (4h):** por que Git não versiona dados · DVC (tracking de dados, remotes, pipelines DVC) · Data Artifact e o início da cadeia de linhagem · conexão com o análogo AWS (Feature Store / S3 versionado).
- **Casa:** versionar o dataset de churn com DVC; registrar duas versões e alternar entre elas. Consolidar o Data Pipeline.
- ** Atrito:** médio (config de remote pode travar).

---

### BLOCO 2 — ML Pipeline / vermelho (Encontros 6–8)

---

**Encontro 6 — Experimentação e tracking (MLflow)**
- **Objetivo:** parar de perder experimentos.
- **Dor motivadora:** "rodei 40 experimentos e perdi qual foi o melhor" (a caixa "Experiments/Trials" do diagrama).
- **Em sala (4h):** MLflow Tracking (params, metrics, artifacts) · instrumentar o treino de churn · comparar runs na UI · o MLflow mapeando quase 1:1 com a coluna Train & Tune.
- **Casa:** rodar um grid de experimentos rastreados; identificar o melhor pela UI. Leitura: "ML Pipeline" no ml-ops.org.
- ** Atrito:** baixo-médio.

---

**Encontro 7 — Model registry e versionamento de modelo**
- **Objetivo:** promover um modelo de "experimento" a "artefato gerenciado".
- **Dor motivadora:** achei o melhor experimento — e agora, como marco qual vai para produção?
- **Em sala (4h):** MLflow Model Registry · versionamento e estágios (staging/production) · Model Artifact e linhagem (dados → código → modelo) · análogo AWS (SageMaker Model Registry).
- **Casa:** registrar o melhor modelo de churn, versioná-lo, promovê-lo a "staging". Consolidação.
- ** Atrito:** baixo-médio.

---

**Encontro 8 — Empacotamento e fechamento do ML Pipeline**
- **Objetivo:** empacotar o modelo em formato servível e consolidar o pipeline de ML.
- **Dor motivadora:** o modelo está no registry mas ainda não é consumível por ninguém.
- **Em sala (4h):** Model Packaging (formatos — pickle/ONNX, trade-offs) · métricas de avaliação como gate · consolidação: Data + ML pipelines rodando juntos de ponta a ponta (ainda **na mão**).
- **Casa:** empacotar o modelo; escrever o script que carrega e prediz. Preparar ambiente do Airflow (docker-compose) para o Encontro 9 — **checkpoint**.
- ** Atrito:** médio.

---

### BLOCO 3 — Orquestração (Encontros 9–11)
*A faixa que o diagrama do ml-ops.org esconde — adicionada explicitamente por cima dos três pipelines.*

---

**Encontro 9 — Airflow: conceito e arquitetura**
- **Objetivo:** entender orquestração e a arquitetura distribuída.
- **Dor motivadora:** rodar dados → treino → avaliação na mão, toda vez, é insustentável.
- **Em sala (4h):** o que um orquestrador faz (e o que **não** faz — não é tracking, não é o loop de um agente) · arquitetura do Airflow (scheduler, worker, metadata DB, executor) via docker-compose · primeiro DAG · o DAG inferido a partir de dependências.
- **Casa:** subir o Airflow, rodar o DAG de exemplo, provocar e ler uma falha. Leitura conceitual sobre orquestração.
- ** Atrito:** ALTO (setup do Airflow + conceitos de agendamento). O checkpoint do Encontro 8 é o que salva a primeira hora.

---

**Encontro 10 — Airflow: costurando os pipelines**
- **Objetivo:** transformar as etapas manuais em um DAG real.
- **Dor motivadora:** as peças existem soltas; falta o fio que as dispara em ordem, com retry.
- **Em sala (4h):** modelar dados → treino → avaliação como DAG · dependências, retry, alerting · o modelo mental de agendamento (`schedule`, `catchup`, `data_interval` — a parte genuinamente difícil, e conceitual, não de infra).
- **Casa:** construir o DAG completo do projeto churn; agendar; estender com uma task extra. Consolidação.
- ** Atrito:** ALTO (agendamento confunde todo mundo — reserve tempo).

---

**Encontro 11 — Airflow: tasks isoladas e a camada de orquestração**
- **Objetivo:** rodar etapas em containers isolados e fechar a visão de orquestração.
- **Dor motivadora:** cada etapa precisa do seu próprio ambiente reproduzível, não tudo no worker.
- **Em sala (4h):** DockerOperator (tasks em containers-irmãos; a pegadinha do `docker.sock`) · a faixa "Orquestração" desenhada por cima dos três pipelines do diagrama · scaling de workers como demonstração.
- **Casa:** converter ao menos uma task do DAG para DockerOperator. Preparar ambiente de deploy (FastAPI) para o Encontro 12.
- ** Atrito:** médio-alto.

---

### BLOCO 4 — Code Pipeline + Deploy / azul (Encontros 12–14)

---

**Encontro 12 — Servindo o modelo (FastAPI + Docker)**
- **Objetivo:** transformar o modelo empacotado em serviço.
- **Dor motivadora:** o modelo no registry não responde a ninguém — falta a interface.
- **Em sala (4h):** FastAPI para inference endpoint · carregar o modelo do registry · containerizar o serviço · testar a predição via HTTP · Batch vs. Hosted Endpoint (conceito + análogo AWS).
- **Casa:** finalizar a API de churn containerizada; escrever um teste de request. Leitura sobre serving.
- ** Atrito:** médio.

---

**Encontro 13 — CI/CD com GitHub Actions**
- **Objetivo:** automatizar teste e build a cada push.
- **Dor motivadora:** o push do colega quebrou o projeto de todo mundo.
- **Em sala (4h):** conceito de CI/CD (aplicado a ML — testa código **e** dados **e** modelo) · GitHub Actions (workflow, jobs, triggers) · pipeline de lint + teste + build da imagem · secrets e runners (ponto de atrito). *Menção de 15min a Jenkins como o legado que verão no mercado.*
- **Casa:** escrever um workflow que roda os testes e builda a imagem no push. Consolidação.
- ** Atrito:** ALTO (secrets, permissões e runners geram erros obscuros).

---

**Encontro 14 — CD: build, integração e deploy**
- **Objetivo:** fechar o ponto de convergência do diagrama (Code + Model → Build).
- **Dor motivadora:** teste passa localmente, mas o deploy ainda é manual e frágil.
- **Em sala (4h):** Build & Integration Testing (onde `CODE` + `MODEL` se encontram) · deploy dev → prod (green) · trunk-based dev e versionamento · a esteira completa disparada por um push.
- **Casa:** completar a esteira de deploy; fazer um deploy dev de ponta a ponta. Preparar apresentação final.
- ** Atrito:** médio-alto.

---

### BLOCO 5 — Fechamento (Encontro 15)

---

**Encontro 15 — Monitoramento, o mapa completo e o que ficou de fora**
- **Objetivo:** fechar o ciclo (feedback loop) e situar o aluno no que ainda não sabe.
- **Dor motivadora:** o modelo em produção degrada silenciosamente com o tempo (model decay).
- **Em sala (4h):** monitoramento & logging (conceito + demo de drift com Evidently — **não** hands-on pesado) · o feedback loop e o "model decay trigger" do diagrama · o diagrama do ml-ops.org **inteiro aceso**, com o projeto de churn mapeado peça a peça · o que ficou de fora (Kubeflow/Kubernetes, LLMOps, cloud gerenciada/SageMaker) apontando para o material assíncrono · apresentações finais.
- **Casa:** —
- **Atrito:** baixo.

---

## 7. Onde as 60h apertam (leitura honesta)

- **Bloco 3 (Orquestração)** é o de maior risco de estouro. Airflow tem duas dificuldades somadas: setup (infra) **e** o modelo mental de agendamento (conceitual). Os três encontros (9–11) são o osso — não dá para comprimir para dois sem sacrificar fluência. Se algo atrasar no curso, o rombo vai aparecer aqui.
- **Encontros de ALTO atrito:** 3 (Docker), 9–10 (Airflow), 13 (CI/CD). Nesses, o checkpoint de sanidade e a preparação de casa são o que separa "aula produtiva" de "aula de suporte técnico".
- **A folga real** veio das 30h de casa. Sem elas, esta grade não caberia — foi o que permitiu não cortar orquestração nem CI/CD. Se a cobrança da casa falhar, o primeiro bloco a sofrer é o 3.

---

## 8. Material assíncrono (o "se virem sozinhos depois")

Pronto para entrega, **não** coberto em sala:
- Kubeflow / Kubernetes (orquestração em K8s) — com o aviso de que é 80% Kubernetes.
- LLMOps / RAG / Agentes — como MLOps aplicado a LLMs.
- Cloud gerenciada (SageMaker Pipelines, Experiments, Model Registry, Endpoints) — os análogos gerenciados de cada ferramenta open-source do curso.
- Jenkins — o CI/CD legado que aparece em empresas com infra antiga.

> Régua: o que é **essencial** para a competência terminal está nas 60h presenciais. O material assíncrono é enriquecimento para os aplicados — não continuação obrigatória. Se algo crítico cair aqui, não foi ensinado.

---
