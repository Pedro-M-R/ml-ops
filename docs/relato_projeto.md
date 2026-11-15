# Registro do desenvolvimento do Permanência

Foi realizado um trabalho para transformar uma análise de churn em uma aplicação
de consulta. O interesse do projeto está nessa passagem: além de treinar um
modelo, foi necessário preparar sua utilização por uma interface, organizar a
execução e escolher uma forma de disponibilizar o serviço pela internet.

Foi utilizada uma base de 7.043 clientes. O termo churn corresponde ao
cancelamento de um serviço, que foi o comportamento considerado no treinamento.
A consulta foi organizada a partir do código do cliente, aproveitando os dados
já cadastrados e evitando o preenchimento manual de todas as características.

## Construção da análise

Antes da comparação dos modelos, foi realizada a validação dos dados com
Pandera. Foi utilizado o DVC para relacionar o treinamento à versão da base,
e o tratamento das características foi incorporado ao pipeline. Dessa maneira,
a preparação utilizada nas previsões acompanha o modelo exportado.

Foram comparadas 22 configurações. Foi reservada uma parte da base para o teste
final, enquanto a seleção foi realizada por validação cruzada de cinco partes
nos dados de treinamento. A regressão logística apresentou o resultado escolhido
nesse processo e foi registrada no MLflow como `churn-champion`.

No teste com 1.761 registros, foram obtidos ROC AUC de 0,8467, acurácia de 77,91%
e F1 de 0,6212. O treinamento utilizou os outros 5.282 registros. Os resultados
e parâmetros podem ser conferidos em
[reports/selection.json](../reports/selection.json).

O MLflow foi utilizado para guardar os experimentos e a versão selecionada.
Foi exportado o pipeline completo, permitindo que o serviço de previsão
carregue o artefato já treinado.

## Utilização do modelo na aplicação

Foi desenvolvida a interface Permanência com Streamlit. A FastAPI ficou
responsável por disponibilizar os clientes e executar as previsões. Portanto,
os dados apresentados na tela são recebidos desse serviço, que aparece como
fonte da inferência.

Na apresentação, foi priorizada a leitura do resultado. A tendência de
permanência ou cancelamento é acompanhada pelas probabilidades e pelo limiar
utilizado na decisão. O padrão é 50%: a classe de churn é atribuída quando a
probabilidade alcança ou ultrapassa esse valor.

Foi incluída uma escala para relacionar a probabilidade ao limiar, além da
resposta original em JSON para conferência. Também foi disponibilizada a
classificação da carteira em lote, com exportação dos resultados. O modelo
foi preparado para estimar cancelamento, e não para avaliar inadimplência.

Para organizar a execução local, foi utilizado Docker Compose. Foi preparado
um contêiner para a API, outro para o painel e outro para o PostgreSQL. O banco
possui um volume persistente, e foi criado um usuário de leitura para a API.
Isso permite conservar a carteira entre recriações dos contêineres e restringir
as operações realizadas durante as consultas.

## Escolha do ambiente de publicação

A execução local depende do computador ligado. Por isso, foi necessária uma
etapa de hospedagem para permitir o acesso à demonstração fora desse ambiente.

Inicialmente, foi considerada a publicação na AWS, utilizando EC2 e
CloudFormation. Foram preparados os arquivos necessários para essa alternativa,
mas a implantação não foi concluída durante a configuração do ambiente. A
mensagem do erro não foi preservada, de modo que não foi possível confirmar
uma causa técnica específica para a dificuldade encontrada.

Foi utilizado o Render como alternativa para dar continuidade à publicação da
FastAPI. O Render é uma plataforma de hospedagem em nuvem que permite executar
aplicações a partir do código do repositório ou de uma imagem Docker. No
projeto, foi possível aproveitar a estrutura preparada para a API e o modelo
exportado. [Documentação da plataforma](https://render.com/docs/web-services)

A escolha reduziu a necessidade de administrar um servidor EC2 para apresentar
a aplicação. A interface Streamlit também foi publicada no Render, no endereço
[permanencia-jose.onrender.com](https://permanencia-jose.onrender.com/), em um serviço
separado da FastAPI. Nessa configuração, o painel utilizou a URL pública da API
para consultar os clientes e solicitar as previsões.

Posteriormente, foi retomada e concluída a implantação na AWS pela região Ohio
(`us-east-2`), utilizando o CloudShell no navegador. O pacote com código, modelo
e base foi enviado para um bucket S3 privado, e o CloudFormation criou a rede,
as permissões e a máquina EC2.

Nessa implantação, a criação de uma `t3.medium` foi recusada por não atender à
elegibilidade do plano gratuito da conta. Foram consultados os tipos disponíveis
e selecionada a `c7i-flex.large`, com 4 GiB de memória. O script e o template
foram ajustados para permitir essa opção.

Na EC2, o Docker Compose iniciou Streamlit, FastAPI e PostgreSQL. Foi realizada
a carga inicial dos clientes no banco, que passou a ser consultado pela API.
O painel ficou disponível em
[http://3.128.155.198:8501](http://3.128.155.198:8501). Inicialmente, o acesso
estava restrito ao IP da conexão de desenvolvimento. Foi adicionada uma regra
TCP na porta 8501 com origem `0.0.0.0/0`, e o acesso por outra rede foi confirmado.

A EC2 permite manter a demonstração funcionando com o computador local
desligado. A disponibilidade depende da instância em execução e das condições
da conta AWS, incluindo saldo e validade dos créditos. O histórico MLflow
permanece local; um servidor MLflow na EC2 ainda não foi publicado. O modelo
selecionado já acompanha a API e não depende desse servidor para prever.

As configurações do Render foram preservadas como alternativa de publicação.
O PostgreSQL gerenciado dessa plataforma recebeu um roteiro e um importador.
Sem banco configurado, a própria API pode ler o CSV, mantendo a FastAPI como
origem das consultas do painel.

## Conferência da entrega

Foram executados testes automatizados dos dados, do modelo, dos contratos da
API e das consultas na interface. Também foram realizadas verificações com
Docker e PostgreSQL, abrangendo a importação dos 7.043 clientes, a conservação
dos registros e a restrição de escrita da conta utilizada pela API.

Foi mantido no painel o conteúdo retornado pela FastAPI, permitindo relacionar
a interpretação visual aos números calculados pelo modelo. A documentação
de instalação e publicação foi organizada em guias separados, para facilitar
a reprodução do ambiente e a continuidade da hospedagem.
