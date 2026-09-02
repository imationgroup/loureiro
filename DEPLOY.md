# Despliegue de loureirosoluciones.com en el VPS

Mismo flujo que **imationgroup/web**: cada push a `main` dispara
`.github/workflows/deploy.yml`, que se conecta por SSH al VPS y ejecuta
`scripts/deploy.sh`. Nginx sirve los estáticos **directamente desde el
directorio del repo clonado** y hace proxy al contenedor del API de
contacto para `api.loureirosoluciones.com`.

## Componentes en el VPS

| Servicio | Subdominio | Origen |
| --- | --- | --- |
| Web estática | `loureirosoluciones.com` (+ `www`) | Nginx → `/home/deploy/apps/loureiro` |
| API de contacto | `api.loureirosoluciones.com` | Nginx → `127.0.0.1:8005` (contenedor `loureiro-contact`) |

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

### 2. Clonar el repo en el VPS

```bash
ssh deploy@76.13.56.232
mkdir -p ~/apps && cd ~/apps
git clone https://github.com/imationgroup/loureiro.git loureiro
cd loureiro
cp .env.example .env
nano .env   # rellena SMTP_* y SUPPORT_EMAIL
```

### 3. Nginx

#### Vhost del sitio estático

`/etc/nginx/sites-available/loureirosoluciones.com`

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name loureirosoluciones.com www.loureirosoluciones.com;

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
sudo ln -s /etc/nginx/sites-available/loureirosoluciones.com /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d loureirosoluciones.com -d www.loureirosoluciones.com
```

> **Permisos**: Nginx (`www-data`) tiene que poder leer el directorio:
> ```bash
> sudo chmod o+x /home/deploy /home/deploy/apps
> chmod -R o+rX /home/deploy/apps/loureiro
> ```

#### Vhost del API de contacto

`/etc/nginx/sites-available/api.loureirosoluciones.com`

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name api.loureirosoluciones.com;

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
sudo ln -s /etc/nginx/sites-available/api.loureirosoluciones.com /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d api.loureirosoluciones.com
```

### 4. DNS

En el panel del registrador del dominio:

| Tipo | Nombre | Valor |
| --- | --- | --- |
| `A` | `loureirosoluciones.com` | `76.13.56.232` |
| `A` | `www` | `76.13.56.232` |
| `A` | `api` | `76.13.56.232` |

Certbot no puede emitir los certificados hasta que el DNS resuelva, así que
este paso va **antes** de los `certbot` de arriba.

### 5. Primer deploy

Push a `main`, o **Actions → Deploy to VPS → Run workflow**. Después:

```bash
curl -I https://loureirosoluciones.com
curl https://api.loureirosoluciones.com/api/health
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
