#!/usr/bin/env python3
"""Publica los posts nuevos del blog como «Novedades» del Perfil de Empresa.

Se ejecuta solo, al final de cada despliegue (ver scripts/deploy.sh): mira qué
posts del blog no se han publicado todavía en Google y los publica. Lo que ya
se publicó queda apuntado en un fichero de estado, así que un despliegue que no
trae posts nuevos no hace nada.

Solo librería estándar: corre con el python3 del VPS, sin instalar nada.

Modos
-----
  --sembrar      Marca como publicados todos los posts que ya hay, sin publicar
                 ninguno. Es el primer paso tras montarlo: si no, el primer
                 despliegue soltaría cuarenta novedades de golpe.
  --nuevos       Publica los posts que aún no estén apuntados (lo del deploy).
  --reciclar     Vuelve a publicar el post cuya novedad sea más antigua. Las
                 novedades de Google se quedan atrás con el tiempo, así que
                 conviene refrescar de vez en cuando.
  --ubicaciones  Lista las cuentas y ubicaciones a las que tiene acceso, para
                 saber qué poner en GOOGLE_UBICACION.
  --autorizar    Pide permiso a Google una vez y escupe el refresh token.
  --probar       Enseña lo que publicaría, sin publicar nada ni tocar el estado.

Configuración (en el .env, junto al resto)
------------------------------------------
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET   Credenciales OAuth de escritorio
  GOOGLE_REFRESH_TOKEN                     Lo da --autorizar
  GOOGLE_UBICACION                         accounts/123.../locations/456...
  GOOGLE_NOVEDADES=0                       Para desactivarlo sin quitar nada

El proceso completo de alta está en DEPLOY.md.
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
WEB = "https://loureirosoluciones.es"
ESTADO = Path(os.getenv("GOOGLE_NOVEDADES_ESTADO",
                        Path.home() / ".local/share/loureiro/novedades-google.json"))

SCOPE = "https://www.googleapis.com/auth/business.manage"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
API_CUENTAS = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
API_UBICACIONES = "https://mybusinessbusinessinformation.googleapis.com/v1"
# Las novedades siguen viviendo en la API v4: no hay equivalente en las nuevas.
API_NOVEDADES = "https://mybusiness.googleapis.com/v4"

# Google corta el texto de una novedad a 1.500 caracteres.
MAX_TEXTO = 1500
PUERTO_AUTORIZACION = 8765


# ── Utilidades ───────────────────────────────────────────────────────────────

def leer_env() -> dict:
    """Variables del entorno, completadas con las del .env si existe."""
    valores = dict(os.environ)
    env = RAIZ / ".env"
    if env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            valores.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))
    return valores


def pedir(url: str, datos=None, token: str = "", metodo: str = "") -> dict:
    cabeceras = {"Accept": "application/json"}
    cuerpo = None
    if isinstance(datos, dict) and metodo != "FORM":
        cuerpo = json.dumps(datos).encode()
        cabeceras["Content-Type"] = "application/json"
    elif metodo == "FORM":
        cuerpo = urllib.parse.urlencode(datos).encode()
        cabeceras["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        cabeceras["Authorization"] = "Bearer " + token
    peticion = urllib.request.Request(url, data=cuerpo, headers=cabeceras)
    try:
        with urllib.request.urlopen(peticion, timeout=60) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detalle = e.read().decode(errors="replace")[:600]
        raise SystemExit(f"Google respondió {e.code} en {url}\n{detalle}")


def token_de_acceso(env: dict) -> str:
    faltan = [c for c in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")
              if not env.get(c)]
    if faltan:
        raise SystemExit("Faltan en el .env: " + ", ".join(faltan))
    r = pedir(TOKEN_URL, {
        "client_id": env["GOOGLE_CLIENT_ID"],
        "client_secret": env["GOOGLE_CLIENT_SECRET"],
        "refresh_token": env["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, metodo="FORM")
    return r["access_token"]


# ── Los posts del blog ───────────────────────────────────────────────────────

def _meta(texto: str, atributo: str, valor: str) -> str:
    m = re.search(rf'<meta\s+{atributo}="{re.escape(valor)}"\s+content="([^"]*)"', texto)
    return html.unescape(m.group(1)).strip() if m else ""


def posts() -> list[dict]:
    """Todos los posts del blog, con su título, texto e imagen.

    Un post es cualquier HTML dentro de blog/ que no sea un índice de
    categoría. La fecha no está en el HTML, así que se ordenan por el orden en
    que aparecen en el sitemap, que es el orden en que se fueron añadiendo.
    """
    orden = {}
    sitemap = (RAIZ / "sitemap.xml").read_text(encoding="utf-8")
    for i, url in enumerate(re.findall(r"<loc>([^<]+)</loc>", sitemap)):
        orden[url.strip()] = i

    encontrados = []
    for ruta in sorted((RAIZ / "blog").rglob("*.html")):
        if ruta.name == "index.html":
            continue
        texto = ruta.read_text(encoding="utf-8")
        url = _meta(texto, "property", "og:url") or \
            WEB + "/" + ruta.relative_to(RAIZ).as_posix()
        titulo = _meta(texto, "property", "og:title")
        if not titulo:
            m = re.search(r"<title>(.*?)</title>", texto, re.S)
            titulo = html.unescape(m.group(1)).split("|")[0].strip() if m else ruta.stem
        encontrados.append({
            "url": url,
            "titulo": titulo,
            "descripcion": _meta(texto, "property", "og:description") or _meta(texto, "name", "description"),
            "imagen": _meta(texto, "property", "og:image"),
            "orden": orden.get(url, 10_000),
        })
    encontrados.sort(key=lambda p: p["orden"])
    return encontrados


def texto_novedad(post: dict) -> str:
    """Lo que se ve en la novedad: titular, resumen y de dónde sale."""
    partes = [post["titulo"]]
    if post["descripcion"]:
        partes.append(post["descripcion"])
    partes.append("Te lo contamos en el blog. ¿Necesitas presupuesto? "
                  "Llámanos al 603 905 128, Ourense y provincia.")
    texto = "\n\n".join(partes)
    return texto[:MAX_TEXTO - 1] + "…" if len(texto) > MAX_TEXTO else texto


# ── Estado ───────────────────────────────────────────────────────────────────

def leer_estado() -> dict:
    if ESTADO.exists():
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    return {"publicados": {}}


def guardar_estado(estado: dict):
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8")


def apuntar(estado: dict, url: str, respuesta: dict | None):
    estado["publicados"][url] = {
        "ultima": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "veces": estado["publicados"].get(url, {}).get("veces", 0) + 1,
        "novedad": (respuesta or {}).get("name", ""),
    }


# ── Publicar ─────────────────────────────────────────────────────────────────

def publicar(env: dict, token: str, post: dict) -> dict:
    ubicacion = env.get("GOOGLE_UBICACION", "")
    if not re.fullmatch(r"accounts/\d+/locations/\d+", ubicacion):
        raise SystemExit("GOOGLE_UBICACION tiene que ser accounts/<id>/locations/<id>. "
                         "Míralo con --ubicaciones.")
    cuerpo = {
        "languageCode": "es",
        "summary": texto_novedad(post),
        "topicType": "STANDARD",
        "callToAction": {"actionType": "LEARN_MORE", "url": post["url"]},
    }
    if post["imagen"]:
        cuerpo["media"] = [{"mediaFormat": "PHOTO", "sourceUrl": post["imagen"]}]
    return pedir(f"{API_NOVEDADES}/{ubicacion}/localPosts", cuerpo, token)


def listar_ubicaciones(env: dict):
    token = token_de_acceso(env)
    cuentas = pedir(API_CUENTAS, token=token).get("accounts", [])
    if not cuentas:
        print("Esa cuenta de Google no gestiona ningún perfil de empresa.")
        return
    for cuenta in cuentas:
        print(f"\n{cuenta['name']}  ({cuenta.get('accountName', 'sin nombre')})")
        url = (f"{API_UBICACIONES}/{cuenta['name']}/locations"
               "?readMask=name,title,storefrontAddress&pageSize=100")
        for u in pedir(url, token=token).get("locations", []):
            ciudad = (u.get("storefrontAddress") or {}).get("locality", "")
            print(f"   GOOGLE_UBICACION={cuenta['name']}/{u['name']}"
                  f"   →  {u.get('title', '')}{' · ' + ciudad if ciudad else ''}")


# ── Autorización, una sola vez ───────────────────────────────────────────────

class _Recoge(BaseHTTPRequestHandler):
    codigo = None

    def do_GET(self):  # noqa: N802 (lo llama http.server)
        _Recoge.codigo = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<h1>Listo</h1><p>Ya puedes cerrar esta pestaña.</p>".encode())

    def log_message(self, *a):
        pass


def autorizar(env: dict):
    """Abre el consentimiento de Google y devuelve el refresh token.

    Se ejecuta UNA vez, en el ordenador de casa (necesita navegador). El
    refresh token que imprime es lo que va al .env del servidor.
    """
    for c in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"):
        if not env.get(c):
            raise SystemExit(f"Falta {c}. Créalo en Google Cloud como «app de escritorio».")
    redirect = f"http://127.0.0.1:{PUERTO_AUTORIZACION}"
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": env["GOOGLE_CLIENT_ID"],
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    })
    print("Se abrirá el navegador para dar permiso. Si no se abre, entra aquí:\n" + url)
    servidor = HTTPServer(("127.0.0.1", PUERTO_AUTORIZACION), _Recoge)
    webbrowser.open(url)
    servidor.handle_request()
    if not _Recoge.codigo:
        raise SystemExit("Google no devolvió el código.")
    r = pedir(TOKEN_URL, {
        "client_id": env["GOOGLE_CLIENT_ID"],
        "client_secret": env["GOOGLE_CLIENT_SECRET"],
        "code": _Recoge.codigo,
        "grant_type": "authorization_code",
        "redirect_uri": redirect,
    }, metodo="FORM")
    print("\nCopia esto al .env del servidor:\n")
    print("GOOGLE_REFRESH_TOKEN=" + r.get("refresh_token", "(no llegó: repite con prompt=consent)"))


# ── Programa ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Publica los posts del blog como novedades en Google.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--sembrar", action="store_true", help="marca lo que ya hay como publicado")
    g.add_argument("--nuevos", action="store_true", help="publica los posts que falten")
    g.add_argument("--reciclar", action="store_true", help="republica la novedad más antigua")
    g.add_argument("--ubicaciones", action="store_true", help="lista cuentas y ubicaciones")
    g.add_argument("--autorizar", action="store_true", help="da de alta el acceso a Google")
    p.add_argument("--probar", action="store_true", help="enseña lo que haría, sin publicar")
    args = p.parse_args()
    env = leer_env()

    if args.autorizar:
        return autorizar(env)
    if args.ubicaciones:
        return listar_ubicaciones(env)

    if env.get("GOOGLE_NOVEDADES", "1") == "0":
        print("Novedades desactivadas (GOOGLE_NOVEDADES=0).")
        return

    estado = leer_estado()
    todos = posts()

    if args.sembrar:
        for post in todos:
            estado["publicados"].setdefault(post["url"], {
                "ultima": "sembrado", "veces": 0, "novedad": ""})
        guardar_estado(estado)
        print(f"Apuntados {len(todos)} posts como ya publicados. "
              "A partir de ahora solo se publican los nuevos.")
        return

    if args.reciclar:
        candidatos = [p_ for p_ in todos if p_["url"] in estado["publicados"]]
        if not candidatos:
            print("Todavía no hay nada publicado que reciclar.")
            return
        pendientes = sorted(candidatos, key=lambda x: estado["publicados"][x["url"]]["ultima"])
        elegidos = pendientes[:1]
    else:
        elegidos = [p_ for p_ in todos if p_["url"] not in estado["publicados"]]

    if not elegidos:
        print("Sin novedades que publicar.")
        return

    for post in elegidos:
        if args.probar:
            print(f"\n─── {post['url']}\n{texto_novedad(post)}\nFoto: {post['imagen'] or '(sin imagen)'}")
            continue
        token = token_de_acceso(env)
        respuesta = publicar(env, token, post)
        apuntar(estado, post["url"], respuesta)
        guardar_estado(estado)
        print(f"Publicado en Google: {post['titulo']}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        # Un fallo aquí nunca debe tumbar un despliegue.
        print(f"Novedades de Google: {e}", file=sys.stderr)
        sys.exit(1)
