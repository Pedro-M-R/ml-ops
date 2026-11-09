# Streamlit + FastAPI na AWS

Para hospedar sem AWS, use o [passo a passo de Render + Streamlit Cloud](deploy_render_streamlit.md).

O **Churn Radar** usa os clientes já existentes em `data/churn.csv`. O layout
tem fundo lavanda, um cartão branco de consulta e o botão roxo **Consultar**.
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
usa Docker e dois contêineres com reinício automático. A API não publica porta
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
   aws login --profile faculdade --region sa-east-1
   ```

   Se seu acesso é por IAM Identity Center da faculdade/empresa, use esta
   alternativa em vez de `aws login`. Informe a Start URL e a região SSO dadas
   pelo administrador, escolha a conta e a role autorizadas, e use `sa-east-1`
   como região padrão dos recursos. A região SSO pode ser diferente.

   ```powershell
   aws configure sso --profile faculdade
   aws sso login --profile faculdade
   ```

3. Confirme a conta autenticada:

   ```powershell
   aws sts get-caller-identity --profile faculdade --region sa-east-1 --no-cli-pager
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
   pagos e usa a instância `t3.medium` por padrão:

   ```powershell
   $ipPublico = (curl.exe -4 -fsS https://checkip.amazonaws.com).Trim()
   Write-Output "Rede autorizada: ${ipPublico}/32"
   python -m uv run python scripts/deploy_aws.py --profile faculdade --region sa-east-1 --allowed-cidr "${ipPublico}/32"
   ```

   Execute a publicação somente depois de confirmar que o comando de IP retornou
   um IPv4 válido. Mantenha a mesma rede/VPN durante a publicação e o acesso.
6. Aguarde o endereço `http://IP_DA_EC2:8501` no terminal. No console AWS, consulte
   **CloudFormation → churn-demo → Outputs → DashboardUrl**, na região São Paulo.
   Abra esse endereço, confirme **API conectada** e teste uma previsão. Após a
   implantação, a aplicação roda na EC2 independentemente do computador local.

Sem `--profile`, a AWS CLI usa sua cadeia normal de credenciais. Nunca coloque
chaves AWS no código, Dockerfile ou pacote. Não é preciso informar senhas ao script.

O script valida o template na AWS, cria/reutiliza um bucket privado específico
da conta e stack, envia o ZIP com chave SHA-256 e solicita a stack `churn-demo`.
Depois aguarda a infraestrutura e verifica `/_stcore/health` do Streamlit. O build
na EC2 pode levar vários minutos. O endereço e o link do Session Manager são
impressos e também aparecem em **CloudFormation → stack → Outputs**.

`CREATE_COMPLETE` confirma a infraestrutura; a aplicação termina de instalar
depois. Acesse o painel, confirme **API conectada** e faça uma análise. Se o
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

Esta implantação inicial usa HTTP, sem login, restrito à rede autorizada. Use
dados de demonstração. Para expor a usuários externos com dados reais, configure
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

1. Abra o [CloudFormation em São Paulo](https://sa-east-1.console.aws.amazon.com/cloudformation/home?region=sa-east-1)
   com a mesma conta do perfil e confira se aparece uma solicitação de concluir
   cadastro, ativação ou verificação.
2. Complete somente as etapas pendentes exibidas pela AWS. Confira o e-mail de
   ativação e eventuais solicitações de verificação; se a AWS solicitar dados
   de pagamento, preencha-os diretamente no console.
3. Se a conta foi criada recentemente, a ativação pode levar até 24 horas,
   conforme a [documentação de criação da conta](https://docs.aws.amazon.com/accounts/latest/reference/getting-started.html).
4. Se o cadastro já está concluído e o erro persistir, abra um chamado de
   **Account and billing support** no [AWS Support](https://console.aws.amazon.com/support/home),
   informando serviço CloudFormation, região `sa-east-1`, operação `DescribeStacks`
   e código `OptInRequired`.

Antes de repetir a publicação, faça apenas esta consulta, que não cria recursos:

```powershell
aws cloudformation list-stacks --profile faculdade --region sa-east-1 --max-items 5 --no-cli-pager
```

Uma resposta JSON, mesmo com lista vazia, confirma que essa consulta foi liberada.
Se retornar `OptInRequired`, a pendência ainda não foi resolvida. O script para
antes de criar o bucket e a stack quando esse erro ocorre em `DescribeStacks`.
Não é necessário alterar o template ou criar novas chaves para tratar esse erro.

## Diagnóstico e atualização

Abra a EC2 pelo link do Session Manager e execute:

```bash
sudo tail -n 100 /var/log/churn-bootstrap.log
sudo docker ps
sudo docker logs --tail 100 churn-api
sudo docker logs --tail 100 churn-dashboard
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
indisponibilidade. Para uma implantação independente, use um novo `--stack-name`
no script, verifique o novo endereço e exclua a stack anterior quando terminar.

## Encerrar os recursos

Exclua a stack pelo CloudFormation ou com o comando abaixo. Isso encerra a EC2 e
remove o disco, a rede e a role criados por ela. A exclusão é irreversível.

```powershell
aws cloudformation delete-stack --stack-name churn-demo --region sa-east-1 --profile faculdade
aws cloudformation wait stack-delete-complete --stack-name churn-demo --region sa-east-1 --profile faculdade
```

O bucket de artefatos foi criado fora da stack e permanece. Exclua seus objetos e
o bucket pelo console S3 quando não precisar mais deles; o nome segue o padrão
`churn-ID_DA_CONTA-churn-demo`. Não remova buckets de outros projetos.

## Referências

Validação desta entrega: 152 testes aprovados; formulário Streamlit exercitado
com a API real; 7.043 clientes previstos em 8 lotes HTTP, com diferença zero em
relação ao pipeline exportado e ordem dos IDs preservada. O relatório está em
`reports/dashboard_verification.json`. O template passou no `cfn-lint` e o
Compose foi validado com `docker compose config --quiet`. Build/execução Docker
e implantação AWS ainda não foram executados: o Docker Engine estava desligado
e não havia AWS CLI ou credenciais configuradas. A inspeção visual no navegador
também ficou indisponível no ambiente; o fluxo de interface passou no AppTest.

- [Streamlit: contêineres Docker e health check](https://docs.streamlit.io/deploy/tutorials/docker)
- [AWS: AMI Amazon Linux 2023 pelo SSM/CloudFormation](https://docs.aws.amazon.com/linux/al2023/ug/ec2.html)
- [AWS: aplicações em EC2 com CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/deploying.applications.html)
- [AWS: scripts de inicialização da instância](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html)
- [AWS: instalação da CLI no Windows](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [AWS: login pela CLI com o navegador](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html)
- [AWS: configuração da CLI com IAM Identity Center](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
