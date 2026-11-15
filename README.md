# Permanência

### Da análise dos clientes a uma aplicação disponível na internet

Foi realizado o desenvolvimento de uma aplicação para consultar a tendência
de permanência de clientes em um serviço. O trabalho reuniu preparação de dados,
comparação de modelos e publicação de uma interface para apresentar as previsões.

**[Abrir o Permanência no Docker — http://127.0.0.1:8501](http://127.0.0.1:8501)**

Esse endereço abre a aplicação local. Para utilizá-lo, o Docker e os
contêineres do projeto precisam estar rodando no computador em que o link
for aberto. Ele não corresponde a um IP público de hospedagem.

O projeto partiu de uma base com **7.043 clientes**. A partir dos registros,
foi preparado um modelo para estimar o churn, termo utilizado para o
cancelamento de um serviço. O resultado do treinamento foi transformado em
um recurso de consulta, acessível pelo código de cada cliente.

## A decisão de levar o projeto para a internet

Executar o modelo no computador foi uma etapa do desenvolvimento. Para permitir
o acesso à demonstração sem manter esse computador ligado, foi realizada a
separação entre o ambiente local e os serviços de hospedagem.

Foi utilizado o **Render para a API** e o **Streamlit Community Cloud para o
painel**. O Render é uma plataforma que disponibiliza aplicações em servidores
na nuvem. No projeto, ele permite executar a FastAPI a partir da estrutura
Docker já preparada, oferecendo um endereço para receber as consultas.
[Conhecer o Render](https://render.com/docs/web-services)

A AWS havia sido considerada para a implantação com EC2. Entretanto, essa
publicação não foi concluída durante a configuração do ambiente.Foi então adotado o Render para dar continuidade à publicação
da aplicação, aproveitando o código e o modelo existentes.

Os arquivos destinados à AWS foram mantidos no repositório como alternativa
futura. A hospedagem adotada para a API utiliza o Render; a criação de uma EC2
não foi concluída nesta entrega.

## Uma consulta com informações para interpretar

Foi criada a interface Permanência para reunir a pesquisa do cliente e a leitura
da previsão em um mesmo lugar. A consulta utiliza o `customerID` cadastrado;
também foram disponibilizados códigos de exemplo retirados da própria base.

A **FastAPI é a fonte dos dados consultados e das previsões apresentadas**.
O Streamlit ficou responsável pela apresentação. O cálculo é executado pelo
modelo carregado na API, e os valores recebidos são utilizados na tela.

Foi dado destaque à tendência apontada pelo modelo, acompanhada das
probabilidades de churn e permanência. O limiar de 50% também é exibido para
explicar a classificação: valores de churn a partir desse ponto correspondem
à classe 1; abaixo dele, à classe 0. Uma escala permite visualizar a posição
da previsão em relação a esse limite.

Para permitir a conferência, foi mantida a resposta original da FastAPI em
JSON, com opção de download. A aplicação também permite consultar a carteira
completa e exportar as classificações. O uso previsto é a análise de tendência
de cancelamento, não a avaliação de inadimplência.

## O trabalho realizado antes da publicação

Foi preparada uma rotina de validação da base com Pandera e de controle dos
dados com DVC. O tratamento das características foi incorporado ao pipeline
do modelo, mantendo a mesma preparação no treinamento e na inferência.

Foram avaliadas **22 configurações**. A escolha utilizou validação cruzada
de cinco partes sobre o conjunto de treinamento. Os dados de teste ficaram
reservados para a avaliação após essa escolha. Foi selecionada uma
**regressão logística**, registrada no MLflow como `churn-champion`.

Na avaliação registrada, foram obtidos:

- **0,8467 de ROC AUC** no conjunto de teste;
- **77,91% de acurácia** no mesmo conjunto;
- **0,6212 de F1**;
- **5.282 registros para treinamento** e **1.761 para teste**.

A acurácia representa a proporção de classificações corretas nesse teste.
ROC AUC e F1 avaliam outros aspectos do desempenho e não devem ser lidos
como percentuais de acerto. O registro completo está em
[reports/selection.json](reports/selection.json).

O MLflow foi utilizado para manter os experimentos e a versão selecionada.
O pipeline exportado acompanha o projeto, permitindo iniciar a API sem
executar um novo treinamento a cada consulta.

## Organização da execução e dos clientes

Foi preparada uma instalação local com Docker Compose, reunindo painel,
API e PostgreSQL. O banco utiliza um volume para conservar os registros
entre recriações dos contêineres, e a API consulta a carteira com uma conta
somente de leitura.

O PostgreSQL em Docker foi implementado e validado no ambiente local. Também
foram preparados um importador e instruções para utilizar o PostgreSQL
gerenciado do Render. Essa opção ainda depende da criação do banco e da
configuração das credenciais na conta de hospedagem.

Enquanto não houver banco configurado, a própria API pode obter os clientes
do CSV distribuído com a aplicação. A tela continua utilizando a FastAPI como
fonte. Quando um PostgreSQL está configurado, uma falha de conexão é informada
em vez de substituir a base por outro arquivo.

Foi mantida uma distinção entre os dois ambientes: os contêineres do computador
dependem dele ligado, enquanto os serviços publicados executam nos servidores
do Render e do Streamlit Cloud. As condições do plano contratado continuam
valendo, incluindo os limites da modalidade gratuita.
[Condições do plano gratuito do Render](https://render.com/docs/free)

## Acessar os arquivos e continuar o projeto

O código da aplicação está em `src/churn/`, e o modelo publicado está em
`deployment/`. Os resultados das avaliações ficam em `reports/`; os scripts
de importação, verificação e empacotamento ficam em `scripts/`.

Foram realizados testes da preparação dos dados, do modelo, da FastAPI e da
interface. A integração local também foi conferida com o PostgreSQL, incluindo
a carga da carteira e o bloqueio de escrita pela conta da API. A suíte pode
ser executada na pasta do projeto com:

```powershell
uv sync --locked --python 3.13
uv run pytest -q
```

As instruções de instalação e publicação foram separadas por necessidade:

- [Iniciar o ambiente Docker com PostgreSQL](docs/postgres.md)
- [Publicar a API e conectar o painel](docs/deploy_render_streamlit.md)
- [Preparar o banco no Render](docs/deploy_render_postgres.md)
- [Consultar a alternativa de implantação AWS](docs/deploy_aws.md)
- [Ler o registro explicativo do desenvolvimento](docs/relato_projeto.md)
- [Consultar os exercícios anteriores](docs/historico_exercicios.md)
