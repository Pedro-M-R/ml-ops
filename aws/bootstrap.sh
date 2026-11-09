#!/usr/bin/env bash
# Amazon Linux 2023; executar como root na raiz do pacote extraído.
set -euo pipefail
cd "$(dirname "$0")/.."
dnf install -y docker
systemctl enable --now docker
docker build --tag churn-app:latest .
docker network inspect churn >/dev/null 2>&1 || docker network create churn
# O script também pode ser repetido para atualizar os dois contêineres.
docker rm -f churn-dashboard churn-api >/dev/null 2>&1 || true
docker run -d --name churn-api --network churn --network-alias api \
  --restart unless-stopped --log-opt max-size=10m --log-opt max-file=3 \
  --health-cmd "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)\"" \
  --health-interval 10s --health-timeout 5s --health-start-period 60s --health-retries 12 \
  churn-app:latest
ready=false
for attempt in $(seq 1 120); do
  if [ "$(docker inspect --format '{{.State.Health.Status}}' churn-api)" = healthy ]; then
    ready=true
    break
  fi
  sleep 5
done
if [ "$ready" != true ]; then
  docker logs churn-api
  echo "A API não ficou pronta." >&2
  exit 1
fi
docker run -d --name churn-dashboard --network churn \
  --restart unless-stopped --log-opt max-size=10m --log-opt max-file=3 \
  -e CHURN_API_URL=http://api:8000 -p 8501:8501 \
  --health-cmd "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)\"" \
  --health-interval 10s --health-timeout 5s --health-retries 12 \
  churn-app:latest churn-dashboard --server.address 0.0.0.0 --server.port 8501
for attempt in $(seq 1 60); do
  if curl --fail --silent http://127.0.0.1:8501/_stcore/health; then
    echo "Painel pronto na porta 8501."
    exit 0
  fi
  sleep 5
done
docker logs churn-dashboard
exit 1
