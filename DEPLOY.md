# Despliegue de loureirosoluciones.es en el VPS

Mismo flujo que **imationgroup/web**: cada push a `main` dispara
`.github/workflows/deploy.yml`, que se conecta por SSH al VPS y ejecuta
`scripts/deploy.sh`. Nginx sirve los estáticos **directamente desde el
directorio del repo clonado** y hace proxy al contenedor del API de
contacto para `api.loureirosoluciones.es`.

## Estado actual (2 sep 2026)

Hecho y verificado en el VPS:

- [x] Repo clonado en `~/apps/loureiro` por SSH con deploy key de solo lectura
- [x] `.env` creado a partir de `.env.example` (con `SMTP_HOST` **vacío** a propósito,
      para que `/api/health` no mienta mientras no haya credenciales reales)
- [x] Contenedor `loureiro-contact` levantado y escuchando en `127.0.0.1:8005`
- [x] Permisos de lectura para `www-data` sobre el directorio del repo
- [x] Probado: `/api/health` → `smtp_configured:false`; un POST a `/api/contact`
      devuelve `502` (el front cae al `mailto:`); el honeypot devuelve `200` sin enviar

Pendiente, porque necesita root o accesos que no tengo:

- [ ] Secretos `VPS_HOST` / `VPS_USER` / `VPS_SSH_KEY` en GitHub Actions
- [ ] DNS del dominio apuntando al VPS
- [ ] Vhosts de Nginx + certbot (requieren sudo)
- [ ] Credenciales SMTP reales en `~/apps/loureiro/.env`

## Componentes en el VPS

| Servicio | Subdominio | Origen |
| --- | --- | --- |
| Web estática | `loureirosoluciones.es` (+ `www`) | Nginx → `/home/deploy/apps/loureiro` |
| API de contacto | `api.loureirosoluciones.es` | Nginx → `127.0.0.1:8005` (contenedor `loureiro-contact`) |

> El puerto **8005** se eligió porque 8000–8004 ya estaban ocupados por los
> otros proyectos del VPS. Si añades más servicios, comprueba antes con
> `ss -ltnp | grep 127.0.0.1`.

## Setup inicial (UNA sola vez)

### 1. Secretos en GitHub

`Settings → Secrets and variables → Actions` del repo:

| Secret | Valor |
| --- | --- |
| `VPS_HOST` | `76.13.56.232` |
| `VPS_USER` | `deploy` |
| `VPS_SSH_KEY` | clave privada con acceso al usuario `deploy` |
| `VPS_PORT` | (opcional) `22` |

Se puede reutilizar la misma clave que ya usa `imationgroup/web`, o generar
una específica en el VPS:

```bash
ssh-keygen -t ed25519 -C "github-actions-loureiro" -f ~/.ssh/gha_loureiro -N ""
cat ~/.ssh/gha_loureiro.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
cat ~/.ssh/gha_loureiro        # ← el bloque entero (BEGIN..END) va al secret
```

### 2. Clonar el repo en el VPS — vía SSH, no HTTPS

> **Ojo.** GitHub **rechaza las operaciones git anónimas por HTTPS desde la IP
> de este VPS**: el `GET /info/refs` responde 200, pero el `POST
> /git-upload-pack` devuelve `401` con `www-authenticate: Basic realm="GitHub"`.
> Por eso `git clone https://…` falla con *«could not read Username»* aunque el
> repo sea público. Afecta a todos los repos del servidor, no solo a este.
>
> La solución que ya usaban `autolinked` y `repartirpancamilo` en esta máquina:
> una **clave de despliegue SSH por repo**, con un alias en `~/.ssh/config`.

**Ya está hecho** para este repo. Quedó configurado así:

```bash
# En el VPS, como deploy:
ssh-keygen -t ed25519 -C "deploy-key-loureiro-vps" -f ~/.ssh/github_loureiro -N ""

cat >> ~/.ssh/config <<'CFG'

Host github-loureiro
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_loureiro
  IdentitiesOnly yes
CFG
```

Y la clave **pública** se dio de alta como deploy key de solo lectura en
`Settings → Deploy keys` del repo (título «VPS deploy (read-only)»).

Con eso, el clonado:

```bash
mkdir -p ~/apps && cd ~/apps
git clone github-loureiro:imationgroup/loureiro.git loureiro
cd loureiro
cp .env.example .env
nano .env   # rellena SMTP_* y SUPPORT_EMAIL
```

`scripts/deploy.sh` hace `git fetch origin` sobre ese mismo remoto SSH, así que
los despliegues siguientes no necesitan nada más.

### 3. Nginx

#### Vhost del sitio estático

`/etc/nginx/sites-available/loureirosoluciones.es`

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name loureirosoluciones.es www.loureirosoluciones.es;

    root /home/deploy/apps/loureiro;
    index index.html;

    # Bloquea archivos del repo que NO deben servirse por HTTP
    location ~ /\.git/ { deny all; return 404; }
    location = /.gitignore { deny all; return 404; }
    location ~ ^/(backend|scripts|\.github)/ { deny all; return 404; }
    location ~ /\.env { deny all; return 404; }
    location ~ \.(md|sh|yml|yaml|Dockerfile)$ { deny all; return 404; }

    location / {
        try_files $uri $uri/ =404;
    }

    location ~* \.(?:css|js|woff2|svg|png|jpg|jpeg|webp|ico)$ {
        expires 30d;
        add_header Cache-Control "public, max-age=2592000, immutable";
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/loureirosoluciones.es /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d loureirosoluciones.es -d www.loureirosoluciones.es
```

> **Permisos**: Nginx (`www-data`) tiene que poder leer el directorio:
> ```bash
> sudo chmod o+x /home/deploy /home/deploy/apps
> chmod -R o+rX /home/deploy/apps/loureiro
> ```

#### Vhost del API de contacto

`/etc/nginx/sites-available/api.loureirosoluciones.es`

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name api.loureirosoluciones.es;

    location / {
        proxy_pass http://127.0.0.1:8005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/api.loureirosoluciones.es /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d api.loureirosoluciones.es
```

### 4. DNS

En el panel del registrador del dominio:

| Tipo | Nombre | Valor |
| --- | --- | --- |
| `A` | `loureirosoluciones.es` | `76.13.56.232` |
| `A` | `www` | `76.13.56.232` |
| `A` | `api` | `76.13.56.232` |

Certbot no puede emitir los certificados hasta que el DNS resuelva, así que
este paso va **antes** de los `certbot` de arriba.

> **Nginx y certbot necesitan root.** El usuario `deploy` no tiene sudo sin
> contraseña, así que estos dos pasos hay que hacerlos con una sesión root.

### 5. Primer deploy

Push a `main`, o **Actions → Deploy to VPS → Run workflow**. Después:

```bash
curl -I https://loureirosoluciones.es
curl https://api.loureirosoluciones.es/api/health
```

El `health` devuelve `{"status":"ok","smtp_configured":true}` cuando el
`.env` tiene `SMTP_HOST`. Si sale `false`, el formulario caerá al mailto de
respaldo en vez de enviar correo.

## Despliegues siguientes

Cada `git push` a `main` lanza el workflow automáticamente.

## Rollback

```bash
ssh deploy@76.13.56.232
cd ~/apps/loureiro
git log --oneline -10
git reset --hard <COMMIT_HASH>
docker compose up -d --build   # solo si afecta al backend
```
