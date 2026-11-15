# Desenvolvimento e publicação do projeto Permanência

## Objetivo da aplicação

Foi desenvolvido um projeto de aprendizado de máquina para estimar a chance de
cancelamento de um serviço por um cliente. Esse tipo de cancelamento recebe o
nome de churn. O objetivo foi transformar um modelo treinado em uma aplicação
que pudesse ser consultada pela internet, com um resultado fácil de interpretar.

Foi utilizada uma base de 7.043 clientes. Na aplicação, a consulta é realizada
pelo código do cliente, sem necessidade de preencher manualmente todas as
características do cadastro. O resultado apresenta a probabilidade de churn,
a probabilidade de permanência e a classe definida pelo modelo.

## Organização do fluxo

Foi realizada a divisão do sistema em três responsabilidades. O Streamlit foi
utilizado para apresentar a tela. A FastAPI ficou responsável por disponibilizar
os clientes e executar as previsões. O armazenamento foi preparado em PostgreSQL,
mantendo também a possibilidade de utilizar o CSV no backend quando o banco
ainda não estiver configurado.

O caminho da consulta pode ser representado assim:

**Código do cliente → Streamlit → FastAPI → base e modelo → resultado no painel.**

A fonte da inferência apresentada na interface é a **FastAPI**. A tela envia
uma solicitação e recebe uma resposta JSON com os valores calculados. Dessa
forma, a previsão não é inventada na interface e a resposta pode ser conferida.

## Preparação e escolha do modelo

Foi realizada a validação da estrutura dos dados antes do treinamento. Também
foi mantido o controle da versão da base com DVC, para relacionar o treinamento
ao arquivo utilizado.

Foram comparadas 22 configurações, com validação cruzada de cinco partes no
conjunto de treinamento. O conjunto de teste foi reservado para a avaliação
após a seleção. Essa separação evita escolher o modelo a partir do resultado
que deveria representar sua avaliação final.

O modelo selecionado foi uma regressão logística. Foram obtidos ROC AUC de
0,8265 na validação cruzada e 0,8467 no teste. A acurácia no teste foi de 77,91%.
As métricas foram registradas no MLflow, e o pipeline completo foi exportado
para ser carregado pela API. Os números estão em
[reports/selection.json](../reports/selection.json).

## Docker e PostgreSQL

Foi utilizada a conteinerização para organizar a execução da API, do painel e
do PostgreSQL. Com o Docker Compose, os serviços podem ser iniciados a partir
da mesma configuração, respeitando a ordem de disponibilidade do banco e da API.

Foi criado um volume para preservar a carteira entre recriações dos
contêineres. A importação inicial do CSV ocorre quando o volume do banco é
preparado pela primeira vez. O usuário utilizado pela API recebe somente
permissão de leitura sobre os clientes.

O Docker local depende do computador ligado. A hospedagem pública foi tratada
separadamente, para que o acesso à aplicação não dependesse da execução no PC.

## Dificuldade encontrada na AWS

Foi preparada uma alternativa de implantação na AWS com EC2, CloudFormation e
Docker. Entretanto, a publicação não foi concluída durante as tentativas de
configuração do ambiente.

A mensagem exata da falha não foi preservada. Por esse motivo, não foi
confirmada uma causa específica, como problema de credencial, permissão ou
ativação de serviço. O guia do projeto contém orientações para o erro
`OptInRequired`, mas esse código não foi confirmado como o erro ocorrido.
Na documentação oficial da AWS, ele está relacionado à necessidade de habilitar
o serviço na conta. [Referência do CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/CommonErrors.html)

Diante da dificuldade de concluir essa etapa, foi adotado outro caminho de
publicação para permitir a continuidade e a apresentação do projeto. Os
arquivos AWS foram preservados para uma implantação futura.

## O que é o Render

O Render é uma plataforma de hospedagem que executa aplicações em servidores
na nuvem. Foi utilizado para publicar a FastAPI a partir do código do projeto,
aproveitando a imagem Docker e o modelo preparado.

A plataforma oferece endereço público com HTTPS e integração com o GitHub para
publicação de versões. Também disponibiliza PostgreSQL gerenciado, que pode
ser conectado à API. [Serviços web do Render](https://render.com/docs/web-services)

## Motivo da escolha do Render

Foi utilizado o Render para dar continuidade à hospedagem da API enquanto a
alternativa AWS não estava concluída. A escolha permitiu aproveitar a estrutura
existente do projeto e reduzir o trabalho de administração de um servidor EC2.

A interface foi publicada no Streamlit Community Cloud, mantendo um endereço
de acesso simples. Nesse formato, o Streamlit apresenta os dados e consulta a
FastAPI hospedada no Render. O computador utilizado no desenvolvimento pode
ser desligado sem encerrar os serviços que já estiverem publicados nessas plataformas.

O Render foi adotado como alternativa de hospedagem da aplicação. Essa escolha
não equivale à execução de uma EC2, pois a infraestrutura é administrada de
outra forma pela plataforma.

## Situação da publicação

Foi publicado o painel em [mlopsjose.streamlit.app](https://mlopsjose.streamlit.app/)
e foi adotado o Render para a API. As atualizações implementadas precisam
concluir o deploy nos serviços conectados ao GitHub para aparecerem online.

O PostgreSQL em Docker foi validado localmente. Para utilizá-lo como serviço
gerenciado no Render, foram preparados um importador de clientes e um roteiro
de conexão. A criação desse banco e a configuração de suas credenciais ainda
são etapas da conta Render, descritas no
[guia de publicação com PostgreSQL](deploy_render_postgres.md).

No plano gratuito, o serviço web do Render pode suspender após 15 minutos sem
tráfego. O PostgreSQL gratuito expira após 30 dias. Essas limitações devem ser
consideradas ao manter a demonstração disponível.
[Limites da modalidade gratuita](https://render.com/docs/free)

## Verificações realizadas

Foram realizados testes automatizados da preparação dos dados, do modelo, das
rotas da API e do fluxo do painel. Também foram verificadas a importação dos
7.043 clientes, a preservação dos registros após a recriação dos contêineres e
a restrição de escrita do usuário utilizado pela API.

Foi conferido que o resultado apresentado no painel utiliza os valores
devolvidos pela FastAPI, incluindo a probabilidade, o limiar e a classe. A
resposta original em JSON foi mantida para permitir a conferência dos dados.

O projeto permite consultar um modelo treinado por uma aplicação online,
mantendo separadas as etapas de treinamento, inferência, armazenamento e
hospedagem. As previsões representam estimativas de cancelamento e não devem
ser interpretadas como garantia de comportamento futuro de um cliente.
