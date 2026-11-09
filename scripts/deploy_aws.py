"""Empacota o modelo e cria a infraestrutura AWS via AWS CLI/CloudFormation."""

import argparse
import hashlib
import ipaddress
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default="sa-east-1")
    parser.add_argument("--stack-name", default="churn-demo")
    parser.add_argument("--allowed-cidr", help="IPv4/CIDR autorizado, normalmente seu IP público/32.")
    parser.add_argument("--instance-type", choices=["t3.small", "t3.medium", "t3.large"], default="t3.medium")
    parser.add_argument("--profile", help="Perfil já autenticado da AWS CLI.")
    parser.add_argument("--prepare-only", action="store_true", help="Gera o pacote sem acessar ou criar recursos AWS.")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", args.stack_name):
        parser.error("--stack-name deve ter até 40 letras minúsculas, dígitos e hífens, iniciando com letra.")
    if not args.prepare_only:
        if not args.allowed_cidr:
            parser.error("Informe --allowed-cidr com seu IP público/32 ou a rede autorizada.")
        try:
            network = ipaddress.IPv4Network(args.allowed_cidr, strict=True)
        except ValueError:
            parser.error("--allowed-cidr deve ser uma rede IPv4/CIDR válida.")
        if network.prefixlen == 0:
            parser.error("Use uma rede específica; 0.0.0.0/0 exporia o painel HTTP sem autenticação.")
        if shutil.which("aws") is None:
            parser.error("Instale a AWS CLI v2 e configure aws configure sso (ou um perfil) antes de publicar.")

    subprocess.run([sys.executable, str(ROOT / "scripts/empacotar.py")], cwd=ROOT, check=True)
    archive = ROOT / "dist/churn-portatil.zip"
    if args.prepare_only:
        print("Pacote pronto. Nenhum recurso AWS foi criado.")
        return

    base = ["aws", "--region", args.region, "--no-cli-pager"]
    if args.profile:
        base += ["--profile", args.profile]

    def aws(*command, allow_failure=False):
        result = subprocess.run([*base, *command], capture_output=True, text=True, encoding="utf-8")
        if result.returncode and not allow_failure:
            raise RuntimeError(result.stderr.strip())
        return result

    identity = json.loads(aws("sts", "get-caller-identity", "--output", "json").stdout)
    account = identity["Account"]
    print(f"Conta: {account} | região: {args.region} | stack: {args.stack_name} | instância: {args.instance_type}")
    # O deploy é de criação: não substitui uma instância existente e seus dados.
    existing = aws("cloudformation", "describe-stacks", "--stack-name", args.stack_name, allow_failure=True)
    if existing.returncode == 0:
        raise RuntimeError("Essa stack já existe. Use outro --stack-name ou siga a atualização por SSM em docs/deploy_aws.md.")
    if "does not exist" not in existing.stderr:
        raise RuntimeError(existing.stderr.strip())
    aws("cloudformation", "validate-template", "--template-body", f"file://{ROOT / 'aws/cloudformation.yaml'}")
    # Nome determinístico e específico desta stack/conta; o bucket permanece para auditoria.
    bucket = f"churn-{account}-{args.stack_name}"[:63].rstrip("-")
    head = aws("s3api", "head-bucket", "--bucket", bucket, "--expected-bucket-owner", account, allow_failure=True)
    if head.returncode:
        if "404" not in head.stderr and "Not Found" not in head.stderr:
            raise RuntimeError(head.stderr.strip())
        create = ["s3api", "create-bucket", "--bucket", bucket]
        if args.region != "us-east-1":
            create += ["--create-bucket-configuration", f"LocationConstraint={args.region}"]
        aws(*create)
    aws("s3api", "put-public-access-block", "--bucket", bucket, "--public-access-block-configuration",
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    key = f"releases/{digest}.zip"
    aws("s3", "cp", str(archive), f"s3://{bucket}/{key}", "--sse", "AES256")
    aws("cloudformation", "create-stack", "--stack-name", args.stack_name,
        "--template-body", f"file://{ROOT / 'aws/cloudformation.yaml'}", "--capabilities", "CAPABILITY_IAM",
        "--parameters", f"ParameterKey=ArtifactBucket,ParameterValue={bucket}",
        f"ParameterKey=ArtifactKey,ParameterValue={key}",
        f"ParameterKey=AllowedCidr,ParameterValue={args.allowed_cidr}",
        f"ParameterKey=InstanceType,ParameterValue={args.instance_type}")
    print("Stack solicitada. A criação gera cobranças de EC2, EBS, IPv4 e S3.", flush=True)
    # CREATE_COMPLETE confirma infraestrutura; a aplicação é verificada separadamente.
    for _ in range(180):
        stack = json.loads(aws("cloudformation", "describe-stacks", "--stack-name", args.stack_name, "--output", "json").stdout)["Stacks"][0]
        status = stack["StackStatus"]
        print(f"Infraestrutura: {status}", flush=True)
        if status == "CREATE_COMPLETE":
            break
        if status != "CREATE_IN_PROGRESS":
            raise RuntimeError(f"Criação interrompida: {status}. Consulte os eventos da stack no CloudFormation.")
        time.sleep(10)
    else:
        raise RuntimeError("Tempo de espera esgotado. A stack pode continuar em criação; consulte o CloudFormation.")
    outputs = {item["OutputKey"]: item["OutputValue"] for item in stack["Outputs"]}
    url = outputs["DashboardUrl"]
    print(f"Infraestrutura criada. Painel: {url}\nAdministração: {outputs['SessionManagerUrl']}", flush=True)
    print("Aguardando o build e a inicialização da aplicação (até 20 minutos)...", flush=True)
    for _ in range(120):
        try:
            with urlopen(url + "/_stcore/health", timeout=5) as response:
                if response.status == 200 and response.read().strip() == b"ok":
                    print(f"Streamlit respondeu ao health check: {url}")
                    print("Abra o painel e confirme 'API conectada' antes de usar as previsões.")
                    return
        except (URLError, TimeoutError, OSError):
            pass
        time.sleep(10)
    raise RuntimeError("Infraestrutura criada, mas o health check não respondeu. Confira o CIDR e /var/log/churn-bootstrap.log pelo Systems Manager.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Deploy não concluído: {exc}", file=sys.stderr)
        sys.exit(1)
