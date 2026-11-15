#!/usr/bin/env bash
# Amazon Linux 2023; executar como root na raiz do pacote extraído.
set -euo pipefail
cd "$(dirname "$0")/.."
dnf install -y docker python3
systemctl enable --now docker

# Amazon Linux fornece o Engine; plugin Compose oficial com versão e checksum.
if ! docker compose version >/dev/null 2>&1; then
  compose_version=v2.39.4
  compose_asset=docker-compose-linux-x86_64
  temporary=$(mktemp -d)
  trap 'rm -rf "$temporary"' EXIT
  curl --fail --location --retry 3 \
    "https://github.com/docker/compose/releases/download/$compose_version/$compose_asset" \
    --output "$temporary/$compose_asset"
  curl --fail --location --retry 3 \
    "https://github.com/docker/compose/releases/download/$compose_version/$compose_asset.sha256" \
    --output "$temporary/$compose_asset.sha256"
  (cd "$temporary" && sha256sum --check "$compose_asset.sha256")
  install -D -m 755 "$temporary/$compose_asset" /usr/local/lib/docker/cli-plugins/docker-compose
fi

# Nome estável: uma atualização do pacote preserva o volume de clientes.
compose=(docker compose --project-name churn -f docker-compose.yml -f compose.postgres.yml -f compose.ec2.yml)
python3 scripts/preparar_postgres.py
"${compose[@]}" config --quiet
"${compose[@]}" build api dashboard postgres

# Migração dos contêineres anteriores, que não eram gerenciados pelo Compose.
for legacy in churn-dashboard churn-api; do
  if docker container inspect "$legacy" >/dev/null 2>&1; then
    docker rm -f "$legacy"
  fi
done
"${compose[@]}" up -d --no-build --wait --wait-timeout 300 api dashboard
"${compose[@]}" exec -T api python -c \
  "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=10)"
echo "Painel e PostgreSQL prontos. Acesso pela porta 8501."
