# Permanência

### Da análise dos clientes a uma aplicação disponível na internet

Foi realizado o desenvolvimento de uma aplicação para consultar a tendência
de permanência de clientes em um serviço. O trabalho reuniu preparação de dados,
comparação de modelos e publicação de uma interface para apresentar as previsões.

**[Acessar o front-end](http://3.128.155.198:8501)**

**[Roteiro de apresentação do projeto completo](docs/apresentacao_projeto.md)**

[Mapa das pastas e arquivos do repositório](docs/mapa_repositorio.md) ·
[Detalhes técnicos a partir do MLflow](docs/apresentacao_mlflow.md)

O painel está hospedado em uma máquina virtual EC2 na AWS e pode ser acessado
por outras pessoas, inclusive fora da rede utilizada no desenvolvimento.
A aplicação permanece disponível enquanto a EC2 estiver em funcionamento,
independentemente do computador local. O IP pode mudar ao parar e iniciar a
instância; nesse caso, o link precisa ser atualizado.

O projeto partiu de uma base com **7.043 clientes**. A partir dos registros,
foi preparado um modelo para estimar o churn, termo utilizado para o
cancelamento de um serviço. O resultado do treinamento foi transformado em
um recurso de consulta, acessível pelo código de cada cliente.

## Hospedagem atual na AWS

**A aplicação está hospedada na AWS, em uma EC2 na região Ohio (`us-east-2`).**
Docker Compose inicia os três serviços na mesma máquina: Streamlit para o painel,
FastAPI para consultas e previsões e PostgreSQL para armazenar os clientes.
Essa publicação permite acessar a demonstração sem manter o computador de
desenvolvimento ligado.

Foi utilizada uma instância `c7i-flex.large`, com 4 GiB de memória. Na implantação,
a opção inicial `t3.medium` foi recusada por elegibilidade do plano da conta, e o
tipo foi ajustado após a consulta às opções disponíveis na região.

Somente o painel recebe acesso externo, na porta 8501. A API e o PostgreSQL
se comunicam pela rede interna Docker. O modelo exportado acompanha a API;
o histórico de experimentos MLflow permanece no ambiente local.

O Render fez parte de uma etapa anterior. Seus arquivos foram preservados
como alternativa e registro do desenvolvimento; **a hospedagem principal atual
é a AWS**. O procedimento de implantação e atualização está no
[guia AWS](docs/deploy_aws.md).

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
O histórico dos experimentos permanece no ambiente local; a publicação de
um servidor MLflow na EC2 ainda não foi realizada.

## Organização da execução e dos clientes

Foi utilizada a mesma organização com Docker Compose no ambiente local e na
EC2: um contêiner para o painel, outro para a API e outro para o PostgreSQL.
O banco utiliza um volume para conservar os registros entre recriações dos
contêineres, e a API consulta a carteira com uma conta somente de leitura.

Na hospedagem AWS, os clientes são importados do CSV para o PostgreSQL na
primeira inicialização. O painel solicita os dados à FastAPI, que consulta
o banco pela rede interna do Docker e executa o modelo treinado.

Para a alternativa no Render, foram mantidos um importador e um guia para o
PostgreSQL gerenciado. Sem um banco configurado, a API pode obter os clientes
do CSV distribuído com a aplicação. Quando um PostgreSQL está configurado,
uma falha de conexão é informada em vez de substituir a base por outro arquivo.

Foi mantida uma distinção entre os dois ambientes: os contêineres do computador
dependem dele ligado, enquanto os serviços publicados executam na EC2.
A elegibilidade ao plano gratuito da AWS não representa hospedagem ilimitada;
o consumo e a validade dos créditos precisam ser acompanhados na conta.

| Componente | Situação atual |
| --- | --- |
| Streamlit | Painel público na EC2 |
| FastAPI e modelo | Contêiner na mesma EC2 |
| PostgreSQL | Contêiner na EC2, acessado internamente pela API |
| MLflow | Histórico local; modelo selecionado exportado para a API |

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

- [Apresentar o projeto completo, com uma fala simples por etapa](docs/apresentacao_projeto.md)
- [Entender a função de cada pasta e arquivo](docs/mapa_repositorio.md)
- [Iniciar o ambiente Docker com PostgreSQL](docs/postgres.md)
- [Publicar na AWS e configurar o acesso público](docs/deploy_aws.md)
- [Consultar a alternativa de publicação no Render](docs/deploy_render_streamlit.md)
- [Preparar o banco no Render](docs/deploy_render_postgres.md)
- [Ler o registro explicativo do desenvolvimento](docs/relato_projeto.md)
- [Consultar os exercícios anteriores](docs/historico_exercicios.md)
