# Streamlit + FastAPI + PostgreSQL na AWS

## Implantação atual

O painel público está disponível em [http://3.128.155.198:8501](http://3.128.155.198:8501).
Foi utilizada uma EC2 `c7i-flex.large`, com 4 GiB de memória, na região Ohio
(`us-east-2`), criada pela stack `permanencia-aws`. A publicação foi realizada
pelo CloudShell com o pacote do projeto. O acesso pela rede móvel foi confirmado.

Streamlit, FastAPI e PostgreSQL executam em contêineres na mesma EC2. O modelo
exportado acompanha a API. O histórico MLflow permanece local, e seu servidor
ainda não foi incluído nessa implantação. O IP informado pode mudar após parar
e iniciar a instância.

O deploy agora também inicia o PostgreSQL em Docker. A carteira é importada do CSV
na primeira inicialização e consultada pelo painel através da API. Consulte
[arquitetura, comparação com a referência e execução local](postgres.md).
Os três serviços ficam na mesma EC2, com banco e API na rede interna Docker.
O painel mostra **Fonte: FastAPI**: ele obtém os clientes e as previsões pela API.
O armazenamento fica no PostgreSQL; sem banco configurado, a API pode ler o CSV.

Para hospedar sem AWS, use o [passo a passo de Render + Streamlit Cloud](deploy_render_streamlit.md).
Para incluir o banco na alternativa de hospedagem no Render, use [PostgreSQL no Render](deploy_render_postgres.md).

No modo local com CSV, o painel **Permanência** usa os clientes já existentes em `data/churn.csv`.
No deploy EC2, esses clientes são importados no PostgreSQL na primeira inicialização.
O layout tem fundo claro, tons de verde e duas colunas: apresentação e resumo
da base à esquerda; consulta e resultado à direita. O botão **Consultar** usa
automaticamente o perfil já cadastrado.
Digite o código do cliente (`customerID`) ou clique em um dos códigos reais
mostrados como exemplo. A tela busca o perfil na base e chama `POST /predict`
da FastAPI com o modelo já treinado; não é necessário preencher características
nem treinar novamente. Um código desconhecido exibe uma mensagem e não chama
o modelo com dados inventados.

O resultado mostra a chance de cancelar, a chance de permanecer e a classificação.
Em **Ver resposta original da API**, o JSON mantém os valores recebidos da
FastAPI, com download. **Ver dados utilizados na análise** mostra o registro
enviado ao modelo. A classe
`0` significa tendência de permanecer cliente (continuar pagando pelo serviço);
`1` significa tendência de cancelar. O alvo `Churn` não mede inadimplência.
A coluna histórica `Churn` é removida antes da previsão. O limiar é `0.5`,
igual ao padrão da API. O painel usa a classe recebida da API.
Em **Consultar a base completa**, clique em **Classificar toda a base** para
consultar todos os registros e baixar a tabela em CSV.
Para usar outro arquivo local, configure `CHURN_DATA_PATH` no processo Streamlit.
O site inclui a cópia `frontend/data/churn.csv`, com os mesmos clientes da base
original. Ela é usada automaticamente quando o CSV do DVC não existe, inclusive
na imagem Docker. Ao atualizar a base original, execute
`python -m uv run python scripts/preparar_base_painel.py` antes de publicar.

## Executar no computador

Os comandos precisam ser executados na pasta que contém `pyproject.toml`.
Se o terminal está em `trabalhojose`, entre primeiro na subpasta do projeto:

```powershell
Set-Location .\ml-ops
```

Se aparece `(.venv-1)` no início do terminal, execute `deactivate`. Não é
necessário ativar um ambiente para usar `uv`. Na pasta `ml-ops`, instale as
dependências e inicie a API:

```powershell
python -m uv sync --locked --python 3.13
python -m uv run churn-serve
```

Em outro terminal, entre também na pasta `ml-ops` antes de iniciar o painel:

```powershell
python -m uv run churn-dashboard
```

Abra http://127.0.0.1:8501. A API fica em http://127.0.0.1:8000.
Se a API estiver em outro endereço, configure `CHURN_API_URL` no terminal do
Streamlit antes de iniciar. O navegador fala apenas com o Streamlit; quem chama
a API é o servidor Python, portanto não é necessário liberar CORS.

```powershell
$env:CHURN_API_URL = 'http://127.0.0.1:8000'
python -m uv run churn-dashboard
```

Se o OneDrive impedir a atualização de `.venv`, use o mesmo ambiente externo
nos dois terminais, sempre dentro de `ml-ops` e após desativar `(.venv-1)`:

```powershell
$env:UV_PROJECT_ENVIRONMENT = Join-Path $env:LOCALAPPDATA 'churn-dashboard-venv'
python -m uv sync --locked --python 3.13
python -m uv run churn-serve
```

No segundo terminal, dentro de `ml-ops`:

```powershell
$env:UV_PROJECT_ENVIRONMENT = Join-Path $env:LOCALAPPDATA 'churn-dashboard-venv'
python -m uv run churn-dashboard
```

`No pyproject.toml found` significa que o terminal está fora da pasta do
projeto. `Failed to spawn: churn-serve` ou `churn-dashboard` pode aparecer
quando o projeto não foi encontrado ou a instalação não foi concluída.
Corrija a pasta e conclua `uv sync` antes de executar os serviços.

Se `churn-serve` informar `WinError 10048` na porta 8000, já existe um processo
usando essa porta. Confira a API em outro terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Se a API deste projeto já estiver rodando e retornar `status: ok`, mantenha-a
aberta e execute somente `churn-dashboard`. Para usar outra porta, inicie a API
com `python -m uv run churn-serve --port 8001` e, no terminal do painel, configure
`$env:CHURN_API_URL = 'http://127.0.0.1:8001'` antes de iniciar o Streamlit.

Com Docker Desktop/Engine iniciado, os dois serviços também podem subir juntos:

```powershell
docker compose up --build -d api dashboard
docker compose logs -f api dashboard
```

Para encerrar: `docker compose down`. As portas locais são 8000 e 8501.

## Criar a infraestrutura AWS

O template `aws/cloudformation.yaml` cria uma VPC, uma sub-rede pública, rota
de internet, security group, IAM role e uma EC2 Amazon Linux 2023. A instância
usa Docker Compose e três contêineres com reinício automático. API e banco não publicam portas
na EC2. Só o Streamlit, na porta 8501, aceita conexões da rede IPv4/CIDR indicada.
O acesso administrativo é pelo AWS Systems Manager Session Manager, sem chave
SSH. O pacote com código e modelo fica em um bucket S3 privado da sua conta.

Pré-requisitos:

- Conta AWS com região habilitada e AWS CLI v2 instalada.
- Perfil autenticado com `aws login` (acesso pelo console) ou, se a conta usa
  IAM Identity Center, `aws configure sso` e `aws sso login`.
- Permissões para CloudFormation, EC2/VPC, IAM (incluindo PassRole), S3 e leitura
  do parâmetro público SSM da AMI. O usuário do console também precisa de
  permissão de Session Manager para administrar a instância.
- `deployment/` e o modelo indicado em `reports/selection.json` disponíveis.
  Os modelos são ignorados pelo Git: o script inclui o artefato local no ZIP.
- Seu IP público IPv4. Use a faixa `SEU_IP_PUBLICO/32` para acesso individual.
  O IP privado do Wi-Fi, como `192.168.x.x`, não é o IP público.

O comando abaixo **cria recursos pagos**. O padrão é `t3.medium` com 4 GiB de RAM
e 30 GiB de disco gp3; há cobranças de EC2, EBS, IPv4 público, S3 e transferência
conforme o uso. Consulte os valores da região na sua conta. Não há promessa de
enquadramento no Free Tier. Para uma demonstração pequena é possível passar
`--instance-type t3.small`, com menos memória para build e execução.

### Contas no plano gratuito da AWS

O padrão `t3.medium` não é elegível ao Free Tier e pode ser recusado em uma conta
restrita ao plano gratuito. Antes de publicar, consulte as opções da região:

```bash
aws ec2 describe-instance-types --region us-east-2 \
  --filters "Name=free-tier-eligible,Values=true" "Name=processor-info.supported-architecture,Values=x86_64" \
  --query 'InstanceTypes[].{Tipo:InstanceType,MemoriaMiB:MemoryInfo.SizeInMiB}' \
  --output table --no-cli-pager
```

Quando aparecer como elegível, `--instance-type c7i-flex.large` mantém 4 GiB de
memória. Também foi permitido `m7i-flex.large`, com 8 GiB. A seleção depende das
opções retornadas pela AWS e do orçamento; elegibilidade não significa execução
gratuita por tempo ilimitado. Acompanhe os créditos e a validade no painel da conta.
Os tipos ARM não foram incluídos porque a AMI e o bootstrap deste deploy são x86_64.

Se a criação falhar por elegibilidade, corrija o tipo e aguarde a stack chegar a
`ROLLBACK_COMPLETE`. Como essa tentativa não criou a aplicação, exclua apenas a
stack dessa tentativa e aguarde `stack-delete-complete` antes de reutilizar seu nome.
O bucket privado de pacotes fica fora da stack e pode ser reutilizado. Uma stack
que já tenha hospedado dados exige backup e análise antes da exclusão.

Referência: [Free Tier para EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html).

### Publicar pelo CloudShell no navegador

Foi esse o caminho utilizado na implantação atual. Os comandos de criação abaixo
são para uma instalação nova; para a stack existente, siga a seção de atualização.

1. Gere o pacote do projeto no computador com
   `uv run python scripts/deploy_aws.py --prepare-only`.
2. No console AWS, selecione Ohio e abra o CloudShell. A sessão já utiliza a
   identidade autenticada no console, sem `aws login` dentro desse terminal.
3. Em **Ações → Upload file**, envie `dist/churn-portatil.zip`.
4. No terminal do CloudShell, extraia e entre na pasta:

   ```bash
   unzip churn-portatil.zip
   cd churn-portatil
   ```

5. Abra `https://checkip.amazonaws.com/` no navegador do computador e copie seu
   IPv4. Substitua o texto no comando abaixo pelo número recebido. Consultar
   esse endereço pelo CloudShell retornaria o IP do ambiente AWS.

   ```bash
   IP_PUBLICO="SEU_IPV4_PUBLICO"
   python3 scripts/deploy_aws.py --region us-east-2 --stack-name permanencia-aws \
     --instance-type c7i-flex.large --allowed-cidr "${IP_PUBLICO}/32"
   ```

6. Acompanhe a stack `permanencia-aws` no CloudFormation. Depois de
   `CREATE_COMPLETE`, aguarde a instalação e teste o endereço de `DashboardUrl`
   no navegador do computador autorizado. O acesso a outras redes é tratado
   na seção de rede deste guia.

### Passos no Windows

1. Instale a [AWS CLI v2 para o usuário atual](https://awscli.amazonaws.com/AWSCLIV2-User.msi).
   Feche e reabra o PowerShell (ou o VS Code, se o terminal não reconhecer `aws`).
   Confira a instalação com `aws --version`. O comando `aws login` exige versão
   2.32.0 ou posterior.
2. Para acesso normal pelo console, rode o comando abaixo e complete o login
   e o MFA no navegador. O perfil `faculdade` é apenas um nome local; pode ser
   usado também para uma conta pessoal. Use uma identidade autorizada a criar
   os recursos do projeto. Para IAM users/roles, o login também requer a policy
   `SignInLocalDevelopmentAccess`.

   ```powershell
   aws login --profile faculdade --region us-east-2
   ```

   Se seu acesso é por IAM Identity Center da faculdade/empresa, use esta
   alternativa em vez de `aws login`. Informe a Start URL e a região SSO dadas
   pelo administrador, escolha a conta e a role autorizadas, e use `us-east-2`
   como região padrão dos recursos. A região SSO pode ser diferente.

   ```powershell
   aws configure sso --profile faculdade
   aws sso login --profile faculdade
   ```

3. Confirme a conta autenticada:

   ```powershell
   aws sts get-caller-identity --profile faculdade --region us-east-2 --no-cli-pager
   ```

   Deve aparecer um JSON com `Account` e `Arn`. Isso confirma a autenticação,
   mas não garante as permissões de criação. Contas educacionais podem bloquear
   IAM/VPC; nesses casos o administrador precisa liberar as permissões listadas
   nos pré-requisitos ou adaptar a implantação à infraestrutura permitida.
4. Abra um terminal livre e prepare o projeto. Neste computador:

   ```powershell
   cd "C:\Users\Pedro\OneDrive\Área de Trabalho\trabalhojose\ml-ops"
   $env:UV_PROJECT_ENVIRONMENT = "$env:LOCALAPPDATA\churn-dashboard-venv"
   python -m uv sync --locked --python 3.13
   python -m uv run python scripts/deploy_aws.py --prepare-only
   ```

   O último comando verifica que o pacote pode ser gerado, sem criar recursos.
   Não é necessário instalar Docker localmente para o script de publicação:
   o build será feito na EC2.
5. Descubra seu IPv4 público e publique. O comando de publicação cria recursos
   e usa explicitamente a `c7i-flex.large`; confira antes a elegibilidade na conta:

   ```powershell
   $ipPublico = (curl.exe -4 -fsS https://checkip.amazonaws.com).Trim()
   Write-Output "Rede autorizada: ${ipPublico}/32"
   python -m uv run python scripts/deploy_aws.py --profile faculdade --region us-east-2 --stack-name permanencia-aws --instance-type c7i-flex.large --allowed-cidr "${ipPublico}/32"
   ```

   Execute a publicação somente depois de confirmar que o comando de IP retornou
   um IPv4 válido. Mantenha a mesma rede/VPN durante a publicação e o acesso.
6. Aguarde o endereço `http://IP_DA_EC2:8501` no terminal. No console AWS, consulte
   **CloudFormation → permanencia-aws → Outputs → DashboardUrl**, na região Ohio.
   Abra esse endereço, confirme **Modelo disponível** e teste uma previsão. Após a
   implantação, a aplicação roda na EC2 independentemente do computador local.

Sem `--profile`, a AWS CLI usa sua cadeia normal de credenciais. Nunca coloque
chaves AWS no código, Dockerfile ou pacote. Não é preciso informar senhas ao script.

O script valida o template na AWS, cria/reutiliza um bucket privado específico
da conta e stack, envia o ZIP com chave SHA-256 e solicita a stack indicada.
Depois aguarda a infraestrutura e verifica `/_stcore/health` do Streamlit. O build
na EC2 pode levar vários minutos. O endereço e o link do Session Manager são
impressos e também aparecem em **CloudFormation → stack → Outputs**.

`CREATE_COMPLETE` confirma a infraestrutura; a aplicação termina de instalar
depois. Acesse o painel, confirme **Modelo disponível** e faça uma análise. Se o
comando for interrompido, consulte a stack antes de tentar novamente: recursos
já criados podem continuar ativos e gerando cobrança.

Para gerar e revisar somente o pacote, sem acessar a AWS:

```powershell
python -m uv run python scripts/deploy_aws.py --prepare-only
```

O resultado fica em `dist/churn-portatil.zip` e inclui os arquivos `aws/` e
`.streamlit/`. A cópia da base usada pelo painel, em `frontend/data/churn.csv`,
também é incluída. O arquivo original do DVC em `data/` exige `--include-data`
no script `scripts/empacotar.py`.

## Rede, HTTPS e uso

O script cria inicialmente uma implantação HTTP, sem login, restrita à rede
informada em `AllowedCidr`. Na demonstração publicada, foi adicionada ao grupo
de segurança da EC2 uma regra TCP para a porta 8501 com origem `0.0.0.0/0`.
Essa regra permite o acesso ao painel por outras conexões de internet. API e
PostgreSQL continuam na rede interna do Docker.

Para conferir as regras pelo CloudShell:

```bash
GRUPO=$(aws cloudformation describe-stack-resource \
  --stack-name permanencia-aws --logical-resource-id SecurityGroup \
  --region us-east-2 --query 'StackResourceDetail.PhysicalResourceId' --output text)
aws ec2 describe-security-groups --group-ids "$GRUPO" --region us-east-2 \
  --query 'SecurityGroups[0].IpPermissions' --output json --no-cli-pager
```

Antes de adicionar uma regra pública, confira se o grupo está associado somente
à EC2 da aplicação. Alterações manuais no grupo devem ser consideradas em futuras
atualizações pelo CloudFormation, pois a regra adicional não está no template.
Para testar outra rede, abra o endereço HTTP no celular com o Wi-Fi desligado.

Quando o script é executado no CloudShell e `AllowedCidr` permite apenas o IP do
computador, a verificação HTTP feita pelo script pode expirar. Isso não interrompe
os contêineres na EC2. Confirme a aplicação pelo navegador autorizado e pelos logs;
evite repetir a criação de uma stack que já chegou a `CREATE_COMPLETE`.

Use dados de demonstração. Para expor a usuários externos com dados reais, configure
um domínio, HTTPS e autenticação antes de ampliar o acesso. A aplicação não grava
os CSVs enviados no disco, mas o processamento e os resultados ficam na memória
da sessão do Streamlit. Não são mantidos após o encerramento da sessão.

O IP público pode mudar após parar/iniciar a EC2; consulte novamente os Outputs.
Se seu IP de acesso mudar, atualize o parâmetro `AllowedCidr` da stack pelo
console CloudFormation, mantendo os demais parâmetros e o template atual.
O script aceita criação de stacks novas; ele recusa substituir uma stack existente.

## Erro OptInRequired antes da criação da stack

Se a autenticação funcionar, mas `DescribeStacks` retornar `OptInRequired`
com a mensagem `The AWS Access Key Id needs a subscription for the service`,
a AWS está recusando o acesso ao serviço no nível da conta. Esse erro não é
causado pelo Streamlit, pelo IP autorizado ou pelo aviso de ambiente virtual.
Segundo a [documentação do CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/CommonErrors.html),
é necessário verificar a habilitação do serviço na conta.

1. Abra o [CloudFormation em Ohio](https://us-east-2.console.aws.amazon.com/cloudformation/home?region=us-east-2)
   com a mesma conta do perfil e confira se aparece uma solicitação de concluir
   cadastro, ativação ou verificação.
2. Complete somente as etapas pendentes exibidas pela AWS. Confira o e-mail de
   ativação e eventuais solicitações de verificação; se a AWS solicitar dados
   de pagamento, preencha-os diretamente no console.
3. Se a conta foi criada recentemente, a ativação pode levar até 24 horas,
   conforme a [documentação de criação da conta](https://docs.aws.amazon.com/accounts/latest/reference/getting-started.html).
4. Se o cadastro já está concluído e o erro persistir, abra um chamado de
   **Account and billing support** no [AWS Support](https://console.aws.amazon.com/support/home),
   informando serviço CloudFormation, região `us-east-2`, operação `DescribeStacks`
   e código `OptInRequired`.

Antes de repetir a publicação, faça apenas esta consulta, que não cria recursos:

```powershell
aws cloudformation list-stacks --profile faculdade --region us-east-2 --max-items 5 --no-cli-pager
```

Uma resposta JSON, mesmo com lista vazia, confirma que essa consulta foi liberada.
Se retornar `OptInRequired`, a pendência ainda não foi resolvida. O script para
antes de criar o bucket e a stack quando esse erro ocorre em `DescribeStacks`.
Não é necessário alterar o template ou criar novas chaves para tratar esse erro.

## Diagnóstico e atualização

Abra a EC2 pelo link do Session Manager e execute:

```bash
sudo tail -n 100 /var/log/churn-bootstrap.log
cd /opt/churn/churn-portatil
sudo docker compose -p churn -f docker-compose.yml -f compose.postgres.yml -f compose.ec2.yml ps
sudo docker compose -p churn -f docker-compose.yml -f compose.postgres.yml -f compose.ec2.yml logs --tail 100 postgres api dashboard
sudo docker compose -p churn -f docker-compose.yml -f compose.postgres.yml -f compose.ec2.yml exec -T api python scripts/verificar_postgres.py
```

Se o log ainda não existir, veja `/var/log/cloud-init-output.log`. Falha no download
do pacote deve ser investigada no cloud-init; a instalação e o build ficam no log
de bootstrap. O perfil de instância lê somente a chave S3 usada nesta implantação.

Para atualizar manualmente código/modelo, gere e envie um novo ZIP privado com
a AWS CLI da máquina local. Atualize a política `ReadDeploymentBundle` da role
da instância para permitir a nova chave S3, ou mantenha a chave original
reescrevendo seu objeto (nesse caso ela deixa de identificar o conteúdo pelo hash).
Na sessão administrativa, baixe o pacote autorizado, extraia em `/opt/churn` e rode:

```bash
cd /opt/churn
sudo unzip -o bundle.zip
sudo bash churn-portatil/aws/bootstrap.sh
```

O bootstrap reconstrói a imagem e substitui os contêineres; há uma breve
indisponibilidade. O volume e as senhas existentes são preservados; atualizar o
CSV do pacote não substitui os registros já carregados. Veja o procedimento de
[backup do PostgreSQL](postgres.md#deploy-e-backup-na-ec2). Para uma implantação independente, use um novo `--stack-name`
no script, verifique o novo endereço e exclua a stack anterior quando terminar.

## Encerrar os recursos

Exclua a stack pelo CloudFormation ou com o comando abaixo. Isso encerra a EC2 e
remove o disco, a rede e a role criados por ela. A exclusão é irreversível.
O PostgreSQL também usa esse disco: faça um backup externo antes de excluir a stack.

```powershell
aws cloudformation delete-stack --stack-name permanencia-aws --region us-east-2 --profile faculdade
aws cloudformation wait stack-delete-complete --stack-name permanencia-aws --region us-east-2 --profile faculdade
```

O bucket de artefatos foi criado fora da stack e permanece. Exclua seus objetos e
o bucket pelo console S3 quando não precisar mais deles; o nome segue o padrão
`churn-ID_DA_CONTA-permanencia-aws`. Não remova buckets de outros projetos.

## Referências

Valide a suíte com `uv run pytest -q` e a integração Docker com
`scripts/verificar_postgres.py`, conforme [o guia do banco](postgres.md).
O teste local do Docker não confirma o provisionamento na AWS: este requer
executar o deploy em uma conta autorizada e conferir os serviços na EC2.

- [Streamlit: contêineres Docker e health check](https://docs.streamlit.io/deploy/tutorials/docker)
- [AWS: AMI Amazon Linux 2023 pelo SSM/CloudFormation](https://docs.aws.amazon.com/linux/al2023/ug/ec2.html)
- [AWS: aplicações em EC2 com CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/deploying.applications.html)
- [AWS: scripts de inicialização da instância](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html)
- [AWS: instalação da CLI no Windows](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [AWS: login pela CLI com o navegador](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html)
- [AWS: configuração da CLI com IAM Identity Center](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
