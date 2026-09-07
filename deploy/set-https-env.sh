#!/usr/bin/env bash
set -euo pipefail
cd /home/azureuser/margin
sed -i 's|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=["https://margin.20.40.60.228.sslip.io"]|' .env
sed -i 's|^MS_REDIRECT_URI=.*|MS_REDIRECT_URI=https://margin.20.40.60.228.sslip.io/api/v1/auth/microsoft/callback|' .env
grep -E '^(ALLOWED_ORIGINS|MS_REDIRECT_URI)=' .env
docker compose -f docker-compose.prod.yml up -d --force-recreate backend worker
sleep 8
docker compose -f docker-compose.prod.yml ps backend worker
curl -fsS https://margin.20.40.60.228.sslip.io/health
echo
curl -fsS -o /dev/null -w 'ui:%{http_code}\n' https://margin.20.40.60.228.sslip.io/
