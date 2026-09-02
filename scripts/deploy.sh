#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Deploy de loureirosoluciones.com en el VPS, ejecutado por GitHub Actions.
# Asume:
#   - El repo está clonado en ~/apps/loureiro
#   - Existe ~/apps/loureiro/.env (no versionado, con SMTP_*)
#   - El usuario deploy pertenece al grupo docker
#   - Nginx sirve los estáticos directamente desde ~/apps/loureiro
#     (root /home/deploy/apps/loureiro;) y hace proxy a 127.0.0.1:8005
#     para api.loureirosoluciones.com.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/apps/loureiro}"
COMPOSE_FILE="docker-compose.yml"

echo "▶ Deploy iniciado: $(date -u +%FT%TZ)"
cd "$APP_DIR"

echo "▶ Fetch + reset a origin/main"
git fetch --prune origin
git reset --hard origin/main

# Los estáticos ya quedan servidos con el reset: el propio directorio del
# repo es el root de Nginx. El vhost bloquea .git/, backend/, scripts/,
# .github/ y .env (ver DEPLOY.md).

echo "▶ Build + up del backend de contacto"
docker compose -f "$COMPOSE_FILE" up -d --build --remove-orphans

echo "▶ Prune de imágenes huérfanas"
docker image prune -f

echo "▶ Estado del backend:"
docker compose -f "$COMPOSE_FILE" ps

echo "✅ Deploy OK: $(date -u +%FT%TZ)"
