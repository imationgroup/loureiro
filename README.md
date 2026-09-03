# loureirosoluciones.es

Web corporativa de **Loureiro Soluciones** — reformas integrales y servicios
para el hogar en Ourense y provincia.

Sitio estático (HTML/CSS/JS vanilla, sin build) + un mini backend FastAPI
para el formulario de contacto. Se despliega en el VPS de imationgroup con
el mismo flujo que `imationgroup/web`: push a `main` → GitHub Actions → SSH →
`scripts/deploy.sh`.

## Estructura

```
index.html            Página principal (one-page)
aviso-legal.html      Aviso legal — falta el nombre del titular
privacidad.html       Política de privacidad — falta el nombre del titular
assets/
  css/styles.css      Toda la hoja de estilos del sitio
  css/legal.css       Estilos exclusivos de las páginas legales
  js/main.js          Menú, animaciones, FAQ y formulario
  img/                favicon.svg, og-image.svg
backend/              API de contacto (FastAPI + SMTP)
scripts/deploy.sh     Script que corre en el VPS
DEPLOY.md             Setup del VPS, Nginx, DNS y certificados
```

## Desarrollo local

No hace falta build ni dependencias. Cualquier servidor estático vale:

```bash
python -m http.server 8080
```

Y abre <http://localhost:8080>. `localhost:8080` ya está en la lista de
`ALLOWED_ORIGINS` del backend.

Para levantar también el backend:

```bash
cp .env.example .env   # rellena SMTP_*
docker compose up --build
```

## Dónde se cambian las cosas

| Qué | Dónde |
| --- | --- |
| Teléfono y WhatsApp | `index.html` (enlaces `tel:` y `wa.me`), `assets/js/main.js` |
| Correo de contacto | `index.html`, `assets/js/main.js` (`EMAIL`), `.env` del VPS (`SUPPORT_EMAIL`) |
| Servicios y textos | `index.html`, sección `#servicios` |
| Concellos de la zona | `index.html`, sección `#zona` |
| Preguntas frecuentes | `index.html`, sección `#faq` |
| Colores y tipografía | `assets/css/styles.css`, bloque `:root` |

## Pendiente

- [ ] **Registros DNS en Cloudflare.** La zona de `loureirosoluciones.es` existe
      pero está **vacía**: sin `A`, sin `MX`, sin nada. Hacen falta tres `A`
      (apex, `www` y `api`) apuntando a `76.13.56.232`, y los `MX` del correo.
- [ ] **Confirmar el correo.** Se asume `contacto@loureirosoluciones.es`. El dominio
      no tiene `MX`, así que el buzón todavía no existe.
- [ ] **Añadir el nombre y apellidos del titular** en `aviso-legal.html` y
      `privacidad.html`. El artículo 10 de la LSSI-CE exige identificar al
      responsable con nombre y apellidos mientras se ejerza como autónomo.
- [ ] **Fotos de obras reales.** El diseño funciona sin fotografía, pero una
      galería de trabajos hechos es la mejora que más va a convertir.
- [ ] **`og-image` en PNG.** Ahora es SVG y la mayoría de redes sociales no lo
      renderiza en las previsualizaciones; conviene exportarlo a PNG 1200×630.
- [ ] **Buzón `contacto@loureirosoluciones.es`** operativo, y `.env` del VPS con
      las credenciales SMTP.
