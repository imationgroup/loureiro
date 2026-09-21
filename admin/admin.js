/* ═══════════════════════════════════════════════════════════════════════
   Panel de gestión de Loureiro Soluciones
   JS sin dependencias, igual que el resto del sitio.

   Todo lo que se pinta pasa por esc(): los datos vienen de la base y se
   insertan como HTML, así que escapar no es opcional.
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
"use strict";

var API = location.hostname === "127.0.0.1" || location.hostname === "localhost"
  ? "http://127.0.0.1:8005"
  : "https://api.loureirosoluciones.es";

var $  = function (s, r) { return (r || document).querySelector(s); };
var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

// Texto listo para comparar con lo que alguien escribe: los euros que pinta
// el navegador llevan un espacio duro antes del €, y eso nadie lo teclea.
function llano(s) {
  return String(s === null || s === undefined ? "" : s)
    .replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim().toLowerCase();
}

function esc(v) {
  if (v === null || v === undefined) return "";
  return String(v).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
function eur(n) {
  return (Number(n) || 0).toLocaleString("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 2 });
}
function num(n) { return (Number(n) || 0).toLocaleString("es-ES", { maximumFractionDigits: 2 }); }
function fecha(f) { return f ? String(f).slice(0, 10).split("-").reverse().join("/") : ""; }

var ico = {
  panel:'<path d="M3 3h7v7H3zM14 3h7v4h-7zM14 11h7v10h-7zM3 14h7v7H3z"/>',
  buzon:'<path d="M4 4h16v12H4z"/><path d="M4 4l8 7 8-7"/>',
  gente:'<path d="M16 20v-2a4 4 0 0 0-8 0v2"/><circle cx="12" cy="8" r="4"/>',
  casco:'<path d="M3 18h18"/><path d="M5 18v-4a7 7 0 0 1 14 0v4"/><path d="M10 7V4h4v3"/>',
  obra:'<path d="M3 21V9l9-6 9 6v12"/><path d="M9 21v-7h6v7"/>',
  euro:'<path d="M17 6a6 6 0 1 0 0 12"/><path d="M4 10h9M4 14h9"/>',
  caja:'<path d="M3 8l9-5 9 5v8l-9 5-9-5z"/><path d="M3 8l9 5 9-5"/><path d="M12 13v8"/>',
  camion:'<rect x="1" y="6" width="13" height="10"/><path d="M14 9h4l3 3v4h-7z"/><circle cx="6" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
  libro:'<path d="M4 4h14a2 2 0 0 1 2 2v14H6a2 2 0 0 1-2-2z"/><path d="M8 8h8M8 12h8"/>',
  mas:'<path d="M12 5v14M5 12h14"/>',
  lapiz:'<path d="M17 3l4 4L8 20H4v-4z"/>',
  papelera:'<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
  ojo:'<path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/>',
  flechas:'<path d="M7 10l5-5 5 5M7 14l5 5 5-5"/>',
  doc:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h5"/>',
  recibo:'<path d="M4 2h16v20l-3-2-3 2-2-2-2 2-3-2-3 2z"/><path d="M8 8h8M8 12h8M8 16h4"/>',
  descarga:'<path d="M12 3v12"/><path d="M7 12l5 5 5-5"/><path d="M4 20h16"/>',
  mapa:'<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
  calendario:'<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4"/>',
  sincro:'<path d="M4 12a8 8 0 0 1 14-5.3L20 8"/><path d="M20 3v5h-5"/><path d="M20 12a8 8 0 0 1-14 5.3L4 16"/><path d="M4 21v-5h5"/>',
  proforma:'<path d="M14 3H6v18h12V7z"/><path d="M14 3v4h4"/><path d="M9 14h6M12 11v6"/>',
  altaCliente:'<path d="M14 20v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="3.5"/><path d="M18 8v6M15 11h6"/>',
  normas:'<path d="M6 3h11a2 2 0 0 1 2 2v16H8a2 2 0 0 1-2-2z"/><path d="M6 17h13"/><path d="M10 7h6M10 11h6"/>',
  arriba:'<path d="M12 19V5"/><path d="M6 11l6-6 6 6"/>',
  abajo:'<path d="M12 5v14"/><path d="M6 13l6 6 6-6"/>',
  firma:'<path d="M3 17c3 0 4-9 7-9s3 9 6 9c2 0 3-2 5-3"/><path d="M3 21h18"/>',
  whatsapp:'<path d="M3 21l1.6-4.7A8.5 8.5 0 1 1 8 19.6z"/><path d="M9 9.5c0 3 2.5 5.5 5.5 5.5l1-1.5-2-1-1 1c-1-.5-2-1.5-2.5-2.5l1-1-1-2z"/>',
  nota:'<path d="M5 3h14v12l-6 6H5z"/><path d="M13 21v-6h6"/><path d="M8 8h8M8 12h5"/>',
  grafico:'<path d="M4 20V11M10 20V4M16 20v-6M3 20h18"/>',
  etiqueta:'<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.5"/>',
  estrella:'<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
  clip:'<path d="M21 11l-8.5 8.5a5 5 0 0 1-7-7L14 4a3.5 3.5 0 0 1 5 5l-8.5 8.5a2 2 0 0 1-3-3L15 7"/>',
  camara:'<path d="M3 8a2 2 0 0 1 2-2h2.5l1.5-2h6l1.5 2H19a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><circle cx="12" cy="13" r="3.5"/>',
  ok:'<path d="M20 6L9 17l-5-5"/>',
  no:'<path d="M18 6L6 18M6 6l12 12"/>',
  equipo:'<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
};
function svg(d, cls) {
  return '<svg viewBox="0 0 24 24" ' + (cls ? 'class="' + cls + '" ' : "") + 'aria-hidden="true">' + d + "</svg>";
}

/* ── Cliente de API ───────────────────────────────────────────────────── */
// La sesión se guarda en el navegador. Con «mantener la sesión iniciada» va a
// localStorage, que sobrevive a cerrar el navegador; sin marcar, a
// sessionStorage, que se borra al cerrar la pestaña. El servidor hace lo mismo
// por su lado: la sesión recordada dura días y la otra, horas.
function guardado(clave) {
  try { return sessionStorage.getItem(clave) || localStorage.getItem(clave) || ""; }
  catch (e) { return ""; }
}
function guardar(clave, valor, recordar) {
  try {
    (recordar ? localStorage : sessionStorage).setItem(clave, valor);
    (recordar ? sessionStorage : localStorage).removeItem(clave);
  } catch (e) {}
}
function olvidar(clave) {
  try { localStorage.removeItem(clave); sessionStorage.removeItem(clave); } catch (e) {}
}

var token = guardado("loureiro_token");

// Usuario de la sesión, con su rol y sus módulos. Lo da el servidor al entrar
// (/login) o al recargar (/yo). Con esto se pinta el menú, pero quien decide
// de verdad qué se ve es el servidor: esconder una pestaña no protege nada.
var YO = null;
function esAdmin() { return !!YO && YO.rol === "admin"; }
function puedeVer(k) {
  if (!YO) return false;
  if (MODULOS[k] && MODULOS[k].permiso) k = MODULOS[k].permiso;
  if (k === "dashboard") return true;
  if (k === "equipo") return esAdmin();
  // Los estatutos los lee todo el mundo: de nada sirve escribir cómo
  // funciona la empresa si media plantilla no puede abrirlo.
  if (k === "estatutos") return true;
  if (esAdmin()) return true;
  if (k === "ingresos") return YO.permisos.indexOf("facturas") >= 0 || YO.permisos.indexOf("contabilidad") >= 0;
  return YO.permisos.indexOf(k) >= 0;
}

function api(ruta, opciones) {
  opciones = opciones || {};
  var cab = { "Content-Type": "application/json" };
  if (token) cab.Authorization = "Bearer " + token;
  return fetch(API + ruta, {
    method: opciones.metodo || "GET",
    headers: cab,
    body: opciones.datos ? JSON.stringify(opciones.datos) : undefined
  }).then(function (r) {
    if (r.status === 401) { salir(true); throw new Error("Sesión caducada"); }
    if (r.status === 204) return null;
    return r.json().then(function (j) {
      if (!r.ok) throw new Error((j && j.detail) || ("Error " + r.status));
      return j;
    }).catch(function (e) {
      if (!r.ok) throw new Error(e.message || ("Error " + r.status));
      throw e;
    });
  });
}

/* ── Login ────────────────────────────────────────────────────────────── */
var loginForm = $("#login-form");
try { $("#li-recordar").checked = localStorage.getItem("loureiro_recordar") !== "0"; } catch (e) {}
loginForm.addEventListener("submit", function (e) {
  e.preventDefault();
  var aviso = $("#login-aviso"), btn = $("#li-btn");
  aviso.hidden = true;
  btn.disabled = true; btn.textContent = "Entrando…";

  var recordar = $("#li-recordar").checked;
  api("/api/admin/login", {
    metodo: "POST",
    datos: { email: $("#li-email").value.trim(), password: $("#li-pass").value,
             recordar: recordar }
  }).then(function (r) { entrarCon(r, recordar); }).catch(function (err) {
    aviso.textContent = err.message;
    aviso.hidden = false;
  }).finally(function () {
    btn.disabled = false; btn.textContent = "Entrar";
    $("#li-pass").value = "";
  });
});

function entrarCon(r, recordar) {
  token = r.token;
  YO = r.usuario;
  guardar("loureiro_token", token, recordar);
  guardar("loureiro_email", r.email, recordar);
  // La casilla se queda como la dejaste para la próxima vez.
  try { localStorage.setItem("loureiro_recordar", recordar ? "1" : "0"); } catch (e) {}
  arrancar(true);
}

function salir(silencioso) {
  var t = token;
  token = "";
  YO = null;
  olvidar("loureiro_token");
  olvidar("loureiro_email");
  if (!silencioso && t) {
    fetch(API + "/api/admin/logout", { method: "POST", headers: { Authorization: "Bearer " + t } }).catch(function(){});
  }
  $("#app").hidden = true;
  $("#login").hidden = false;
  mostrarAcceso("login");
  cerrarCampana();
  document.title = "Panel de gestión · Loureiro Soluciones";
}
$("#btn-salir").addEventListener("click", function () { salir(false); });

/* ── He olvidado mi contraseña y enlaces de invitación ────────────────── */
function mostrarAcceso(cual) {
  ["login", "recuperar", "clave"].forEach(function (k) { $("#" + k + "-form").hidden = k !== cual; });
  $("#login-aviso").hidden = true;
  $("#login-titulo").textContent = cual === "recuperar" ? "Recuperar la contraseña"
                                 : cual === "clave" ? "Crea tu contraseña" : "Panel de gestión";
  $("#login-sub").textContent = cual === "recuperar" ? "Te mandamos un enlace para cambiarla."
                              : cual === "clave" ? "" : "Acceso restringido.";
}
function avisoAcceso(texto, tipo) {
  var a = $("#login-aviso");
  a.className = "aviso " + (tipo === "ok" ? "aviso--ok" : "aviso--err");
  a.textContent = texto;
  a.hidden = false;
}

$("#li-olvido").addEventListener("click", function () {
  mostrarAcceso("recuperar");
  $("#re-email").value = $("#li-email").value;
  $("#re-email").focus();
});
$("#re-volver").addEventListener("click", function () { mostrarAcceso("login"); });
$("#recuperar-form").addEventListener("submit", function (e) {
  e.preventDefault();
  var btn = $("#re-btn"), email = $("#re-email").value.trim();
  if (!email) { avisoAcceso("Escribe tu correo."); return; }
  btn.disabled = true;
  api("/api/admin/recuperar", { metodo: "POST", datos: { email: email } }).then(function () {
    // El servidor contesta lo mismo exista o no el correo, y aquí también:
    // la pantalla no sirve para averiguar quién tiene cuenta.
    avisoAcceso("Si ese correo tiene acceso al panel, te acaba de llegar un enlace para " +
                "cambiar la contraseña. Caduca en 2 horas.", "ok");
  }).catch(function (err) { avisoAcceso(err.message); })
    .finally(function () { btn.disabled = false; });
});

// Enlace de invitación o de recuperación: …/admin/#clave=XXXX
var claveToken = "";
function abrirEnlaceClave() {
  var m = /^#clave=([A-Za-z0-9_-]+)/.exec(location.hash);
  if (!m) return false;
  claveToken = m[1];
  // Fuera de la barra de direcciones y del historial: es de un solo uso y no
  // tiene que quedarse a la vista ni volver con el botón de atrás.
  history.replaceState(null, "", location.pathname);
  $("#app").hidden = true;
  $("#login").hidden = false;
  mostrarAcceso("clave");
  $("#cl-hola").textContent = "Comprobando el enlace…";
  api("/api/admin/clave/comprobar", { metodo: "POST", datos: { token: claveToken } }).then(function (r) {
    $("#login-titulo").textContent = r.tipo === "recuperar" ? "Cambia tu contraseña" : "Crea tu contraseña";
    $("#cl-hola").innerHTML = "Hola" + (r.nombre ? " <b>" + esc(r.nombre) + "</b>" : "") +
      ". Tu usuario para entrar es <b>" + esc(r.email) + "</b>.";
    $("#cl-pass").focus();
  }).catch(function (err) {
    $("#cl-hola").textContent = "";
    $("#cl-btn").disabled = true;
    avisoAcceso(err.message);
  });
  return true;
}
$("#clave-form").addEventListener("submit", function (e) {
  e.preventDefault();
  var p1 = $("#cl-pass").value, p2 = $("#cl-pass2").value, btn = $("#cl-btn");
  if (p1.length < 10) { avisoAcceso("La contraseña tiene que tener al menos 10 caracteres."); return; }
  if (p1 !== p2) { avisoAcceso("Las dos contraseñas no coinciden."); return; }
  btn.disabled = true; btn.textContent = "Guardando…";
  api("/api/admin/clave", { metodo: "POST", datos: { token: claveToken, password: p1 } })
    .then(function (r) {
      claveToken = "";
      $("#cl-pass").value = ""; $("#cl-pass2").value = "";
      entrarCon(r, true);
    })
    .catch(function (err) { avisoAcceso(err.message); })
    .finally(function () { btn.disabled = false; btn.textContent = "Guardar y entrar"; });
});

/* ── Definición de los módulos ────────────────────────────────────────── */
var CATEGORIAS_PRO = ["Electricista", "Albañil", "Fontanero", "Pintor", "Carpintero",
  "Climatización", "Instalador de pellets", "Limpieza", "Yesero", "Soldador",
  "Cristalero", "Cerrajero", "Jardinero", "Otro"];

var ESTADOS_SOL  = ["pendiente", "atendida", "descartada"];
var TIPOS_CITA   = ["visita", "presupuesto", "obra", "revisión", "otro"];
var ESTADOS_CITA = ["pendiente", "hecha", "cancelada"];
var QUIEN_CANCELA = ["cliente", "profesional", "empresa"];
var IVAS = [{ v: 21, t: "21 %" }, { v: 10, t: "10 %" }, { v: 0, t: "0 %" }];
// Desplegable de IVA para las líneas de los documentos. Un tipo antiguo que no
// esté en la lista (un 4 %) se conserva como opción: si no, al guardar se
// cambiaría sin que nadie lo decidiera.
function opcionesIva(v) {
  var ops = IVAS.slice();
  if (v !== "" && v !== null && v !== undefined &&
      !ops.some(function (o) { return Number(o.v) === Number(v); })) ops.push({ v: Number(v), t: v + " %" });
  return ops.map(function (o) {
    return '<option value="' + o.v + '"' + (Number(o.v) === Number(v) ? " selected" : "") + ">" + esc(o.t) + "</option>";
  }).join("");
}

/* ── Provincias y municipios ──────────────────────────────────────────────
   Ourense va con sus 92 concellos completos porque es la zona de trabajo.
   Del resto se incluyen las localidades principales; el campo admite
   escribir libremente, así que la lista orienta pero no limita.        */
var PROVINCIAS = ["Ourense", "Pontevedra", "A Coruña", "Lugo",
  "Álava", "Albacete", "Alicante", "Almería", "Asturias", "Ávila", "Badajoz",
  "Baleares", "Barcelona", "Burgos", "Cáceres", "Cádiz", "Cantabria",
  "Castellón", "Ceuta", "Ciudad Real", "Córdoba", "Cuenca", "Girona",
  "Granada", "Guadalajara", "Guipúzcoa", "Huelva", "Huesca", "Jaén",
  "La Rioja", "Las Palmas", "León", "Lleida", "Madrid", "Málaga", "Melilla",
  "Murcia", "Navarra", "Palencia", "Salamanca", "Santa Cruz de Tenerife",
  "Segovia", "Sevilla", "Soria", "Tarragona", "Teruel", "Toledo", "Valencia",
  "Valladolid", "Vizcaya", "Zamora", "Zaragoza"];

var MUNICIPIOS = {
  "Ourense": ["Allariz","Amoeiro","A Arnoia","Avión","Baltar","Bande",
    "Baños de Molgas","Barbadás","O Barco de Valdeorras","Beade","Beariz",
    "Os Blancos","Boborás","A Bola","O Bolo","Calvos de Randín",
    "Carballeda de Avia","Carballeda de Valdeorras","O Carballiño","Cartelle",
    "Castrelo de Miño","Castrelo do Val","Castro Caldelas","Celanova","Cenlle",
    "Chandrexa de Queixa","Coles","Cortegada","Cualedro","Entrimo","Esgos",
    "Gomesende","A Gudiña","O Irixo","Larouco","Laza","Leiro","Lobeira",
    "Lobios","Maceda","Manzaneda","Maside","Melón","A Merca","A Mezquita",
    "Montederramo","Monterrei","Muíños","Nogueira de Ramuín","Oímbra","Ourense",
    "Paderne de Allariz","Padrenda","Parada de Sil","O Pereiro de Aguiar",
    "A Peroxa","Petín","Piñor","A Pobra de Trives","Pontedeva","Porqueira",
    "Punxín","Quintela de Leirado","Rairiz de Veiga","Ramirás","Ribadavia",
    "Riós","A Rúa","Rubiá","San Amaro","San Cibrao das Viñas",
    "San Cristovo de Cea","San Xoán de Río","Sandiás","Sarreaus","Taboadela","A Teixeira","Toén",
    "Trasmiras","A Veiga","Verea","Verín","Viana do Bolo","Vilamarín",
    "Vilamartín de Valdeorras","Vilar de Barrio","Vilar de Santos","Vilardevós",
    "Vilariño de Conso","Xinzo de Limia","Xunqueira de Ambía",
    "Xunqueira de Espadanedo"],
  "Pontevedra": ["Vigo","Pontevedra","Vilagarcía de Arousa","Redondela",
    "Cangas","Marín","Ponteareas","A Estrada","Lalín","Poio","Nigrán","Moaña",
    "Tui","O Porriño","Baiona","Cambados","Gondomar","Sanxenxo","Silleda",
    "A Guarda","Salvaterra de Miño","Bueu","Mos","Caldas de Reis"],
  "A Coruña": ["A Coruña","Santiago de Compostela","Ferrol","Narón","Oleiros",
    "Arteixo","Culleredo","Ribeira","Carballo","Ames","Cambre","Boiro",
    "Betanzos","Sada","As Pontes de García Rodríguez","Noia","Cee","Melide",
    "Ordes","Padrón","Muros","Fene","Carral"],
  "Lugo": ["Lugo","Monforte de Lemos","Viveiro","Vilalba","Sarria","Foz",
    "Ribadeo","Burela","Chantada","Guitiriz","Mondoñedo","A Fonsagrada",
    "Becerreá","Palas de Rei","Monterroso","Quiroga"]
};

// Localidades sueltas para el resto de provincias: la capital y poco más.
["Álava:Vitoria-Gasteiz","Albacete:Albacete","Alicante:Alicante|Elche|Torrevieja|Benidorm",
 "Almería:Almería|Roquetas de Mar|El Ejido","Asturias:Oviedo|Gijón|Avilés|Langreo",
 "Ávila:Ávila","Badajoz:Badajoz|Mérida|Don Benito","Baleares:Palma|Ibiza|Manacor|Calvià",
 "Barcelona:Barcelona|Badalona|Sabadell|Terrassa|Hospitalet de Llobregat|Mataró",
 "Burgos:Burgos|Miranda de Ebro","Cáceres:Cáceres|Plasencia","Cádiz:Cádiz|Jerez de la Frontera|Algeciras|San Fernando",
 "Cantabria:Santander|Torrelavega|Camargo","Castellón:Castellón de la Plana|Vila-real|Burriana",
 "Ceuta:Ceuta","Ciudad Real:Ciudad Real|Puertollano|Tomelloso","Córdoba:Córdoba|Lucena|Puente Genil",
 "Cuenca:Cuenca","Girona:Girona|Figueres|Blanes|Lloret de Mar","Granada:Granada|Motril|Almuñécar",
 "Guadalajara:Guadalajara|Azuqueca de Henares","Guipúzcoa:San Sebastián|Irún|Errenteria",
 "Huelva:Huelva|Almonte|Lepe","Huesca:Huesca|Monzón|Barbastro","Jaén:Jaén|Linares|Andújar",
 "La Rioja:Logroño|Calahorra","Las Palmas:Las Palmas de Gran Canaria|Telde|Arrecife|Puerto del Rosario",
 "León:León|Ponferrada|San Andrés del Rabanedo","Lleida:Lleida|Balaguer",
 "Madrid:Madrid|Móstoles|Alcalá de Henares|Fuenlabrada|Leganés|Getafe|Alcorcón|Torrejón de Ardoz",
 "Málaga:Málaga|Marbella|Mijas|Vélez-Málaga|Fuengirola|Torremolinos|Estepona",
 "Melilla:Melilla","Murcia:Murcia|Cartagena|Lorca|Molina de Segura",
 "Navarra:Pamplona|Tudela|Barañáin","Palencia:Palencia","Salamanca:Salamanca|Béjar",
 "Santa Cruz de Tenerife:Santa Cruz de Tenerife|San Cristóbal de La Laguna|Arona|Adeje",
 "Segovia:Segovia","Sevilla:Sevilla|Dos Hermanas|Alcalá de Guadaíra|Utrera",
 "Soria:Soria","Tarragona:Tarragona|Reus|Salou|Tortosa","Teruel:Teruel|Alcañiz",
 "Toledo:Toledo|Talavera de la Reina|Illescas","Valencia:Valencia|Torrent|Gandía|Paterna|Sagunto",
 "Valladolid:Valladolid|Medina del Campo","Vizcaya:Bilbao|Barakaldo|Getxo|Portugalete",
 "Zamora:Zamora|Benavente","Zaragoza:Zaragoza|Calatayud|Utebo"
].forEach(function (fila) {
  var t = fila.split(":");
  MUNICIPIOS[t[0]] = t[1].split("|");
});

var MODULOS = {
  dashboard: { titulo: "Panel", sub: "Resumen de la empresa", icono: ico.panel, especial: "dashboard" },

  agenda: {
    titulo: "Agenda", sub: "Citas y visitas con clientes", icono: ico.calendario,
    recurso: "citas", especial: "agenda", uno: "cita", borrarDesdeFicha: true,
    duracion: { inicio: "inicio", fin: "fin", minutos: 60 },
    campos: [
      { c: "titulo", t: "Qué es", req: true, ayuda: "Por ejemplo: visita para presupuesto de baño" },
      { c: "tipo", t: "Tipo", tipo: "select", ops: TIPOS_CITA, mitad: true },
      { c: "estado", t: "Estado", tipo: "select", ops: ESTADOS_CITA, mitad: true },
      { c: "inicio", t: "Empieza", tipo: "fechahora", req: true, mitad: true },
      { c: "fin", t: "Termina", tipo: "fechahora", mitad: true, ayuda: "Se pone sola una hora después. Cámbiala si dura más, aunque sean varios días" },
      { c: "profesional_id", t: "Profesional", tipo: "ref", de: "profesionales", mitad: true, pordefecto: "miProfesional" },
      // Se escribe el cliente y el desplegable de obras se queda con las suyas.
      { c: "cliente_id", t: "Cliente", tipo: "busca", de: "clientes", mitad: true, filtraObras: "obra_id",
        placeholder: "Escribe para buscar el cliente", etiqueta: function (c) { return c.nombre; } },
      { c: "obra_id", t: "Obra", tipo: "ref", de: "obras" },
      { c: "direccion", t: "Dirección", ayuda: "Si la dejas vacía se usa la de la obra o, si no hay obra, la del cliente" },
      { c: "cancelada_por", t: "¿Quién la cancela?", tipo: "select",
        ops: QUIEN_CANCELA, soloSi: { campo: "estado", valor: "cancelada" } },
      { c: "motivo_cancelacion", t: "Motivo de la cancelación", tipo: "area",
        soloSi: { campo: "estado", valor: "cancelada" },
        ayuda: "Para acordarse dentro de tres meses de por qué se cayó" },
      { c: "notas", t: "Notas", tipo: "area" }
    ]
  },

  solicitudes: {
    titulo: "Solicitudes", sub: "Peticiones llegadas desde la web", icono: ico.buzon,
    recurso: "solicitudes",
    columnas: [
      { c: "nombre", t: "Nombre" },
      { c: "servicio", t: "Servicio" },
      { c: "telefono", t: "Teléfono" },
      { c: "email", t: "Email" },
      { c: "estado", t: "Estado", tipo: "estadoRapido", ops: ESTADOS_SOL },
      { c: "cliente_id", t: "Cliente", tipo: "ref", de: "clientes" },
      { c: "creado", t: "Recibida", tipo: "fecha" }
    ],
    // Accion extra en cada fila, ademas de editar y borrar
    accion: {
      ico: "altaCliente", titulo: "Pasar a cliente",
      oculta: function (f) { return !!f.cliente_id; },   // ya convertida
      fn: function (f) { pasarACliente(f); }
    },
    campos: [
      { c: "nombre", t: "Nombre", req: true, tipo: "cliente", de: "clientes",
        ayuda: "Elige un cliente de la lista o escribe un nombre nuevo: se le abre ficha al guardar" },
      { c: "email", t: "Email", tipo: "email", mitad: true },
      { c: "telefono", t: "Teléfono", mitad: true },
      { c: "servicio", t: "Servicio", mitad: true },
      { c: "estado", t: "Estado", tipo: "select", ops: ESTADOS_SOL, mitad: true },
      { c: "origen", t: "Cómo nos conoció", tipo: "lista", de: "listas/cliente-origenes",
        vacio: "Sin indicar",
        ayuda: "Si viene de la web, lo trae puesto. Al pasar la solicitud a cliente, se va con ella." },
      { c: "mensaje", t: "Mensaje", tipo: "area" },
      { c: "notas", t: "Notas internas", tipo: "area" }
    ]
  },

  visitas: { titulo: "Visitas", sub: "Notas y fotos de la toma de datos, antes del presupuesto",
             icono: ico.camara, especial: "visitas" },

  notas: {
    titulo: "Notas", sub: "Apuntes sueltos y de cada obra", icono: ico.nota,
    recurso: "notas", especial: "notas", uno: "nota", borrarDesdeFicha: true, fotos: true,
    campos: [
      { c: "titulo", t: "Título", ayuda: "Opcional. Por ejemplo: pedido de azulejo" },
      { c: "cliente_id", t: "Cliente", tipo: "busca", de: "clientes", mitad: true, filtraObras: "obra_id",
        placeholder: "Opcional", etiqueta: function (c) { return c.nombre; } },
      { c: "obra_id", t: "Obra", tipo: "ref", de: "obras", mitad: true,
        ayuda: "Cliente y obra son opcionales: una nota puede no ser de nadie" },
      { c: "contenido", t: "Nota", tipo: "area", req: true,
        ayuda: "Admite **negrita**, listas empezando la línea con «- » y títulos con «## »" }
    ]
  },

  clientes: {
    titulo: "Clientes", sub: "Quién te contrata", icono: ico.gente, recurso: "clientes",
    filtroPropio: "clientes",
    // Botón para ir a casa del cliente. Solo sale si hay calle: con solo la
    // ciudad o la provincia, el navegador llevaría al centro del pueblo.
    acciones: [
      { ico: "ojo", titulo: "Ficha del cliente", fn: function (f) { abrirFicha(f.id); } },
      { ico: "estrella", titulo: "Pedir reseña de Google por WhatsApp",
        oculta: function (f) { return !telefonoWhatsApp(f.telefono); },
        fn: function (f) { pedirResena(f, function () { ir("clientes"); }); } },
      { ico: "mapa", titulo: "Cómo llegar (Google Maps)",
        oculta: function (f) { return !String(f.direccion || "").trim(); },
        fn: function (f) { abrirMaps(f); } }
    ],
    columnas: [
      { c: "nombre", t: "Nombre" }, { c: "nif", t: "NIF" },
      { c: "telefono", t: "Teléfono" }, { c: "email", t: "Email" },
      { c: "ciudad", t: "Ciudad" }, { c: "origen", t: "Nos conoció por" }
    ],
    campos: [
      { c: "nombre", t: "Nombre o razón social", req: true },
      { c: "nif", t: "NIF / CIF", mitad: true },
      { c: "telefono", t: "Teléfono", mitad: true },
      { c: "email", t: "Email", tipo: "email", mitad: true },
      { c: "direccion", t: "Dirección" },
      { c: "cp", t: "Código postal", mitad: true },
      { c: "provincia", t: "Provincia", tipo: "provincia", mitad: true },
      { c: "ciudad", t: "Ciudad", tipo: "ciudad" },
      { c: "origen", t: "Cómo nos conoció", tipo: "lista", de: "listas/cliente-origenes",
        vacio: "Sin indicar",
        ayuda: "De aquí sale el informe de qué canal trae trabajo (Clientes > De dónde vienen)" },
      { c: "notas", t: "Notas", tipo: "area" }
    ]
  },

  profesionales: {
    titulo: "Profesionales", sub: "Tu cuadrilla, por oficio y zona", icono: ico.casco,
    recurso: "profesionales",
    columnas: [
      { c: "nombre", t: "Nombre" },
      { c: "categoria", t: "Oficios", tipo: "tags" },
      { c: "ciudades", t: "Opera en" },
      { c: "telefono", t: "Teléfono" },
      { c: "tarifa_hora", t: "€/hora", tipo: "eur", num: true },
      { c: "activo", t: "Estado", tipo: "bool", si: "Activo", no: "Baja" }
    ],
    campos: [
      { c: "nombre", t: "Nombre", req: true },
      { c: "categoria", t: "Oficios", tipo: "multi", ops: CATEGORIAS_PRO, req: true,
        ayuda: "Marca todos los que haga. Un profesional puede tener varios." },
      { c: "telefono", t: "Teléfono", mitad: true },
      { c: "email", t: "Email", tipo: "email", mitad: true },
      { c: "nif", t: "NIF", mitad: true },
      { c: "provincia", t: "Provincia", tipo: "provincia", mitad: true },
      { c: "ciudades", t: "Ciudades donde opera", ayuda: "Separadas por comas: Ourense, Barbadás, Allariz" },
      { c: "tarifa_hora", t: "Tarifa por hora (€)", tipo: "numero", mitad: true },
      { c: "autonomo", t: "Régimen", tipo: "select", ops: [{ v: 1, t: "Autónomo" }, { v: 0, t: "En plantilla" }], mitad: true },
      { c: "activo", t: "Estado", tipo: "select", ops: [{ v: 1, t: "Activo" }, { v: 0, t: "Baja" }], mitad: true },
      { c: "notas", t: "Notas", tipo: "area" }
    ]
  },

  obras: {
    titulo: "Obras", sub: "Trabajos en marcha y cerrados", icono: ico.obra,
    recurso: "obras", especial: "obras",
    // Al elegir el cliente se copia su dirección (ver abrirFormulario).
    direccionDe: { campo: "cliente_id", de: "clientes" },
    campos: [
      { c: "titulo", t: "Título de la obra", req: true },
      { c: "codigo", t: "Código", mitad: true, ayuda: "Referencia interna, p. ej. OB-2026-014" },
      { c: "estado", t: "Estado", tipo: "lista", de: "listas/obra-estados", mitad: true },
      { c: "cliente_id", t: "Cliente", tipo: "ref", de: "clientes", mitad: true },
      { c: "presupuesto_id", t: "Presupuesto", tipo: "busca", de: "documentos/presupuestos",
        placeholder: "Escribe el número o el cliente",
        etiqueta: function (p) {
          return p.numero + " · " + (p.cliente || "sin cliente") + " · " + eur(p.total);
        },
        filtra: function (p) { return p.estado !== "cancelado"; },
        trae: [{ campo: "importe_venta", de: "base" },
               { campo: "cliente_id", de: "cliente_id" }],
        ayuda: "De aquí salen el importe y el cliente de la obra. Los cancelados no se ofrecen." },
      { c: "importe_venta", t: "Importe presupuestado al cliente (sin IVA)", tipo: "eurofijo",
        placeholder: "Sale del presupuesto que elijas" },
      { c: "direccion", t: "Dirección" },
      { c: "cp", t: "Código postal", mitad: true },
      { c: "provincia", t: "Provincia", tipo: "provincia", mitad: true },
      { c: "ciudad", t: "Ciudad", tipo: "ciudad" },
      { c: "fecha_inicio", t: "Inicio", tipo: "fecha", mitad: true },
      { c: "fecha_fin_prevista", t: "Fin previsto", tipo: "fecha", mitad: true },
      { c: "fecha_fin_real", t: "Fin real", tipo: "fecha", mitad: true },
      { c: "notas", t: "Notas", tipo: "area" }
    ]
  },

  // Por dentro sigue siendo "costes" (tabla, API y permisos de cada miembro);
  // lo que cambia es el nombre que se ve.
  costes: {
    titulo: "Gastos", sub: "Todo lo que sale de caja, por obra o de la empresa", icono: ico.euro,
    // «nuevo» porque gasto es masculino: el título por defecto es «Nueva …».
    recurso: "costes", uno: "gasto", nuevo: "Nuevo gasto",
    // Desplegable encima de la tabla para ver los gastos de una sola obra.
    filtro: { c: "obra_id", de: "obras", todos: "Todas las obras", vacio: "Gastos de empresa",
              cliente: "clientes" },
    // El importe se escribe con el IVA incluido, que es lo que pone el tique.
    // Se guarda la base (lo que cuenta la contabilidad) y se enseña el total.
    conIva: true,
    // Totales por estado de lo que se ve (con los filtros y la búsqueda).
    resumen: function (filas) {
      var por = {}, total = 0;
      filas.forEach(function (f) {
        var k = f.estado || "sin estado";
        por[k] = por[k] || { n: 0, t: 0 };
        por[k].n++; por[k].t += conIva(f); total += conIva(f);
      });
      var cuantos = function (n) { return n + " gasto" + (n === 1 ? "" : "s"); };
      var h = '<div class="metricas">';
      (cache["listas/gasto-estados"] || []).forEach(function (e) {
        var x = por[e.nombre] || { n: 0, t: 0 };
        h += metrica(eur(x.t), e.nombre + " · " + cuantos(x.n), e.pagado ? "metrica--verde" : "");
        delete por[e.nombre];
      });
      Object.keys(por).forEach(function (k) { h += metrica(eur(por[k].t), k + " · " + cuantos(por[k].n), "metrica--rojo"); });
      return h + metrica(eur(total), "Total · " + cuantos(filas.length), "metrica--azul") + "</div>";
    },
    suma: function (filas) {
      var base = filas.reduce(function (a, f) { return a + (Number(f.importe) || 0); }, 0);
      var total = filas.reduce(function (a, f) { return a + conIva(f); }, 0);
      return "Total de lo que se ve: <b>" + eur(total) + "</b>" +
             ' <span style="color:var(--muted)">· base ' + eur(base) + " · IVA " + eur(total - base) + "</span>";
    },
    columnas: [
      { c: "fecha", t: "Fecha", tipo: "fecha" },
      { c: "concepto", t: "Concepto" },
      { c: "categoria", t: "Categoría", tipo: "tag" },
      { c: "obra_id", t: "Obra", tipo: "ref", de: "obras", vacio: "Empresa" },
      { c: "obra_id", t: "Cliente", tipo: "clienteObra" },
      { c: "profesional_id", t: "Profesional", tipo: "ref", de: "profesionales" },
      { c: "importe", t: "Total (IVA incl.)", tipo: "conIva", num: true },
      { c: "estado", t: "Estado", tipo: "estadoGasto" }
    ],
    campos: [
      { c: "concepto", t: "Concepto", req: true },
      { c: "categoria", t: "Categoría", tipo: "lista", de: "listas/gasto-categorias", mitad: true },
      { c: "fecha", t: "Fecha", tipo: "fecha", mitad: true, pordefecto: "hoy" },
      { c: "importe", t: "Importe con IVA incluido (€)", tipo: "numero", mitad: true, req: true },
      { c: "iva", t: "IVA", tipo: "select", ops: IVAS, mitad: true, pordefecto: 21 },
      { c: "_cliente", t: "Cliente", tipo: "filtraObras", de: "clientes", para: "obra_id",
        ayuda: "Para encontrar la obra: escribe el cliente y se quedan solo sus obras" },
      // Obligatorio: o una obra o, a propósito, gastos de la empresa (seguros,
      // gestoría, la furgoneta). Sin elegir no se guarda.
      { c: "obra_id", t: "A qué obra va", tipo: "ref", de: "obras", req: true, sinObra: "Gastos de empresa (no es de una obra)" },
      { c: "profesional_id", t: "Profesional", tipo: "ref", de: "profesionales", mitad: true, pordefecto: "miProfesional" },
      { c: "proveedor_id", t: "Proveedor", tipo: "ref", de: "proveedores", mitad: true },
      { c: "factura_ref", t: "Nº de factura", mitad: true },
      { c: "estado", t: "Estado", tipo: "lista", de: "listas/gasto-estados" },
      { c: "notas", t: "Notas", tipo: "area" }
    ]
  },

  ingresos: {
    titulo: "Ingresos", sub: "Facturación a clientes", icono: ico.euro, recurso: "ingresos",
    conIva: true,
    columnas: [
      { c: "fecha", t: "Fecha", tipo: "fecha" },
      { c: "concepto", t: "Concepto" },
      { c: "obra_id", t: "Obra", tipo: "ref", de: "obras" },
      { c: "cliente_id", t: "Cliente", tipo: "ref", de: "clientes" },
      { c: "factura_ref", t: "Factura" },
      { c: "importe", t: "Total (IVA incl.)", tipo: "conIva", num: true },
      { c: "cobrado", t: "Cobro", tipo: "bool", si: "Cobrado", no: "Pendiente" }
    ],
    campos: [
      { c: "concepto", t: "Concepto", req: true },
      { c: "fecha", t: "Fecha", tipo: "fecha", mitad: true, pordefecto: "hoy" },
      { c: "factura_ref", t: "Nº de factura", mitad: true },
      { c: "importe", t: "Importe con IVA incluido (€)", tipo: "numero", mitad: true, req: true },
      { c: "iva", t: "IVA", tipo: "select", ops: IVAS, mitad: true, pordefecto: 21 },
      { c: "obra_id", t: "Obra", tipo: "ref", de: "obras", mitad: true },
      { c: "cliente_id", t: "Cliente", tipo: "ref", de: "clientes", mitad: true },
      { c: "cobrado", t: "Estado", tipo: "select", ops: [{ v: 0, t: "Pendiente de cobro" }, { v: 1, t: "Cobrado" }] },
      { c: "notas", t: "Notas", tipo: "area" }
    ]
  },

  stock: {
    titulo: "Almacén", sub: "Material disponible", icono: ico.caja, recurso: "stock",
    especial: "stock",
    columnas: [
      { c: "nombre", t: "Artículo" }, { c: "referencia", t: "Ref." },
      { c: "categoria", t: "Categoría" },
      { c: "cantidad", t: "Cantidad", tipo: "cantidad", num: true },
      { c: "minimo", t: "Mínimo", num: true },
      { c: "precio_unitario", t: "Precio ud. (IVA incl.)", tipo: "eur", num: true },
      { c: "ubicacion", t: "Ubicación" }
    ],
    campos: [
      { c: "nombre", t: "Artículo", req: true },
      { c: "referencia", t: "Referencia", mitad: true },
      { c: "categoria", t: "Categoría", mitad: true },
      { c: "cantidad", t: "Cantidad actual", tipo: "numero", mitad: true },
      { c: "unidad", t: "Unidad", mitad: true, ayuda: "ud, m, m², kg, l…" },
      { c: "minimo", t: "Stock mínimo", tipo: "numero", mitad: true, ayuda: "Avisa cuando baje de aquí" },
      { c: "precio_unitario", t: "Precio unitario con IVA (€)", tipo: "numero", mitad: true,
        ayuda: "Lo que pone el tique. Al sacar material a una obra se apunta el gasto con este precio" },
      { c: "proveedor_id", t: "Proveedor", tipo: "ref", de: "proveedores", mitad: true },
      { c: "ubicacion", t: "Ubicación", mitad: true }
    ]
  },

  proveedores: {
    titulo: "Proveedores", sub: "A quién compras", icono: ico.camion, recurso: "proveedores",
    columnas: [
      { c: "nombre", t: "Nombre" }, { c: "categoria", t: "Categoría" },
      { c: "telefono", t: "Teléfono" }, { c: "email", t: "Email" }, { c: "nif", t: "NIF" }
    ],
    campos: [
      { c: "nombre", t: "Nombre", req: true },
      { c: "categoria", t: "Categoría", mitad: true, ayuda: "Material eléctrico, saneamiento…" },
      { c: "nif", t: "NIF", mitad: true },
      { c: "telefono", t: "Teléfono", mitad: true },
      { c: "email", t: "Email", tipo: "email", mitad: true },
      { c: "notas", t: "Notas", tipo: "area" }
    ]
  },

  presupuestos: { titulo: "Presupuestos", sub: "Ofertas enviadas a clientes",
                  icono: ico.doc, especial: "documento", tipo: "presupuestos" },

  proformas: { titulo: "Proformas", sub: "Facturas proforma, sin valor fiscal",
               icono: ico.proforma, especial: "documento", tipo: "proformas" },

  facturas: { titulo: "Facturas", sub: "Lo que has facturado",
              icono: ico.recibo, especial: "documento", tipo: "facturas" },

  contabilidad: { titulo: "Contabilidad", sub: "Resultado, IVA y pendientes", icono: ico.libro, especial: "contabilidad" }
};

MODULOS.equipo = { titulo: "Equipo", sub: "Quién entra al panel y a qué", icono: ico.equipo, especial: "equipo" };
// Submenús de Gastos: sus listas de categorías y estados.
MODULOS.gastos_categorias = { titulo: "Categorías de gasto", menu: "Categorías", sub: "Para clasificar los gastos",
  icono: ico.etiqueta, especial: "listaEditable", lista: "gasto-categorias", permiso: "costes" };
MODULOS.gastos_estados = { titulo: "Estados de gasto", menu: "Estados", sub: "Pendiente, pagado… los que uséis",
  icono: ico.ok, especial: "listaEditable", lista: "gasto-estados", permiso: "costes" };
MODULOS.obras_estados = { titulo: "Estados de obra", menu: "Estados", sub: "Presupuesto, en curso… los que uséis",
  icono: ico.ok, especial: "listaEditable", lista: "obra-estados", permiso: "obras" };
// Submenús de Clientes: de dónde vienen y la lista de canales.
MODULOS.clientes_origenes = { titulo: "Cómo nos conocen", menu: "Orígenes",
  sub: "Los canales por los que llega la gente",
  icono: ico.etiqueta, especial: "listaEditable", lista: "cliente-origenes", permiso: "clientes" };
MODULOS.clientes_origen = { titulo: "De dónde vienen", menu: "De dónde vienen",
  sub: "Qué canal trae clientes, obras y dinero",
  icono: ico.grafico, especial: "origenes", permiso: "clientes" };
// La ficha de un cliente: no sale en el menú, se entra desde Clientes.
MODULOS.ficha_cliente = { titulo: "Ficha de cliente", sub: "", icono: ico.gente, especial: "fichaCliente",
  permiso: "clientes" };
MODULOS.estatutos = { titulo: "Estatutos", sub: "Cómo funciona la empresa", icono: ico.normas, especial: "estatutos" };

// Responsable: quién lleva cada cosa. Solo lo ve y lo cambia el administrador;
// lo que crea un miembro es suyo sin preguntar.
["agenda", "solicitudes", "clientes", "obras", "notas", "costes", "ingresos"].forEach(function (k) {
  MODULOS[k].campos.push({ c: "usuario_id", t: "Responsable", tipo: "ref", de: "equipo",
    soloAdmin: true, pordefecto: "yo",
    ayuda: "Solo lo ven esa persona y el administrador. Empieza puesto en ti." });
  if (MODULOS[k].columnas) {
    MODULOS[k].columnas.push({ c: "usuario_id", t: "Responsable", tipo: "ref", de: "equipo", soloAdmin: true });
  }
});

var ORDEN_MENU = [
  { sep: null, items: ["dashboard", "agenda", "solicitudes", "visitas"] },
  { sep: "Gestión", items: [{ k: "obras", hijos: ["obras_estados"] }, "notas",
                            { k: "clientes", hijos: ["clientes_origen", "clientes_origenes"] },
                            "profesionales"] },
  { sep: "Economía", items: ["presupuestos", "proformas", "facturas",
                             { k: "costes", hijos: ["gastos_categorias", "gastos_estados"] }, "contabilidad"] },
  { sep: "Recursos", items: ["stock", "proveedores"] },
  { sep: "Empresa", items: ["estatutos", "equipo"] }
];

/* ── Caché de referencias (para los desplegables) ─────────────────────── */
var cache = {};
function cargarRef(nombre) {
  if (cache[nombre]) return Promise.resolve(cache[nombre]);
  return api("/api/admin/" + nombre).then(function (r) { cache[nombre] = r; return r; });
}
function nombreDe(lista, id) {
  if (!id) return "";
  var f = (cache[lista] || []).filter(function (x) { return x.id === id; })[0];
  return f ? (f.titulo || f.nombre) : "#" + id;
}
function invalidar() { cache = {}; }

// Lista del servidor que necesita un campo para pintarse: el desplegable de
// un "ref" y también el del nombre con fichero de clientes detrás.
function listaDe(c) {
  return (c.tipo === "ref" || c.tipo === "cliente" || c.tipo === "busca" ||
          c.tipo === "filtraObras" || c.tipo === "lista") ? c.de : null;
}

// Un desplegable con buscador no guarda lo que se escribe, sino el registro al
// que corresponde: se pinta una etiqueta por fila y luego hay que deshacer el
// camino para saber de cuál era.
function opcionesBusca(campo) {
  return (cache[campo.de] || [])
    .filter(campo.filtra || function () { return true; })
    .map(function (o) { return { id: o.id, txt: campo.etiqueta(o), fila: o }; });
}
// Deja solo lo del cliente elegido. Lo que no es de nadie se sigue ofreciendo
// —una obra sin cliente puede ser justo la que se está asignando— y lo que ya
// estuviera puesto también, para no romper un enlace al guardar.
function soloDelCliente(lista, cid, sel) {
  if (!cid) return lista;
  return lista.filter(function (o) {
    var de = o.cliente_id === undefined ? (o.fila || {}).cliente_id : o.cliente_id;
    return !de || String(de) === String(cid) || String(o.id) === String(sel);
  });
}

function pintarDatalist(id, ops) {
  var dl = document.getElementById(id);
  if (!dl) return;
  dl.innerHTML = ops.map(function (o) {
    return '<option value="' + esc(o.txt) + '"></option>';
  }).join("");
}

function buscaElegida(campo, texto) {
  var q = llano(texto);
  if (!q) return null;
  var ops = opcionesBusca(campo);
  var exacto = ops.filter(function (o) { return llano(o.txt) === q; });
  if (exacto.length) return exacto[0];
  // Nadie teclea la etiqueta entera. Con que lo escrito deje una sola opción
  // en pie —el número del presupuesto, el nombre del cliente— ya se sabe cuál
  // es. Si deja dos, no: se elige a ciegas y no se acierta.
  var caben = ops.filter(function (o) { return llano(o.txt).indexOf(q) >= 0; });
  return caben.length === 1 ? caben[0] : null;
}

// El cliente que se llama exactamente así, si lo hay. Lo que se escribe en el
// campo es un nombre, no un id: al guardar hay que volver a buscarlo.
function clientePorNombre(lista, nombre) {
  var q = llano(nombre);
  if (!q) return null;
  return (cache[lista] || []).filter(function (o) {
    return llano(o.nombre) === q;
  })[0] || null;
}

// Campos y columnas que tocan a este usuario: el responsable, solo al admin.
function camposDe(m) {
  return (m.campos || []).filter(function (c) { return !c.soloAdmin || esAdmin(); });
}
function columnasDe(m) {
  return (m.columnas || []).filter(function (c) { return !c.soloAdmin || esAdmin(); });
}

/* ── Router ───────────────────────────────────────────────────────────── */
var vistaActual = "dashboard";

function pintarMenu() {
  var h = "";
  ORDEN_MENU.forEach(function (grupo) {
    var items = grupo.items.map(function (x) { return typeof x === "string" ? { k: x, hijos: [] } : x; })
      .filter(function (x) { return puedeVer(x.k); });
    if (!items.length) return;
    if (grupo.sep) h += '<div class="sep">' + esc(grupo.sep) + "</div>";
    items.forEach(function (x) {
      var m = MODULOS[x.k], hijos = x.hijos.filter(puedeVer);
      var abierto = x.k === vistaActual || hijos.indexOf(vistaActual) >= 0;
      h += '<button data-vista="' + x.k + '"' + (x.k === vistaActual ? ' class="is-on"' : "") + ">" +
           svg(m.icono) + "<span>" + esc(m.titulo) + "</span>" +
           (hijos.length ? svg(abierto ? ico.arriba : ico.abajo, "lat__flecha") : "") + "</button>";
      if (abierto) hijos.forEach(function (k) {
        h += '<button class="lat__sub' + (k === vistaActual ? " is-on" : "") + '" data-vista="' + k + '">' +
             "<span>" + esc(MODULOS[k].menu || MODULOS[k].titulo) + "</span></button>";
      });
    });
  });
  $("#menu").innerHTML = h;
  $$("#menu button").forEach(function (b) {
    b.addEventListener("click", function () {
      // Desde el menú, las notas se abren todas; filtradas, desde su obra.
      if (b.dataset.vista === "notas") NOTAS_OBRA = "";
      ir(b.dataset.vista);
      $("#lat").classList.remove("is-open");
    });
  });
}

// Vista a la que se vuelve al guardar o borrar desde un formulario, si no es
// la del propio módulo (la ficha de cliente). Cualquier navegación la olvida.
var VOLVER = null;

function ir(k) {
  VOLVER = null;
  if (!MODULOS[k] || !puedeVer(k)) k = "dashboard";
  vistaActual = k;
  location.hash = k;
  pintarMenu();
  actualizarCampana();
  var m = MODULOS[k];
  $("#vista-titulo").textContent = m.titulo;
  $("#vista-sub").textContent = k === "dashboard" && !esAdmin()
    ? "Tu resumen: tus obras, tus clientes y tus números" : m.sub;
  $("#vista-acciones").innerHTML = "";
  $("#vista").innerHTML = '<div class="vacia">Cargando…</div>';

  if (m.especial === "dashboard") return verDashboard();
  if (m.especial === "equipo") return verMiembros();
  if (m.especial === "estatutos") return verEstatutos();
  if (m.especial === "agenda") return verAgenda();
  if (m.especial === "contabilidad") return verContabilidad();
  if (m.especial === "obras") return verObras();
  if (m.especial === "stock") return verStock();
  if (m.especial === "visitas") return verVisitas();
  if (m.especial === "notas") return verNotas();
  if (m.especial === "fichaCliente") return verFichaCliente();
  if (m.especial === "listaEditable") return verListaEditable(k);
  if (m.especial === "origenes") return verOrigenes();
  if (m.especial === "documento") return verDocumentos(k);
  return verTabla(k);
}

window.addEventListener("hashchange", function () {
  var k = location.hash.replace("#", "");
  if (MODULOS[k] && puedeVer(k) && k !== vistaActual) ir(k);
});

/* ── Vista genérica de tabla ──────────────────────────────────────────── */
// Filtro elegido en cada tabla que lo tiene. Se conserva al volver de guardar.
var FILTRO = {};

function verTabla(clave) {
  var m = MODULOS[clave];
  var refs = [];
  columnasDe(m).concat(camposDe(m)).forEach(function (c) {
    var de = listaDe(c);
    if (de && refs.indexOf(de) < 0) refs.push(de);
  });

  $("#vista-acciones").innerHTML =
    '<button class="btn btn--amber" id="btn-nuevo">' + svg(ico.mas) + "Nuevo</button>";
  $("#btn-nuevo").addEventListener("click", function () {
    var e = m.filtro && FILTRO[clave], inicial = null;
    if (e && (e.obra || e.cliente)) {
      inicial = {};
      if (e.obra) inicial[m.filtro.c] = e.obra === "ninguna" ? "ninguna" : Number(e.obra);
      if (e.cliente) inicial._cliente = e.cliente;
    }
    abrirFormulario(clave, null, inicial);
  });

  var fil = m.filtro;
  if (fil && fil.cliente && refs.indexOf(fil.cliente) < 0) refs.push(fil.cliente);
  // En Clientes el desplegable filtra la propia lista.
  var propio = m.filtroPropio;
  if (propio && refs.indexOf(propio) < 0) refs.push(propio);

  Promise.all([api("/api/admin/" + m.recurso)].concat(refs.map(cargarRef)))
    .then(function (res) {
      var filas = res[0];
      // Filtro por cliente y por obra. El cliente se escribe (va filtrando la
      // lista según se teclea) y, con él puesto, el desplegable de obras solo
      // ofrece las suyas.
      var est = (fil || propio) ? (FILTRO[clave] = FILTRO[clave] || { cliente: "", obra: "" }) : null;
      $("#vista").innerHTML =
        '<div class="herr">' +
        ((fil && fil.cliente) || propio
          ? '<input id="filtro-cliente" list="lista-filtro-cliente" autocomplete="off" class="herr__cliente"' +
            ' placeholder="Cliente: escribe para filtrar…" value="' + esc(est.cliente) + '">' +
            '<datalist id="lista-filtro-cliente">' + (cache[fil ? fil.cliente : propio] || []).map(function (c) {
              return '<option value="' + esc(c.nombre) + '"></option>';
            }).join("") + "</datalist>"
          : "") +
        (fil ? '<select id="filtro" aria-label="' + esc(fil.todos) + '"></select>' : "") +
        '<input type="search" id="buscar" placeholder="Buscar…"></div>' +
        (m.resumen ? '<div id="tabla-resumen"></div>' : "") +
        '<div class="tabla-caja"><div class="tabla-scroll" id="caja-tabla"></div>' +
        (m.suma ? '<div class="tabla-suma" id="tabla-suma"></div>' : "") + "</div>";

      function clientesEscritos() { return clientesQueEncajan(fil.cliente, est && est.cliente); }
      function obraDe(id) {
        return (cache[fil.de] || []).filter(function (o) { return String(o.id) === String(id); })[0];
      }
      function pintarObras() {
        var clis = clientesEscritos();
        var obras = (cache[fil.de] || []).filter(function (o) {
          return !clis || clis.indexOf(String(o.cliente_id)) >= 0;
        });
        // La obra elegida se suelta si ya no es de los clientes que quedan.
        if (est.obra && est.obra !== "ninguna" &&
            !obras.some(function (o) { return String(o.id) === est.obra; })) est.obra = "";
        if (clis && est.obra === "ninguna") est.obra = "";
        $("#filtro").innerHTML =
          '<option value="">' + esc(clis ? "Todas sus obras (" + obras.length + ")" : fil.todos) + "</option>" +
          (clis ? "" : '<option value="ninguna"' + (est.obra === "ninguna" ? " selected" : "") + ">" +
                       esc(fil.vacio) + "</option>") +
          obras.map(function (o) {
            return '<option value="' + o.id + '"' + (String(o.id) === est.obra ? " selected" : "") + ">" +
                   esc(o.titulo || o.nombre) + "</option>";
          }).join("");
      }

      function repintar() {
        var q = llano($("#buscar").value);
        var clis = fil && fil.cliente ? clientesEscritos() : null;
        var vistas = filas.filter(function (f) {
          if (fil) {
            if (est.obra === "ninguna" && f[fil.c]) return false;
            if (est.obra && est.obra !== "ninguna" && String(f[fil.c]) !== est.obra) return false;
            if (clis) {
              var o = obraDe(f[fil.c]);
              if (!o || clis.indexOf(String(o.cliente_id)) < 0) return false;
            }
          }
          if (propio) {
            var cp = clientesQueEncajan(propio, est.cliente);
            if (cp && cp.indexOf(String(f.id)) < 0) return false;
          }
          return !q || textoBusqueda(m, f).indexOf(q) >= 0;
        });
        pintarFilas(clave, vistas);
        if (m.suma) $("#tabla-suma").innerHTML = m.suma(vistas);
        if (m.resumen) $("#tabla-resumen").innerHTML = m.resumen(vistas);
      }
      if (fil) pintarObras();
      repintar();
      $("#buscar").addEventListener("input", repintar);
      if (fil) $("#filtro").addEventListener("change", function () {
        est.obra = this.value;
        repintar();
      });
      if ($("#filtro-cliente")) $("#filtro-cliente").addEventListener("input", function () {
        est.cliente = this.value;
        if (fil) pintarObras();
        repintar();
      });
    })
    .catch(error);
}

// Ids de los clientes que encajan con lo escrito, o null si no hay nada
// escrito. Si el nombre está entero, solo ese: «Carmen López» no tiene por
// qué traer también a «Carmen López Díaz».
function clientesQueEncajan(lista, texto) {
  var q = llano(texto);
  if (!q) return null;
  var todos = cache[lista] || [];
  var exacto = todos.filter(function (c) { return llano(c.nombre) === q; });
  var caben = exacto.length ? exacto : todos.filter(function (c) { return llano(c.nombre).indexOf(q) >= 0; });
  return caben.map(function (c) { return String(c.id); });
}

// Lo que se busca en una fila: sus datos y además los nombres que enseña la
// tabla (la obra, el cliente, el profesional), no los números que guarda.
function textoBusqueda(m, f) {
  var partes = Object.keys(f).map(function (k) { return f[k]; });
  columnasDe(m).forEach(function (col) {
    if (col.tipo === "ref") partes.push(nombreDe(col.de, f[col.c]) || col.vacio || "");
    if (col.tipo === "clienteObra") partes.push(clienteDeObra(f[col.c]));
    if (col.tipo === "fecha") partes.push(fecha(f[col.c]));
  });
  return llano(partes.join(" "));
}

// Importe con IVA de un apunte que guarda la base.
function conIva(f) { return (Number(f.importe) || 0) * (1 + (Number(f.iva) || 0) / 100); }

// Cliente de la obra de una fila, para los gastos, que cuelgan de la obra.
function clienteDeObra(obraId) {
  var o = (cache.obras || []).filter(function (x) { return x.id === obraId; })[0];
  return o && o.cliente_id ? nombreDe("clientes", o.cliente_id) : "";
}

function celda(col, fila) {
  var v = fila[col.c];
  if (col.tipo === "eur") return v ? eur(v) : "—";
  if (col.tipo === "fecha") return esc(fecha(v));
  if (col.tipo === "estadoGasto") {
    var est = (cache["listas/gasto-estados"] || []).filter(function (e) { return e.nombre === v; })[0];
    return v ? '<span class="tag ' + (est && est.pagado ? "tag--verde" : "tag--amber") + '">' + esc(v) + "</span>" : "—";
  }
  if (col.tipo === "conIva") return fila[col.c] ? eur(conIva(fila)) : "—";
  if (col.tipo === "clienteObra") return esc(clienteDeObra(v)) || "—";
  if (col.tipo === "ref") {
    return esc(nombreDe(col.de, v)) || (col.vacio ? '<span class="tag">' + esc(col.vacio) + "</span>" : "—");
  }
  if (col.tipo === "cantidad") {
    var bajo = fila.minimo > 0 && fila.cantidad <= fila.minimo;
    return '<span class="' + (bajo ? "tag tag--rojo" : "") + '">' +
           num(v) + " " + esc(fila.unidad || "") + "</span>";
  }
  if (col.tipo === "bool") {
    return '<span class="tag ' + (v ? "tag--verde" : "tag--amber") + '">' +
           esc(v ? col.si : col.no) + "</span>";
  }
  if (col.tipo === "tags") {
    if (!v) return "—";
    return String(v).split(",").map(function (x) {
      return '<span class="tag" style="margin-right:4px">' + esc(x.trim()) + "</span>";
    }).join("");
  }
  if (col.tipo === "estadoRapido") {
    // Desplegable en la propia fila: cambiar de estado no obliga a abrir la
    // ficha. El manejador está en pintarFilas.
    return '<select class="estado-rapido estado-rapido--' + esc(v) + '" data-estado="' +
      fila.id + '" aria-label="Estado de ' + esc(fila.nombre || "") + '">' +
      col.ops.map(function (o) {
        return "<option" + (o === v ? " selected" : "") + ">" + esc(o) + "</option>";
      }).join("") + "</select>";
  }
  if (col.tipo === "tag") {
    var clase = "";
    if (v === "en curso" || v === "atendida" || v === "terminada") clase = " tag--verde";
    if (v === "pendiente" || v === "presupuesto") clase = " tag--amber";
    if (v === "cancelada" || v === "descartada") clase = " tag--rojo";
    return v ? '<span class="tag' + clase + '">' + esc(v) + "</span>" : "—";
  }
  return esc(v) || "—";
}

// Botones propios de cada fila, además de editar y borrar.
function accionesDe(m) { return m.acciones || (m.accion ? [m.accion] : []); }

function pintarFilas(clave, filas) {
  var m = MODULOS[clave], caja = $("#caja-tabla");
  if (!filas.length) {
    caja.innerHTML = '<div class="vacia">Todavía no hay nada aquí. Pulsa «Nuevo» para empezar.</div>';
    return;
  }
  var h = "<table><thead><tr>";
  var cols = columnasDe(m);
  cols.forEach(function (c) { h += '<th' + (c.num ? ' class="num"' : "") + ">" + esc(c.t) + "</th>"; });
  h += '<th class="num">Acciones</th></tr></thead><tbody>';
  filas.forEach(function (f) {
    h += "<tr>";
    cols.forEach(function (c) { h += "<td" + (c.num ? ' class="num"' : "") + ">" + celda(c, f) + "</td>"; });
    h += '<td class="acciones">' +
         accionesDe(m).map(function (a, i) {
           return a.oculta && a.oculta(f) ? ""
             : '<button data-accion="' + i + ":" + f.id + '" title="' + esc(a.titulo) + '">' + svg(ico[a.ico]) + "</button>";
         }).join("") +
         '<button data-editar="' + f.id + '" title="Editar">' + svg(ico.lapiz) + "</button>" +
         '<button class="borrar" data-borrar="' + f.id + '" title="Borrar">' + svg(ico.papelera) + "</button>" +
         "</td></tr>";
  });
  caja.innerHTML = h + "</tbody></table>";

  $$("[data-editar]", caja).forEach(function (b) {
    b.addEventListener("click", function () {
      abrirFormulario(clave, filas.filter(function (x) { return x.id == b.dataset.editar; })[0]);
    });
  });
  $$("[data-borrar]", caja).forEach(function (b) {
    b.addEventListener("click", function () { confirmarBorrado(clave, b.dataset.borrar); });
  });
  $$("[data-accion]", caja).forEach(function (b) {
    b.addEventListener("click", function () {
      var p = b.dataset.accion.split(":");
      accionesDe(m)[p[0]].fn(filas.filter(function (x) { return String(x.id) === p[1]; })[0]);
    });
  });
  // Cambio de estado desde la fila. Si el servidor lo rechaza, el desplegable
  // vuelve a su valor para no enseñar un estado que no se ha guardado.
  $$("[data-estado]", caja).forEach(function (sel) {
    sel.addEventListener("change", function () {
      var f = filas.filter(function (x) { return x.id == sel.dataset.estado; })[0];
      var antes = f.estado, ahora = sel.value;
      sel.disabled = true;
      api("/api/admin/" + m.recurso + "/" + f.id, { metodo: "PUT", datos: { estado: ahora } })
        .then(function () {
          f.estado = ahora;
          sel.className = "estado-rapido estado-rapido--" + ahora;
          actualizarCampana();
          avisar((f.nombre ? f.nombre + ": " : "") + ahora);
        })
        .catch(function (e) { sel.value = antes; avisar(e.message, "err"); })
        .finally(function () { sel.disabled = false; });
    });
  });
}

/* ── Modal ────────────────────────────────────────────────────────────── */
function modal(titulo, cuerpo, pie, ancho) {
  $("#modal-host").innerHTML =
    '<div class="modal" id="modal"><div class="modal__caja' + (ancho ? " modal__caja--ancho" : "") + '">' +
    '<div class="modal__cab"><h2>' + esc(titulo) + '</h2>' +
    '<button id="modal-x" aria-label="Cerrar">&times;</button></div>' +
    cuerpo + '<div class="modal__pie">' + pie + "</div></div></div>";
  $("#modal-x").addEventListener("click", cerrarModal);
  // A propósito NO se cierra al pinchar fuera: con un formulario a medio
  // rellenar, un clic despistado en el fondo tiraba todo lo escrito.
  // Se cierra con el aspa, con Cancelar o con Escape.
  document.addEventListener("keydown", escCierra);
}
function escCierra(e) { if (e.key === "Escape") cerrarModal(); }
function cerrarModal() {
  $("#modal-host").innerHTML = "";
  document.removeEventListener("keydown", escCierra);
}

function campoHTML(campo, valor, esNuevo) {
  var v = valor === null || valor === undefined ? "" : valor;
  if (campo.tipo === "fechahora" && v) v = String(v).slice(0, 16);
  // El responsable y el profesional se ponen en quien ha entrado siempre que
  // estén vacíos, también al editar algo que no tenía a nadie. El resto de
  // valores por defecto, solo en lo nuevo.
  var deSesion = campo.pordefecto === "yo" || campo.pordefecto === "miProfesional";
  if ((esNuevo || deSesion) && v === "" && campo.pordefecto !== undefined) {
    v = campo.pordefecto === "hoy" ? new Date().toISOString().slice(0, 10)
      : campo.pordefecto === "yo" ? ((YO && YO.id) || "")
      : campo.pordefecto === "miProfesional" ? ((YO && YO.profesional_id) || "")
      : campo.pordefecto;
  }
  var h = '<div class="campo"' +
          (campo.soloSi ? ' data-solosi="' + esc(campo.soloSi.campo) + "=" + esc(campo.soloSi.valor) + '"' : "") +
          '><label for="c-' + campo.c + '">' + esc(campo.t) + (campo.req ? " *" : "") + "</label>";
  if (campo.tipo === "area") {
    h += '<textarea id="c-' + campo.c + '" data-c="' + campo.c + '">' + esc(v) + "</textarea>";
  } else if (campo.tipo === "select") {
    h += '<select id="c-' + campo.c + '" data-c="' + campo.c + '">';
    var enLista = campo.ops.some(function (o) {
      return String(typeof o === "object" ? o.v : o) === String(v);
    });
    if (v !== "" && !enLista) h += '<option value="' + esc(v) + '" selected>' + esc(v) + (campo.c === "iva" ? " %" : "") + "</option>";
    campo.ops.forEach(function (o) {
      var val = (typeof o === "object") ? o.v : o;
      var txt = (typeof o === "object") ? o.t : o;
      h += '<option value="' + esc(val) + '"' + (String(val) === String(v) ? " selected" : "") + ">" + esc(txt) + "</option>";
    });
    h += "</select>";
  } else if (campo.tipo === "multi") {
    var puestos = String(v || "").split(",").map(function (x) { return x.trim(); });
    h += '<div class="multi" data-multi="' + campo.c + '">';
    campo.ops.forEach(function (o) {
      h += "<label><input type=\"checkbox\" value=\"" + esc(o) + "\"" +
           (puestos.indexOf(o) >= 0 ? " checked" : "") + ">" + esc(o) + "</label>";
    });
    h += "</div>";
  } else if (campo.tipo === "provincia") {
    h += '<select id="c-' + campo.c + '" data-c="' + campo.c + '" data-provincia>';
    var prov = v || "Ourense";   // por defecto, la de casa
    PROVINCIAS.forEach(function (o) {
      h += '<option value="' + esc(o) + '"' + (o === prov ? " selected" : "") + ">" + esc(o) + "</option>";
    });
    h += "</select>";
  } else if (campo.tipo === "ciudad") {
    // input + datalist: se escribe y va filtrando, pero admite cualquier
    // valor. Un <select> obligaría a tener TODOS los municipios de España.
    h += '<input id="c-' + campo.c + '" data-c="' + campo.c + '" data-ciudad' +
         ' list="lista-' + campo.c + '" autocomplete="off"' +
         ' placeholder="Escribe para filtrar…" value="' + esc(v) + '">' +
         '<datalist id="lista-' + campo.c + '"></datalist>';
  } else if (campo.tipo === "busca") {
    // Desplegable con buscador. Un <select> con doscientos presupuestos no hay
    // quien lo mire: aquí se escribe el número o el nombre del cliente y la
    // lista se va quedando corta sola. Lo que se guarda no es el texto, sino
    // el registro elegido (ver el guardado).
    var ops = opcionesBusca(campo);
    var yaEsta = ops.filter(function (o) { return String(o.id) === String(v); })[0];
    h += '<input id="c-' + campo.c + '" data-busca="' + campo.c + '"' +
         // Si además filtra obras, lo engancha el mismo código que en Gastos.
         (campo.filtraObras ? ' data-filtra-obras="' + esc(campo.filtraObras) + '" data-lista="' + esc(campo.de) + '"' : "") +
         ' list="lista-' + campo.c + '" autocomplete="off"' +
         ' placeholder="' + esc(campo.placeholder || "Escribe para buscar…") + '"' +
         ' value="' + esc(yaEsta ? yaEsta.txt : "") + '">' +
         '<datalist id="lista-' + campo.c + '">' +
         ops.map(function (o) { return '<option value="' + esc(o.txt) + '"></option>'; }).join("") +
         "</datalist>";
  } else if (campo.tipo === "eurofijo") {
    // Importe que no se teclea: lo trae otro campo. Se enseña con formato de
    // euros, que es como se lee, y el número de verdad viaja en data-valor.
    h += '<input id="c-' + campo.c + '" data-c="' + campo.c + '" readonly' +
         ' data-valor="' + esc(v === "" ? "" : Number(v)) + '"' +
         ' placeholder="' + esc(campo.placeholder || "") + '"' +
         ' value="' + esc(v === "" ? "" : eur(v)) + '">';
  } else if (campo.tipo === "cliente") {
    // Desplegable de clientes que además deja escribir. Un nombre que no esté
    // en la lista no es un error: es un cliente nuevo y el servidor le abre
    // ficha al guardar. Con un <select> habría que darlo de alta antes, en
    // otra pestaña, y volver aquí a empezar de cero.
    h += '<input id="c-' + campo.c + '" data-c="' + campo.c + '" data-cliente="' + esc(campo.de) + '"' +
         ' list="lista-' + campo.c + '" autocomplete="off"' +
         ' placeholder="Elige un cliente o escribe un nombre nuevo"' +
         ' value="' + esc(v) + '">' +
         '<datalist id="lista-' + campo.c + '">' +
         (cache[campo.de] || []).map(function (o) {
           return '<option value="' + esc(o.nombre) + '"></option>';
         }).join("") + "</datalist>";
  } else if (campo.tipo === "lista") {
    // Desplegable con una lista que se edita en el panel (categorías y estados
    // de los gastos). Se guarda el nombre. Vacío: el primero, o el primer
    // estado pendiente. Un valor que ya no está en la lista se conserva.
    var items = cache[campo.de] || [];
    // Hay listas donde no contestar es una respuesta: cómo nos conoció un
    // cliente no siempre se sabe, y poner el primero por defecto sería
    // inventárselo justo en el dato del que luego sale el informe.
    if (v === "" && !campo.vacio) {
      var pend = items.filter(function (x) { return !x.pagado; })[0];
      v = ((campo.de === "listas/gasto-estados" && pend) || items[0] || {}).nombre || "";
    }
    h += '<select id="c-' + campo.c + '" data-c="' + campo.c + '">' +
         (campo.vacio ? '<option value=""' + (v === "" ? " selected" : "") + ">" +
                        esc(campo.vacio) + "</option>" : "") +
         (v && !items.some(function (x) { return x.nombre === v; })
           ? '<option value="' + esc(v) + '" selected>' + esc(v) + "</option>" : "") +
         items.map(function (x) {
           return '<option value="' + esc(x.nombre) + '"' + (x.nombre === v ? " selected" : "") + ">" + esc(x.nombre) + "</option>";
         }).join("") + "</select>";
  } else if (campo.tipo === "filtraObras") {
    // No se guarda (no lleva data-c): solo sirve para encontrar la obra. Se
    // escribe y el desplegable de obras se queda con las de ese cliente.
    h += '<input id="c-' + campo.c + '" data-filtra-obras="' + esc(campo.para) + '"' +
         ' data-lista="' + esc(campo.de) + '" list="lista-' + campo.c + '" autocomplete="off"' +
         ' placeholder="Escribe para filtrar las obras…" value="' + esc(v) + '">' +
         '<datalist id="lista-' + campo.c + '">' + (cache[campo.de] || []).map(function (o) {
           return '<option value="' + esc(o.nombre) + '"></option>';
         }).join("") + "</datalist>";
  } else if (campo.tipo === "ref" && campo.sinObra) {
    // Aquí vacío no significa «sin rellenar» sino una elección: ninguna obra.
    // Por eso va aparte del vacío de verdad, que no deja guardar. Un registro
    // que ya existe sin obra se abre con esa opción elegida.
    var ninguna = (!esNuevo && v === "") || v === "ninguna";
    h += '<select id="c-' + campo.c + '" data-c="' + campo.c + '">' +
         '<option value=""' + (!ninguna && v === "" ? " selected" : "") + ">— elige a qué va —</option>" +
         '<option value="ninguna"' + (ninguna ? " selected" : "") + ">" + esc(campo.sinObra) + "</option>";
    if (v !== "" && !(cache[campo.de] || []).some(function (o) { return String(o.id) === String(v); })) {
      h += '<option value="' + esc(v) + '" selected>(lo lleva otra persona)</option>';
    }
    (cache[campo.de] || []).forEach(function (o) {
      h += '<option value="' + o.id + '"' + (String(o.id) === String(v) ? " selected" : "") + ">" +
           esc(o.titulo || o.nombre) + "</option>";
    });
    h += "</select>";
  } else if (campo.tipo === "ref") {
    h += '<select id="c-' + campo.c + '" data-c="' + campo.c + '"><option value="">' +
         (campo.de === "equipo" ? "— nadie: solo el administrador —" : "— sin asignar —") + "</option>";
    // Si la ficha apunta a algo que esta persona no ve (el administrador la
    // enlazó con el cliente de un compañero), se conserva: sin esta opción el
    // desplegable saldría en blanco y al guardar se perdería el enlace.
    if (v !== "" && !(cache[campo.de] || []).some(function (o) { return String(o.id) === String(v); })) {
      h += '<option value="' + esc(v) + '" selected>(lo lleva otra persona)</option>';
    }
    (cache[campo.de] || []).forEach(function (o) {
      h += '<option value="' + o.id + '"' + (String(o.id) === String(v) ? " selected" : "") + ">" +
           esc(o.titulo || o.nombre) + "</option>";
    });
    h += "</select>";
  } else {
    var tipo = campo.tipo === "numero" ? "number" : campo.tipo === "fecha" ? "date"
             : campo.tipo === "fechahora" ? "datetime-local"
             : campo.tipo === "email" ? "email" : "text";
    h += '<input id="c-' + campo.c + '" data-c="' + campo.c + '" type="' + tipo + '"' +
         (campo.tipo === "numero" ? ' step="any"' : "") +
         ' value="' + esc(v) + '">';
  }
  if (campo.ayuda) h += '<small style="color:var(--muted-2);font-size:.79rem">' + esc(campo.ayuda) + "</small>";
  return h + "</div>";
}

function abrirFormulario(clave, registro, inicial) {
  var m = MODULOS[clave], editando = !!registro;
  // "inicial": valores de partida para uno NUEVO (la agenda abre la cita en
  // el día que se pinchó). No es un registro: se crea, no se edita.
  var vals = registro || inicial || null;
  if (m.conIva && registro && registro.importe !== null && registro.importe !== undefined) {
    vals = Object.assign({}, registro, { importe: Math.round(conIva(registro) * 100) / 100 });
  }
  var refs = [];
  var campos = camposDe(m);
  campos.forEach(function (c) {
    var de = listaDe(c);
    if (de && refs.indexOf(de) < 0) refs.push(de);
  });

  Promise.all(refs.map(cargarRef)).then(function () {
    var cuerpo = '<div class="aviso aviso--err" id="f-err" hidden></div><form id="f-form">';
    var buffer = [];
    campos.forEach(function (campo) {
      if (campo.mitad) {
        buffer.push(campo);
        if (buffer.length === 2) {
          cuerpo += '<div class="rejilla-2">' +
            campoHTML(buffer[0], vals && vals[buffer[0].c], !editando) +
            campoHTML(buffer[1], vals && vals[buffer[1].c], !editando) + "</div>";
          buffer = [];
        }
      } else {
        if (buffer.length) {
          cuerpo += campoHTML(buffer[0], vals && vals[buffer[0].c], !editando);
          buffer = [];
        }
        cuerpo += campoHTML(campo, vals && vals[campo.c], !editando);
      }
    });
    if (buffer.length) cuerpo += campoHTML(buffer[0], vals && vals[buffer[0].c], !editando);
    cuerpo += "</form>";
    if (m.fotos) {
      cuerpo += '<div class="vis-cab"><span class="vis-cab__t">Imágenes</span><span class="vis-cab__btns">' +
        '<label class="btn btn--amber btn--sm">' + svg(ico.camara) + "Hacer foto" +
          '<input type="file" accept="image/*" capture="environment" class="f-imagen" hidden></label>' +
        '<label class="btn btn--fant btn--sm">' + svg(ico.mas) + "Subir imagen" +
          '<input type="file" accept="image/*" multiple class="f-imagen" hidden></label></span></div>' +
        '<div class="fotos" id="f-fotos"></div>' +
        '<div class="vis-cab" style="margin-top:16px"><span class="vis-cab__t">Archivos</span><span class="vis-cab__btns">' +
        '<label class="btn btn--fant btn--sm">' + svg(ico.clip) + "Adjuntar archivo" +
          '<input type="file" multiple class="f-archivo" hidden accept="' +
          EXT_ARCHIVO.map(function (e) { return "." + e; }).join(",") + '"></label></span></div>' +
        '<div class="adjuntos" id="f-archivos"></div>' +
        '<small style="color:var(--muted-2);font-size:.79rem">PDF, Word, Excel, PowerPoint, OpenDocument, TXT o CSV, hasta 20 MB cada uno.</small>';
    }

    modal(m.uno ? (editando ? "Editar " + m.uno : m.nuevo || "Nueva " + m.uno)
               : (editando ? "Editar " : "Nuevo en ") + m.titulo.toLowerCase(), cuerpo,
      (editando && m.borrarDesdeFicha
        ? '<button class="btn btn--peligro" id="f-borrar" style="margin-right:auto">Borrar</button>'
        : "") +
      '<button class="btn btn--fant" id="f-cancelar">Cancelar</button>' +
      '<button class="btn btn--amber" id="f-guardar">Guardar</button>');

    var galeria = m.fotos ? galeriaFotos({
      caja: "#f-fotos", entradas: "#modal .f-imagen", guardar: "#f-guardar",
      existentes: registro && registro.fotos,
      padre: function () { return m.recurso + "/" + (registro && registro.id); }
    }) : null;
    var adjuntos = m.fotos ? listaArchivos({
      caja: "#f-archivos", entradas: "#modal .f-archivo", guardar: "#f-guardar",
      existentes: registro && registro.archivos,
      padre: function () { return m.recurso + "/" + (registro && registro.id); }
    }) : null;

    // La lista de ciudades depende de la provincia elegida y se rehace
    // cada vez que esta cambia.
    var selProv = $("#f-form [data-provincia]");
    function refrescarCiudades() {
      var prov = selProv ? selProv.value : "Ourense";
      var municipios = MUNICIPIOS[prov] || [];
      $$("#f-form [data-ciudad]").forEach(function (inp) {
        var dl = document.getElementById("lista-" + inp.dataset.c);
        if (!dl) return;
        dl.innerHTML = municipios.map(function (m) {
          return '<option value="' + esc(m) + '"></option>';
        }).join("");
      });
    }
    refrescarCiudades();
    if (selProv) {
      selProv.addEventListener("change", function () {
        // Si la ciudad escrita no es de la provincia nueva, se limpia:
        // dejarla puesta daría un dato incoherente sin avisar.
        var prov = selProv.value, municipios = MUNICIPIOS[prov] || [];
        $$("#f-form [data-ciudad]").forEach(function (inp) {
          if (inp.value && municipios.indexOf(inp.value) < 0) inp.value = "";
        });
        refrescarCiudades();
      });
    }

    // Al escribir el nombre de un cliente que ya está fichado se traen su
    // correo y su teléfono, para no tener que ir a mirarlos. Solo se rellenan
    // los huecos y lo que se puso solo con el cliente anterior: un teléfono
    // escrito a mano no se pisa.
    var inpCli = $("#f-form [data-cliente]"), pegado = {};
    if (inpCli) inpCli.addEventListener("change", function () {
      // Si el nombre pasa a ser el de otra persona —o el de nadie, porque se
      // está fichando a alguien nuevo—, lo que se trajo del cliente anterior
      // se borra. Dejarlo puesto acabaría dando de alta a un cliente nuevo
      // con el correo y el teléfono de otro.
      var cli = clientePorNombre(inpCli.dataset.cliente, inpCli.value);
      var traido = false;
      ["email", "telefono"].forEach(function (c) {
        var el = $("#c-" + c);
        if (!el || (el.value.trim() && el.value !== pegado[c])) return;
        el.value = cli ? (cli[c] || "") : "";
        pegado[c] = el.value;
        if (el.value) traido = true;
      });
      if (cli && traido) avisar("Datos de contacto de " + cli.nombre);
    });

    // Con un cliente elegido, el buscador solo sugiere lo suyo: buscar el
    // presupuesto de una obra entre los de toda la empresa es buscar de más.
    var selCliente = $("#c-cliente_id");
    function filtrarSugerencias() {
      $$("#f-form [data-busca]").forEach(function (inp) {
        var campo = campos.filter(function (c) { return c.c === inp.dataset.busca; })[0];
        if (!campo) return;
        var puesto = buscaElegida(campo, inp.value);
        pintarDatalist("lista-" + campo.c,
          soloDelCliente(opcionesBusca(campo), selCliente && selCliente.value,
                         puesto && puesto.id));
      });
    }
    if (selCliente) {
      filtrarSugerencias();
      selCliente.addEventListener("change", filtrarSugerencias);
    }

    // Al elegir en un desplegable con buscador, el campo que depende de él se
    // rellena solo (el importe de la obra sale del presupuesto). Si lo escrito
    // no es ninguna de las opciones se borra: dejar un texto a medias haría
    // creer que la obra tiene presupuesto cuando al guardar no tendría ninguno.
    $$("#f-form [data-busca]").forEach(function (inp) {
      var campo = campos.filter(function (c) { return c.c === inp.dataset.busca; })[0];
      if (!campo) return;
      inp.addEventListener("change", function () {
        var op = buscaElegida(campo, inp.value);
        if (op) inp.value = op.txt;      // se ve entero lo que ha quedado elegido
        else if (inp.value.trim()) {
          inp.value = "";
          avisar("Elige uno de la lista", "err");
        }
        (campo.trae || []).forEach(function (t) {
          var destino = $("#c-" + t.campo);
          if (!destino) return;
          var valor = op ? op.fila[t.de] : "";
          if (valor === null || valor === undefined) valor = "";
          if (destino.hasAttribute("data-valor")) {
            destino.dataset.valor = valor;
            destino.value = valor === "" ? "" : eur(valor);
          } else {
            // Se avisa del cambio a mano: de un cliente cuelgan otras cosas
            // (su dirección), y si no se dispara no se enteran.
            destino.value = valor;
            destino.dispatchEvent(new Event("change", { bubbles: true }));
          }
        });
      });
    });

    // Cliente para encontrar la obra: deja en el desplegable solo sus obras.
    // «Gastos de empresa» y lo que lleva otra persona se ofrecen siempre. Al
    // editar, o al elegir la obra con el cliente vacío, se pone el de la obra.
    $$("#f-form [data-filtra-obras]").forEach(function (inp) {
      var sel = $("#c-" + inp.dataset.filtraObras);
      if (!sel) return;
      var todas = $$("option", sel).map(function (o) { return { v: o.value, t: o.text }; });
      function obraDe(id) {
        return (cache.obras || []).filter(function (o) { return String(o.id) === String(id); })[0];
      }
      function clienteDeLaObra() {
        var o = obraDe(sel.value);
        if (!inp.value.trim() && o && o.cliente_id) inp.value = nombreDe(inp.dataset.lista, o.cliente_id);
      }
      function filtrar() {
        var clis = clientesQueEncajan(inp.dataset.lista, inp.value), antes = sel.value;
        sel.innerHTML = todas.filter(function (op) {
          var o = obraDe(op.v);
          return !clis || !o || clis.indexOf(String(o.cliente_id)) >= 0;
        }).map(function (op) {
          return '<option value="' + esc(op.v) + '">' + esc(op.t) + "</option>";
        }).join("");
        sel.value = antes;
        if (sel.value !== antes) sel.value = "";
      }
      clienteDeLaObra();
      filtrar();
      inp.addEventListener("input", filtrar);
      // También al salir del campo: el buscador borra lo que no es un cliente.
      inp.addEventListener("change", filtrar);
      sel.addEventListener("change", clienteDeLaObra);
    });

    // Campos que solo se pintan cuando otro campo tiene cierto valor: el
    // motivo de la cancelación no tiene por qué estorbar mientras la cita
    // sigue en pie.
    $$("#f-form [data-solosi]").forEach(function (caja) {
      var partes = caja.dataset.solosi.split("="), mando = $("#c-" + partes[0]);
      if (!mando) return;
      var repintar = function () { caja.style.display = mando.value === partes[1] ? "" : "none"; };
      repintar();
      mando.addEventListener("change", repintar);
    });

    $("#f-cancelar").addEventListener("click", cerrarModal);
    if ($("#f-borrar")) $("#f-borrar").addEventListener("click", function () {
      confirmarBorrado(clave, registro.id);
    });

    // Al elegir la hora de inicio, la de fin se pone sola una hora después.
    // Si la cita ya duraba más (una obra de varios días), se desplaza entera
    // y conserva lo que dura, para no deshacer el fin que se había puesto.
    if (m.duracion) {
      var inpIni = $("#c-" + m.duracion.inicio), inpFin = $("#c-" + m.duracion.fin);
      var iniAntes = inpIni ? inpIni.value : "";
      var moverFin = function () {
        var nuevo = leerLocal(inpIni.value);
        if (!nuevo) return;
        var antes = leerLocal(iniAntes), fin = leerLocal(inpFin.value);
        var dura = (antes && fin && fin > antes) ? fin - antes : m.duracion.minutos * 60000;
        inpFin.value = escribirLocal(new Date(nuevo.getTime() + dura));
        iniAntes = inpIni.value;
      };
      if (inpIni && inpFin) {
        inpIni.addEventListener("input", moverFin);
        inpIni.addEventListener("change", moverFin);
      }
    }

    // Al elegir el cliente, la dirección se copia de su ficha. Solo se tocan
    // los campos vacíos o los que se rellenaron solos con el cliente anterior:
    // si alguien ya escribió otra dirección (una obra en una segunda vivienda),
    // se respeta.
    if (m.direccionDe) {
      var selCli = $("#c-" + m.direccionDe.campo), puesto = {};
      var libre = function (c) {
        var el = $("#c-" + c);
        return !!el && (!el.value.trim() || el.value === puesto[c]);
      };
      if (selCli) selCli.addEventListener("change", function () {
        var cli = (cache[m.direccionDe.de] || []).filter(function (x) {
          return String(x.id) === selCli.value;
        })[0];
        if (!cli) return;
        var ciudadLibre = libre("ciudad"), copiado = false;
        // La provincia va primero: al cambiarla se rehace la lista de
        // municipios y se vacía una ciudad que no sea de esa provincia.
        var prov = $("#c-provincia");
        if (prov && cli.provincia && ciudadLibre && prov.value !== cli.provincia) {
          prov.value = cli.provincia;
          prov.dispatchEvent(new Event("change"));
          copiado = true;
        }
        ["direccion", "cp", "ciudad"].forEach(function (c) {
          var el = $("#c-" + c);
          if (!el || !(c === "ciudad" ? ciudadLibre : libre(c))) return;
          // Si el cliente nuevo no tiene ese dato, se vacía el que se rellenó
          // con el anterior: mejor un hueco que el código postal de otra ciudad.
          var valor = cli[c] || "";
          if (valor && el.value !== valor) copiado = true;
          el.value = valor;
          puesto[c] = valor;
        });
        if (copiado) avisar("Dirección copiada de la ficha de " + cli.nombre);
      });
    }
    $("#f-guardar").addEventListener("click", function () {
      var datos = {}, falta = null;
      $$("#f-form [data-multi]").forEach(function (caja) {
        var marcados = $$("input:checked", caja).map(function (i) { return i.value; });
        var campo = m.campos.filter(function (c) { return c.c === caja.dataset.multi; })[0];
        if (campo && campo.req && !marcados.length) falta = falta || campo.t;
        datos[caja.dataset.multi] = marcados.join(", ") || null;
      });
      $$("#f-form [data-c]").forEach(function (el) {
        var campo = m.campos.filter(function (c) { return c.c === el.dataset.c; })[0];
        var val = el.value.trim();
        if (campo.req && !val) falta = falta || campo.t;
        if (campo.tipo === "eurofijo") {
          // Vacío = sin importe conocido; no se manda, para no poner a cero
          // una obra antigua que lo tuviera escrito a mano.
          if (el.dataset.valor !== "") datos[el.dataset.c] = Number(el.dataset.valor);
        }
        else if (campo.tipo === "numero") {
          // Vacío = no se envía. La columna aplica su valor por defecto;
          // mandar null rompería el NOT NULL de iva, importe, etc.
          if (val !== "") datos[el.dataset.c] = Number(val);
        }
        else if (campo.tipo === "ref" && campo.sinObra && val === "ninguna") datos[el.dataset.c] = null;
        else if (campo.tipo === "ref") datos[el.dataset.c] = val === "" ? null : Number(val);
        else if (campo.tipo === "select" && campo.ops.length && typeof campo.ops[0] === "object")
          datos[el.dataset.c] = Number(val);
        else if (campo.tipo === "fecha") { if (val !== "") datos[el.dataset.c] = val; }
        else datos[el.dataset.c] = val || null;
      });
      // Los desplegables con buscador guardan el registro elegido, no el texto.
      $$("#f-form [data-busca]").forEach(function (inp) {
        var campo = campos.filter(function (c) { return c.c === inp.dataset.busca; })[0];
        if (!campo) return;
        var op = buscaElegida(campo, inp.value);
        datos[campo.c] = op ? op.id : null;
      });
      // Si el nombre escrito es el de un cliente de la lista, la solicitud
      // queda colgada de su ficha. Si no lo es y es nueva, el servidor le abre
      // una; si no lo es y se está editando, no se toca el enlace que tuviera:
      // cambiarle una tilde al nombre no es motivo para soltarle el cliente.
      if (inpCli) {
        var elegido = clientePorNombre(inpCli.dataset.cliente, inpCli.value);
        if (elegido) datos.cliente_id = elegido.id;
      }
      if (falta) { var e = $("#f-err"); e.textContent = "Falta: " + falta; e.hidden = false; return; }
      if (m.conIva && datos.importe !== undefined) {
        // Con cuatro decimales: la base de 110 € al 10 % es 100, no 99,999999…
        datos.importe = Math.round(datos.importe / (1 + (Number(datos.iva) || 0) / 100) * 10000) / 10000;
      }

      var btn = $("#f-guardar"); btn.disabled = true; btn.textContent = "Guardando…";
      api("/api/admin/" + m.recurso + (editando ? "/" + registro.id : ""),
          { metodo: editando ? "PUT" : "POST", datos: datos })
        .then(function (r) {
          // A partir de aquí ya existe: si falla una imagen, el siguiente
          // Guardar edita en vez de crear otra.
          registro = Object.assign({}, registro || {}, r); editando = true;
          return Promise.resolve(galeria ? galeria.subir() : null)
            .then(function () { return adjuntos ? adjuntos.subir() : null; });
        })
        .then(function () { invalidar(); cerrarModal(); ir(VOLVER || clave); })
        .catch(function (err) {
          var e = $("#f-err");
          var faltan = (galeria && galeria.pendientes()) || (adjuntos && adjuntos.pendientes());
          e.textContent = err.message + (faltan ? ". Falta algo por subir: pulsa Guardar otra vez." : "");
          e.hidden = false;
          btn.disabled = false; btn.textContent = "Guardar";
        });
    });
  });
}

function confirmarBorrado(clave, id) {
  var m = MODULOS[clave];
  modal("Confirmar borrado",
    "<p style='color:var(--muted)'>Se va a borrar este registro de <b>" + esc(m.titulo.toLowerCase()) +
    "</b>. No se puede deshacer.</p>",
    '<button class="btn btn--fant" id="b-no">Cancelar</button>' +
    '<button class="btn btn--peligro" id="b-si">Borrar</button>');
  $("#b-no").addEventListener("click", cerrarModal);
  $("#b-si").addEventListener("click", function () {
    api("/api/admin/" + m.recurso + "/" + id, { metodo: "DELETE" })
      .then(function () { invalidar(); cerrarModal(); ir(VOLVER || clave); })
      .catch(error);
  });
}

/* ── Solicitud → cliente ──────────────────────────────────────────────── */
function pasarACliente(s) {
  modal("Pasar a cliente",
    '<p style="color:var(--muted);line-height:1.55">Se va a dar de alta a <b>' +
      esc(s.nombre) + "</b> como cliente" +
      (s.email ? ' con el correo <b>' + esc(s.email) + "</b>" : "") + ".<br>" +
      "Si ya hay un cliente con ese correo se enlaza con el que existe, " +
      "en vez de duplicarlo.</p>",
    '<button class="btn btn--fant" id="c-no">Cancelar</button>' +
    '<button class="btn btn--amber" id="c-si">Pasar a cliente</button>');
  $("#c-no").addEventListener("click", cerrarModal);
  $("#c-si").addEventListener("click", function () {
    this.disabled = true;
    api("/api/admin/solicitudes/" + s.id + "/convertir", { metodo: "POST" })
      .then(function (r) {
        invalidar();          // la caché de clientes se queda vieja si no
        cerrarModal();
        // El aviso va ANTES de repintar: si ir() falla por lo que sea, el
        // catch se lo tragaba y el usuario no llegaba a ver la confirmación.
        avisar(r.creado
          ? "Cliente creado: " + r.cliente.nombre
          : "Ya existía un cliente con ese correo. Solicitud enlazada con " +
            r.cliente.nombre + ".");
        ir("solicitudes");
      })
      .catch(function (e) { cerrarModal(); error(e); });
  });
}

/* Aviso breve flotante. No usa alert() para no cortar el flujo, y va colgado
   del <body> y no de #vista: la vista se repinta en cuanto responde la API y
   se llevaba por delante el aviso antes de que diese tiempo a leerlo. */
function avisar(texto, tipo) {
  var caja = document.createElement("div");
  caja.className = "toast" + (tipo === "err" ? " toast--err" : "");
  caja.textContent = texto;
  document.body.appendChild(caja);
  setTimeout(function () { caja.classList.add("toast--fuera"); }, 5200);
  setTimeout(function () { caja.remove(); }, 5600);
}

/* ── Cómo llegar ──────────────────────────────────────────────────────── */
/* Abre Google Maps con la ruta en coche desde donde estés hasta la dirección.
   Es el enlace oficial de rutas de Maps: en el móvil abre la app y deja la
   navegación lista para arrancar; en el ordenador abre la web. */
function abrirMaps(f) {
  var ciudad = String(f.ciudad || "").trim();
  var provincia = String(f.provincia || "").trim();
  // En Ourense capital ciudad y provincia coinciden; no se repite.
  if (provincia.toLowerCase() === ciudad.toLowerCase()) provincia = "";
  var destino = [f.direccion, f.cp, ciudad, provincia, "España"]
    .map(function (x) { return String(x || "").trim(); })
    .filter(Boolean).join(", ");
  window.open("https://www.google.com/maps/dir/?api=1&travelmode=driving&destination=" +
              encodeURIComponent(destino), "_blank", "noopener");
}

/* ── Descarga del PDF ─────────────────────────────────────────────────── */
function descargarPdf(tipo, id, numero) {
  bajarPdf("/api/admin/documentos/" + tipo + "/" + id + "/pdf",
           (numero || NOMBRE_DOC[tipo].uno + "-" + id) + ".pdf");
}

// El PDF de una firma que se archivó al editar el presupuesto: lo que el
// cliente firmó aquel día, tal cual.
function descargarPdfFirma(d, firmaId) {
  bajarPdf("/api/admin/documentos/presupuestos/" + d.id + "/firmas/" + firmaId + "/pdf",
           (d.numero || "presupuesto-" + d.id) + "-firmado.pdf");
}

function bajarPdf(ruta, nombre) {
  // No se puede usar api(): eso espera JSON. Y tampoco vale un enlace
  // normal, porque la sesión va en la cabecera Authorization y un <a href>
  // no la manda. Se descarga a mano y se envuelve en un blob.
  fetch(API + ruta, {
    headers: { Authorization: "Bearer " + token }
  }).then(function (res) {
    if (res.status === 401) { salir(true); throw new Error("Sesión caducada"); }
    if (!res.ok) {
      // Una factura sin número o sin NIF se rechaza con 422 y un motivo
      // concreto; se enseña ese motivo en vez de un error genérico.
      return res.json().then(
        function (j) { throw new Error((j && j.detail) || "No se pudo generar el PDF"); },
        function () { throw new Error("No se pudo generar el PDF"); });
    }
    return res.blob();
  }).then(function (blob) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = nombre;
    document.body.appendChild(a);
    a.click();
    a.remove();
    // Se libera con retardo: revocarlo en el mismo tick corta la descarga
    // que acaba de empezar en algunos navegadores.
    setTimeout(function () { URL.revokeObjectURL(url); }, 8000);
  }).catch(function (e) { avisar(e.message, "err"); });
}

function error(err) {
  $("#vista").innerHTML = '<div class="aviso aviso--err">' + esc(err.message || err) + "</div>";
}

/* ── Dashboard ────────────────────────────────────────────────────────── */
// Periodo del panel: "2026" (un año) o "2026-09" (un mes). Por defecto, el
// año en curso. Se conserva mientras dura la sesión en el navegador.
var PERIODO = null;
var MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"];

function periodoDe(fecha, tipo) {
  return tipo === "anio" ? String(fecha.getFullYear())
    : fecha.getFullYear() + "-" + ("0" + (fecha.getMonth() + 1)).slice(-2);
}
function nombrePeriodo(p) {
  if (p.length === 4) return "Año " + p;
  var n = MESES[Number(p.slice(5)) - 1];
  return n.charAt(0).toUpperCase() + n.slice(1) + " " + p.slice(0, 4);
}
// El periodo de al lado: un año o un mes antes (paso -1) o después (+1).
function periodoVecino(p, paso) {
  if (p.length === 4) return String(Number(p) + paso);
  return periodoDe(new Date(Number(p.slice(0, 4)), Number(p.slice(5)) - 1 + paso, 1), "mes");
}

// Pinta los botones de periodo en la barra de la vista y devuelve el elegido.
// Lo comparten el Panel y el informe de orígenes: el año o el mes elegido vale
// para los dos, así que al cambiarlo en uno sigue puesto al ir al otro.
function pintarPeriodo(repintar) {
  var hoy = new Date();
  var periodo = PERIODO || periodoDe(hoy, "anio");
  var actual = periodoDe(hoy, periodo.length === 4 ? "anio" : "mes");
  var anterior = periodoVecino(periodoDe(hoy, "mes"), -1);
  function boton(p, txt) {
    return '<button type="button" data-periodo="' + p + '"' + (p === periodo ? ' class="is-on"' : "") + ">" + txt + "</button>";
  }
  $("#vista-acciones").innerHTML =
    '<div class="periodo">' +
      '<div class="periodo__rapidos">' +
        boton(periodoDe(hoy, "anio"), "Este año") + boton(periodoDe(hoy, "mes"), "Este mes") +
        boton(anterior, "Mes anterior") +
      "</div>" +
      '<div class="periodo__nav">' +
        '<button type="button" data-periodo="' + periodoVecino(periodo, -1) + '" aria-label="Anterior">‹</button>' +
        "<b>" + esc(nombrePeriodo(periodo)) + "</b>" +
        '<button type="button" data-periodo="' + periodoVecino(periodo, 1) + '" aria-label="Siguiente"' +
          (periodo >= actual ? " disabled" : "") + ">›</button>" +
      "</div>" +
    "</div>";
  $$("#vista-acciones [data-periodo]").forEach(function (b) {
    b.addEventListener("click", function () { PERIODO = b.dataset.periodo; repintar(); });
  });
  return periodo;
}

function verDashboard() {
  var periodo = pintarPeriodo(verDashboard);
  var esAnio = periodo.length === 4;

  api("/api/admin/dashboard?periodo=" + periodo).then(function (d) {
    var c = d.contadores, margen = (d.periodo.ingresos || 0) - (d.periodo.gastos || 0);
    var del = esAnio ? "del año" : "del mes";

    var h = '<div class="metricas">' +
      metrica(c.obras_activas, "Obras activas", "") +
      (c.solicitudes_nuevas === null ? ""
        : metrica(c.solicitudes_nuevas, "Solicitudes sin atender", c.solicitudes_nuevas ? "metrica--azul" : "")) +
      // Resultados sin IVA (el IVA es de Hacienda); lo pendiente, con IVA.
      metrica(eur(d.periodo.ingresos), "Ingresos " + del + " · sin IVA", "metrica--verde") +
      metrica(eur(d.periodo.gastos), "Gastos " + del + " · sin IVA", "metrica--rojo") +
      metrica(eur(margen), "Margen " + del + " · sin IVA", margen >= 0 ? "metrica--verde" : "metrica--rojo") +
      (c.stock_bajo === null ? ""
        : metrica(c.stock_bajo, "Artículos bajo mínimo", c.stock_bajo ? "metrica--rojo" : "")) +
      "</div>";

    h += '<div class="paneles--3 paneles">';

    // Evolución
    var ev = d.evolucion || [];
    var altura = function (v) { return v ? Math.max(3, v / tope * 100) : 0; };
    var tope = Math.max.apply(null, ev.map(function (m) { return Math.max(m.ingresos || 0, m.gastos || 0); }).concat([1]));
    h += '<div class="tarjeta"><h3>Ingresos y gastos <span>' +
         (esAnio ? esc(periodo) : "6 meses hasta " + esc(nombrePeriodo(periodo).toLowerCase())) +
         " · sin IVA</span></h3>";
    if (!ev.length) h += '<div class="vacia">Sin movimientos todavía.</div>';
    else {
      h += '<div class="grafico">';
      ev.forEach(function (m) {
        h += '<div class="barra-col"><div class="barra-par">' +
             // Un mes sin movimientos no pinta barra: la rayita mínima hacía
             // creer que había algo.
             '<div class="barra barra--in" style="height:' + altura(m.ingresos) + '%"></div>' +
             '<div class="barra barra--out" style="height:' + altura(m.gastos) + '%"></div>' +
             "</div><small" + (m.mes === periodo ? ' class="is-on"' : "") + ">" +
             esc(String(m.mes).slice(5) + "/" + String(m.mes).slice(2, 4)) + "</small></div>";
      });
      h += '</div><div class="leyenda"><span><i style="background:var(--verde)"></i>Ingresos</span>' +
           '<span><i style="background:var(--rojo)"></i>Gastos</span></div>';
    }
    h += "</div>";

    // Pendientes
    h += '<div class="tarjeta"><h3>Pendiente <span>con IVA</span></h3>' +
         '<div style="display:grid;gap:14px">' +
         '<div><b style="font-family:var(--ff-h);font-size:1.5rem;color:var(--verde)">' + eur(d.pendientes.cobro) + "</b>" +
         '<div style="font-size:.83rem;color:var(--muted)">Por cobrar a clientes</div></div>' +
         '<div><b style="font-family:var(--ff-h);font-size:1.5rem;color:var(--rojo)">' + eur(d.pendientes.pago) + "</b>" +
         '<div style="font-size:.83rem;color:var(--muted)">Por pagar a proveedores</div></div>' +
         "</div></div>";
    h += "</div>";

    // Obras y solicitudes recientes
    h += '<div class="paneles" style="margin-top:16px">';
    h += '<div class="tarjeta"><h3>Últimas obras <span>margen sin IVA</span></h3>' + (d.obras_recientes.length
      ? '<div class="tabla-scroll"><table class="tabla-corta"><tbody>' + d.obras_recientes.map(function (o) {
          var m2 = (o.importe_venta || 0) - (o.costes || 0);
          return "<tr><td><b>" + esc(o.titulo) + "</b><div style='font-size:.8rem;color:var(--muted)'>" +
                 esc(o.cliente || "sin cliente") + (o.ciudad ? " · " + esc(o.ciudad) : "") + "</div></td>" +
                 '<td><span class="tag">' + esc(o.estado) + "</span></td>" +
                 '<td class="num" style="color:' + (m2 >= 0 ? "var(--verde)" : "var(--rojo)") + '">' + eur(m2) + "</td></tr>";
        }).join("") + "</tbody></table></div>"
      : '<div class="vacia">Sin obras todavía.</div>') + "</div>";

    if (puedeVer("solicitudes")) h += '<div class="tarjeta"><h3>Últimas solicitudes</h3>' + (d.solicitudes_recientes.length
      ? '<div class="tabla-scroll"><table class="tabla-corta"><tbody>' + d.solicitudes_recientes.map(function (s) {
          return "<tr><td><b>" + esc(s.nombre) + "</b><div style='font-size:.8rem;color:var(--muted)'>" +
                 esc(s.servicio || "") + "</div></td>" +
                 '<td><span class="tag ' + (s.estado === "pendiente" ? "tag--amber" : "") + '">' + esc(s.estado) + "</span></td>" +
                 '<td class="num" style="font-size:.82rem;color:var(--muted)">' + esc(fecha(s.creado)) + "</td></tr>";
        }).join("") + "</tbody></table></div>"
      : '<div class="vacia">Ninguna todavía.</div>') + "</div>";
    h += "</div>";

    if (d.avisos_stock.length) {
      h += '<div class="tarjeta" style="margin-top:16px"><h3>Material bajo mínimo</h3>' +
        '<div class="tabla-scroll"><table class="tabla-corta"><tbody>' + d.avisos_stock.map(function (a) {
          return "<tr><td>" + esc(a.nombre) + '</td><td class="num"><span class="tag tag--rojo">' +
                 num(a.cantidad) + " " + esc(a.unidad || "") + '</span></td><td class="num" style="color:var(--muted);font-size:.83rem">mín. ' +
                 num(a.minimo) + "</td></tr>";
        }).join("") + "</tbody></table></div></div>";
    }

    $("#vista").innerHTML = h;
  }).catch(error);
}

function metrica(valor, etiqueta, clase) {
  return '<div class="metrica ' + (clase || "") + '"><b>' + esc(valor) + "</b><span>" + esc(etiqueta) + "</span></div>";
}

/* ── Obras: tabla con rentabilidad y asignación ───────────────────────── */
// Verde si el estado cuenta como obra activa; rojo si es una cancelada.
function claseEstadoObra(nombre, estados) {
  var e = (estados || []).filter(function (x) { return x.nombre === nombre; })[0];
  if (e && e.activa) return "tag--verde";
  return /cancel/i.test(nombre || "") ? "tag--rojo" : "tag--amber";
}

function verObras() {
  $("#vista-acciones").innerHTML =
    '<button class="btn btn--amber" id="btn-nuevo">' + svg(ico.mas) + "Nueva obra</button>";
  $("#btn-nuevo").addEventListener("click", function () { abrirFormulario("obras", null); });

  var conNotas = puedeVer("notas");
  Promise.all([api("/api/admin/informes/obras"), cargarRef("clientes"), cargarRef("obras")]
              .concat([esAdmin() ? cargarRef("equipo") : null, conNotas ? api("/api/admin/notas") : [],
                       cargarRef("listas/obra-estados")]))
    .then(function (res) {
      var obras = res[0];
      var nNotas = {};
      res[4].forEach(function (n) { if (n.obra_id) nNotas[n.obra_id] = (nNotas[n.obra_id] || 0) + 1; });
      if (!obras.length) {
        $("#vista").innerHTML = '<div class="tabla-caja"><div class="vacia">Todavía no hay obras. Pulsa «Nueva obra».</div></div>';
        return;
      }
      // Filtro por cliente (se escribe) y por estado. Se conserva al volver
      // de guardar una obra, como el de Gastos.
      var est = FILTRO.obras = FILTRO.obras || { cliente: "", estado: "" };
      $("#vista").innerHTML =
        '<div class="herr">' +
          '<input id="filtro-cliente" list="lista-filtro-cliente" autocomplete="off" class="herr__cliente"' +
          ' placeholder="Cliente: escribe para filtrar…" value="' + esc(est.cliente) + '">' +
          '<datalist id="lista-filtro-cliente">' + (cache.clientes || []).map(function (c) {
            return '<option value="' + esc(c.nombre) + '"></option>';
          }).join("") + "</datalist>" +
          '<select id="filtro-estado" aria-label="Estado"><option value="">Todos los estados</option>' +
          res[5].map(function (e) {
            return '<option value="' + esc(e.nombre) + '"' + (e.nombre === est.estado ? " selected" : "") + ">" +
                   esc(e.nombre) + "</option>";
          }).join("") + "</select>" +
          '<input type="search" id="buscar" placeholder="Buscar obra…">' +
        "</div>" +
        '<div id="obras-resumen"></div>' +
        '<div class="tabla-caja"><div class="tabla-scroll" id="obras-tabla"></div></div>';

      function fila(o) {
        var margen = (o.importe_venta || 0) - (o.costes || 0);
        var pct = o.importe_venta ? Math.round(margen / o.importe_venta * 100) : null;
        return "<tr><td><b>" + esc(o.titulo) + "</b>" +
             (o.codigo ? '<div style="font-size:.78rem;color:var(--muted-2)">' + esc(o.codigo) + "</div>" : "") +
             "</td><td>" + (esc(o.cliente) || "—") + "</td>" +
             (esAdmin() ? "<td>" + (esc(nombreDe("equipo", o.usuario_id)) || "—") + "</td>" : "") +
             '<td><span class="tag ' + claseEstadoObra(o.estado, res[5]) + '">' + esc(o.estado) + "</span></td>" +
             '<td><button class="btn btn--sm ' + (o.n_profesionales ? "btn--fant" : "btn--amber") +
             '" data-equipo="' + o.id + '" title="Asignar profesionales a esta obra">' +
             svg(ico.equipo) + (o.n_profesionales ? o.n_profesionales + " asignados" : "Asignar") + "</button></td>" +
             (conNotas
               ? '<td><button class="btn btn--sm btn--fant" data-notas="' + o.id + '" title="Ver las notas de esta obra">' +
                 svg(ico.nota) + (nNotas[o.id] ? nNotas[o.id] + " nota" + (nNotas[o.id] === 1 ? "" : "s") : "Notas") +
                 "</button></td>"
               : "") +
             '<td class="num">' + eur(o.importe_venta) + '</td><td class="num">' + eur(o.costes) + '</td><td class="num">' + eur(o.facturado) + "</td>" +
             '<td class="num" style="color:' + (margen >= 0 ? "var(--verde)" : "var(--rojo)") + '"><b>' + eur(margen) + "</b>" +
             (pct !== null ? '<div style="font-size:.76rem;color:var(--muted)">' + pct + "%</div>" : "") + "</td>" +
             '<td class="acciones"><button data-editar="' + o.id + '" title="Editar">' + svg(ico.lapiz) + "</button>" +
             '<button class="borrar" data-borrar="' + o.id + '" title="Borrar">' + svg(ico.papelera) + "</button></td></tr>";
      }

      function repintar() {
        var clis = clientesQueEncajan("clientes", est.cliente), q = llano($("#buscar").value);
        var vistas = obras.filter(function (o) {
          if (est.estado && o.estado !== est.estado) return false;
          if (clis && clis.indexOf(String(o.cliente_id)) < 0) return false;
          return !q || llano([o.titulo, o.codigo, o.cliente, o.ciudad, o.estado].join(" ")).indexOf(q) >= 0;
        });

        // Resumen de lo que se ve: presupuestado, gastos y margen.
        var sum = function (c) { return vistas.reduce(function (a, o) { return a + (Number(o[c]) || 0); }, 0); };
        var venta = sum("importe_venta"), gastos = sum("costes"), margen = venta - gastos;
        $("#obras-resumen").innerHTML = '<div class="metricas">' +
          metrica(eur(venta), "Presupuestado sin IVA · " + vistas.length + " obra" + (vistas.length === 1 ? "" : "s"), "metrica--azul") +
          metrica(eur(gastos), "Gastos sin IVA", "metrica--rojo") +
          metrica(eur(margen), "Margen" + (venta ? " · " + Math.round(margen / venta * 100) + " %" : ""),
                  margen >= 0 ? "metrica--verde" : "metrica--rojo") +
          "</div>";

        var caja = $("#obras-tabla");
        if (!vistas.length) {
          caja.innerHTML = '<div class="vacia">Ninguna obra con estos filtros.</div>';
          return;
        }
        caja.innerHTML = "<table><thead><tr>" +
          "<th>Obra</th><th>Cliente</th>" + (esAdmin() ? "<th>Responsable</th>" : "") +
          "<th>Estado</th><th>Profesionales</th>" + (conNotas ? "<th>Notas</th>" : "") +
          '<th class="num">Presupuestado</th><th class="num">Gastos</th><th class="num">Facturado</th>' +
          '<th class="num">Margen</th><th class="num">Acciones</th></tr></thead><tbody>' +
          vistas.map(fila).join("") + "</tbody></table>";

        $$("[data-editar]", caja).forEach(function (b) {
          b.addEventListener("click", function () {
            api("/api/admin/obras").then(function (todas) {
              abrirFormulario("obras", todas.filter(function (x) { return x.id == b.dataset.editar; })[0]);
            });
          });
        });
        $$("[data-borrar]", caja).forEach(function (b) {
          b.addEventListener("click", function () { confirmarBorrado("obras", b.dataset.borrar); });
        });
        $$("[data-equipo]", caja).forEach(function (b) {
          b.addEventListener("click", function () { verEquipo(b.dataset.equipo); });
        });
        $$("[data-notas]", caja).forEach(function (b) {
          b.addEventListener("click", function () { notasDeObra(b.dataset.notas); });
        });
      }
      repintar();
      $("#filtro-cliente").addEventListener("input", function () { est.cliente = this.value; repintar(); });
      $("#filtro-estado").addEventListener("change", function () { est.estado = this.value; repintar(); });
      $("#buscar").addEventListener("input", repintar);
    }).catch(error);
}

function verEquipo(obraId) {
  Promise.all([api("/api/admin/obras/" + obraId + "/profesionales"), cargarRef("profesionales")])
    .then(function (res) {
      var asignados = res[0], todos = res[1];
      var ids = asignados.map(function (a) { return a.profesional_id; });
      var libres = todos.filter(function (p) { return ids.indexOf(p.id) < 0 && p.activo; });

      var cuerpo = '<div class="aviso aviso--err" id="eq-err" hidden></div>';
      cuerpo += asignados.length
        ? '<div class="tabla-caja" style="margin-bottom:18px"><table><tbody>' + asignados.map(function (a) {
            return "<tr><td><b>" + esc(a.nombre) + '</b><div style="font-size:.8rem;color:var(--muted)">' +
                   esc(a.categoria) + (a.rol ? " · " + esc(a.rol) : "") + "</div></td>" +
                   '<td class="num" style="color:var(--muted);font-size:.85rem">' +
                   (a.tarifa_hora ? eur(a.tarifa_hora) + "/h" : "") + "</td>" +
                   '<td class="acciones"><button class="borrar" data-quitar="' + a.profesional_id + '">' + svg(ico.papelera) + "</button></td></tr>";
          }).join("") + "</tbody></table></div>"
        : '<p style="color:var(--muted);margin-bottom:18px">Todavía no hay nadie asignado a esta obra.</p>';

      if (libres.length) {
        cuerpo += '<div class="rejilla-2"><div class="campo"><label for="eq-pro">Añadir profesional</label>' +
          '<select id="eq-pro">' + libres.map(function (p) {
            return '<option value="' + p.id + '"' + (YO && p.id === YO.profesional_id ? " selected" : "") + ">" +
                   esc(p.nombre) + " — " + esc(p.categoria) + "</option>";
          }).join("") + "</select></div>" +
          '<div class="campo"><label for="eq-rol">Rol en la obra</label><input id="eq-rol" placeholder="Opcional"></div></div>';
      } else {
        cuerpo += '<p style="color:var(--muted-2);font-size:.88rem">No quedan profesionales activos por asignar.</p>';
      }

      modal("Profesionales de la obra", cuerpo,
        '<button class="btn btn--fant" id="eq-cerrar">Cerrar</button>' +
        (libres.length ? '<button class="btn btn--amber" id="eq-add">Asignar</button>' : ""));

      $("#eq-cerrar").addEventListener("click", function () { cerrarModal(); ir("obras"); });
      $$("[data-quitar]").forEach(function (b) {
        b.addEventListener("click", function () {
          api("/api/admin/obras/" + obraId + "/profesionales/" + b.dataset.quitar, { metodo: "DELETE" })
            .then(function () { verEquipo(obraId); }).catch(function (e) {
              var el = $("#eq-err"); el.textContent = e.message; el.hidden = false;
            });
        });
      });
      if (libres.length) {
        $("#eq-add").addEventListener("click", function () {
          api("/api/admin/obras/" + obraId + "/profesionales", {
            metodo: "POST",
            datos: { profesional_id: Number($("#eq-pro").value), rol: $("#eq-rol").value.trim() || null }
          }).then(function () { verEquipo(obraId); }).catch(function (e) {
            var el = $("#eq-err"); el.textContent = e.message; el.hidden = false;
          });
        });
      }
    }).catch(error);
}

/* ── Almacén: tabla con entradas y salidas ───────────────────────────── */
function verStock() {
  $("#vista-acciones").innerHTML =
    '<button class="btn btn--amber" id="btn-nuevo">' + svg(ico.mas) + "Nuevo artículo</button>";
  $("#btn-nuevo").addEventListener("click", function () { abrirFormulario("stock", null); });

  Promise.all([api("/api/admin/stock"), cargarRef("proveedores"), cargarRef("obras")])
    .then(function (res) {
      var arts = res[0];
      if (!arts.length) {
        $("#vista").innerHTML = '<div class="tabla-caja"><div class="vacia">El almacén está vacío. Pulsa «Nuevo artículo».</div></div>';
        return;
      }
      var h = '<div class="tabla-caja"><div class="tabla-scroll"><table><thead><tr>' +
        '<th>Artículo</th><th>Ref.</th><th>Categoría</th><th class="num">Existencias</th>' +
        '<th class="num">Mínimo</th><th class="num">Precio ud.</th><th class="num">Valor</th>' +
        '<th class="num">Acciones</th></tr></thead><tbody>';
      arts.forEach(function (a) {
        var bajo = a.minimo > 0 && a.cantidad <= a.minimo;
        h += "<tr><td><b>" + esc(a.nombre) + "</b>" +
             (a.ubicacion ? '<div style="font-size:.78rem;color:var(--muted-2)">' + esc(a.ubicacion) + "</div>" : "") +
             "</td><td>" + (esc(a.referencia) || "—") + "</td><td>" + (esc(a.categoria) || "—") + "</td>" +
             '<td class="num"><span class="tag ' + (bajo ? "tag--rojo" : "tag--verde") + '">' +
             num(a.cantidad) + " " + esc(a.unidad || "") + "</span></td>" +
             '<td class="num" style="color:var(--muted)">' + num(a.minimo) + "</td>" +
             '<td class="num">' + eur(a.precio_unitario) + '</td>' +
             '<td class="num">' + eur((a.cantidad || 0) * (a.precio_unitario || 0)) + "</td>" +
             '<td class="acciones">' +
             '<button data-mover="' + a.id + '" title="Entrada / salida">' + svg(ico.flechas) + "</button>" +
             '<button data-editar="' + a.id + '" title="Editar">' + svg(ico.lapiz) + "</button>" +
             '<button class="borrar" data-borrar="' + a.id + '" title="Borrar">' + svg(ico.papelera) + "</button></td></tr>";
      });
      var total = arts.reduce(function (s, a) { return s + (a.cantidad || 0) * (a.precio_unitario || 0); }, 0);
      $("#vista").innerHTML = h + "</tbody></table></div>" +
        '<div style="padding:14px 16px;border-top:1px solid var(--line);text-align:right;font-size:.9rem">' +
        'Valor total del almacén: <b>' + eur(total) + "</b></div></div>";

      $$("[data-editar]").forEach(function (b) {
        b.addEventListener("click", function () {
          abrirFormulario("stock", arts.filter(function (x) { return x.id == b.dataset.editar; })[0]);
        });
      });
      $$("[data-borrar]").forEach(function (b) {
        b.addEventListener("click", function () { confirmarBorrado("stock", b.dataset.borrar); });
      });
      $$("[data-mover]").forEach(function (b) {
        b.addEventListener("click", function () {
          moverStock(arts.filter(function (x) { return x.id == b.dataset.mover; })[0]);
        });
      });
    }).catch(error);
}

function moverStock(art) {
  var obras = cache.obras || [];
  modal("Movimiento de almacén: " + art.nombre,
    '<div class="aviso aviso--err" id="mv-err" hidden></div>' +
    '<p style="color:var(--muted);margin-bottom:16px">Existencias actuales: <b>' +
      num(art.cantidad) + " " + esc(art.unidad || "") + "</b></p>" +
    '<div class="rejilla-2">' +
      '<div class="campo"><label for="mv-tipo">Tipo</label><select id="mv-tipo">' +
        '<option value="entrada">Entrada</option><option value="salida">Salida</option></select></div>' +
      '<div class="campo"><label for="mv-cant">Cantidad</label><input id="mv-cant" type="number" step="any" min="0"></div>' +
    "</div>" +
    '<div class="campo"><label for="mv-obra">Obra (si es salida a obra)</label><select id="mv-obra">' +
      '<option value="">— sin obra —</option>' +
      obras.map(function (o) { return '<option value="' + o.id + '">' + esc(o.titulo) + "</option>"; }).join("") +
    "</select><small style='color:var(--muted-2);font-size:.79rem'>Una salida a obra genera automáticamente su gasto de material.</small></div>" +
    '<div class="campo"><label for="mv-nota">Nota</label><input id="mv-nota" placeholder="Opcional"></div>',
    '<button class="btn btn--fant" id="mv-cancelar">Cancelar</button>' +
    '<button class="btn btn--amber" id="mv-ok">Registrar</button>');

  $("#mv-cancelar").addEventListener("click", cerrarModal);
  $("#mv-ok").addEventListener("click", function () {
    var cant = Number($("#mv-cant").value);
    if (!cant || cant <= 0) {
      var e = $("#mv-err"); e.textContent = "Indica una cantidad mayor que cero."; e.hidden = false; return;
    }
    api("/api/admin/stock/" + art.id + "/movimientos", {
      metodo: "POST",
      datos: {
        tipo: $("#mv-tipo").value, cantidad: cant,
        obra_id: $("#mv-obra").value ? Number($("#mv-obra").value) : null,
        nota: $("#mv-nota").value.trim() || null
      }
    }).then(function () { invalidar(); cerrarModal(); ir("stock"); })
      .catch(function (err) { var e = $("#mv-err"); e.textContent = err.message; e.hidden = false; });
  });
}

/* ── Listas editables: Gastos > Categorías / Estados, Obras > Estados ──── */
// Todas se gestionan igual: nombre, cuántos registros la usan, editar y
// borrar. Algunas llevan además una marca por elemento: si el gasto cuenta
// como pagado (lo que suma contabilidad en lo pendiente) o si la obra cuenta
// como activa (el contador del panel).
var LISTAS_EDIT = {
  "gasto-categorias": { una: "categoría", nueva: "Nueva categoría", ruta: "listas/gasto-categorias",
    cosas: "gastos", ayuda: "Si cambias el nombre de una categoría, cambia también en todos los gastos que la llevan." },
  "gasto-estados": { una: "estado", nueva: "Nuevo estado", ruta: "listas/gasto-estados", cosas: "gastos",
    marca: { c: "pagado", si: "Pagado", no: "Pendiente de pago", pregunta: "Un gasto en este estado cuenta como" },
    ayuda: "El estado marcado como «Pagado» cuenta como pagado en contabilidad; el resto, como pendiente de pago. " +
           "Los gastos nuevos empiezan en el primer estado pendiente de la lista." },
  "cliente-origenes": { una: "origen", nueva: "Nuevo origen", ruta: "listas/cliente-origenes",
    cosas: "usos",
    ayuda: "Son las opciones del desplegable «¿Cómo nos conociste?» de la web y de la ficha del cliente. " +
           "Si cambias un nombre, cambia en los clientes y solicitudes que lo llevan." },
  "obra-estados": { una: "estado", nueva: "Nuevo estado", ruta: "listas/obra-estados", cosas: "obras",
    marca: { c: "activa", si: "Obra activa", no: "No activa", pregunta: "Una obra en este estado cuenta como" },
    ayuda: "Las obras en un estado marcado como activo cuentan en «Obras activas» del panel. " +
           "Las obras nuevas empiezan en el primer estado de la lista." }
};

function verListaEditable(clave) {
  var L = LISTAS_EDIT[MODULOS[clave].lista];
  $("#vista-acciones").innerHTML =
    '<button class="btn btn--amber" id="btn-nuevo">' + svg(ico.mas) + esc(L.nueva) + "</button>";
  $("#btn-nuevo").addEventListener("click", function () { formListaEditable(clave, null); });

  api("/api/admin/" + L.ruta).then(function (filas) {
    cache[L.ruta] = filas;
    var h = '<div class="tabla-caja"><div class="tabla-scroll"><table><thead><tr><th>Nombre</th>' +
      (L.marca ? "<th>Cuenta como</th>" : "") +
      '<th class="num">' + esc(L.cosas.charAt(0).toUpperCase() + L.cosas.slice(1)) + '</th><th class="num">Acciones</th></tr></thead><tbody>';
    filas.forEach(function (f) {
      var si = L.marca && f[L.marca.c];
      h += "<tr><td><b>" + esc(f.nombre) + "</b></td>" +
        (L.marca ? '<td><span class="tag ' + (si ? "tag--verde" : "tag--amber") + '">' +
                   esc(si ? L.marca.si : L.marca.no) + "</span></td>" : "") +
        '<td class="num">' + f.n + "</td>" +
        '<td class="acciones"><button data-editar="' + f.id + '" title="Editar">' + svg(ico.lapiz) + "</button>" +
        '<button class="borrar" data-borrar="' + f.id + '" title="Borrar">' + svg(ico.papelera) + "</button></td></tr>";
    });
    $("#vista").innerHTML = h + "</tbody></table></div></div>" +
      '<p style="color:var(--muted-2);font-size:.84rem;line-height:1.55;margin-top:14px">' + esc(L.ayuda) + "</p>";
    function fila(id) { return filas.filter(function (x) { return String(x.id) === String(id); })[0]; }
    $$("[data-editar]").forEach(function (b) {
      b.addEventListener("click", function () { formListaEditable(clave, fila(b.dataset.editar)); });
    });
    $$("[data-borrar]").forEach(function (b) {
      b.addEventListener("click", function () { borrarDeLista(clave, fila(b.dataset.borrar), filas); });
    });
  }).catch(error);
}

function formListaEditable(clave, f) {
  var L = LISTAS_EDIT[MODULOS[clave].lista];
  var si = f && L.marca && f[L.marca.c];
  modal(f ? "Editar " + L.una : L.nueva,
    '<div class="aviso aviso--err" id="lg-err" hidden></div>' +
    '<div class="campo"><label for="lg-nombre">Nombre *</label><input id="lg-nombre" maxlength="60" value="' +
      esc(f ? f.nombre : "") + '"></div>' +
    (L.marca
      ? '<div class="campo"><label for="lg-marca">' + esc(L.marca.pregunta) + '</label><select id="lg-marca">' +
        '<option value="0"' + (si ? "" : " selected") + ">" + esc(L.marca.no) + "</option>" +
        '<option value="1"' + (si ? " selected" : "") + ">" + esc(L.marca.si) + "</option></select></div>"
      : "") +
    (f && f.n ? '<p style="color:var(--muted-2);font-size:.85rem">Lo llevan ' + f.n + " " + L.cosas +
                ": cambian con él.</p>" : ""),
    '<button class="btn btn--fant" id="lg-no">Cancelar</button><button class="btn btn--amber" id="lg-si">Guardar</button>');
  $("#lg-nombre").focus();
  $("#lg-no").addEventListener("click", cerrarModal);
  $("#lg-si").addEventListener("click", function () {
    var btn = this, datos = { nombre: $("#lg-nombre").value.trim() };
    if (L.marca) datos.marca = $("#lg-marca").value === "1";
    if (!datos.nombre) { var e = $("#lg-err"); e.textContent = "Pon un nombre."; e.hidden = false; return; }
    btn.disabled = true;
    api("/api/admin/" + L.ruta + (f ? "/" + f.id : ""), { metodo: f ? "PUT" : "POST", datos: datos })
      .then(function () { invalidar(); cerrarModal(); ir(clave); })
      .catch(function (err) {
        var e = $("#lg-err"); e.textContent = err.message; e.hidden = false; btn.disabled = false;
      });
  });
}

// Borrar uno que está en uso pide a cuál se pasan sus registros: ninguno se
// puede quedar con una categoría o un estado que ya no existe.
function borrarDeLista(clave, f, filas) {
  var L = LISTAS_EDIT[MODULOS[clave].lista];
  var otras = filas.filter(function (x) { return x.id !== f.id; });
  if (!otras.length) { avisar("No se puede borrar: tiene que quedar al menos uno", "err"); return; }
  modal("Borrar " + L.una,
    '<div class="aviso aviso--err" id="lg-err" hidden></div>' +
    (f.n
      ? '<p style="color:var(--muted);line-height:1.55">Hay <b>' + f.n + "</b> " + L.cosas + " con «" + esc(f.nombre) +
        "». Antes de borrar, di a dónde se pasan.</p>" +
        '<div class="campo"><label for="lg-mover">Pasarlos a</label><select id="lg-mover">' +
        otras.map(function (o) { return '<option value="' + esc(o.nombre) + '">' + esc(o.nombre) + "</option>"; }).join("") +
        "</select></div>"
      : "<p style='color:var(--muted)'>Se va a borrar «" + esc(f.nombre) + "». No lo usa nadie.</p>"),
    '<button class="btn btn--fant" id="lg-no">Cancelar</button><button class="btn btn--peligro" id="lg-si">Borrar</button>');
  $("#lg-no").addEventListener("click", cerrarModal);
  $("#lg-si").addEventListener("click", function () {
    var destino = $("#lg-mover") ? $("#lg-mover").value : "";
    api("/api/admin/" + L.ruta + "/" + f.id + (destino ? "?mover_a=" + encodeURIComponent(destino) : ""),
        { metodo: "DELETE" })
      .then(function (r) {
        invalidar(); cerrarModal();
        avisar(r.movidos ? r.movidos + " " + L.cosas + " pasados a «" + destino + "»" : "Borrado");
        ir(clave);
      })
      .catch(function (err) { var e = $("#lg-err"); e.textContent = err.message; e.hidden = false; });
  });
}

/* ── Reseñas de Google ────────────────────────────────────────────────── */
// El enlace para dejar reseña lo da el propio Perfil de Empresa. Se guarda una
// vez y se lee al entrar, para que al pulsar el botón se pueda abrir WhatsApp
// en el mismo clic: si se pidiera al servidor primero, el navegador bloquearía
// la ventana.
//
// La reseña NO se pide sola en ningún momento: solo cuando se pulsa el botón.
var RESENAS_URL = "";

function cargarEnlaceResenas() {
  if (!puedeVer("clientes")) return Promise.resolve("");
  return api("/api/admin/ajustes/resenas_url")
    .then(function (r) { RESENAS_URL = r.valor || ""; return RESENAS_URL; })
    .catch(function () { return ""; });
}

function textoResena(cliente) {
  var nombre = String(cliente.nombre || "").trim().split(" ")[0];
  return "Hola" + (nombre ? " " + nombre : "") + ", somos Loureiro Soluciones. " +
    "Si has quedado contento con el trabajo, ¿nos dejas una reseña en Google? " +
    "Es un minuto y nos ayuda mucho a que otros vecinos nos encuentren:\n" + RESENAS_URL;
}

// Guarda el enlace de reseñas. Solo el administrador.
function configurarResenas(despues) {
  if (!esAdmin()) {
    return avisar("Falta el enlace de reseñas. Que lo configure el administrador.", "err");
  }
  modal("Enlace para dejar reseña",
    '<div class="aviso aviso--err" id="re-err" hidden></div>' +
    '<p style="color:var(--muted);line-height:1.55">En tu Perfil de Empresa de Google, ' +
    'en «Pedir reseñas», Google te da un enlace corto. Pégalo aquí y se usará en todos ' +
    'los mensajes.</p>' +
    '<div class="campo"><label for="re-url">Enlace</label>' +
    '<input id="re-url" placeholder="https://g.page/r/..." value="' + esc(RESENAS_URL) + '"></div>',
    '<button class="btn btn--fant" id="re-no">Cancelar</button>' +
    '<button class="btn btn--amber" id="re-si">Guardar</button>');
  $("#re-no").addEventListener("click", cerrarModal);
  $("#re-si").addEventListener("click", function () {
    var btn = this;
    btn.disabled = true;
    api("/api/admin/ajustes/resenas_url", { metodo: "PUT", datos: { valor: $("#re-url").value.trim() } })
      .then(function (r) {
        RESENAS_URL = r.valor;
        cerrarModal();
        avisar("Enlace guardado");
        if (despues) despues();
      })
      .catch(function (e) { btn.disabled = false; var el = $("#re-err"); el.textContent = e.message; el.hidden = false; });
  });
}

// Abre WhatsApp con el mensaje escrito y apunta la fecha en la ficha.
function pedirResena(cliente, alTerminar) {
  var tel = telefonoWhatsApp(cliente.telefono);
  if (!tel) return avisar("Ese cliente no tiene un teléfono válido para WhatsApp", "err");
  if (!RESENAS_URL) return configurarResenas(function () { pedirResena(cliente, alTerminar); });

  var ventana = window.open("https://wa.me/" + tel + "?text=" + encodeURIComponent(textoResena(cliente)),
                            "_blank");
  if (!ventana) avisar("El navegador no ha dejado abrir WhatsApp", "err");
  api("/api/admin/clientes/" + cliente.id,
      { metodo: "PUT", datos: { resena_pedida: new Date().toISOString().slice(0, 10) } })
    .then(function () {
      invalidar();
      avisar("Apuntado: reseña pedida a " + cliente.nombre);
      if (alTerminar) alTerminar();
    })
    .catch(function (e) { avisar(e.message, "err"); });
}

/* ── Ficha de cliente ─────────────────────────────────────────────────── */
// Todo lo de un cliente en una página: datos, mapa, obras, presupuestos,
// facturas con lo cobrado y lo pendiente, visitas y notas. Lo que se abre
// desde aquí (editar, nueva nota, una factura…) vuelve aquí al guardar.
var FICHA_ID = null;
try { FICHA_ID = Number(sessionStorage.getItem("loureiro_ficha")) || null; } catch (e) {}

function abrirFicha(id) {
  FICHA_ID = Number(id);
  try { sessionStorage.setItem("loureiro_ficha", String(FICHA_ID)); } catch (e) {}
  ir("ficha_cliente");
}

// Lo que se abre desde la ficha vuelve a ella al guardar o borrar.
function desdeFicha(fn) {
  return function () { VOLVER = "ficha_cliente"; fn.apply(null, arguments); };
}

function direccionCompleta(c) {
  return [c.direccion, [c.cp, c.ciudad].filter(Boolean).join(" "), c.provincia]
    .map(function (x) { return String(x || "").trim(); }).filter(Boolean).join(", ");
}

function verFichaCliente() {
  if (!FICHA_ID) return ir("clientes");
  Promise.all([api("/api/admin/clientes/" + FICHA_ID + "/ficha"), cargarRef("clientes"), cargarRef("obras"),
               puedeVer("obras") ? cargarRef("listas/obra-estados") : null, esAdmin() ? cargarRef("equipo") : null])
    .then(function (res) {
      var d = res[0], c = d.cliente;
      $("#vista-titulo").textContent = c.nombre;
      $("#vista-sub").textContent = ["Ficha de cliente", c.nif, c.ciudad].filter(Boolean).join(" · ");

      // Acciones de arriba.
      var acc = '<button class="btn btn--fant" id="fc-volver">← Clientes</button>' +
        '<button class="btn btn--fant" id="fc-editar">' + svg(ico.lapiz) + "Editar</button>";
      if (telefonoWhatsApp(c.telefono)) {
        acc += '<button class="btn btn--fant" id="fc-resena" title="Abre WhatsApp con el mensaje escrito">' +
               svg(ico.estrella) + (c.resena_pedida ? "Pedir reseña otra vez" : "Pedir reseña") + "</button>";
      }
      if (d.notas) acc += '<button class="btn btn--fant" id="fc-nota">' + svg(ico.nota) + "Nota</button>";
      if (d.visitas && puedeVer("visitas")) acc += '<button class="btn btn--fant" id="fc-visita">' + svg(ico.camara) + "Visita</button>";
      if (d.presupuestos) acc += '<button class="btn btn--amber" id="fc-presu">' + svg(ico.doc) + "Presupuesto</button>";
      $("#vista-acciones").innerHTML = '<div class="fc-acciones">' + acc + "</div>";

      var h = "";
      // Números.
      var obras = d.obras || [], presus = d.presupuestos || [];
      var presupuestado = presus.filter(function (p) { return p.estado !== "cancelado"; })
        .reduce(function (a, p) { return a + (p.total || 0); }, 0);
      h += '<div class="metricas">';
      if (d.obras) h += metrica(String(obras.length), obras.length === 1 ? "Obra" : "Obras", "");
      if (d.presupuestos) h += metrica(eur(presupuestado), "Presupuestado (" + presus.length + ")", "metrica--azul");
      if (d.cuentas) {
        h += metrica(eur(d.cuentas.facturado), "Facturado", "") +
             metrica(eur(d.cuentas.cobrado), "Pagado", "metrica--verde") +
             metrica(eur(d.cuentas.pendiente), "Debe", d.cuentas.pendiente > 0 ? "metrica--rojo" : "metrica--verde");
      }
      h += "</div>";

      // Datos y mapa.
      var dir = direccionCompleta(c);
      h += '<div class="paneles fc-datos"><div class="tarjeta"><h3>Datos</h3><dl class="fc-dl">' +
        dato("Teléfono", c.telefono ? '<a href="tel:' + esc(c.telefono.replace(/\s/g, "")) + '">' + esc(c.telefono) + "</a>" +
             (telefonoWhatsApp(c.telefono) ? ' · <a href="https://wa.me/' + telefonoWhatsApp(c.telefono) +
               '" target="_blank" rel="noopener">WhatsApp</a>' : "") : "") +
        dato("Email", c.email ? '<a href="mailto:' + esc(c.email) + '">' + esc(c.email) + "</a>" : "") +
        dato("NIF", esc(c.nif)) +
        dato("Dirección", esc(dir)) +
        dato("Cliente desde", esc(fecha(c.creado))) +
        dato("Nos conoció por", esc(c.origen)) +
        dato("Reseña pedida", esc(fecha(c.resena_pedida))) +
        (esAdmin() ? dato("Responsable", esc(nombreDe("equipo", c.usuario_id))) : "") +
        "</dl>" + (c.notas ? '<div class="fc-notas-ficha">' + textoRico(c.notas) + "</div>" : "") + "</div>" +
        '<div class="tarjeta fc-mapa"><h3>Localización' +
          (c.direccion ? '<button class="btn btn--fant btn--sm" id="fc-ruta">' + svg(ico.mapa) + "Cómo llegar</button>" : "") +
        "</h3>" +
        (dir
          ? '<iframe title="Mapa" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="https://maps.google.com/maps?q=' +
            encodeURIComponent(dir + ", España") + '&z=15&output=embed"></iframe>'
          : '<div class="vacia">Sin dirección en la ficha.</div>') +
        "</div></div>";

      // Obras.
      if (d.obras) {
        h += seccion("Obras", obras.length, obras.map(function (o) {
          var margen = (o.importe_venta || 0) - (o.costes || 0);
          return '<tr data-obra="' + o.id + '"><td><b>' + esc(o.titulo) + "</b>" +
            (o.codigo ? '<div class="fc-sub">' + esc(o.codigo) + "</div>" : "") + "</td>" +
            '<td><span class="tag ' + claseEstadoObra(o.estado, cache["listas/obra-estados"]) + '">' + esc(o.estado) + "</span></td>" +
            '<td class="num">' + eur(o.importe_venta) + '</td><td class="num">' + eur(o.costes) + "</td>" +
            '<td class="num" style="color:' + (margen >= 0 ? "var(--verde)" : "var(--rojo)") + '"><b>' + eur(margen) + "</b></td></tr>";
        }), "<th>Obra</th><th>Estado</th><th class='num'>Presupuestado</th><th class='num'>Gastos</th><th class='num'>Margen</th>");
      }
      // Presupuestos y facturas.
      [["presupuestos", "Presupuestos"], ["facturas", "Facturas"]].forEach(function (t) {
        if (!d[t[0]]) return;
        h += seccion(t[1], d[t[0]].length, d[t[0]].map(function (x) {
          return '<tr data-doc="' + t[0] + ":" + x.id + '"><td><b>' + (esc(x.numero) || "#" + x.id) + "</b></td>" +
            "<td>" + esc(fecha(x.fecha)) + "</td><td>" + (esc(x.obra) || "—") + "</td>" +
            '<td><span class="tag ' + claseEstadoDoc(x.estado) + '">' + esc(x.estado) + "</span></td>" +
            '<td class="num"><b>' + eur(x.total) + "</b></td></tr>";
        }), "<th>Número</th><th>Fecha</th><th>Obra</th><th>Estado</th><th class='num'>Total</th>");
      });
      // Visitas.
      if (d.visitas) {
        h += '<div class="tarjeta fc-bloque"><h3>Visitas <span>' + d.visitas.length + "</span></h3>" +
          (d.visitas.length ? '<div class="vis-lista">' + d.visitas.map(function (v) {
            return '<button type="button" class="vis-item" data-visita="' + v.id + '">' +
              '<span class="vis-item__foto">' +
                (v.portada ? '<img alt="" data-foto="visitas/' + v.id + "/" + v.portada + '/m">' : svg(ico.camara)) +
                (v.n_fotos > 1 ? "<em>" + v.n_fotos + "</em>" : "") + "</span>" +
              '<span class="vis-item__txt"><b>' + esc(v.titulo || "Visita") + "</b><small>" + esc(fecha(v.fecha)) +
              (v.n_fotos ? " · " + v.n_fotos + " foto" + (v.n_fotos === 1 ? "" : "s") : "") + "</small></span></button>";
          }).join("") + "</div>" : '<div class="vacia">Sin visitas.</div>') + "</div>";
      }
      // Notas.
      if (d.notas) {
        h += '<div class="tarjeta fc-bloque"><h3>Notas <span>' + d.notas.length + "</span></h3>" +
          (d.notas.length ? '<div class="notas">' + d.notas.map(function (n) {
            return '<button type="button" class="nota" data-nota="' + n.id + '"><span class="nota__cab">' +
              (n.obra ? '<span class="tag tag--azul">' + esc(n.obra) + "</span>" : '<span class="tag">Del cliente</span>') +
              "<small>" + esc(fecha(n.actualizado || n.creado)) + "</small></span>" +
              (n.titulo ? "<b>" + esc(n.titulo) + "</b>" : "") +
              '<span class="nota__txt">' + textoRico(n.contenido) + "</span>" + miniaturasNota(n) + archivosNota(n) + "</button>";
          }).join("") + "</div>" : '<div class="vacia">Sin notas. Pulsa «Nota» arriba para añadir una.</div>') + "</div>";
      }
      $("#vista").innerHTML = h;
      pintarFotos($("#vista"));

      // Manejadores.
      $("#fc-volver").addEventListener("click", function () { ir("clientes"); });
      $("#fc-editar").addEventListener("click", desdeFicha(function () { abrirFormulario("clientes", c); }));
      if ($("#fc-nota")) $("#fc-nota").addEventListener("click", desdeFicha(function () {
        abrirFormulario("notas", null, { cliente_id: c.id });
      }));
      if ($("#fc-visita")) $("#fc-visita").addEventListener("click", desdeFicha(function () {
        abrirVisita(null, { cliente_id: c.id });
      }));
      if ($("#fc-presu")) $("#fc-presu").addEventListener("click", desdeFicha(function () {
        editarDocumento("presupuestos", null, { cliente_id: c.id });
      }));
      if ($("#fc-ruta")) $("#fc-ruta").addEventListener("click", function () { abrirMaps(c); });
      if ($("#fc-resena")) $("#fc-resena").addEventListener("click", function () {
        pedirResena(c, function () { ir("ficha_cliente"); });
      });
      $$("[data-obra]").forEach(function (tr) {
        tr.addEventListener("click", desdeFicha(function () {
          api("/api/admin/obras").then(function (todas) {
            abrirFormulario("obras", todas.filter(function (x) { return String(x.id) === tr.dataset.obra; })[0]);
          });
        }));
      });
      $$("[data-doc]").forEach(function (tr) {
        tr.addEventListener("click", desdeFicha(function () {
          var p = tr.dataset.doc.split(":");
          if (puedeVer(p[0])) editarDocumento(p[0], p[1]);
        }));
      });
      $$("[data-visita]").forEach(function (b) {
        b.addEventListener("click", desdeFicha(function () { abrirVisita(Number(b.dataset.visita)); }));
      });
      $$("[data-nota]").forEach(function (b) {
        b.addEventListener("click", desdeFicha(function () {
          abrirFormulario("notas", d.notas.filter(function (n) { return String(n.id) === b.dataset.nota; })[0]);
        }));
      });
    }).catch(function (e) {
      // Un cliente que ya no existe (o de otra persona): de vuelta a la lista.
      FICHA_ID = null;
      avisar(e.message, "err");
      ir("clientes");
    });

  function dato(t, v) { return v ? "<dt>" + esc(t) + "</dt><dd>" + v + "</dd>" : ""; }
  function seccion(titulo, n, filas, cab) {
    return '<div class="tarjeta fc-bloque"><h3>' + esc(titulo) + " <span>" + n + "</span></h3>" +
      (filas.length
        ? '<div class="tabla-scroll"><table class="fc-tabla"><thead><tr>' + cab + "</tr></thead><tbody>" +
          filas.join("") + "</tbody></table></div>"
        : '<div class="vacia">Nada todavía.</div>') + "</div>";
  }
}

/* ── Notas ────────────────────────────────────────────────────────────── */
// Obra por la que se está filtrando: "" todas, "sin" las que no son de
// ninguna, o el id de una obra. Se conserva al guardar una nota, y el botón
// «Notas» de la lista de obras entra ya con la suya puesta.
var NOTAS_OBRA = "";

function notasDeObra(obraId) {
  NOTAS_OBRA = String(obraId);
  ir("notas");
}

function verNotas() {
  $("#vista-acciones").innerHTML =
    '<button class="btn btn--amber" id="btn-nuevo">' + svg(ico.mas) + "Nueva nota</button>";
  $("#btn-nuevo").addEventListener("click", function () {
    // Con una obra elegida en el filtro, la nota nueva ya va a esa obra.
    var obra = NOTAS_OBRA && NOTAS_OBRA !== "sin" ? Number(NOTAS_OBRA) : null;
    abrirFormulario("notas", null, obra ? { obra_id: obra } : null);
  });

  Promise.all([api("/api/admin/notas"), cargarRef("obras"), cargarRef("clientes")].concat(esAdmin() ? [cargarRef("equipo")] : []))
    .then(function (res) {
      var notas = res[0];
      // En el filtro solo salen las obras que tienen notas, más la elegida.
      var conNotas = {};
      notas.forEach(function (n) { if (n.obra_id) conNotas[n.obra_id] = (conNotas[n.obra_id] || 0) + 1; });
      var obras = (cache.obras || []).filter(function (o) {
        return conNotas[o.id] || String(o.id) === NOTAS_OBRA;
      });
      var sinObra = notas.filter(function (n) { return !n.obra_id; }).length;
      if (NOTAS_OBRA && NOTAS_OBRA !== "sin" && !obras.length) NOTAS_OBRA = "";

      $("#vista").innerHTML =
        '<div class="herr">' +
          '<select id="notas-obra" aria-label="Obra">' +
            '<option value="">Todas las notas (' + notas.length + ")</option>" +
            '<option value="sin"' + (NOTAS_OBRA === "sin" ? " selected" : "") + ">Sin obra (" + sinObra + ")</option>" +
            obras.map(function (o) {
              return '<option value="' + o.id + '"' + (String(o.id) === NOTAS_OBRA ? " selected" : "") + ">" +
                     esc(o.titulo) + " (" + (conNotas[o.id] || 0) + ")</option>";
            }).join("") +
          "</select>" +
          '<input type="search" id="buscar" placeholder="Buscar en las notas…">' +
        "</div>" +
        '<div class="notas" id="notas-lista"></div>';

      function pintar() {
        var q = llano($("#buscar").value);
        var filas = notas.filter(function (n) {
          if (NOTAS_OBRA === "sin" && n.obra_id) return false;
          if (NOTAS_OBRA && NOTAS_OBRA !== "sin" && String(n.obra_id) !== NOTAS_OBRA) return false;
          return !q || [n.titulo, n.contenido, nombreDe("obras", n.obra_id)].some(function (x) {
            return llano(x).indexOf(q) >= 0;
          });
        });
        var caja = $("#notas-lista");
        if (!filas.length) {
          caja.innerHTML = '<div class="tabla-caja"><div class="vacia">' +
            (notas.length ? "No hay notas con este filtro." : "Todavía no hay notas. Pulsa «Nueva nota».") +
            "</div></div>";
          return;
        }
        caja.innerHTML = filas.map(function (n) {
          return '<button type="button" class="nota" data-nota="' + n.id + '">' +
            '<span class="nota__cab">' +
              (n.obra_id ? '<span class="tag tag--azul">' + esc(nombreDe("obras", n.obra_id)) + "</span>"
                         : n.cliente_id ? '<span class="tag">' + esc(nombreDe("clientes", n.cliente_id)) + "</span>"
                         : '<span class="tag">Sin obra</span>') +
              "<small>" + esc(fecha(n.actualizado || n.creado)) +
              (esAdmin() && n.usuario_id ? " · " + esc(nombreDe("equipo", n.usuario_id)) : "") + "</small>" +
            "</span>" +
            (n.titulo ? "<b>" + esc(n.titulo) + "</b>" : "") +
            '<span class="nota__txt">' + textoRico(n.contenido) + "</span>" +
            miniaturasNota(n) + archivosNota(n) + "</button>";
        }).join("");
        pintarFotos(caja);
        $$("[data-nota]", caja).forEach(function (b) {
          b.addEventListener("click", function () {
            abrirFormulario("notas", notas.filter(function (x) { return String(x.id) === b.dataset.nota; })[0]);
          });
        });
      }
      pintar();
      $("#notas-obra").addEventListener("change", function () { NOTAS_OBRA = this.value; pintar(); });
      $("#buscar").addEventListener("input", pintar);
    }).catch(error);
}

/* ── Visitas: notas y fotos de la toma de datos ───────────────────────── */
// Las fotos piden sesión, así que no valen como src de un <img>: se bajan con
// el token y se enseñan desde un blob. Se guardan las URL ya hechas para no
// bajar dos veces la misma miniatura al repintar la lista.
var FOTOS = {};
// `padre` es de quién es la foto: "visitas/5" o "notas/3".
function urlFoto(padre, foto, mini) {
  var clave = padre + "/" + foto + (mini ? "/m" : "");
  if (FOTOS[clave]) return FOTOS[clave];
  FOTOS[clave] = fetch(API + "/api/admin/" + padre + "/fotos/" + foto + (mini ? "?mini=1" : ""),
                       { headers: { Authorization: "Bearer " + token } })
    .then(function (r) {
      if (!r.ok) throw new Error("No se ha podido cargar la foto");
      return r.blob();
    })
    .then(function (b) { return URL.createObjectURL(b); })
    .catch(function (e) { delete FOTOS[clave]; throw e; });
  return FOTOS[clave];
}
// Rellena los <img data-foto="visitas/5/12[/m]"> que haya dentro de `caja`.
function pintarFotos(caja) {
  $$("img[data-foto]", caja).forEach(function (img) {
    var p = img.dataset.foto.split("/"), mini = p[p.length - 1] === "m";
    if (mini) p.pop();
    var foto = p.pop();
    urlFoto(p.join("/"), foto, mini).then(function (u) { img.src = u; })
      .catch(function () { img.alt = "No se ha podido cargar"; img.classList.add("is-rota"); });
  });
}

// La foto del móvil pesa varios megas y no hace falta: se reduce aquí, antes
// de subirla. 1600 px de lado dan para ver una grieta o leer una etiqueta, y
// cada foto queda por debajo del mega que deja pasar Nginx por petición.
var FOTO_LADO = 1600, FOTO_MAX = 850000, MINI_LADO = 360;
function lienzo(img, lado) {
  var w = img.width, h = img.height, k = Math.min(1, lado / Math.max(w, h));
  var c = document.createElement("canvas");
  c.width = Math.round(w * k); c.height = Math.round(h * k);
  c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
  return c;
}
function cargarImagen(file) {
  // createImageBitmap endereza la foto según su EXIF. Si el navegador no lo
  // tiene, un <img>, que los navegadores de hoy también enderezan al pintar.
  if (window.createImageBitmap) {
    return createImageBitmap(file, { imageOrientation: "from-image" }).catch(function () {
      return cargarConImg(file);
    });
  }
  return cargarConImg(file);
}
function cargarConImg(file) {
  return new Promise(function (ok, ko) {
    var u = URL.createObjectURL(file), img = new Image();
    img.onload = function () { URL.revokeObjectURL(u); ok(img); };
    img.onerror = function () {
      URL.revokeObjectURL(u);
      ko(new Error("«" + file.name + "» no es una imagen que se pueda abrir"));
    };
    img.src = u;
  });
}
function reducirFoto(file) {
  return cargarImagen(file).then(function (img) {
    var lado = FOTO_LADO, calidad = 0.82, datos;
    // Si aun así pesa demasiado (fotos con mucho detalle), se baja la calidad y
    // luego el tamaño hasta que quepa.
    for (var i = 0; i < 8; i++) {
      datos = lienzo(img, lado).toDataURL("image/jpeg", calidad);
      if (datos.length <= FOTO_MAX) break;
      if (calidad > 0.6) calidad -= 0.1; else lado = Math.round(lado * 0.8);
    }
    return { imagen: datos, miniatura: lienzo(img, MINI_LADO).toDataURL("image/jpeg", 0.7) };
  });
}

// Visor a pantalla completa. Escape lo cierra a él y no a la ficha de debajo.
function verFotoGrande(padre, foto) {
  var capa = document.createElement("div");
  capa.className = "visor";
  capa.innerHTML = '<button class="visor__x" aria-label="Cerrar">&times;</button>' +
                   '<div class="vacia">Cargando…</div>';
  document.body.appendChild(capa);
  function cerrar() { capa.remove(); window.removeEventListener("keydown", tecla, true); }
  function tecla(e) { if (e.key === "Escape") { e.stopPropagation(); cerrar(); } }
  window.addEventListener("keydown", tecla, true);
  capa.addEventListener("click", cerrar);
  urlFoto(padre, foto, false).then(function (u) {
    capa.innerHTML = '<button class="visor__x" aria-label="Cerrar">&times;</button><img alt="" src="' + u + '">';
  }).catch(function (e) { cerrar(); avisar(e.message, "err"); });
}

function miniaturasNota(n) {
  var fotos = n.fotos || [];
  if (!fotos.length) return "";
  return '<span class="nota__fotos">' + fotos.slice(0, 3).map(function (f) {
    return '<img alt="" data-foto="notas/' + n.id + "/" + f + '/m">';
  }).join("") + (fotos.length > 3 ? "<em>+" + (fotos.length - 3) + "</em>" : "") + "</span>";
}
function archivosNota(n) {
  var a = n.archivos || [];
  if (!a.length) return "";
  return '<span class="nota__archivos">' + svg(ico.clip) +
    esc(a.length === 1 ? a[0].nombre : a.length + " archivos") + "</span>";
}

// Galería de un formulario: las fotos que ya tiene y las nuevas, que se
// preparan (reducidas) al elegirlas y se suben al guardar, cuando ya se sabe
// el id de lo que se está guardando. Las que ya estaban se borran al momento.
function galeriaFotos(o) {
  var existentes = (o.existentes || []).slice(), nuevas = [];
  function pintar() {
    var caja = $(o.caja);
    if (!caja) return;
    caja.innerHTML = existentes.map(function (f) {
      return '<div class="foto"><button type="button" class="foto__ver" data-ver="' + f + '" title="Ver en grande">' +
        '<img alt="" data-foto="' + o.padre() + "/" + f + '/m"></button>' +
        '<button type="button" class="foto__x" data-quitar="' + f + '" title="Borrar la imagen">&times;</button></div>';
    }).join("") + nuevas.map(function (f, i) {
      return '<div class="foto foto--nueva"><img alt="" src="' + f.miniatura + '">' +
        '<span class="foto__marca">Sin subir</span>' +
        '<button type="button" class="foto__x" data-descartar="' + i + '" title="Quitar">&times;</button></div>';
    }).join("") || '<div class="fotos__vacia">Sin imágenes.</div>';
    pintarFotos(caja);
    $$("[data-ver]", caja).forEach(function (b) {
      b.addEventListener("click", function () { verFotoGrande(o.padre(), b.dataset.ver); });
    });
    $$("[data-descartar]", caja).forEach(function (b) {
      b.addEventListener("click", function () { nuevas.splice(Number(b.dataset.descartar), 1); pintar(); });
    });
    $$("[data-quitar]", caja).forEach(function (b) {
      b.addEventListener("click", function () {
        if (!confirm("¿Borrar esta imagen? No se puede deshacer.")) return;
        b.disabled = true;
        api("/api/admin/" + o.padre() + "/fotos/" + b.dataset.quitar, { metodo: "DELETE" })
          .then(function () {
            existentes = existentes.filter(function (f) { return String(f) !== b.dataset.quitar; });
            pintar();
          })
          .catch(function (e) { b.disabled = false; avisar(e.message, "err"); });
      });
    });
  }
  function elegidas(input) {
    var files = Array.prototype.slice.call(input.files || []);
    input.value = "";
    if (!files.length) return;
    var btn = $(o.guardar);
    btn.disabled = true; btn.textContent = "Preparando imágenes…";
    files.reduce(function (cadena, file) {
      return cadena.then(function () {
        return reducirFoto(file).then(function (f) { nuevas.push(f); pintar(); })
          .catch(function (e) { avisar(e.message, "err"); });
      });
    }, Promise.resolve()).then(function () { btn.disabled = false; btn.textContent = "Guardar"; });
  }
  $$(o.entradas).forEach(function (inp) { inp.addEventListener("change", function () { elegidas(this); }); });
  pintar();
  return {
    pendientes: function () { return nuevas.length; },
    // Sube las nuevas de una en una; si una falla, las que quedan siguen ahí
    // para volver a intentarlo.
    subir: function () {
      var btn = $(o.guardar), total = nuevas.length, n = 0;
      return nuevas.slice().reduce(function (cadena, f) {
        return cadena.then(function () {
          n++;
          if (btn) btn.textContent = "Subiendo imagen " + n + " de " + total + "…";
          return api("/api/admin/" + o.padre() + "/fotos", { metodo: "POST", datos: f })
            .then(function (r) { nuevas.splice(nuevas.indexOf(f), 1); existentes.push(r.id); });
        });
      }, Promise.resolve());
    }
  };
}

// Archivos adjuntos (PDF, Word, Excel…). Van por trozos porque el servidor no
// deja pasar más de un mega por petición: se abre la subida, se manda cada
// trozo y se cierra, y el servidor comprueba que ha llegado entero.
var EXT_ARCHIVO = ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "txt", "csv"];
var MAX_ARCHIVO = 20 * 1024 * 1024;

function tamanoLegible(b) {
  return b < 1024 * 1024 ? Math.max(1, Math.round(b / 1024)) + " KB" : (b / 1024 / 1024).toFixed(1).replace(".", ",") + " MB";
}
function trozoBase64(blob) {
  return new Promise(function (ok, ko) {
    var r = new FileReader();
    r.onload = function () { ok(String(r.result).split(",")[1] || ""); };
    r.onerror = function () { ko(new Error("No se ha podido leer el archivo")); };
    r.readAsDataURL(blob);
  });
}
// Se baja con la sesión (un enlace normal no la lleva) y se guarda con su nombre.
function descargarAdjunto(ruta, nombre) {
  fetch(API + "/api/admin/" + ruta, { headers: { Authorization: "Bearer " + token } })
    .then(function (r) { if (!r.ok) throw new Error("No se ha podido descargar"); return r.blob(); })
    .then(function (b) {
      var u = URL.createObjectURL(b), a = document.createElement("a");
      a.href = u; a.download = nombre; document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(u); }, 4000);
    })
    .catch(function (e) { avisar(e.message, "err"); });
}

function listaArchivos(o) {
  var existentes = (o.existentes || []).slice(), nuevos = [];
  function pintar() {
    var caja = $(o.caja);
    if (!caja) return;
    caja.innerHTML = existentes.map(function (a) {
      return '<div class="adjunto"><button type="button" class="adjunto__nombre" data-bajar="' + a.id + '" title="Descargar">' +
        svg(ico.clip) + "<span>" + esc(a.nombre) + "</span><small>" + tamanoLegible(a.tamano) + "</small></button>" +
        '<button type="button" class="adjunto__x" data-quitar="' + a.id + '" title="Borrar el archivo">&times;</button></div>';
    }).join("") + nuevos.map(function (f, i) {
      return '<div class="adjunto adjunto--nuevo"><span class="adjunto__nombre">' + svg(ico.clip) +
        "<span>" + esc(f.name) + "</span><small>" + tamanoLegible(f.size) + " · sin subir</small></span>" +
        '<button type="button" class="adjunto__x" data-descartar="' + i + '" title="Quitar">&times;</button></div>';
    }).join("");
    $$("[data-bajar]", caja).forEach(function (b) {
      b.addEventListener("click", function () {
        var a = existentes.filter(function (x) { return String(x.id) === b.dataset.bajar; })[0];
        descargarAdjunto(o.padre() + "/archivos/" + a.id, a.nombre);
      });
    });
    $$("[data-descartar]", caja).forEach(function (b) {
      b.addEventListener("click", function () { nuevos.splice(Number(b.dataset.descartar), 1); pintar(); });
    });
    $$("[data-quitar]", caja).forEach(function (b) {
      b.addEventListener("click", function () {
        if (!confirm("¿Borrar este archivo? No se puede deshacer.")) return;
        b.disabled = true;
        api("/api/admin/" + o.padre() + "/archivos/" + b.dataset.quitar, { metodo: "DELETE" })
          .then(function () {
            existentes = existentes.filter(function (a) { return String(a.id) !== b.dataset.quitar; });
            pintar();
          })
          .catch(function (e) { b.disabled = false; avisar(e.message, "err"); });
      });
    });
  }
  $$(o.entradas).forEach(function (inp) {
    inp.addEventListener("change", function () {
      Array.prototype.slice.call(inp.files || []).forEach(function (f) {
        var ext = String(f.name.split(".").pop()).toLowerCase();
        if (EXT_ARCHIVO.indexOf(ext) < 0) return avisar("«" + f.name + "»: solo PDF, Word, Excel, PowerPoint, OpenDocument, TXT o CSV", "err");
        if (f.size > MAX_ARCHIVO) return avisar("«" + f.name + "» pasa de 20 MB", "err");
        if (!f.size) return avisar("«" + f.name + "» está vacío", "err");
        nuevos.push(f);
      });
      inp.value = "";
      pintar();
    });
  });
  pintar();

  function subirUno(f) {
    var btn = $(o.guardar), base = "/api/admin/" + o.padre() + "/archivos";
    return api(base, { metodo: "POST", datos: { nombre: f.name, tamano: f.size } }).then(function (a) {
      var trozos = Math.ceil(f.size / a.trozo), i = 0;
      function siguiente() {
        if (i >= trozos) return api(base + "/" + a.id + "/fin", { metodo: "POST" });
        if (btn) btn.textContent = "Subiendo «" + f.name + "» " + Math.round(i / trozos * 100) + " %…";
        return trozoBase64(f.slice(i * a.trozo, (i + 1) * a.trozo)).then(function (b64) {
          return api(base + "/" + a.id + "/trozos/" + i, { metodo: "PUT", datos: { datos: b64 } });
        }).then(function () { i++; return siguiente(); });
      }
      return siguiente();
    });
  }
  return {
    pendientes: function () { return nuevos.length; },
    subir: function () {
      return nuevos.slice().reduce(function (cadena, f) {
        return cadena.then(function () {
          return subirUno(f).then(function (r) { nuevos.splice(nuevos.indexOf(f), 1); existentes.push(r); });
        });
      }, Promise.resolve());
    }
  };
}

function tituloVisita(v) { return v.titulo || "Visita"; }
function etiquetaVisita(v) {
  return fecha(v.fecha) + " · " + tituloVisita(v) + (v.cliente ? " · " + v.cliente : "") +
         (v.n_fotos ? " · " + v.n_fotos + " foto" + (v.n_fotos === 1 ? "" : "s") : "");
}
function chipsPresupuestos(lista) {
  return (lista || []).map(function (p) {
    var clase = p.estado === "cancelado" ? "tag--rojo"
              : (p.estado === "aceptado" || p.estado === "firmado") ? "tag--verde" : "tag--amber";
    return '<span class="tag ' + clase + '">' + esc(p.numero || "#" + p.id) + "</span>";
  }).join(" ");
}

function verVisitas() {
  $("#vista-acciones").innerHTML =
    '<button class="btn btn--amber" id="btn-nuevo">' + svg(ico.mas) + "Nueva visita</button>";
  $("#btn-nuevo").addEventListener("click", function () { abrirVisita(null); });

  Promise.all([api("/api/admin/visitas"), cargarRef("clientes")]).then(function (res) {
    var visitas = res[0];
    if (!visitas.length) {
      $("#vista").innerHTML = '<div class="tabla-caja"><div class="vacia">Todavía no hay visitas. ' +
        "Pulsa «Nueva visita» cuando vayas a casa de un cliente a tomar datos.</div></div>";
      return;
    }
    $("#vista").innerHTML =
      '<div class="herr"><input type="search" id="buscar" placeholder="Buscar por cliente, dirección o notas…"></div>' +
      '<div class="vis-lista" id="vis-lista"></div>';
    function pintar(filas) {
      var caja = $("#vis-lista");
      if (!filas.length) { caja.innerHTML = '<div class="vacia">Nada coincide con la búsqueda.</div>'; return; }
      caja.innerHTML = filas.map(function (v) {
        return '<button type="button" class="vis-item" data-visita="' + v.id + '">' +
          '<span class="vis-item__foto">' +
            (v.portada ? '<img alt="" data-foto="visitas/' + v.id + "/" + v.portada + '/m">' : svg(ico.camara)) +
            (v.n_fotos > 1 ? "<em>" + v.n_fotos + "</em>" : "") + "</span>" +
          '<span class="vis-item__txt"><b>' + esc(tituloVisita(v)) + "</b>" +
            "<small>" + esc(fecha(v.fecha)) + " · " + esc(v.cliente || "sin cliente") + "</small>" +
            (v.direccion ? "<small>" + esc(v.direccion) + "</small>" : "") +
            (v.presupuestos.length
              ? '<span class="vis-item__presu">' + chipsPresupuestos(v.presupuestos) + "</span>"
              : '<small class="vis-item__sin">Sin presupuesto todavía</small>') +
          "</span></button>";
      }).join("");
      $$("[data-visita]", caja).forEach(function (b) {
        b.addEventListener("click", function () { abrirVisita(Number(b.dataset.visita)); });
      });
      pintarFotos(caja);
    }
    pintar(visitas);
    $("#buscar").addEventListener("input", function () {
      var q = llano(this.value);
      pintar(!q ? visitas : visitas.filter(function (v) {
        return [v.titulo, v.cliente, v.direccion, v.notas, fecha(v.fecha)]
          .concat(v.presupuestos.map(function (p) { return p.numero; }))
          .some(function (x) { return llano(x).indexOf(q) >= 0; });
      }));
    });
  }).catch(error);
}

// Ficha de la visita: datos, notas y fotos en una sola ventana, que es como se
// usa en la obra con el móvil en la mano. Las fotos nuevas se preparan al
// elegirlas y se suben al guardar; si se corta la cobertura a medias, la
// ventana sigue abierta con las que faltan y basta con volver a Guardar.
function abrirVisita(id, inicial) {
  var puedeEditar = puedeVer("visitas");
  Promise.all([
    id ? api("/api/admin/visitas/" + id) : Promise.resolve(null),
    cargarRef("clientes")
  ].concat(esAdmin() ? [cargarRef("equipo")] : [])).then(function (res) {
    var v = res[0] || Object.assign({
      fecha: new Date().toISOString().slice(0, 10), fotos: [], presupuestos: [],
      usuario_id: YO && YO.id      // lo que se crea es de quien lo crea
    }, inicial || {});
    var nuevas = [];               // fotos elegidas, ya reducidas, sin subir

    var cuerpo = '<div class="aviso aviso--err" id="v-err" hidden></div>' +
      '<div class="rejilla-2">' +
        '<div class="campo"><label for="v-cliente">Cliente *</label><select id="v-cliente">' +
          '<option value="">— elige el cliente —</option>' +
          (cache.clientes || []).map(function (o) {
            return '<option value="' + o.id + '"' + (String(o.id) === String(v.cliente_id) ? " selected" : "") + ">" +
                   esc(o.nombre) + "</option>";
          }).join("") + "</select></div>" +
        '<div class="campo"><label for="v-fecha">Fecha</label><input id="v-fecha" type="date" value="' +
          esc(v.fecha) + '"></div>' +
      "</div>" +
      '<div class="campo"><label for="v-titulo">Qué quiere hacer</label><input id="v-titulo" value="' +
        esc(v.titulo) + '" placeholder="Por ejemplo: reforma del baño y cambio de ventanas"></div>' +
      '<div class="campo"><label for="v-dir">Dirección</label><input id="v-dir" value="' + esc(v.direccion) +
        '" placeholder="Se copia de la ficha del cliente"></div>' +
      '<div class="campo"><label for="v-notas">Notas</label><textarea id="v-notas" class="v-notas" ' +
        'placeholder="Medidas, estado, materiales, lo que ha pedido el cliente…">' + esc(v.notas) + "</textarea></div>" +
      (esAdmin()
        ? '<div class="campo"><label for="v-resp">Responsable</label><select id="v-resp">' +
          '<option value="">— nadie: solo el administrador —</option>' +
          (cache.equipo || []).map(function (o) {
            return '<option value="' + o.id + '"' + (String(o.id) === String(v.usuario_id || (YO && YO.id)) ? " selected" : "") + ">" +
                   esc(o.nombre || o.email) + "</option>";
          }).join("") + "</select>" +
          '<small style="color:var(--muted-2);font-size:.79rem">Solo lo ven esa persona y el administrador.</small></div>'
        : "") +
      '<div class="vis-cab"><span class="vis-cab__t">Fotos</span>' +
        (puedeEditar
          ? '<span class="vis-cab__btns"><label class="btn btn--amber btn--sm">' + svg(ico.camara) + "Hacer foto" +
              '<input type="file" accept="image/*" capture="environment" id="v-camara" hidden></label>' +
            '<label class="btn btn--fant btn--sm">' + svg(ico.mas) + "De la galería" +
              '<input type="file" accept="image/*" multiple id="v-galeria" hidden></label></span>'
          : "") +
      "</div>" +
      '<div class="fotos" id="v-fotos"></div>' +
      (id
        ? '<div class="vis-cab" style="margin-top:20px"><span class="vis-cab__t">Presupuestos de esta visita</span>' +
          (puedeVer("presupuestos")
            ? '<button type="button" class="btn btn--fant btn--sm" id="v-presu">' + svg(ico.doc) + "Hacer presupuesto</button>"
            : "") + "</div>" +
          '<div style="font-size:.88rem;color:var(--muted)">' +
          (v.presupuestos.length ? chipsPresupuestos(v.presupuestos) : "Todavía ninguno.") + "</div>"
        : "");

    modal(id ? tituloVisita(v) : "Nueva visita", cuerpo,
      (id && puedeEditar ? '<button class="btn btn--peligro" id="v-borrar" style="margin-right:auto">Borrar</button>' : "") +
      '<button class="btn btn--fant" id="v-cancelar">' + (puedeEditar ? "Cancelar" : "Cerrar") + "</button>" +
      (puedeEditar ? '<button class="btn btn--amber" id="v-guardar">Guardar</button>' : ""), true);

    function pintarGaleria() {
      var h = (v.fotos || []).map(function (f) {
        return '<div class="foto"><button type="button" class="foto__ver" data-ver="' + f.id + '" title="Ver en grande">' +
          '<img alt="" data-foto="visitas/' + id + "/" + f.id + '/m"></button>' +
          (puedeEditar ? '<button type="button" class="foto__x" data-quitar="' + f.id + '" title="Borrar la foto">&times;</button>' : "") +
          "</div>";
      }).join("") + nuevas.map(function (f, i) {
        return '<div class="foto foto--nueva"><img alt="" src="' + f.miniatura + '">' +
          '<span class="foto__marca">Sin subir</span>' +
          '<button type="button" class="foto__x" data-descartar="' + i + '" title="Quitar">&times;</button></div>';
      }).join("");
      $("#v-fotos").innerHTML = h || '<div class="fotos__vacia">' +
        (puedeEditar ? "Sin fotos. Hazlas desde aquí mismo con el móvil." : "Sin fotos.") + "</div>";
      pintarFotos($("#v-fotos"));
      $$("[data-ver]", $("#v-fotos")).forEach(function (b) {
        b.addEventListener("click", function () { verFotoGrande("visitas/" + id, b.dataset.ver); });
      });
      $$("[data-descartar]", $("#v-fotos")).forEach(function (b) {
        b.addEventListener("click", function () { nuevas.splice(Number(b.dataset.descartar), 1); pintarGaleria(); });
      });
      $$("[data-quitar]", $("#v-fotos")).forEach(function (b) {
        b.addEventListener("click", function () {
          if (!confirm("¿Borrar esta foto? No se puede deshacer.")) return;
          b.disabled = true;
          api("/api/admin/visitas/" + id + "/fotos/" + b.dataset.quitar, { metodo: "DELETE" })
            .then(function () {
              v.fotos = v.fotos.filter(function (f) { return String(f.id) !== b.dataset.quitar; });
              pintarGaleria();
            })
            .catch(function (e) { b.disabled = false; avisar(e.message, "err"); });
        });
      });
    }
    pintarGaleria();

    function elegidas(input) {
      var files = Array.prototype.slice.call(input.files || []);
      input.value = "";           // para poder volver a elegir la misma
      if (!files.length) return;
      var btn = $("#v-guardar");
      btn.disabled = true; btn.textContent = "Preparando fotos…";
      // De una en una: reducir diez fotos de 12 megapíxeles a la vez puede
      // dejar sin memoria a un móvil modesto.
      files.reduce(function (cadena, file) {
        return cadena.then(function () {
          return reducirFoto(file).then(function (f) { nuevas.push(f); pintarGaleria(); })
            .catch(function (e) { avisar(e.message, "err"); });
        });
      }, Promise.resolve()).then(function () {
        btn.disabled = false; btn.textContent = "Guardar";
      });
    }
    if ($("#v-camara")) $("#v-camara").addEventListener("change", function () { elegidas(this); });
    if ($("#v-galeria")) $("#v-galeria").addEventListener("change", function () { elegidas(this); });

    // La dirección sale de la ficha del cliente, salvo que ya se haya escrito
    // otra a mano (una segunda vivienda, un local).
    var dirPuesta = "";
    $("#v-cliente").addEventListener("change", function () {
      var sel = this.value;
      var c = (cache.clientes || []).filter(function (x) { return String(x.id) === sel; })[0];
      var dir = $("#v-dir");
      if (dir.value.trim() && dir.value !== dirPuesta) return;
      dir.value = dirPuesta = c
        ? [c.direccion, [c.cp, c.ciudad].filter(Boolean).join(" ")].filter(Boolean).join(", ")
        : "";
    });
    if (!id && v.cliente_id && !v.direccion) $("#v-cliente").dispatchEvent(new Event("change"));

    function hayPendientes(que) {
      return !nuevas.length || confirm("Hay " + nuevas.length + " foto" + (nuevas.length === 1 ? "" : "s") +
                                       " sin subir. " + que);
    }
    if ($("#v-presu")) $("#v-presu").addEventListener("click", function () {
      if (!hayPendientes("Si sigues se pierden. ¿Seguir?")) return;
      editarDocumento("presupuestos", null, { cliente_id: v.cliente_id, visita_id: id });
    });
    $("#v-cancelar").addEventListener("click", function () {
      if (hayPendientes("¿Cerrar sin subirlas?")) cerrarModal();
    });
    if ($("#v-borrar")) $("#v-borrar").addEventListener("click", function () {
      var n = (v.fotos || []).length;
      if (!confirm("Se borra la visita con sus notas" + (n ? " y sus " + n + " fotos" : "") +
                   ". Los presupuestos que salieron de ella se quedan. ¿Borrar?")) return;
      api("/api/admin/visitas/" + id, { metodo: "DELETE" })
        .then(function () { invalidar(); cerrarModal(); avisar("Visita borrada"); ir(VOLVER || "visitas"); })
        .catch(function (e) { avisar(e.message, "err"); });
    });

    if ($("#v-guardar")) $("#v-guardar").addEventListener("click", function () {
      var err = $("#v-err"), btn = this;
      err.hidden = true;
      var datos = {
        cliente_id: $("#v-cliente").value ? Number($("#v-cliente").value) : null,
        fecha: $("#v-fecha").value || null,
        titulo: $("#v-titulo").value.trim() || null,
        direccion: $("#v-dir").value.trim() || null,
        notas: $("#v-notas").value.trim() || null
      };
      if (!datos.cliente_id) { err.textContent = "Elige el cliente de la visita."; err.hidden = false; return; }
      if (esAdmin()) datos.usuario_id = $("#v-resp").value ? Number($("#v-resp").value) : null;
      btn.disabled = true; btn.textContent = "Guardando…";

      api("/api/admin/visitas" + (id ? "/" + id : ""), { metodo: id ? "PUT" : "POST", datos: datos })
        .then(function (r) {
          id = r.id;            // si falla una foto, el siguiente Guardar ya edita
          var total = nuevas.length, n = 0;
          return nuevas.slice().reduce(function (cadena, f) {
            return cadena.then(function () {
              n++;
              btn.textContent = "Subiendo foto " + n + " de " + total + "…";
              return api("/api/admin/visitas/" + id + "/fotos", { metodo: "POST", datos: f })
                .then(function () { nuevas.splice(nuevas.indexOf(f), 1); });
            });
          }, Promise.resolve());
        })
        .then(function () {
          invalidar(); cerrarModal(); avisar("Visita guardada"); ir(VOLVER || "visitas");
        })
        .catch(function (e) {
          err.textContent = e.message + (nuevas.length
            ? ". Faltan " + nuevas.length + " foto" + (nuevas.length === 1 ? "" : "s") +
              " por subir: pulsa Guardar otra vez cuando tengas cobertura."
            : "");
          err.hidden = false;
          btn.disabled = false; btn.textContent = "Guardar";
          pintarGaleria();
        });
    });
  }).catch(error);
}

/* ── Presupuestos y facturas ──────────────────────────────────────────── */
var ESTADOS_DOC = {
  presupuestos: ["borrador", "enviado", "firmado", "aceptado", "cancelado"],
  facturas: ["emitida", "cobrada", "anulada"],
  proformas: ["borrador", "enviada", "aceptada", "facturada", "anulada"]
};

var NOMBRE_DOC = {
  presupuestos: { uno: "presupuesto", nuevo: "Nuevo presupuesto" },
  proformas:    { uno: "proforma",    nuevo: "Nueva proforma" },
  facturas:     { uno: "factura",     nuevo: "Nueva factura" }
};

function claseEstadoDoc(e) {
  return ["aceptado", "aceptada", "cobrada", "facturada", "firmado"].indexOf(e) >= 0 ? "tag--verde"
       : (e === "cancelado" || e === "anulada") ? "tag--rojo" : "tag--amber";
}

function verDocumentos(clave) {
  var m = MODULOS[clave], tipo = m.tipo;
  $("#vista-acciones").innerHTML =
    '<button class="btn btn--amber" id="btn-nuevo">' + svg(ico.mas) +
    NOMBRE_DOC[tipo].nuevo + "</button>";
  if (tipo === "presupuestos" && esAdmin()) {
    $("#vista-acciones").innerHTML =
      '<button class="btn btn--fant" id="btn-condiciones">' + svg(ico.doc) + "Condiciones</button>" +
      $("#vista-acciones").innerHTML;
    $("#btn-condiciones").addEventListener("click", editarCondiciones);
  }
  $("#btn-nuevo").addEventListener("click", function () { editarDocumento(tipo, null); });

  Promise.all([api("/api/admin/documentos/" + tipo), cargarRef("clientes"), cargarRef("obras")]
              .concat(esAdmin() ? [cargarRef("equipo")] : []))
    .then(function (res) {
      var docs = res[0];
      if (!docs.length) {
        $("#vista").innerHTML = '<div class="tabla-caja"><div class="vacia">Todavía no hay ' +
          esc(m.titulo.toLowerCase()) + ". Pulsa el botón de arriba para crear el primero.</div></div>";
        return;
      }
      // Filtros (cliente, obra de ese cliente, estado y búsqueda) y resumen por
      // estado de lo que queda, como en Gastos. Se conservan al volver.
      var est = FILTRO[clave] = FILTRO[clave] || { cliente: "", obra: "", estado: "" };
      $("#vista").innerHTML =
        '<div class="herr">' +
          '<input id="filtro-cliente" list="lista-filtro-cliente" autocomplete="off" class="herr__cliente"' +
          ' placeholder="Cliente: escribe para filtrar…" value="' + esc(est.cliente) + '">' +
          '<datalist id="lista-filtro-cliente">' + (cache.clientes || []).map(function (c) {
            return '<option value="' + esc(c.nombre) + '"></option>';
          }).join("") + "</datalist>" +
          '<select id="filtro-obra" aria-label="Obra"></select>' +
          '<select id="filtro-estado" aria-label="Estado"><option value="">Todos los estados</option>' +
          ESTADOS_DOC[tipo].map(function (e) {
            return '<option value="' + esc(e) + '"' + (e === est.estado ? " selected" : "") + ">" + esc(e) + "</option>";
          }).join("") + "</select>" +
          '<input type="search" id="buscar" placeholder="Buscar…">' +
        "</div>" +
        '<div id="tabla-resumen"></div>' +
        '<div class="tabla-caja"><div class="tabla-scroll" id="docs-tabla"></div>' +
        '<div class="tabla-suma" id="tabla-suma"></div></div>';

      function pintarObras() {
        var clis = clientesQueEncajan("clientes", est.cliente);
        var obras = (cache.obras || []).filter(function (o) {
          return !clis || clis.indexOf(String(o.cliente_id)) >= 0;
        });
        if (est.obra && est.obra !== "sin" && !obras.some(function (o) { return String(o.id) === est.obra; })) est.obra = "";
        $("#filtro-obra").innerHTML =
          '<option value="">' + (clis ? "Todas sus obras (" + obras.length + ")" : "Todas las obras") + "</option>" +
          '<option value="sin"' + (est.obra === "sin" ? " selected" : "") + ">Sin obra</option>" +
          obras.map(function (o) {
            return '<option value="' + o.id + '"' + (String(o.id) === est.obra ? " selected" : "") + ">" + esc(o.titulo) + "</option>";
          }).join("");
      }

      function repintar() {
        var clis = clientesQueEncajan("clientes", est.cliente), q = llano($("#buscar").value);
        var vistas = docs.filter(function (d) {
          if (clis && clis.indexOf(String(d.cliente_id)) < 0) return false;
          if (est.obra === "sin" && d.obra_id) return false;
          if (est.obra && est.obra !== "sin" && String(d.obra_id) !== est.obra) return false;
          if (est.estado && d.estado !== est.estado) return false;
          return !q || llano([d.numero, d.cliente, d.obra, d.notas, d.estado, fecha(d.fecha)].join(" ")).indexOf(q) >= 0;
        });

        var por = {}, total = 0, base = 0;
        vistas.forEach(function (d) {
          por[d.estado] = por[d.estado] || { n: 0, t: 0 };
          por[d.estado].n++; por[d.estado].t += d.total || 0;
          total += d.total || 0; base += d.base || 0;
        });
        var cuantos = function (n) { return n + " " + (n === 1 ? NOMBRE_DOC[tipo].uno : m.titulo.toLowerCase()); };
        $("#tabla-resumen").innerHTML = '<div class="metricas">' +
          ESTADOS_DOC[tipo].map(function (e) {
            var x = por[e] || { n: 0, t: 0 };
            return metrica(eur(x.t), e + " · " + cuantos(x.n), claseEstadoDoc(e).replace("tag--", "metrica--").replace("metrica--amber", ""));
          }).join("") +
          metrica(eur(total), "Total · " + cuantos(vistas.length), "metrica--azul") + "</div>";
        $("#tabla-suma").innerHTML = "Total de lo que se ve: <b>" + eur(total) + "</b>" +
          ' <span style="color:var(--muted)">· base ' + eur(base) + " · IVA " + eur(total - base) + "</span>";

        if (!vistas.length) {
          $("#docs-tabla").innerHTML = '<div class="vacia">Nada con estos filtros.</div>';
          return;
        }
        var h = "<table><thead><tr>" +
          "<th>Número</th><th>Cliente</th><th>Obra</th>" + (esAdmin() ? "<th>Responsable</th>" : "") +
          "<th>Fecha</th><th>Estado</th>" +
          '<th class="num">Base</th><th class="num">IVA</th><th class="num">Total</th>' +
          '<th class="num">Acciones</th></tr></thead><tbody>';
        vistas.forEach(function (d) {
          var clase = claseEstadoDoc(d.estado);
          h += "<tr><td><b>" + (esc(d.numero) || "#" + d.id) + "</b>" +
               '<div style="font-size:.78rem;color:var(--muted-2)">' + d.n_lineas +
               " línea" + (d.n_lineas === 1 ? "" : "s") + "</div></td>" +
               "<td>" + (esc(d.cliente) || "—") + "</td><td>" + (esc(d.obra) || "—") + "</td>" +
               (esAdmin() ? "<td>" + (esc(nombreDe("equipo", d.usuario_id)) || "—") + "</td>" : "") +
               "<td>" + esc(fecha(d.fecha)) + "</td>" +
               '<td><span class="tag ' + clase + '">' + esc(d.estado) + "</span></td>" +
               '<td class="num">' + eur(d.base) + '</td>' +
               '<td class="num" style="color:var(--muted)">' + eur(d.iva) + "</td>" +
               '<td class="num"><b>' + eur(d.total) + "</b></td>" +
               '<td class="acciones">' +
               (tipo === "presupuestos" && !d.firmado_el && d.estado !== "cancelado"
                 ? '<button data-firmar="' + d.id + '" title="Enviar al cliente para que lo firme">' +
                   svg(ico.firma) + "</button>"
                 : "") +
               (tipo === "presupuestos" && (d.firmado_el || d.firmas_previas)
                 ? '<button data-verfirma="' + d.id + '" title="' +
                   (d.firmado_el ? "Ver la firma del cliente" : "Ver las firmas de antes de editarlo") +
                   '">' + svg(ico.firma) + "</button>"
                 : "") +
               (tipo === "presupuestos" && !d.firmado_el && d.estado !== "aceptado" && d.estado !== "cancelado"
                 ? '<button data-aceptar="' + d.id + '" title="Marcar como aceptado">' + svg(ico.ok) + "</button>"
                 : "") +
               (tipo === "presupuestos" && d.estado !== "cancelado"
                 ? '<button data-cancelar="' + d.id + '" title="Cancelar el presupuesto">' + svg(ico.no) + "</button>"
                 : "") +
               (d.visita_id && puedeVer("visitas")
                 ? '<button data-visita="' + d.visita_id + '" title="Ver la visita: notas y fotos">' +
                   svg(ico.camara) + "</button>"
                 : "") +
               '<button data-pdf="' + d.id + '" data-num="' + esc(d.numero || "") +
                 '" title="Descargar PDF">' + svg(ico.descarga) + "</button>" +
               (tipo === "presupuestos" && puedeVer("proformas")
                 ? '<button data-proforma="' + d.id + '" title="Crear proforma">' + svg(ico.proforma) + "</button>"
                 : "") +
               (tipo !== "facturas" && puedeVer("facturas")
                 ? '<button data-facturar="' + d.id + '" title="Convertir en factura">' + svg(ico.recibo) + "</button>"
                 : "") +
               '<button data-editar="' + d.id + '" title="' +
                 (d.firmado_el ? "Editar: la firma se archiva y vuelve a borrador" : "Editar") +
                 '">' + svg(ico.lapiz) + "</button>" +
               // Borrar un presupuesto firmado no: se llevaría por delante la
               // prueba de lo que aceptó el cliente. Para eso está cancelarlo.
               (d.firmado_el
                 ? ""
                 : '<button class="borrar" data-borrar="' + d.id + '" title="Borrar">' +
                   svg(ico.papelera) + "</button>") +
               "</td></tr>";
        });
        $("#docs-tabla").innerHTML = h + "</tbody></table>";
        enganchar();
      }

      function enganchar() {
        $$("[data-pdf]").forEach(function (b) {
          b.addEventListener("click", function () {
            descargarPdf(tipo, b.dataset.pdf, b.dataset.num);
          });
        });
        $$("[data-visita]").forEach(function (b) {
          b.addEventListener("click", function () { abrirVisita(Number(b.dataset.visita)); });
        });
        $$("[data-aceptar]").forEach(function (b) {
          b.addEventListener("click", function () {
            b.disabled = true;
            api("/api/admin/documentos/" + tipo + "/" + b.dataset.aceptar + "/estado",
                { metodo: "POST", datos: { estado: "aceptado" } })
              .then(function () { avisar("Presupuesto aceptado"); ir(clave); })
              .catch(function (e) { b.disabled = false; avisar(e.message, "err"); });
          });
        });
        $$("[data-cancelar]").forEach(function (b) {
          b.addEventListener("click", function () { cancelarPresupuesto(tipo, b.dataset.cancelar, clave); });
        });
        $$("[data-firmar]").forEach(function (b) {
          b.addEventListener("click", function () {
            var d = docs.filter(function (x) { return String(x.id) === b.dataset.firmar; })[0];
            enviarAFirmar(d, clave);
          });
        });
        $$("[data-verfirma]").forEach(function (b) {
          b.addEventListener("click", function () {
            var d = docs.filter(function (x) { return String(x.id) === b.dataset.verfirma; })[0];
            verFirma(d);
          });
        });
        $$("[data-editar]").forEach(function (b) {
          b.addEventListener("click", function () { editarDocumento(tipo, b.dataset.editar); });
        });
        $$("[data-borrar]").forEach(function (b) {
          b.addEventListener("click", function () {
            modal("Confirmar borrado",
              "<p style='color:var(--muted)'>Se va a borrar este documento y todas sus líneas. No se puede deshacer.</p>",
              '<button class="btn btn--fant" id="b-no">Cancelar</button>' +
              '<button class="btn btn--peligro" id="b-si">Borrar</button>');
            $("#b-no").addEventListener("click", cerrarModal);
            $("#b-si").addEventListener("click", function () {
              api("/api/admin/documentos/" + tipo + "/" + b.dataset.borrar, { metodo: "DELETE" })
                .then(function () { cerrarModal(); ir(clave); }).catch(error);
            });
          });
        });
        $$("[data-facturar]").forEach(function (b) {
          b.addEventListener("click", function () {
            modal("Convertir en factura",
              "<p style='color:var(--muted)'>Se creará una factura con las mismas líneas y " +
                (tipo === "presupuestos" ? "el presupuesto quedará como <b>aceptado</b>."
                                         : "la proforma quedará como <b>facturada</b>.") + "</p>",
              '<button class="btn btn--fant" id="fa-no">Cancelar</button>' +
              '<button class="btn btn--amber" id="fa-si">Crear factura</button>');
            $("#fa-no").addEventListener("click", cerrarModal);
            $("#fa-si").addEventListener("click", function () {
              api("/api/admin/documentos/" + tipo + "/" + b.dataset.facturar + "/facturar",
                  { metodo: "POST" })
                .then(function () { cerrarModal(); ir("facturas"); })
                .catch(function (e) { cerrarModal(); error(e); });
            });
          });
        });
        $$("[data-proforma]").forEach(function (b) {
          b.addEventListener("click", function () {
            modal("Crear proforma",
              "<p style='color:var(--muted)'>Se creará una factura proforma con las mismas líneas, " +
              "con su propia numeración, y el presupuesto quedará como <b>aceptado</b>. " +
              "La proforma no cuenta en la contabilidad: no es una factura.</p>",
              '<button class="btn btn--fant" id="pf-no">Cancelar</button>' +
              '<button class="btn btn--amber" id="pf-si">Crear proforma</button>');
            $("#pf-no").addEventListener("click", cerrarModal);
            $("#pf-si").addEventListener("click", function () {
              api("/api/admin/documentos/presupuestos/" + b.dataset.proforma + "/proforma",
                  { metodo: "POST" })
                .then(function () { cerrarModal(); ir("proformas"); })
                .catch(function (e) { cerrarModal(); error(e); });
            });
          });
        });
      }

      pintarObras();
      repintar();
      $("#filtro-cliente").addEventListener("input", function () { est.cliente = this.value; pintarObras(); repintar(); });
      $("#filtro-obra").addEventListener("change", function () { est.obra = this.value; repintar(); });
      $("#filtro-estado").addEventListener("change", function () { est.estado = this.value; repintar(); });
      $("#buscar").addEventListener("input", repintar);
    }).catch(error);
}

/* ── Firma del presupuesto ────────────────────────────────────────────── */
// Teléfono listo para wa.me: solo cifras y con prefijo de país. Un móvil
// español de 9 cifras lleva el 34 delante; si ya trae prefijo (+351, 0033…) se
// respeta. Si no salen al menos 9 cifras no es un teléfono que valga.
function telefonoWhatsApp(t) {
  var n = String(t || "").replace(/[^\d+]/g, "");
  if (n.indexOf("00") === 0) n = n.slice(2);
  n = n.replace(/\D/g, "");
  if (n.length === 9) n = "34" + n;
  return n.length >= 11 ? n : "";
}

function enviarAFirmar(d, clave) {
  var numero = d.numero || "#" + d.id;
  var cli = (cache.clientes || []).filter(function (c) { return c.id === d.cliente_id; })[0];
  var email = cli && String(cli.email || "").trim();
  var tel = cli && telefonoWhatsApp(cli.telefono);

  // Cada canal se ofrece solo si hay a dónde mandarlo. Desactivado se sigue
  // viendo, con el motivo: así se sabe qué falta en la ficha del cliente.
  function opcion(canal, icono, titulo, destino, falta) {
    return '<button type="button" class="envio' + (destino ? "" : " envio--off") + '" data-canal="' + canal + '"' +
      (destino ? "" : " disabled") + ">" + svg(icono) +
      "<span><b>" + esc(titulo) + "</b><small>" + esc(destino || falta) + "</small></span></button>";
  }
  var sinCliente = "El presupuesto no tiene cliente";
  modal("Mandar a firmar " + numero,
    '<div class="aviso aviso--err" id="fm-err" hidden></div>' +
    '<p style="color:var(--muted);line-height:1.55">Le llega al cliente un enlace privado donde ' +
    "puede leer el presupuesto con sus condiciones y firmarlo desde el móvil. " +
    "Al firmar se guarda el PDF tal cual, con la fecha, la hora y su firma.</p>" +
    '<div class="envios">' +
      opcion("correo", ico.buzon, "Por correo", email, cli ? "El cliente no tiene correo en su ficha" : sinCliente) +
      opcion("whatsapp", ico.whatsapp, "Por WhatsApp", tel ? cli.telefono : "",
             cli ? (cli.telefono ? "El teléfono de la ficha no parece válido" : "El cliente no tiene teléfono en su ficha")
                 : sinCliente) +
    "</div>" +
    '<p style="color:var(--muted-2);font-size:.88rem;line-height:1.55">Mientras no lo firme puedes ' +
    "seguir editándolo. Si lo editas después de firmado, la firma se archiva y hay que volver a mandárselo.</p>",
    '<button class="btn btn--fant btn--sm" id="fm-enlace" style="margin-right:auto">Solo copiar el enlace</button>' +
    '<button class="btn btn--fant" id="fm-no">Cancelar</button>');
  $("#fm-no").addEventListener("click", cerrarModal);

  function fallo(e) {
    var err = $("#fm-err");
    if (!err) return avisar(e.message, "err");
    err.textContent = e.message; err.hidden = false;
    $$(".envios [data-canal]").forEach(function (b) { b.classList.remove("is-cargando"); });
  }
  function pedir(canal) {
    return api("/api/admin/documentos/presupuestos/" + d.id + "/enviar-firma",
               { metodo: "POST", datos: { canal: canal } });
  }

  $$(".envios [data-canal]").forEach(function (b) {
    b.addEventListener("click", function () {
      if (b.disabled || b.classList.contains("is-cargando")) return;
      b.classList.add("is-cargando");
      if (b.dataset.canal === "correo") {
        pedir("correo").then(function (r) {
          cerrarModal();
          if (r.enviado) { avisar("Enviado a " + r.email); ir(clave); return; }
          // Si el correo falla, el enlace se enseña para pasarlo a mano.
          enlaceParaCopiar(numero, r.enlace, r.motivo);
          ir(clave);
        }).catch(fallo);
        return;
      }
      // WhatsApp se abre desde aquí, con el mensaje ya escrito, y sale del
      // teléfono de quien lo manda. La ventana se abre antes de pedir el enlace:
      // abierta después de esperar al servidor, el navegador la bloquea.
      var ventana = window.open("", "_blank");
      pedir("whatsapp").then(function (r) {
        var nombre = String(r.nombre || "").split(" ")[0];
        var texto = "Hola" + (nombre ? " " + nombre : "") + ", te paso el presupuesto " + numero +
          " de Loureiro Soluciones. Puedes leerlo y, si estás de acuerdo, firmarlo desde el móvil aquí:\n" +
          r.enlace + "\n\nEl enlace es personal, no lo compartas.";
        var url = "https://wa.me/" + tel + "?text=" + encodeURIComponent(texto);
        cerrarModal();
        if (ventana) ventana.location.href = url;
        else enlaceParaCopiar(numero, r.enlace, "El navegador no ha dejado abrir WhatsApp.");
        ir(clave);
      }).catch(function (e) { if (ventana) ventana.close(); fallo(e); });
    });
  });

  $("#fm-enlace").addEventListener("click", function () {
    var btn = this;
    btn.disabled = true;
    pedir("whatsapp").then(function (r) {
      cerrarModal();
      enlaceParaCopiar(numero, r.enlace, "");
      ir(clave);
    }).catch(function (e) { btn.disabled = false; fallo(e); });
  });
}

function enlaceParaCopiar(numero, enlace, motivo) {
  modal("Pásale el enlace al cliente",
    '<p style="color:var(--muted);line-height:1.55">' + esc(motivo || "") +
    " Puedes mandárselo por WhatsApp. Con él lee el presupuesto " + esc(numero) + " y lo firma.</p>" +
    '<div class="ag-url"><input id="fm-url" readonly value="' + esc(enlace) + '">' +
    '<button class="btn btn--fant btn--sm" id="fm-copiar">Copiar</button></div>',
    '<button class="btn btn--amber" id="fm-ok">Hecho</button>');
  $("#fm-ok").addEventListener("click", cerrarModal);
  $("#fm-copiar").addEventListener("click", function () {
    var inp = $("#fm-url");
    inp.select();
    var hecho = function () { avisar("Enlace copiado"); };
    if (navigator.clipboard) {
      navigator.clipboard.writeText(inp.value).then(hecho, function () { document.execCommand("copy"); hecho(); });
    } else { document.execCommand("copy"); hecho(); }
  });
}

function verFirma(d) {
  api("/api/admin/documentos/presupuestos/" + d.id + "/firma").then(function (f) {
    var fila = function (k, v) {
      return "<tr><td style='color:var(--muted);white-space:nowrap;padding:6px 14px 6px 0'>" + esc(k) +
             "</td><td style='word-break:break-all'>" + esc(v || "—") + "</td></tr>";
    };
    // Las firmas archivadas: las que tenía antes de que se editara. Se enseñan
    // con su fecha y su PDF, que es lo que prueba qué aceptó aquel día.
    var antes = (f.anteriores || []).map(function (a) {
      return '<div style="border:1px solid var(--line);border-radius:10px;padding:12px;margin-top:10px">' +
        "<b>" + esc(a.firmante_nombre || "Sin nombre") + "</b>" +
        '<span style="color:var(--muted-2)"> · firmado el ' + esc(fecha(a.firmado_el)) +
        " · archivado el " + esc(fecha(a.anulada_el)) + "</span>" +
        '<div style="color:var(--muted);font-size:.82rem;word-break:break-all;margin-top:6px">' +
        "Huella del PDF: " + esc(a.hash_pdf || "—") + "</div>" +
        '<button class="btn btn--fant btn--sm" data-pdffirma="' + a.id +
        '" style="margin-top:9px">' + svg(ico.descarga) + "Descargar lo que firmó</button></div>";
    }).join("");

    modal("Firma de " + esc(d.numero || "#" + d.id),
      (f.firmado_el
        ? (f.imagen
            ? '<div style="background:#fff;border-radius:10px;padding:10px;margin-bottom:16px;text-align:center">' +
              '<img src="' + esc(f.imagen) + '" alt="Firma del cliente" style="max-width:100%;height:110px;object-fit:contain"></div>'
            : "") +
          '<div class="tabla-caja"><div class="tabla-scroll"><table><tbody>' +
          fila("Firmado por", f.firmante_nombre) +
          fila("NIF", f.firmante_nif) +
          fila("Fecha y hora (UTC)", f.firmado_el) +
          fila("Dirección IP", f.ip) +
          fila("Navegador", f.agente) +
          fila("Huella del documento", f.huella) +
          fila("Huella del PDF firmado", f.hash_pdf) +
          fila("Pidió empezar antes de los 14 días", f.inicio_inmediato ? "Sí" : "No") +
          "</tbody></table></div></div>" +
          '<p style="color:var(--muted-2);font-size:.84rem;line-height:1.55;margin-top:14px">Estas son ' +
          "las pruebas de la aceptación. El PDF que se descarga es exactamente el que firmó el cliente.</p>"
        : '<p style="color:var(--muted);line-height:1.55">Este presupuesto <b>no está firmado ' +
          "ahora mismo</b>: se editó después de firmarlo, así que aquella firma dejó de valer para " +
          "lo que pone hoy. Si quieres que lo vuelva a firmar, mándaselo otra vez.</p>") +
      (antes
        ? '<h3 style="font-size:.95rem;margin:22px 0 4px">Firmas de antes de editarlo</h3>' +
          '<p style="color:var(--muted-2);font-size:.84rem;margin:0 0 6px">Ya no valen para el ' +
          "presupuesto de ahora, pero se guardan enteras: son la prueba de lo que se aceptó " +
          "en su día.</p>" + antes
        : ""),
      '<button class="btn btn--amber" id="vf-ok">Cerrar</button>', true);
    $$("[data-pdffirma]").forEach(function (b) {
      b.addEventListener("click", function () {
        descargarPdfFirma(d, b.dataset.pdffirma);
      });
    });
    $("#vf-ok").addEventListener("click", cerrarModal);
  }).catch(function (e) { avisar(e.message, "err"); });
}

function editarCondiciones() {
  api("/api/admin/condiciones").then(function (r) {
    modal("Condiciones de contratación",
      '<div class="aviso aviso--err" id="cd-err" hidden></div>' +
      '<p style="color:var(--muted);line-height:1.55">Este texto sale en todos los presupuestos, ' +
      "en su hoja de condiciones, y es lo que acepta el cliente al firmar. La primera línea de cada " +
      "párrafo hace de título; deja una línea en blanco entre bloques.</p>" +
      '<div class="campo"><textarea id="cd-texto" style="min-height:320px">' + esc(r.texto) + "</textarea></div>" +
      '<p style="color:var(--muted-2);font-size:.84rem;line-height:1.55">Al presupuesto se le añade ' +
      "además, por ley, el aviso del derecho de desistimiento de 14 días para clientes particulares. " +
      "Eso no se puede quitar, pero el cliente puede pedir que empecéis antes y entonces sí responde " +
      "de los gastos si se echa atrás.</p>",
      '<button class="btn btn--fant" id="cd-no">Cancelar</button>' +
      '<button class="btn btn--amber" id="cd-si">Guardar</button>', true);
    $("#cd-no").addEventListener("click", cerrarModal);
    $("#cd-si").addEventListener("click", function () {
      var btn = this;
      btn.disabled = true; btn.textContent = "Guardando…";
      api("/api/admin/condiciones", { metodo: "PUT", datos: { texto: $("#cd-texto").value } })
        .then(function () { cerrarModal(); avisar("Condiciones guardadas"); })
        .catch(function (e) {
          var err = $("#cd-err");
          err.textContent = e.message; err.hidden = false;
          btn.disabled = false; btn.textContent = "Guardar";
        });
    });
  }).catch(function (e) { avisar(e.message, "err"); });
}

function cancelarPresupuesto(tipo, id, clave) {
  modal("Cancelar el presupuesto",
    '<div class="aviso aviso--err" id="cx-err" hidden></div>' +
    '<p style="color:var(--muted);line-height:1.55">Queda como cancelado, con la fecha de hoy. ' +
    "No se borra: sigue ahí con su número y sus líneas.</p>" +
    '<div class="campo"><label for="cx-motivo">Motivo de la cancelación *</label>' +
    '<textarea id="cx-motivo" placeholder="Lo deja para el año que viene, cogió otra oferta, no contesta…"></textarea></div>',
    '<button class="btn btn--fant" id="cx-no">Volver</button>' +
    '<button class="btn btn--peligro" id="cx-si">Cancelar el presupuesto</button>');
  $("#cx-no").addEventListener("click", cerrarModal);
  $("#cx-motivo").focus();
  $("#cx-si").addEventListener("click", function () {
    var motivo = $("#cx-motivo").value.trim(), err = $("#cx-err"), btn = this;
    if (!motivo) { err.textContent = "Escribe el motivo."; err.hidden = false; return; }
    btn.disabled = true;
    api("/api/admin/documentos/" + tipo + "/" + id + "/estado",
        { metodo: "POST", datos: { estado: "cancelado", motivo: motivo } })
      .then(function () { cerrarModal(); avisar("Presupuesto cancelado"); ir(clave); })
      .catch(function (e) { err.textContent = e.message; err.hidden = false; btn.disabled = false; });
  });
}

// El presupuesto del que sale una factura o una proforma. Se busca igual que
// en las obras: por número o por el nombre del cliente.
var CAMPO_PRESUPUESTO = {
  c: "presupuesto_id", de: "documentos/presupuestos",
  etiqueta: function (p) {
    return p.numero + " · " + (p.cliente || "sin cliente") + " · " + eur(p.total);
  },
  filtra: function (p) { return p.estado !== "cancelado"; }
};

// `inicial`: valores de partida de uno nuevo. La ficha de una visita abre así
// el presupuesto, ya con su cliente y colgado de ella.
// Precio con IVA de una línea que guarda la base, y al revés. La base se
// guarda con seis decimales: con dos, 21 € con IVA al 21 % serían 17,36 € y
// siete unidades ya no sumarían 147 €.
function pvpDe(l) { return Math.round((Number(l.precio) || 0) * (1 + (Number(l.iva) || 0) / 100) * 100) / 100; }
function baseDe(pvp, iva) { return Math.round(pvp / (1 + (iva || 0) / 100) * 1e6) / 1e6; }

function editarDocumento(tipo, id, inicial) {
  var esFactura = tipo === "facturas";
  // Solo el presupuesto dice de qué visita sale: es el documento que se hace
  // con las notas y las fotos delante.
  var deVisita = tipo === "presupuestos";
  // Facturas y proformas salen de un presupuesto; un presupuesto no sale de
  // otro, así que ahí el campo no pinta nada.
  var dePresupuesto = tipo === "facturas" || tipo === "proformas";
  Promise.all([
    id ? api("/api/admin/documentos/" + tipo + "/" + id) : Promise.resolve(null),
    cargarRef("clientes"), cargarRef("obras")
  ].concat(esAdmin() ? [cargarRef("equipo")] : [])
   .concat(dePresupuesto ? [cargarRef("documentos/presupuestos")] : [])
   .concat(deVisita ? [cargarRef("visitas")] : [])).then(function (res) {
    var doc = res[0] || Object.assign({
      lineas: [], estado: ESTADOS_DOC[tipo][0],
      fecha: new Date().toISOString().slice(0, 10),
      usuario_id: YO && YO.id      // lo que se crea es de quien lo crea
    }, inicial || {});
    var lineas = (doc.lineas || []).map(function (l) {
      return {
        concepto: l.concepto, cantidad: l.cantidad, unidad: l.unidad,
        precio: l.precio, iva: l.iva, pvp: pvpDe(l), dePresu: false
      };
    });
    if (!lineas.length) lineas.push({ concepto: "", cantidad: 1, unidad: "ud", precio: 0, iva: 21, pvp: 0 });

    function mismaLinea(a, b) {
      return String(a.concepto).trim() === String(b.concepto).trim() &&
             Number(a.cantidad) === Number(b.cantidad) &&
             Number(a.precio) === Number(b.precio) &&
             Number(a.iva) === Number(b.iva);
    }

    // De un documento que ya venía de un presupuesto se marca qué líneas son
    // todavía las suyas. Así, al elegir otro presupuesto, se sustituyen esas y
    // se quedan las que se añadieron a mano. Si el presupuesto ya no está, se
    // quedan todas como propias, que es lo prudente.
    if (doc.presupuesto_id) {
      api("/api/admin/documentos/" + tipo + "/desde-presupuesto/" + doc.presupuesto_id)
        .then(function (r) {
          lineas.forEach(function (l) {
            l.dePresu = r.lineas.some(function (o) { return mismaLinea(l, o); });
          });
        })
        .catch(function () {});
    }

    function opciones(lista, sel, deCliente) {
      // Igual que en los formularios: un enlace con algo de otra persona se conserva.
      var ajeno = sel && !(cache[lista] || []).some(function (o) { return String(o.id) === String(sel); });
      return '<option value="">' + (lista === "equipo" ? "— nadie: solo el administrador —" : "— sin asignar —") +
        "</option>" + (ajeno ? '<option value="' + esc(sel) + '" selected>(lo lleva otra persona)</option>' : "") +
        soloDelCliente(cache[lista] || [], deCliente, sel).map(function (o) {
        return '<option value="' + o.id + '"' + (String(o.id) === String(sel) ? " selected" : "") + ">" +
               esc(o.titulo || o.nombre) + "</option>";
      }).join("");
    }

    // Las visitas del cliente elegido, con fecha y fotos para reconocerlas.
    function opcionesVisita(sel, cid) {
      var ajena = sel && !(cache.visitas || []).some(function (o) { return String(o.id) === String(sel); });
      return '<option value="">— sin visita —</option>' +
        (ajena ? '<option value="' + esc(sel) + '" selected>(lo lleva otra persona)</option>' : "") +
        soloDelCliente(cache.visitas || [], cid, sel).map(function (o) {
          return '<option value="' + o.id + '"' + (String(o.id) === String(sel) ? " selected" : "") + ">" +
                 esc(etiquetaVisita(o)) + "</option>";
        }).join("");
    }

    function campoPresupuesto(sel) {
      var ops = soloDelCliente(opcionesBusca(CAMPO_PRESUPUESTO), doc.cliente_id, sel);
      var yaEsta = ops.filter(function (o) { return String(o.id) === String(sel); })[0];
      return '<div class="campo"><label for="d-presu">Presupuesto</label>' +
        '<input id="d-presu" list="lista-d-presu" autocomplete="off"' +
        ' placeholder="Escribe el número o el cliente" value="' +
        esc(yaEsta ? yaEsta.txt : "") + '">' +
        '<datalist id="lista-d-presu">' +
        ops.map(function (o) { return '<option value="' + esc(o.txt) + '"></option>'; }).join("") +
        "</datalist>" +
        '<small style="color:var(--muted-2);font-size:.79rem">Al elegirlo se traen ' +
        "sus líneas, su cliente, su obra y sus notas. Las líneas que añadas aparte se " +
        "quedan como están.</small></div>";
    }

    var cuerpo = '<div class="aviso aviso--err" id="d-err" hidden></div>' +
      (doc.firmado_el
        ? '<div class="aviso aviso--aviso">Este presupuesto lo firmó <b>' +
          esc(doc.firmante_nombre || "el cliente") + "</b> el " + esc(fecha(doc.firmado_el)) +
          ". Si guardas cambios, esa firma se guarda aparte y el presupuesto vuelve a " +
          "<b>borrador</b>: lo que pone ahora ya no es lo que firmó, y hay que mandárselo " +
          "otra vez.</div>"
        : "") +
      '<div class="rejilla-2">' +
        // El número no se escribe: lo pone la serie al guardar y luego ya no
        // cambia. Se enseña para poder leerlo y copiarlo, nada más.
        '<div class="campo"><label for="d-numero">Número</label>' +
          '<input id="d-numero" readonly value="' + esc(doc.numero) +
          '" placeholder="Se pone solo al guardar">' +
          (doc.numero ? "" :
            '<small style="color:var(--muted-2);font-size:.79rem">' +
            (esFactura
              ? "Va detrás de la última factura. La serie tiene que ser correlativa, "
                + "así que no se toca a mano."
              : "Sigue la serie y no se toca a mano.") + "</small>") + "</div>" +
        '<div class="campo"><label for="d-fecha">Fecha</label><input id="d-fecha" type="date" value="' +
          esc(doc.fecha) + '"></div>' +
      "</div>" +
      (dePresupuesto ? campoPresupuesto(doc.presupuesto_id) : "") +
      '<div class="rejilla-2">' +
        '<div class="campo"><label for="d-cliente">Cliente</label><select id="d-cliente">' +
          opciones("clientes", doc.cliente_id) + "</select></div>" +
        '<div class="campo"><label for="d-obra">Obra</label><select id="d-obra">' +
          opciones("obras", doc.obra_id, doc.cliente_id) + "</select></div>" +
      "</div>" +
      (deVisita
        ? '<div class="campo"><label for="d-visita">Visita</label><select id="d-visita">' +
          opcionesVisita(doc.visita_id, doc.cliente_id) + "</select>" +
          '<small style="color:var(--muted-2);font-size:.79rem">La toma de datos de la que sale: ' +
          "sus notas y sus fotos, en la pestaña Visitas.</small></div>"
        : "") +
      '<div class="rejilla-2">' +
        '<div class="campo"><label for="d-estado">Estado</label><select id="d-estado">' +
          ESTADOS_DOC[tipo].map(function (e) {
            return "<option" + (e === doc.estado ? " selected" : "") + ">" + esc(e) + "</option>";
          }).join("") + "</select></div>" +
        (esFactura
          ? '<div class="campo"><label for="d-venc">Vencimiento</label><input id="d-venc" type="date" value="' + esc(doc.vencimiento) + '"></div>'
          : '<div class="campo"><label for="d-validez">Validez (días)</label><input id="d-validez" type="number" value="' + (doc.validez || 30) + '"></div>') +
      "</div>" +
      (tipo === "presupuestos"
        ? '<div class="campo" id="d-motivo-caja"><label for="d-motivo">Motivo de la cancelación</label>' +
          '<textarea id="d-motivo">' + esc(doc.motivo_cancelacion) + "</textarea>" +
          (doc.cancelado_el ? '<small style="color:var(--muted-2);font-size:.79rem">Cancelado el ' +
            esc(fecha(doc.cancelado_el)) + "</small>" : "") + "</div>"
        : "") +
      (esAdmin()
        ? '<div class="campo"><label for="d-resp">Responsable</label><select id="d-resp">' +
          opciones("equipo", doc.usuario_id || (YO && YO.id)) + "</select>" +
          '<small style="color:var(--muted-2);font-size:.79rem">Solo lo ven esa persona y el administrador.</small></div>'
        : "") +
      '<label style="font-size:.83rem;color:var(--muted);display:block;margin:18px 0 8px">Líneas</label>' +
      '<div class="lineas-cab"><span>Concepto</span><span>Cant.</span><span>Ud.</span>' +
        "<span>Precio IVA incl.</span><span>IVA %</span><span>Importe IVA incl.</span><span></span></div>" +
      '<div class="lineas" id="d-lineas"></div>' +
      '<button class="btn btn--fant btn--sm" id="d-add" style="margin-top:10px">' +
        svg(ico.mas) + "Añadir línea</button>" +
      '<div class="totales" id="d-totales"></div>' +
      '<div class="campo" style="margin-top:16px"><label for="d-notas">Notas</label><textarea id="d-notas">' +
        esc(doc.notas) + "</textarea></div>";

    modal(id ? "Editar " + NOMBRE_DOC[tipo].uno : NOMBRE_DOC[tipo].nuevo, cuerpo,
      '<button class="btn btn--fant" id="d-cancelar">Cancelar</button>' +
      '<button class="btn btn--amber" id="d-guardar">Guardar</button>', true);

    function pintarLineas() {
      $("#d-lineas").innerHTML = lineas.map(function (l, i) {
        return '<div class="linea" data-i="' + i + '">' +
          '<input class="l-concepto" placeholder="Concepto" value="' + esc(l.concepto) + '">' +
          '<input class="l-cant" type="number" step="any" placeholder="Cant." value="' + esc(l.cantidad) + '">' +
          '<input class="l-ud" placeholder="ud" value="' + esc(l.unidad) + '">' +
          '<input class="l-precio" type="number" step="any" placeholder="Precio con IVA" value="' + esc(l.pvp) + '">' +
          '<select class="l-iva" aria-label="IVA">' + opcionesIva(l.iva) + "</select>" +
          '<span class="l-total">' + eur((l.cantidad || 0) * (l.pvp || 0)) + "</span>" +
          '<button class="l-borrar" title="Quitar línea">' + svg(ico.papelera) + "</button>" +
          "</div>";
      }).join("");
      $$("#d-lineas .linea").forEach(function (fila) {
        var i = Number(fila.dataset.i);
        function leer() {
          // Se escribe el precio con IVA, como pone el tique; la base sale de
          // ahí. Si se cambia el IVA, el precio con IVA escrito se mantiene.
          var pvp = Number($(".l-precio", fila).value) || 0, iva = Number($(".l-iva", fila).value) || 0;
          lineas[i] = {
            concepto: $(".l-concepto", fila).value,
            cantidad: Number($(".l-cant", fila).value) || 0,
            unidad: $(".l-ud", fila).value || "ud",
            pvp: pvp, iva: iva, precio: baseDe(pvp, iva)
          };
          $(".l-total", fila).textContent = eur(lineas[i].cantidad * pvp);
          pintarTotales();
        }
        $$("input, select", fila).forEach(function (inp) { inp.addEventListener("input", leer); });
        $(".l-borrar", fila).addEventListener("click", function () {
          lineas.splice(i, 1);
          if (!lineas.length) lineas.push({ concepto: "", cantidad: 1, unidad: "ud", precio: 0, iva: 21, pvp: 0 });
          pintarLineas(); pintarTotales();
        });
      });
    }

    function pintarTotales() {
      var base = lineas.reduce(function (a, l) { return a + (l.cantidad || 0) * (l.precio || 0); }, 0);
      var iva = lineas.reduce(function (a, l) {
        return a + (l.cantidad || 0) * (l.precio || 0) * (l.iva || 0) / 100;
      }, 0);
      $("#d-totales").innerHTML =
        "<div><span>Base imponible</span><b>" + eur(base) + "</b></div>" +
        "<div><span>IVA</span><b>" + eur(iva) + "</b></div>" +
        '<div class="grande"><span>Total</span><b>' + eur(base + iva) + "</b></div>";
    }

    pintarLineas(); pintarTotales();

    // El motivo solo estorba mientras el presupuesto sigue vivo.
    if ($("#d-motivo-caja")) {
      var selEstado = $("#d-estado");
      var verMotivo = function () {
        $("#d-motivo-caja").style.display = selEstado.value === "cancelado" ? "" : "none";
      };
      verMotivo();
      selEstado.addEventListener("change", verMotivo);
    }

    // Al elegir el presupuesto, la factura se rellena con lo suyo. Las notas
    // solo se pisan si están vacías o si las puso otro presupuesto antes: lo
    // que se haya escrito a mano no se toca.
    var inpPresu = $("#d-presu"), pegado = {};
    if (inpPresu) inpPresu.addEventListener("change", function () {
      var op = buscaElegida(CAMPO_PRESUPUESTO, inpPresu.value);
      if (!op) {
        if (inpPresu.value.trim()) { inpPresu.value = ""; avisar("Elige uno de la lista", "err"); }
        return;
      }
      inpPresu.value = op.txt;
      api("/api/admin/documentos/" + tipo + "/desde-presupuesto/" + op.id).then(function (r) {
        var propias = lineas.filter(function (l) {
          return !l.dePresu && String(l.concepto).trim();
        });
        lineas = r.lineas.map(function (l) {
          return { concepto: l.concepto, cantidad: l.cantidad, unidad: l.unidad,
                   precio: l.precio, iva: l.iva, pvp: pvpDe(l), dePresu: true };
        }).concat(propias);
        // El cliente lo manda siempre el presupuesto: una factura con las líneas
        // de un presupuesto y el nombre de otro cliente está mal emitida, y es
        // un fallo que no se ve hasta que la recibe quien no era.
        if (r.cabecera.cliente_id) {
          $("#d-cliente").value = r.cabecera.cliente_id;
          pegado.cliente = $("#d-cliente").value;
        }
        // La obra y las notas solo se pegan si están vacías o si las puso otro
        // presupuesto antes: lo elegido o escrito a mano no se toca. Si el
        // presupuesto nuevo no trae obra, se quita la que pegó el anterior.
        ["obra", "notas"].forEach(function (k) {
          var el = $("#d-" + k);
          var valor = r.cabecera[k === "obra" ? "obra_id" : "notas"];
          valor = valor === null || valor === undefined ? "" : String(valor);
          if (el.value.trim() && el.value !== pegado[k]) return;
          el.value = valor;
          pegado[k] = el.value;
        });
        pintarLineas(); pintarTotales();
        filtrarPorCliente();
        avisar("Traído del presupuesto " + (r.presupuesto.numero || op.id));
      }).catch(function (e) { avisar(e.message, "err"); });
    });

    // Con un cliente elegido, la obra y el presupuesto que se ofrecen son los
    // suyos: buscar entre los de toda la empresa es buscar de más. Y si lo que
    // había puesto era de otro cliente se quita, porque una factura a nombre de
    // Carmen colgada de la obra de Manuel no la cuadra nadie.
    function filtrarPorCliente() {
      var cid = $("#d-cliente").value;
      var selObra = $("#d-obra");
      var obra = (cache.obras || []).filter(function (o) {
        return String(o.id) === selObra.value;
      })[0];
      var sobra = cid && obra && obra.cliente_id && String(obra.cliente_id) !== String(cid);
      selObra.innerHTML = opciones("obras", sobra ? "" : selObra.value, cid);

      var quitado = sobra ? ["la obra"] : [];
      var selVisita = $("#d-visita");
      if (selVisita) {
        var visita = (cache.visitas || []).filter(function (o) { return String(o.id) === selVisita.value; })[0];
        var sobraVisita = cid && visita && visita.cliente_id && String(visita.cliente_id) !== String(cid);
        selVisita.innerHTML = opcionesVisita(sobraVisita ? "" : selVisita.value, cid);
        if (sobraVisita) quitado.push("la visita");
      }
      if (inpPresu) {
        var elegido = buscaElegida(CAMPO_PRESUPUESTO, inpPresu.value);
        if (cid && elegido && elegido.fila.cliente_id &&
            String(elegido.fila.cliente_id) !== String(cid)) {
          inpPresu.value = "";
          elegido = null;
          quitado.push("el presupuesto");
        }
        pintarDatalist("lista-d-presu",
          soloDelCliente(opcionesBusca(CAMPO_PRESUPUESTO), cid, elegido && elegido.id));
      }
      if (quitado.length) {
        avisar("Se ha quitado " + quitado.join(" y ") + ": era de otro cliente");
      }
    }
    $("#d-cliente").addEventListener("change", filtrarPorCliente);

    // Elegir la visita antes que el cliente pone el cliente de la visita.
    if ($("#d-visita")) $("#d-visita").addEventListener("change", function () {
      var sel = this.value;
      var visita = (cache.visitas || []).filter(function (o) { return String(o.id) === sel; })[0];
      if (visita && visita.cliente_id && !$("#d-cliente").value) {
        $("#d-cliente").value = visita.cliente_id;
        filtrarPorCliente();
      }
    });

    $("#d-add").addEventListener("click", function () {
      lineas.push({ concepto: "", cantidad: 1, unidad: "ud", precio: 0, iva: 21, pvp: 0 });
      pintarLineas(); pintarTotales();
    });
    $("#d-cancelar").addEventListener("click", cerrarModal);
    $("#d-guardar").addEventListener("click", function () {
      // dePresu es una marca del editor, no una columna: no sale de aquí.
      var utiles = lineas.filter(function (l) { return String(l.concepto).trim(); })
        .map(function (l) {
          return { concepto: l.concepto, cantidad: l.cantidad, unidad: l.unidad,
                   precio: l.precio, iva: l.iva };
        });
      if (!utiles.length) {
        var e = $("#d-err");
        e.textContent = "Añade al menos una línea con concepto.";
        e.hidden = false;
        return;
      }
      var cabecera = {
        fecha: $("#d-fecha").value || null,
        cliente_id: $("#d-cliente").value ? Number($("#d-cliente").value) : null,
        obra_id: $("#d-obra").value ? Number($("#d-obra").value) : null,
        visita_id: $("#d-visita") && $("#d-visita").value ? Number($("#d-visita").value) : null,
        estado: $("#d-estado").value,
        notas: $("#d-notas").value.trim() || null
      };
      if (inpPresu) {
        var elegido = buscaElegida(CAMPO_PRESUPUESTO, inpPresu.value);
        cabecera.presupuesto_id = elegido ? elegido.id : null;
      }
      if (esFactura) cabecera.vencimiento = $("#d-venc").value || null;
      else cabecera.validez = Number($("#d-validez").value) || 30;
      if (esAdmin()) cabecera.usuario_id = $("#d-resp").value ? Number($("#d-resp").value) : null;
      if ($("#d-motivo")) cabecera.motivo_cancelacion = $("#d-motivo").value.trim() || null;

      var btn = $("#d-guardar");
      btn.disabled = true; btn.textContent = "Guardando…";
      api("/api/admin/documentos/" + tipo + (id ? "/" + id : ""),
          { metodo: id ? "PUT" : "POST", datos: { cabecera: cabecera, lineas: utiles } })
        .then(function () { invalidar(); cerrarModal(); ir(VOLVER || tipo); })
        .catch(function (err) {
          var e = $("#d-err"); e.textContent = err.message; e.hidden = false;
          btn.disabled = false; btn.textContent = "Guardar";
        });
    });
  }).catch(error);
}

/* ── Contabilidad ─────────────────────────────────────────────────────── */
function verContabilidad() {
  var anio = new Date().getFullYear();
  api("/api/admin/informes/contabilidad?anio=" + anio).then(function (d) {
    var t = d.totales;
    var resultado = (t.ingresos || 0) - (t.gastos || 0);
    var ivaLiquidar = (t.iva_repercutido || 0) - (t.iva_soportado || 0);

    var h = '<div class="metricas">' +
      metrica(eur(t.ingresos), "Ingresos " + anio, "metrica--verde") +
      metrica(eur(t.gastos), "Gastos " + anio, "metrica--rojo") +
      metrica(eur(resultado), "Resultado", resultado >= 0 ? "metrica--verde" : "metrica--rojo") +
      metrica(eur(ivaLiquidar), "IVA a liquidar", "metrica--azul") +
      metrica(eur(t.pendiente_cobro), "Pendiente de cobro", "") +
      metrica(eur(t.pendiente_pago), "Pendiente de pago", "") +
      "</div>";

    var meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
                 "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
    h += '<div class="paneles">';
    h += '<div class="tarjeta"><h3>Mes a mes <span>' + anio + "</span></h3>" + (d.meses.length
      ? '<div class="tabla-scroll"><table><thead><tr><th>Mes</th><th class="num">Ingresos</th>' +
        '<th class="num">Gastos</th><th class="num">Resultado</th></tr></thead><tbody>' +
        d.meses.map(function (m) {
          var r = (m.ingresos || 0) - (m.gastos || 0);
          return "<tr><td>" + esc(meses[parseInt(m.mes, 10)] || m.mes) + '</td><td class="num">' + eur(m.ingresos) +
                 '</td><td class="num">' + eur(m.gastos) + '</td><td class="num" style="color:' +
                 (r >= 0 ? "var(--verde)" : "var(--rojo)") + '"><b>' + eur(r) + "</b></td></tr>";
        }).join("") + "</tbody></table></div>"
      : '<div class="vacia">Sin movimientos este año.</div>') + "</div>";

    h += '<div class="tarjeta"><h3>Gastos por categoría</h3>' + (d.gastos_por_categoria.length
      ? '<div class="tabla-scroll"><table><tbody>' + d.gastos_por_categoria.map(function (g) {
          var pct = t.gastos ? Math.round(g.total / t.gastos * 100) : 0;
          return "<tr><td>" + esc(g.categoria) + '<div style="height:4px;border-radius:2px;background:var(--amber);width:' +
                 Math.max(4, pct) + '%;margin-top:6px"></div></td>' +
                 '<td class="num">' + eur(g.total) + '<div style="font-size:.76rem;color:var(--muted)">' + pct + "%</div></td></tr>";
        }).join("") + "</tbody></table></div>"
      : '<div class="vacia">Sin gastos registrados.</div>') + "</div>";
    h += "</div>";

    h += '<div class="tarjeta" style="margin-top:16px"><h3>IVA</h3>' +
      '<div class="tabla-scroll"><table><tbody>' +
      "<tr><td>IVA repercutido (facturado a clientes)</td><td class=\"num\">" + eur(t.iva_repercutido) + "</td></tr>" +
      "<tr><td>IVA soportado (pagado en compras)</td><td class=\"num\">" + eur(t.iva_soportado) + "</td></tr>" +
      "<tr><td><b>Diferencia a liquidar</b></td><td class=\"num\"><b>" + eur(ivaLiquidar) + "</b></td></tr>" +
      "</tbody></table></div>" +
      '<p style="color:var(--muted-2);font-size:.83rem;margin-top:14px">' +
      "Estos números son para llevar el control interno del negocio. No sustituyen a tu gestoría " +
      "ni a las declaraciones fiscales: sirven para que sepas en todo momento cómo vas.</p></div>";

    $("#vista").innerHTML = h;
  }).catch(error);
}

/* ── De dónde vienen los clientes ─────────────────────────── */
// Para saber dónde merece la pena gastar: qué trae cada canal en clientes,
// solicitudes, obras y dinero facturado. Un canal a cero también dice algo,
// así que sale en la tabla igual, apagado.
function verOrigenes() {
  var periodo = pintarPeriodo(verOrigenes);

  api("/api/admin/informes/origenes?periodo=" + periodo).then(function (d) {
    var t = d.totales;
    var del = periodo.length === 4 ? "del año" : "del mes";

    var h = '<div class="metricas">' +
      metrica(t.clientes, "Clientes nuevos " + del, "") +
      metrica(t.solicitudes, "Solicitudes " + del, "") +
      metrica(t.obras, "Obras " + del, "") +
      metrica(eur(t.facturado), "Facturado " + del + " · sin IVA", "metrica--verde") +
      "</div>";

    h += '<div class="tarjeta" style="margin-top:16px"><h3>Por dónde llegaron <span>' +
         esc(nombrePeriodo(periodo)) + "</span></h3>";

    if (!t.clientes && !t.solicitudes && !t.obras && !t.facturado) {
      h += '<div class="vacia">Nada apuntado en este periodo.</div>';
    } else {
      h += '<div class="tabla-scroll"><table><thead><tr><th>Canal</th>' +
        '<th class="num">Clientes</th><th class="num">Solicitudes</th>' +
        '<th class="num">Obras</th><th class="num">Facturado</th></tr></thead><tbody>' +
        d.items.map(function (f) {
          var pct = t.facturado ? Math.round(f.facturado / t.facturado * 100) : 0;
          var vacio = !f.clientes && !f.solicitudes && !f.obras && !f.facturado;
          return "<tr" + (vacio ? ' style="opacity:.45"' : "") + "><td><b>" + esc(f.origen) + "</b>" +
            (f.facturado ? '<div style="height:4px;border-radius:2px;background:var(--amber);width:' +
              Math.max(4, pct) + '%;margin-top:6px"></div>' : "") + "</td>" +
            '<td class="num">' + f.clientes + "</td>" +
            '<td class="num">' + f.solicitudes + "</td>" +
            '<td class="num">' + f.obras + "</td>" +
            '<td class="num"><b>' + eur(f.facturado) + "</b>" +
            (f.facturado ? '<div style="font-size:.76rem;color:var(--muted)">' + pct + "%</div>" : "") +
            "</td></tr>";
        }).join("") + "</tbody></table></div>";
    }

    h += '<p style="color:var(--muted-2);font-size:.83rem;margin-top:14px">' +
      "Cada cosa cuenta en el periodo en que se dio de alta, y el facturado va sin IVA. " +
      "El canal se apunta en la ficha del cliente, y las solicitudes de la web lo traen " +
      "puesto si la persona lo dice. Los canales se cambian en Clientes › Orígenes.</p></div>";

    $("#vista").innerHTML = h;
  }).catch(error);
}

/* ── Agenda ───────────────────────────────────────────────────────────── */
// Estado de la vista. Se conserva al volver de guardar una cita, para no
// saltar al mes actual cada vez que se toca algo.
var AG = { mes: null, vista: null, pro: "", citas: [] };
var AG_DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"];
var AG_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

function dos(n) { return (n < 10 ? "0" : "") + n; }
function isoDia(d) { return d.getFullYear() + "-" + dos(d.getMonth() + 1) + "-" + dos(d.getDate()); }
function horaDe(s) { return String(s || "").slice(11, 16); }
function diaLargo(iso) {
  var p = iso.split("-");
  return new Date(+p[0], +p[1] - 1, +p[2]).toLocaleDateString("es-ES",
    { weekday: "long", day: "numeric", month: "long" });
}

function nuevaCita(dia) {
  abrirFormulario("agenda", null, {
    inicio: dia + "T09:00", fin: dia + "T10:00", tipo: "visita", estado: "pendiente",
    profesional_id: AG.pro ? Number(AG.pro) : (YO && YO.profesional_id) || null
  });
}

function abrirCita(id) {
  var c = AG.citas.filter(function (x) { return String(x.id) === String(id); })[0];
  if (c) abrirFormulario("agenda", c);
}

// Fechas "AAAA-MM-DDTHH:MM" en hora local. Se leen a mano y no con
// new Date(texto): así no hay dudas de si el navegador lo toma como UTC.
function leerLocal(s) {
  s = String(s || "");
  if (s.length < 16) return null;
  var f = s.slice(0, 10).split("-"), h = s.slice(11, 16).split(":");
  var d = new Date(+f[0], +f[1] - 1, +f[2], +h[0], +h[1]);
  return isNaN(d.getTime()) ? null : d;
}
function escribirLocal(d) { return isoDia(d) + "T" + dos(d.getHours()) + ":" + dos(d.getMinutes()); }
function fechaHora(s) {
  var d = leerLocal(s);
  return d ? d.getDate() + " " + AG_MESES[d.getMonth()].slice(0, 3) + " " + horaDe(s) : "";
}

/* Días que ocupa una cita, del de inicio al de fin. Una que acaba justo a
   las 00:00 no ocupa el día siguiente. */
function diasDeCita(c) {
  var ini = leerLocal(c.inicio), fin = leerLocal(c.fin_efectivo) || ini;
  var ultimo = new Date(fin.getTime());
  if (fin > ini && fin.getHours() === 0 && fin.getMinutes() === 0) ultimo.setDate(ultimo.getDate() - 1);
  var dias = [], d = new Date(ini.getFullYear(), ini.getMonth(), ini.getDate());
  var tope = new Date(ultimo.getFullYear(), ultimo.getMonth(), ultimo.getDate());
  while (d <= tope) { dias.push(isoDia(d)); d.setDate(d.getDate() + 1); }
  return dias;
}

var CLASE_TIPO = { "visita": "visita", "presupuesto": "presupuesto", "obra": "obra",
                   "revisión": "revision", "otro": "otro" };
function claseTipo(t) { return "tipo-" + (CLASE_TIPO[t] || "otro"); }
function nombreTipo(t) { t = String(t || "otro"); return t.charAt(0).toUpperCase() + t.slice(1); }

function textoCita(c, varios) {
  var rango = varios ? fechaHora(c.inicio) + " → " + fechaHora(c.fin_efectivo)
                     : horaDe(c.inicio) + "–" + horaDe(c.fin_efectivo);
  return nombreTipo(c.tipo) + ": " + c.titulo + " · " + rango +
    (c.cliente ? " · " + c.cliente : "") + (c.profesional ? " (" + c.profesional + ")" : "") +
    (c.estado !== "pendiente" ? " · " + c.estado : "") +
    (c.estado === "cancelada" && c.cancelada_por ? " (la cancela el " + c.cancelada_por + ")" : "") +
    (c.motivo_cancelacion ? ": " + c.motivo_cancelacion : "") +
    (c.solapa ? ". ¡Este profesional tiene otra cita a la vez!" : "");
}
function clasesCita(c) {
  return claseTipo(c.tipo) + " ag-est--" + esc(c.estado) + (c.solapa ? " ag-cita--solapa" : "");
}
function etiquetaCita(c) {
  return (c.estado === "hecha" ? "✓ " : "") + "<b>" + esc(horaDe(c.inicio)) + "</b> " + esc(c.titulo);
}

/* Cita de un solo día: una ficha dentro de la celda. */
function chipCita(c) {
  return '<button type="button" class="ag-cita ' + clasesCita(c) + '" data-cita="' + c.id +
    '" title="' + esc(textoCita(c, false)) + '">' + etiquetaCita(c) + "</button>";
}

/* El mes se pinta por semanas. Las citas de varios días NO van dentro de las
   celdas: son una barra por semana, pintada encima de la fila y con fondo
   opaco, así que se ve como una línea seguida sin que la corten los bordes de
   los días. Cada barra ocupa un carril (una altura) y las celdas dejan ese
   hueco arriba para que las fichas de un solo día queden debajo. */
function pintarMes(desde, hasta, primero, citas) {
  var hoy = isoDia(new Date()), inicioRejilla = isoDia(desde);
  var barras = [], porDia = {};
  citas.forEach(function (c) {
    var dias = diasDeCita(c);
    if (dias.length > 1) barras.push({ c: c, dias: dias });
    else (porDia[dias[0]] = porDia[dias[0]] || []).push(c);
  });
  var h = '<div class="ag-mesgrid"><div class="ag-cab">' +
    AG_DIAS.map(function (d) { return "<div>" + d + "</div>"; }).join("") + '</div><div class="ag-dias">';
  var d = new Date(desde);
  while (d <= hasta) {
    var semana = [];
    for (var i = 0; i < 7; i++) { semana.push(isoDia(d)); d.setDate(d.getDate() + 1); }

    // Trozo de cada cita de varios días que cae en esta semana
    var trozos = [];
    barras.forEach(function (b) {
      var cols = [];
      semana.forEach(function (k, col) { if (b.dias.indexOf(k) >= 0) cols.push(col); });
      if (!cols.length) return;
      var a = cols[0], z = cols[cols.length - 1];
      var empieza = b.dias[0] === semana[a];
      trozos.push({
        c: b.c, a: a, z: z, empieza: empieza,
        acaba: b.dias[b.dias.length - 1] === semana[z],
        // El título va una sola vez: el día que empieza o, si empezó antes de
        // lo que se ve, en el primer día visible para que no quede sin nombre.
        titulo: empieza || (semana[a] === inicioRejilla && b.dias[0] < inicioRejilla)
      });
    });
    // Carriles: cada barra en la primera altura libre; antes las que empiezan
    // antes y, a igualdad, las más largas.
    trozos.sort(function (x, y) { return x.a - y.a || (y.z - y.a) - (x.z - x.a) || x.c.id - y.c.id; });
    var carriles = [];
    trozos.forEach(function (s) {
      var n = 0;
      while (carriles[n] !== undefined && carriles[n] >= s.a) n++;
      carriles[n] = s.z;
      s.carril = n;
    });

    h += '<div class="ag-semana" style="--carriles:' + carriles.length + '">';
    semana.forEach(function (k) {
      var dd = leerLocal(k + "T00:00");
      var fichas = (porDia[k] || []).sort(function (x, y) {
        return x.inicio < y.inicio ? -1 : x.inicio > y.inicio ? 1 : x.id - y.id;
      });
      h += '<div class="ag-dia' + (dd.getMonth() !== primero.getMonth() ? " ag-dia--fuera" : "") +
        (k === hoy ? " ag-dia--hoy" : "") + '" data-dia="' + k + '">' +
        '<span class="ag-num">' + dd.getDate() + "</span>" + fichas.map(chipCita).join("") + "</div>";
    });
    trozos.forEach(function (s) {
      h += '<button type="button" class="ag-barra-cita ' + clasesCita(s.c) +
        (s.empieza ? "" : " ag-barra-cita--viene") + (s.acaba ? "" : " ag-barra-cita--sigue") +
        '" style="--col:' + s.a + ";--span:" + (s.z - s.a + 1) + ";--carril:" + s.carril +
        ";--mi:" + (s.empieza ? "3px" : "0px") + ";--md:" + (s.acaba ? "3px" : "0px") + '"' +
        ' data-cita="' + s.c.id + '" title="' + esc(textoCita(s.c, true)) + '">' +
        (s.titulo ? etiquetaCita(s.c) : "") + "</button>";
    });
    h += "</div>";
  }
  return h + "</div></div>";
}

function leyendaTipos() {
  return '<div class="ag-leyenda">' + TIPOS_CITA.map(function (t) {
    return '<span class="' + claseTipo(t) + '">' + esc(nombreTipo(t)) + "</span>";
  }).join("") + "</div>";
}

function pintarLista(primero, citas) {
  var mes = isoDia(primero).slice(0, 7), inicioMes = isoDia(primero);
  // Entra toda cita que ocupe algún día del mes; la que empezó el mes
  // anterior se agrupa en el día 1.
  var clave = function (c) { var k = c.inicio.slice(0, 10); return k < inicioMes ? inicioMes : k; };
  var delMes = citas.filter(function (c) {
    return diasDeCita(c).some(function (k) { return k.slice(0, 7) === mes; });
  }).sort(function (a, b) {
    var ka = clave(a), kb = clave(b);
    if (ka !== kb) return ka < kb ? -1 : 1;
    return a.inicio < b.inicio ? -1 : a.inicio > b.inicio ? 1 : a.id - b.id;
  });
  if (!delMes.length) {
    return '<div class="tabla-caja"><div class="vacia">No hay citas este mes. ' +
      "Pulsa «Nueva cita» para crear la primera.</div></div>";
  }
  var h = '<div class="ag-lista">', dia = "";
  delMes.forEach(function (c) {
    var k = clave(c);
    if (k !== dia) {
      if (dia) h += "</div>";
      dia = k;
      h += '<div class="ag-grupo"><h3>' + esc(diaLargo(k)) + "</h3>";
    }
    var varios = diasDeCita(c).length > 1;
    var horas = varios ? fechaHora(c.inicio) + " → " + fechaHora(c.fin_efectivo)
                       : horaDe(c.inicio) + "–" + horaDe(c.fin_efectivo);
    var detalle = c.estado === "cancelada"
      ? "Cancelada" + (c.cancelada_por ? " por el " + c.cancelada_por : "") +
        (c.motivo_cancelacion ? ": " + c.motivo_cancelacion : "")
      : [nombreTipo(c.tipo), c.cliente, c.profesional, c.direccion_efectiva].filter(Boolean).join(" · ");
    var clase = c.estado === "hecha" ? " tag--verde" : c.estado === "cancelada" ? " tag--rojo" : " tag--amber";
    h += '<button type="button" class="ag-item ' + claseTipo(c.tipo) + ' ag-item--' + esc(c.estado) +
      '" data-cita="' + c.id + '">' +
      '<span class="ag-hora' + (varios ? " ag-hora--varios" : "") + '">' + esc(horas) + "</span>" +
      '<span class="ag-txt"><b>' + esc(c.titulo) + "</b>" +
      (detalle ? "<small>" + esc(detalle) + "</small>" : "") +
      (c.solapa ? '<small class="ag-solapa">Este profesional tiene otra cita a la vez</small>' : "") +
      "</span>" + '<span class="tag' + clase + '">' + esc(c.estado) + "</span></button>";
  });
  return h + "</div></div>";
}

function verAgenda() {
  var hoy = new Date();
  if (!AG.mes) AG.mes = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
  if (!AG.vista) AG.vista = window.innerWidth < 760 ? "lista" : "mes";

  $("#vista-acciones").innerHTML =
    '<button class="btn btn--fant" id="ag-sync">' + svg(ico.sincro) + "Google Calendar</button>" +
    '<button class="btn btn--amber" id="ag-nueva">' + svg(ico.mas) + "Nueva cita</button>";
  $("#ag-nueva").addEventListener("click", function () { nuevaCita(isoDia(new Date())); });
  $("#ag-sync").addEventListener("click", verSuscripcion);

  // La rejilla va de lunes a domingo: empieza el lunes de la semana del día 1
  // y acaba el domingo de la semana del último día del mes.
  var primero = AG.mes;
  var desde = new Date(primero);
  desde.setDate(1 - ((primero.getDay() + 6) % 7));
  var ultimo = new Date(primero.getFullYear(), primero.getMonth() + 1, 0);
  var hasta = new Date(ultimo);
  hasta.setDate(ultimo.getDate() + (6 - ((ultimo.getDay() + 6) % 7)));

  Promise.all([api("/api/admin/agenda?desde=" + isoDia(desde) + "&hasta=" + isoDia(hasta)),
               cargarRef("profesionales")])
    .then(function (res) {
      AG.citas = res[0];
      var citas = AG.citas.filter(function (c) { return !AG.pro || String(c.profesional_id) === AG.pro; });
      var h = '<div class="ag-barra"><div class="ag-nav">' +
        '<button class="btn btn--fant btn--sm" id="ag-prev" aria-label="Mes anterior">‹</button>' +
        '<button class="btn btn--fant btn--sm" id="ag-hoy">Hoy</button>' +
        '<button class="btn btn--fant btn--sm" id="ag-sig" aria-label="Mes siguiente">›</button>' +
        '<h2 class="ag-mes">' + AG_MESES[primero.getMonth()] + " " + primero.getFullYear() + "</h2></div>" +
        '<div class="ag-filtros"><select id="ag-pro" aria-label="Profesional">' +
        '<option value="">Todos los profesionales</option>' +
        (cache.profesionales || []).map(function (p) {
          return '<option value="' + p.id + '"' + (String(p.id) === AG.pro ? " selected" : "") + ">" +
                 esc(p.nombre) + "</option>";
        }).join("") + "</select>" +
        '<div class="ag-vistas">' +
        '<button type="button" data-agvista="mes"' + (AG.vista === "mes" ? ' class="is-on"' : "") + ">Mes</button>" +
        '<button type="button" data-agvista="lista"' + (AG.vista === "lista" ? ' class="is-on"' : "") + ">Lista</button>" +
        "</div></div></div>";
      h += AG.vista === "mes" ? pintarMes(desde, hasta, primero, citas) : pintarLista(primero, citas);
      h += leyendaTipos();
      $("#vista").innerHTML = h;

      var v = $("#vista");
      $("#ag-prev").addEventListener("click", function () {
        AG.mes = new Date(primero.getFullYear(), primero.getMonth() - 1, 1); verAgenda();
      });
      $("#ag-sig").addEventListener("click", function () {
        AG.mes = new Date(primero.getFullYear(), primero.getMonth() + 1, 1); verAgenda();
      });
      $("#ag-hoy").addEventListener("click", function () { AG.mes = null; verAgenda(); });
      $("#ag-pro").addEventListener("change", function () { AG.pro = this.value; verAgenda(); });
      $$("[data-agvista]", v).forEach(function (b) {
        b.addEventListener("click", function () { AG.vista = b.dataset.agvista; verAgenda(); });
      });
      $$("[data-cita]", v).forEach(function (b) {
        b.addEventListener("click", function (e) { e.stopPropagation(); abrirCita(b.dataset.cita); });
      });
      // Al pasar por encima de una cita de varios días se iluminan todos sus
      // trozos, también los de las otras semanas.
      $$("[data-cita]", v).forEach(function (b) {
        var todos = function () { return $$('[data-cita="' + b.dataset.cita + '"]', v); };
        b.addEventListener("mouseenter", function () { todos().forEach(function (x) { x.classList.add("is-hover"); }); });
        b.addEventListener("mouseleave", function () { todos().forEach(function (x) { x.classList.remove("is-hover"); }); });
      });
      // Pinchar en un hueco del día abre una cita nueva ese día.
      $$("[data-dia]", v).forEach(function (celda) {
        celda.addEventListener("click", function () { nuevaCita(celda.dataset.dia); });
      });
    })
    .catch(error);
}

function verSuscripcion() {
  api("/api/admin/agenda/suscripcion").then(function (r) {
    modal("Ver la agenda en Google Calendar",
      '<p style="color:var(--muted);line-height:1.55">Añade este enlace <b>una sola vez</b> en ' +
      "Google Calendar y " + (r.completa ? "las citas del panel" : "<b>tus citas</b>") +
      " aparecerán solas, también en el móvil.</p>" +
      '<div class="ag-url"><input id="ag-url" readonly value="' + esc(r.url) + '">' +
      '<button class="btn btn--fant btn--sm" id="ag-copiar">Copiar</button></div>' +
      '<ol class="ag-pasos">' +
        "<li>Abre <b>Google Calendar en el ordenador</b> (calendar.google.com). Desde la app del móvil no se puede añadir por enlace.</li>" +
        "<li>En la columna de la izquierda, junto a <b>Otros calendarios</b>, pulsa <b>+</b> y elige <b>Desde URL</b>.</li>" +
        "<li>Pega el enlace y pulsa <b>Añadir calendario</b>. En poco rato lo verás también en el móvil.</li>" +
      "</ol>" +
      '<p style="color:var(--muted-2);font-size:.84rem;line-height:1.55">Va solo del panel a Google: las citas ' +
      "se crean y se cambian aquí. Google vuelve a leer el enlace cada varias horas, así que un cambio " +
      "puede tardar en verse allí. <b>El enlace da acceso a tu agenda</b>: no lo compartas. Si se filtra, " +
      "pulsa «Cambiar enlace» y el anterior deja de funcionar.</p>",
      '<button class="btn btn--fant" id="ag-renovar">Cambiar enlace</button>' +
      '<button class="btn btn--amber" id="ag-cerrar">Hecho</button>');
    $("#ag-cerrar").addEventListener("click", cerrarModal);
    $("#ag-copiar").addEventListener("click", function () {
      var inp = $("#ag-url");
      inp.select();
      var hecho = function () { avisar("Enlace copiado"); };
      if (navigator.clipboard) {
        navigator.clipboard.writeText(inp.value).then(hecho, function () { document.execCommand("copy"); hecho(); });
      } else { document.execCommand("copy"); hecho(); }
    });
    $("#ag-renovar").addEventListener("click", function () {
      // Primer clic avisa, el segundo cambia: cambiarlo rompe la suscripción
      // que ya esté puesta en Google.
      var b = this;
      if (!b.dataset.seguro) {
        b.dataset.seguro = "1";
        b.textContent = "¿Seguro? El enlace actual dejará de funcionar";
        b.className = "btn btn--peligro";
        return;
      }
      api("/api/admin/agenda/suscripcion/renovar", { metodo: "POST" }).then(function (n) {
        $("#ag-url").value = n.url;
        b.dataset.seguro = "";
        b.textContent = "Cambiar enlace";
        b.className = "btn btn--fant";
        avisar("Enlace nuevo creado. Tendrás que añadirlo otra vez en Google Calendar.");
      }).catch(function (e) { avisar(e.message, "err"); });
    });
  }).catch(function (e) { avisar(e.message, "err"); });
}

/* ── Estatutos: cómo funciona la empresa ──────────────────────────────── */
/* El texto se guarda en crudo y se pinta aquí. Se escapa SIEMPRE antes de
   reconocer el formato, así que lo que escriba el administrador no puede
   colar etiquetas en una página que lee todo el equipo. */
function negrita(t) {
  return esc(t).replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
}

function textoRico(txt) {
  var h = "", lista = false;
  String(txt || "").split(/\r?\n/).forEach(function (linea) {
    var t = linea.trim();
    var cerrar = function () { if (lista) { h += "</ul>"; lista = false; } };
    if (!t) { cerrar(); return; }
    if (t.indexOf("## ") === 0) { cerrar(); h += "<h4>" + negrita(t.slice(3)) + "</h4>"; return; }
    if (t.indexOf("- ") === 0) {
      if (!lista) { h += "<ul>"; lista = true; }
      h += "<li>" + negrita(t.slice(2)) + "</li>";
      return;
    }
    cerrar();
    h += "<p>" + negrita(t) + "</p>";
  });
  if (lista) h += "</ul>";
  return h;
}

function verEstatutos() {
  if (esAdmin()) {
    $("#vista-acciones").innerHTML =
      '<button class="btn btn--amber" id="btn-nuevo">' + svg(ico.mas) + "Nueva sección</button>";
    $("#btn-nuevo").addEventListener("click", function () { formSeccion(null); });
  }

  api("/api/admin/estatutos").then(function (secciones) {
    if (!secciones.length) {
      $("#vista").innerHTML = '<div class="tabla-caja"><div class="vacia">' +
        (esAdmin()
          ? "Aquí se escribe cómo funciona la empresa, para que todo el equipo lo tenga a mano: " +
            "cómo se atiende una solicitud, qué se mira en una visita, cómo se cobra una obra, " +
            "qué hacer ante una urgencia. Pulsa «Nueva sección» para empezar."
          : "Todavía no hay nada escrito. Cuando el administrador lo redacte, aparecerá aquí.") +
        "</div></div>";
      return;
    }
    var h = '<div class="estatutos">';
    secciones.forEach(function (s, i) {
      h += '<article class="tarjeta est"><div class="est__cab"><h3>' + esc(s.titulo) + "</h3>" +
        (esAdmin()
          ? '<div class="acciones">' +
            (i > 0 ? '<button data-sube="' + s.id + '" title="Subir">' + svg(ico.arriba) + "</button>" : "") +
            (i < secciones.length - 1 ? '<button data-baja="' + s.id + '" title="Bajar">' + svg(ico.abajo) + "</button>" : "") +
            '<button data-editar="' + s.id + '" title="Editar">' + svg(ico.lapiz) + "</button>" +
            '<button class="borrar" data-borrar="' + s.id + '" title="Borrar">' + svg(ico.papelera) + "</button>" +
            "</div>"
          : "") +
        "</div>" +
        '<div class="est__texto">' + textoRico(s.contenido) + "</div>" +
        (s.actualizado
          ? '<p class="est__pie">Actualizado ' + esc(hace(s.actualizado)) +
            (s.autor_nombre || s.autor_email ? " por " + esc(s.autor_nombre || s.autor_email) : "") + "</p>"
          : "") +
        "</article>";
    });
    $("#vista").innerHTML = h + "</div>";

    var buscar = function (id) { return secciones.filter(function (x) { return String(x.id) === String(id); })[0]; };
    $$("[data-editar]").forEach(function (b) {
      b.addEventListener("click", function () { formSeccion(buscar(b.dataset.editar)); });
    });
    var mover = function (b, hacia) {
      b.disabled = true;
      api("/api/admin/estatutos/" + b.dataset[hacia === "arriba" ? "sube" : "baja"] + "/mover?hacia=" + hacia,
          { metodo: "POST" })
        .then(function () { ir("estatutos"); })
        .catch(function (e) { b.disabled = false; avisar(e.message, "err"); });
    };
    $$("[data-sube]").forEach(function (b) { b.addEventListener("click", function () { mover(b, "arriba"); }); });
    $$("[data-baja]").forEach(function (b) { b.addEventListener("click", function () { mover(b, "abajo"); }); });
    $$("[data-borrar]").forEach(function (b) {
      b.addEventListener("click", function () {
        var s = buscar(b.dataset.borrar);
        modal("Borrar la sección",
          "<p style='color:var(--muted);line-height:1.55'>Se va a borrar <b>" + esc(s.titulo) +
          "</b> de los estatutos. No se puede deshacer.</p>",
          '<button class="btn btn--fant" id="b-no">Cancelar</button>' +
          '<button class="btn btn--peligro" id="b-si">Borrar</button>');
        $("#b-no").addEventListener("click", cerrarModal);
        $("#b-si").addEventListener("click", function () {
          api("/api/admin/estatutos/" + s.id, { metodo: "DELETE" })
            .then(function () { cerrarModal(); ir("estatutos"); })
            .catch(function (e) { cerrarModal(); avisar(e.message, "err"); });
        });
      });
    });
  }).catch(error);
}

function formSeccion(s) {
  var editando = !!s;
  s = s || { titulo: "", contenido: "" };
  modal(editando ? "Editar sección" : "Nueva sección",
    '<div class="aviso aviso--err" id="es-err" hidden></div>' +
    '<div class="campo"><label for="es-titulo">Título *</label>' +
    '<input id="es-titulo" value="' + esc(s.titulo) + '" placeholder="Cómo atendemos una solicitud"></div>' +
    '<div class="campo"><label for="es-texto">Contenido</label>' +
    '<textarea id="es-texto" style="min-height:260px">' + esc(s.contenido) + "</textarea>" +
    '<small style="color:var(--muted-2);font-size:.79rem">Puedes usar <b>## </b> al principio de una ' +
    'línea para un subtítulo, <b>- </b> para viñetas y <b>**negrita**</b>.</small></div>',
    '<button class="btn btn--fant" id="es-cancelar">Cancelar</button>' +
    '<button class="btn btn--amber" id="es-guardar">Guardar</button>', true);

  $("#es-cancelar").addEventListener("click", cerrarModal);
  $("#es-titulo").focus();
  $("#es-guardar").addEventListener("click", function () {
    var datos = { titulo: $("#es-titulo").value.trim(), contenido: $("#es-texto").value };
    var err = $("#es-err"), btn = this;
    if (!datos.titulo) { err.textContent = "Ponle un título."; err.hidden = false; return; }
    btn.disabled = true; btn.textContent = "Guardando…";
    api("/api/admin/estatutos" + (editando ? "/" + s.id : ""),
        { metodo: editando ? "PUT" : "POST", datos: datos })
      .then(function () { cerrarModal(); ir("estatutos"); })
      .catch(function (e) {
        err.textContent = e.message; err.hidden = false;
        btn.disabled = false; btn.textContent = "Guardar";
      });
  });
}

/* ── Equipo: quién entra al panel y a qué ─────────────────────────────── */
// Módulos que se pueden dar a un miembro, en el orden del menú.
var MODULOS_EQUIPO = ["agenda", "solicitudes", "visitas", "obras", "notas", "clientes", "profesionales",
  "presupuestos", "proformas", "facturas", "costes", "contabilidad", "stock", "proveedores"];

function verMiembros() {
  $("#vista-acciones").innerHTML =
    '<button class="btn btn--amber" id="btn-nuevo">' + svg(ico.mas) + "Nuevo miembro</button>";
  $("#btn-nuevo").addEventListener("click", function () { formMiembro(null); });

  Promise.all([api("/api/admin/equipo"), cargarRef("profesionales")]).then(function (res) {
    var gente = res[0];
    var h = '<div class="tabla-caja"><div class="tabla-scroll"><table><thead><tr>' +
      "<th>Persona</th><th>Rol</th><th>Estado</th><th>Profesional</th><th>Puede entrar en</th>" +
      '<th>Último acceso</th><th class="num">Acciones</th></tr></thead><tbody>';
    gente.forEach(function (p) {
      var estado = p.estado === "activo" ? '<span class="tag tag--verde">Activo</span>'
        : p.estado === "invitado" ? '<span class="tag tag--amber">Invitación pendiente</span>'
        : '<span class="tag tag--rojo">De baja</span>';
      var accesos = p.rol === "admin" ? '<span style="color:var(--muted)">Todo</span>'
        : p.permisos.length ? p.permisos.map(function (k) {
            return '<span class="tag" style="margin:0 4px 4px 0">' + esc(MODULOS[k] ? MODULOS[k].titulo : k) + "</span>";
          }).join("")
        : '<span style="color:var(--muted-2)">Solo su panel</span>';
      h += "<tr><td><b>" + esc(p.nombre) + '</b><div style="font-size:.8rem;color:var(--muted)">' +
             esc(p.email) + "</div></td>" +
           '<td><span class="tag ' + (p.rol === "admin" ? "tag--azul" : "") + '">' +
             (p.rol === "admin" ? "Administrador" : "Miembro") + "</span></td>" +
           "<td>" + estado + "</td>" +
           "<td>" + (esc(p.profesional) || "—") + "</td>" +
           "<td>" + accesos + "</td>" +
           '<td style="font-size:.84rem;color:var(--muted)">' + (p.ultimo_acceso ? esc(hace(p.ultimo_acceso)) : "Nunca") + "</td>" +
           '<td class="acciones">' +
           (p.estado === "invitado"
             ? '<button data-invitar="' + p.id + '" title="Reenviar la invitación">' + svg(ico.buzon) + "</button>" : "") +
           '<button data-editar="' + p.id + '" title="Editar">' + svg(ico.lapiz) + "</button>" +
           (p.id !== YO.id
             ? '<button class="borrar" data-borrar="' + p.id + '" title="Quitar del equipo">' + svg(ico.papelera) + "</button>" : "") +
           "</td></tr>";
    });
    $("#vista").innerHTML = h + "</tbody></table></div></div>" +
      '<p style="color:var(--muted-2);font-size:.84rem;line-height:1.55;margin-top:14px">Cada miembro entra solo en las ' +
      "pestañas que le marques y en ellas ve solo lo que lleva él: sus citas, clientes, obras, presupuestos, facturas, " +
      "gastos y las solicitudes que le repartas. Almacén, proveedores y profesionales son de la empresa: quien los " +
      "tenga los ve enteros. Tú, como administrador, lo ves todo.</p>";

    var buscar = function (id) { return gente.filter(function (x) { return String(x.id) === String(id); })[0]; };
    $$("[data-editar]").forEach(function (b) {
      b.addEventListener("click", function () { formMiembro(buscar(b.dataset.editar)); });
    });
    $$("[data-invitar]").forEach(function (b) {
      b.addEventListener("click", function () {
        b.disabled = true;
        api("/api/admin/equipo/" + b.dataset.invitar + "/invitar", { metodo: "POST" })
          .then(function (r) { resultadoInvitacion(buscar(b.dataset.invitar), r); })
          .catch(function (e) { avisar(e.message, "err"); })
          .finally(function () { b.disabled = false; });
      });
    });
    $$("[data-borrar]").forEach(function (b) {
      b.addEventListener("click", function () {
        var p = buscar(b.dataset.borrar);
        modal("Quitar del equipo",
          "<p style='color:var(--muted);line-height:1.55'>Se va a quitar a <b>" + esc(p.nombre) + "</b> del panel " +
          "y no podrá volver a entrar.<br>Lo que lleva (clientes, obras, facturas…) <b>no se borra</b>: pasa a ser " +
          "tuyo y desde ahí se lo puedes dar a otra persona.</p>" +
          "<p style='color:var(--muted-2);font-size:.86rem'>Si solo quieres cortarle el acceso un tiempo, " +
          "edítalo y ponlo de baja.</p>",
          '<button class="btn btn--fant" id="b-no">Cancelar</button>' +
          '<button class="btn btn--peligro" id="b-si">Quitar del equipo</button>');
        $("#b-no").addEventListener("click", cerrarModal);
        $("#b-si").addEventListener("click", function () {
          api("/api/admin/equipo/" + p.id, { metodo: "DELETE" })
            .then(function () { invalidar(); cerrarModal(); avisar(p.nombre + " ya no está en el equipo"); ir("equipo"); })
            .catch(function (e) { cerrarModal(); avisar(e.message, "err"); });
        });
      });
    });
  }).catch(error);
}

function resultadoInvitacion(p, r) {
  if (r.enviado) { avisar("Invitación enviada a " + p.email); return; }
  // Si el correo no sale, el enlace se enseña para pasárselo por otra vía.
  modal("No se ha podido enviar el correo",
    '<p style="color:var(--muted);line-height:1.55">Pásale este enlace a <b>' + esc(p.nombre) +
    "</b> por WhatsApp o como prefieras. Con él crea su contraseña; sirve una sola vez y caduca en 7 días.</p>" +
    '<div class="ag-url"><input id="inv-url" readonly value="' + esc(r.enlace) + '">' +
    '<button class="btn btn--fant btn--sm" id="inv-copiar">Copiar</button></div>',
    '<button class="btn btn--amber" id="inv-ok">Hecho</button>');
  $("#inv-ok").addEventListener("click", cerrarModal);
  $("#inv-copiar").addEventListener("click", function () {
    var inp = $("#inv-url");
    inp.select();
    var hecho = function () { avisar("Enlace copiado"); };
    if (navigator.clipboard) {
      navigator.clipboard.writeText(inp.value).then(hecho, function () { document.execCommand("copy"); hecho(); });
    } else { document.execCommand("copy"); hecho(); }
  });
}

function formMiembro(p) {
  var editando = !!p, esYo = editando && p.id === YO.id;
  p = p || { nombre: "", email: "", rol: "miembro", permisos: [], profesional_id: null, activo: true };
  var pros = cache.profesionales || [];
  var ayuda = function (t) { return '<small style="color:var(--muted-2);font-size:.79rem">' + t + "</small>"; };
  var cuerpo = '<div class="aviso aviso--err" id="m-err" hidden></div>' +
    '<div class="rejilla-2">' +
      '<div class="campo"><label for="m-nombre">Nombre *</label><input id="m-nombre" value="' + esc(p.nombre) + '"></div>' +
      '<div class="campo"><label for="m-email">Correo *</label><input id="m-email" type="email" value="' + esc(p.email) + '">' +
        (esYo ? ayuda("Es tu usuario para entrar. Si lo cambias, tendrás que volver a entrar con el nuevo.")
              : editando ? "" : ayuda("Ahí le llegará la invitación para crear su contraseña.")) +
      "</div>" +
    "</div>" +
    '<div class="rejilla-2">' +
      '<div class="campo"><label for="m-rol">Rol</label><select id="m-rol"' + (esYo ? " disabled" : "") + ">" +
        '<option value="miembro"' + (p.rol !== "admin" ? " selected" : "") + ">Miembro: solo lo suyo</option>" +
        '<option value="admin"' + (p.rol === "admin" ? " selected" : "") + ">Administrador: lo ve todo</option>" +
      "</select></div>" +
      '<div class="campo"><label for="m-pro">Ficha de profesional</label><select id="m-pro">' +
        '<option value="">— ninguna —</option>' +
        pros.map(function (x) {
          return '<option value="' + x.id + '"' + (String(x.id) === String(p.profesional_id) ? " selected" : "") + ">" +
                 esc(x.nombre) + " — " + esc(x.categoria) + "</option>";
        }).join("") +
      "</select>" + ayuda("Su agenda incluirá las citas donde figure como profesional.") + "</div>" +
    "</div>" +
    '<div class="campo" id="m-permisos-caja"><label>Puede entrar en</label>' +
      '<div class="multi" id="m-permisos">' + MODULOS_EQUIPO.map(function (k) {
        return '<label><input type="checkbox" value="' + k + '"' + (p.permisos.indexOf(k) >= 0 ? " checked" : "") + ">" +
               esc(MODULOS[k].titulo) + "</label>";
      }).join("") + "</div>" +
      ayuda("El Panel lo tiene siempre, con sus propios números. En cada pestaña verá solo lo que lleva él.") +
    "</div>" +
    '<p id="m-admin-nota" style="color:var(--muted);font-size:.88rem;margin:4px 0 12px" hidden>' +
      "El administrador entra en todo y lo ve todo, también Equipo.</p>" +
    (editando && !esYo
      ? '<div class="campo"><label for="m-activo">Acceso</label><select id="m-activo">' +
        '<option value="1"' + (p.activo ? " selected" : "") + ">Activo</option>" +
        '<option value="0"' + (!p.activo ? " selected" : "") + ">De baja: no puede entrar</option></select></div>"
      : "");

  modal(editando ? "Editar a " + p.nombre : "Nuevo miembro del equipo", cuerpo,
    '<button class="btn btn--fant" id="m-cancelar">Cancelar</button>' +
    '<button class="btn btn--amber" id="m-guardar">' + (editando ? "Guardar" : "Invitar") + "</button>", true);

  function pintarRol() {
    var admin = $("#m-rol").value === "admin";
    // style y no hidden: .campo lleva display:grid y taparía el atributo.
    $("#m-permisos-caja").style.display = admin ? "none" : "";
    $("#m-admin-nota").hidden = !admin;
  }
  pintarRol();
  $("#m-rol").addEventListener("change", pintarRol);
  $("#m-cancelar").addEventListener("click", cerrarModal);
  $("#m-guardar").addEventListener("click", function () {
    var err = $("#m-err"), btn = this;
    var datos = {
      nombre: $("#m-nombre").value.trim(),
      email: $("#m-email").value.trim(),
      rol: $("#m-rol").value,
      profesional_id: $("#m-pro").value ? Number($("#m-pro").value) : null,
      permisos: $$("#m-permisos input:checked").map(function (i) { return i.value; }),
      activo: $("#m-activo") ? $("#m-activo").value === "1" : true
    };
    if (!datos.nombre || !datos.email) { err.textContent = "Falta el nombre o el correo."; err.hidden = false; return; }
    var cambiaMiCorreo = esYo && datos.email.toLowerCase() !== String(p.email).toLowerCase();
    btn.disabled = true; btn.textContent = editando ? "Guardando…" : "Invitando…";
    api("/api/admin/equipo" + (editando ? "/" + p.id : ""), { metodo: editando ? "PUT" : "POST", datos: datos })
      .then(function (r) {
        invalidar(); cerrarModal();
        // Cambiar el propio correo cierra la sesión en el servidor.
        if (cambiaMiCorreo) { salir(true); avisoAcceso("Correo cambiado. Entra con el nuevo.", "ok"); return; }
        if (editando) avisar("Guardado");
        else resultadoInvitacion(r.miembro, r);
        ir("equipo");
      })
      .catch(function (e) {
        err.textContent = e.message; err.hidden = false;
        btn.disabled = false; btn.textContent = editando ? "Guardar" : "Invitar";
      });
  });
}

/* ── Campanita de notificaciones ──────────────────────────────────────── */
var avisosPend = { total: 0, items: [] };

/* "hace 5 min", "hace 2 h", "ayer"... Las fechas de SQLite van en UTC y sin
   zona; sin la Z el navegador las leería como hora local y saldrían dos
   horas desplazadas. */
function hace(s) {
  if (!s) return "";
  s = String(s);
  if (s.length <= 10) return fecha(s);
  var min = Math.round((Date.now() - new Date(s.replace(" ", "T") + "Z").getTime()) / 60000);
  if (isNaN(min)) return fecha(s);
  if (min < 1) return "ahora mismo";
  if (min < 60) return "hace " + min + " min";
  var h = Math.round(min / 60);
  if (h < 24) return "hace " + h + " h";
  var d = Math.round(h / 24);
  if (d === 1) return "ayer";
  if (d < 7) return "hace " + d + " días";
  return fecha(s);
}

function actualizarCampana() {
  if (!token) return;
  api("/api/admin/notificaciones").then(function (n) {
    avisosPend = n;
    var num = $("#campana-num");
    num.textContent = n.total > 99 ? "99+" : String(n.total);
    num.hidden = !n.total;
    $("#campana-btn").setAttribute("aria-label", n.total
      ? n.total + (n.total === 1 ? " notificación pendiente" : " notificaciones pendientes")
      : "Sin notificaciones pendientes");
    // El número también en la pestaña del navegador, para verlo sin tener
    // el panel delante.
    document.title = (n.total ? "(" + n.total + ") " : "") + "Panel de gestión · Loureiro Soluciones";
    if (!$("#campana-panel").hidden) pintarCampana();
  }).catch(function () {});
}

function pintarCampana() {
  var n = avisosPend, p = $("#campana-panel");
  p.innerHTML =
    '<div class="campana__cab">Pendiente de atender' +
      (n.total ? " <span>" + n.total + "</span>" : "") + "</div>" +
    (n.items.length
      ? n.items.map(function (it) {
          return '<button type="button" class="campana__item" data-noti="' + it.id +
                 '" data-tipo="' + esc(it.tipo) + '">' +
                 "<b>" + esc(it.titulo) + "</b><span>" + esc(it.detalle) + " · " +
                 esc(hace(it.fecha)) + "</span></button>";
        }).join("")
      : '<div class="campana__vacio">Todo atendido. No hay nada pendiente.</div>') +
    ((n.total > n.items.length) && puedeVer("solicitudes")
      ? '<button type="button" class="campana__todas">Ver todas las solicitudes</button>'
      : "");

  // Pinchar un aviso lleva a lo que avisa y lo abre: la solicitud con su
  // mensaje, o el presupuesto que lleva días sin respuesta.
  $$("[data-noti]", p).forEach(function (b) {
    b.addEventListener("click", function () {
      var id = b.dataset.noti;
      cerrarCampana();
      if (b.dataset.tipo === "presupuesto") {
        ir("presupuestos");
        return editarDocumento("presupuestos", id);
      }
      ir("solicitudes");
      api("/api/admin/solicitudes").then(function (lista) {
        var f = lista.filter(function (x) { return String(x.id) === id; })[0];
        if (f) abrirFormulario("solicitudes", f);
      }).catch(error);
    });
  });
  var todas = p.querySelector(".campana__todas");
  if (todas) todas.addEventListener("click", function () { cerrarCampana(); ir("solicitudes"); });
}

function abrirCampana() {
  pintarCampana();
  $("#campana-panel").hidden = false;
  $("#campana-btn").setAttribute("aria-expanded", "true");
  actualizarCampana();
}
function cerrarCampana() {
  $("#campana-panel").hidden = true;
  $("#campana-btn").setAttribute("aria-expanded", "false");
}

$("#campana-btn").addEventListener("click", function (e) {
  e.stopPropagation();
  if ($("#campana-panel").hidden) abrirCampana(); else cerrarCampana();
});
document.addEventListener("click", function (e) {
  if (!$("#campana-panel").hidden && !$("#campana").contains(e.target)) cerrarCampana();
});
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") cerrarCampana();
});
document.addEventListener("visibilitychange", function () {
  if (!document.hidden) actualizarCampana();
});

/* ── Arranque ─────────────────────────────────────────────────────────── */
var relojCampana = null;
function arrancar(desdeLogin) {
  $("#login").hidden = true;
  $("#app").hidden = false;
  $("#sesion-email").textContent = YO
    ? (YO.nombre || YO.email) + (esAdmin() ? " · administrador" : "")
    : guardado("loureiro_email");
  invalidar();
  cargarEnlaceResenas();
  // Al entrar con la contraseña se abre siempre el Panel, aunque la URL traiga
  // la vista de la sesión anterior. Al recargar con la sesión viva sí se
  // respeta la vista en la que estabas.
  var inicial = location.hash.replace("#", "");
  ir(!desdeLogin && MODULOS[inicial] ? inicial : "dashboard");
  // La campanita se refresca al cambiar de vista (lo hace ir()), cada minuto
  // y al volver a la pestaña.
  if (!relojCampana) relojCampana = setInterval(actualizarCampana, 60000);
}

$("#btn-menu").addEventListener("click", function () { $("#lat").classList.toggle("is-open"); });

if (abrirEnlaceClave()) {
  // Viene de un correo de invitación o de recuperación: primero eso.
} else if (token) {
  api("/api/admin/yo").then(function (u) { YO = u; arrancar(false); }).catch(function () { salir(true); });
} else {
  api("/api/admin/estado").then(function (e) {
    if (!e.configurado) {
      var a = $("#login-aviso");
      a.className = "aviso aviso--err";
      a.textContent = "El panel aún no tiene contraseña configurada. Ejecuta scripts/set-admin-password.py en el servidor.";
      a.hidden = false;
    }
  }).catch(function () {});
}
})();
