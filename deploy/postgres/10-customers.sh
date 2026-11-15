#!/usr/bin/env bash
set -euo pipefail
reader_password=$(cat /run/secrets/db_reader_password)
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=ON_ERROR_STOP=1 --set=reader_password="$reader_password" \
  --file=/opt/churn/customers.sql
