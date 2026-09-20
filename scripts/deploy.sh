#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Deploy de loureirosoluciones.es en el VPS, ejecutado por GitHub Actions.
# Asume:
#   - El repo está clonado en ~/apps/loureiro
#   - Existe ~/apps/loureiro/.env (no versionado, con SMTP_*)
#   - El usuario deploy pertenece al grupo docker
#   - Nginx sirve los estáticos directamente desde ~/apps/loureiro
#     (root /home/deploy/apps/loureiro;) y hace proxy a 127.0.0.1:8005
#     para api.loureirosoluciones.es.
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

# El RSS del blog. De aquí se entera Make (u otro conector) de que hay post
# nuevo para publicarlo como novedad en el Perfil de Empresa de Google.
echo "▶ Feed del blog"
python3 scripts/generar-feed.py || echo "⚠ No se pudo generar feed.xml"

# Publicación directa en Google, solo si algún día aprueban el acceso a su API
# y se configuran las credenciales en el .env (ver DEPLOY.md).
if grep -q "^GOOGLE_REFRESH_TOKEN=" .env 2>/dev/null; then
  echo "▶ Novedades de Google"
  python3 scripts/novedades-google.py --nuevos || echo "⚠ Novedades de Google: se salta"
fi

echo "✅ Deploy OK: $(date -u +%FT%TZ)"
