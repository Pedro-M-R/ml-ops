# Permanência: apresentação do projeto completo

Fala de aproximadamente **7 a 8 minutos**, dependendo do ritmo. O [mapa do repositório](mapa_repositorio.md) explica cada pasta e arquivo para acompanhar a navegação no GitHub. Os [detalhes técnicos](apresentacao_mlflow.md) complementam este roteiro.

## Texto para apresentar

Olá! Vou apresentar o **Permanência**, um projeto que utiliza aprendizado de máquina para estimar a chance de um cliente cancelar um serviço, o chamado **churn**. A proposta foi desenvolver o modelo e organizar seu uso em uma aplicação que permite consultar a previsão pelo código do cliente. Vou explicar o papel das principais partes do repositório, desde os dados até a hospedagem atual na AWS.

O projeto utiliza uma base de **7.043 clientes**. A pasta `data` reúne o ponteiro do arquivo versionado pelo DVC. A pasta `frontend/data` contém uma cópia que acompanha a aplicação e serve para a carga inicial dos clientes. Não são duas carteiras diferentes: a cópia é preparada a partir da base do projeto. O alvo é cancelamento de serviço, e não inadimplência.

Antes de treinar, utilizamos **Pandera para validar os dados**. O código confere campos obrigatórios, tipos e regras, como tempo como cliente dentro do intervalo previsto, cobranças não negativas e respostas de churn com valores permitidos. Isso ajuda a impedir que dados incompatíveis avancem para o treinamento. Essa parte fica em `src/churn/data.py`.

O **Git versiona o código**, enquanto o **DVC identifica a versão dos dados**. A pasta `.dvc` contém a configuração desse controle. O treinamento compara o hash do CSV com o ponteiro DVC e interrompe a execução se os valores divergirem. Assim, o resultado fica relacionado ao dado realmente utilizado. O remote DVC configurado é local e precisa estar acessível para recuperar a base em outro computador.

Os arquivos de configuração também têm funções diferentes. O `.gitignore` evita enviar senhas e arquivos locais ao Git; o `.dockerignore` evita incluí-los na imagem. O `.gitattributes` padroniza aspectos dos arquivos entre sistemas. O `.python-version` indica Python 3.13, o `pyproject.toml` define dependências e comandos, e o `uv.lock` registra as versões resolvidas para reinstalar o ambiente.

No **MLflow**, os treinamentos passaram a guardar parâmetros, métricas e modelos. Isso permite comparar experimentos e identificar a origem dos resultados. O histórico atual fica local, em SQLite e na pasta de artefatos. O Git não precisa guardar todas as execuções; ele guarda o código e os relatórios selecionados para documentar a entrega.

A preparação dos dados e o classificador foram reunidos em um **pipeline do scikit-learn**. Valores numéricos ausentes são preenchidos pela mediana, os números são padronizados e as categorias são representadas com one-hot encoding. O identificador e a resposta histórica `Churn` ficam fora das entradas. O pipeline mantém as transformações aprendidas junto ao modelo para aplicá-las também na previsão.

Para selecionar o modelo, reservamos **75% da base para treinamento e 25% para teste**, preservando a proporção das classes. Foram 5.282 registros para treino e 1.761 para teste. Essa divisão equilibra dados para aprender e dados para a avaliação final, sem representar uma proporção obrigatória ou comprovadamente ideal.

A **validação ocorreu dentro do treino**, com cinco divisões. Em cada rodada, o candidato aprende com quatro partes e é avaliado na restante. Depois comparamos a média das métricas. O pré-processamento também é aprendido somente na parte de treino de cada rodada. Isso evita usar a validação para preparar o modelo e mantém o teste separado da escolha dos candidatos.

Foram comparados **22 candidatos**: seis regressões logísticas, nove Random Forests, seis HistGradientBoostings e uma referência simples. Com cinco divisões, foram 110 ajustes de validação, além do ajuste final do vencedor. A regressão logística venceu pela maior ROC-AUC média. A configuração escolhida utilizou `C` igual a 0,1 e regularização L2. A diferença para o segundo colocado foi pequena, sem demonstração formal de superioridade estatística.

No teste final, obtivemos **ROC-AUC de 0,8467 e acurácia de 77,91%**. O recall foi de 55,67%: identificamos 319 dos 573 churns reais. A precisão foi de 70,26%: dos 454 alertas, 319 correspondiam a churn. Esses resultados ficam em `reports`, junto ao ranking, à divisão dos dados e às verificações da aplicação.

A classificação usa um **limiar de 50%**. A API permite alterá-lo, mas o painel utiliza o padrão. A acurácia, a precisão e o recall apresentados usam esse corte; a ROC-AUC considera diferentes limiares. Uma campanha real ainda precisaria definir o corte conforme seus custos e benefícios.

O pipeline escolhido foi registrado no MLflow como **`churn-champion`, versão 1**, e exportado para `deployment`. Essa pasta contém o modelo treinado, suas dependências, a assinatura e uma cópia do código necessário para carregá-lo. Comparamos as probabilidades do original com as versões recarregadas para conferir a exportação. Esse código é uma fotografia do treinamento, enquanto `src/churn` contém o código atual da aplicação.

A **FastAPI** carrega o pipeline pronto uma vez na inicialização, valida as entradas e devolve as previsões. Também fornece rotas para buscar clientes, verificar a prontidão e consultar a documentação. O **Streamlit** apresenta o painel: o usuário informa o código, o cadastro vem da API e a previsão é solicitada ao mesmo serviço. A tela mostra probabilidades, classe, limiar e a resposta original para conferência. Não há treinamento a cada consulta.

O **PostgreSQL** armazena a carteira, consultada pela API com uma conta somente de leitura. A pasta `deploy/postgres` contém a inicialização do banco e da tabela. O volume conserva os dados entre recriações dos contêineres, mas continua sendo necessário backup fora da instância. A pasta `scripts` reúne tarefas auxiliares, como preparar a base, importar clientes, verificar a API e empacotar o projeto.

O **Docker Compose** organiza banco, API e painel. Um arquivo define a execução base, outro acrescenta o PostgreSQL e outro adapta as portas para a EC2. As verificações de prontidão coordenam a partida dos serviços. Na pasta `aws`, o CloudFormation descreve a infraestrutura e o bootstrap prepara a máquina e inicia os contêineres.

**A hospedagem principal atual é a AWS**, em uma EC2 na região Ohio. O pacote foi enviado por CloudShell a um S3 privado, e o painel recebeu acesso pela porta 8501. API e banco ficam na rede interna Docker. O Render foi uma etapa anterior; `render.yaml` e seus guias permanecem como alternativa. O histórico MLflow continua local, enquanto a API utiliza o modelo exportado.

Por fim, `tests` reúne os testes automatizados, e `docs` contém os guias de execução e o registro das decisões. Na revisão de 16 de novembro, 182 testes passaram. A grade de MLOps presente na raiz é um planejamento de curso: mencionar Airflow ou integração contínua nesse material não significa que essas partes estejam implementadas no projeto.

A principal entrega foi conectar dados validados e um treinamento rastreável a uma aplicação consultável na internet. Os próximos passos são definir o limiar por critérios de negócio, avaliar clientes novos e melhorar a operação com monitoramento, backup automático e controle de acesso.

## Ordem para navegar no GitHub

1. **README:** objetivo, acesso e hospedagem atual na AWS.
2. **`data`, `.dvc` e configurações da raiz:** origem dos dados e reprodução do ambiente.
3. **`src/churn`:** validação, pipeline, seleção, API e interface.
4. **`reports` e `deployment`:** evidências dos resultados e modelo exportado.
5. **`frontend`, `deploy/postgres` e arquivos Docker:** interface, armazenamento e execução.
6. **`aws`:** infraestrutura e inicialização na nuvem.
7. **`scripts`, `tests` e `docs`:** tarefas auxiliares, verificações e instruções.

Para explicar um arquivo específico, consulte o [mapa completo do repositório](mapa_repositorio.md). A publicação e o acesso externo descritos aqui seguem o registro da implantação; esta revisão não realizou um novo deploy nem uma confirmação atual do IP público.
