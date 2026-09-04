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
  equipo:'<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
};
function svg(d, cls) {
  return '<svg viewBox="0 0 24 24" ' + (cls ? 'class="' + cls + '" ' : "") + 'aria-hidden="true">' + d + "</svg>";
}

/* ── Cliente de API ───────────────────────────────────────────────────── */
var token = localStorage.getItem("loureiro_token") || "";

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
loginForm.addEventListener("submit", function (e) {
  e.preventDefault();
  var aviso = $("#login-aviso"), btn = $("#li-btn");
  aviso.hidden = true;
  btn.disabled = true; btn.textContent = "Entrando…";

  api("/api/admin/login", {
    metodo: "POST",
    datos: { email: $("#li-email").value.trim(), password: $("#li-pass").value }
  }).then(function (r) {
    token = r.token;
    localStorage.setItem("loureiro_token", token);
    localStorage.setItem("loureiro_email", r.email);
    arrancar();
  }).catch(function (err) {
    aviso.textContent = err.message;
    aviso.hidden = false;
  }).finally(function () {
    btn.disabled = false; btn.textContent = "Entrar";
    $("#li-pass").value = "";
  });
});

function salir(silencioso) {
  var t = token;
  token = "";
  localStorage.removeItem("loureiro_token");
  localStorage.removeItem("loureiro_email");
  if (!silencioso && t) {
    fetch(API + "/api/admin/logout", { method: "POST", headers: { Authorization: "Bearer " + t } }).catch(function(){});
  }
  $("#app").hidden = true;
  $("#login").hidden = false;
}
$("#btn-salir").addEventListener("click", function () { salir(false); });

/* ── Definición de los módulos ────────────────────────────────────────── */
var CATEGORIAS_PRO = ["Electricista", "Albañil", "Fontanero", "Pintor", "Carpintero",
  "Climatización", "Instalador de pellets", "Limpieza", "Yesero", "Soldador",
  "Cristalero", "Cerrajero", "Jardinero", "Otro"];

var ESTADOS_OBRA = ["presupuesto", "en curso", "pausada", "terminada", "cancelada"];
var ESTADOS_SOL  = ["nueva", "contactada", "presupuestada", "ganada", "perdida"];
var CAT_COSTE    = ["material", "mano de obra", "maquinaria", "residuos", "subcontrata", "otros"];

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

  solicitudes: {
    titulo: "Solicitudes", sub: "Peticiones llegadas desde la web", icono: ico.buzon,
    recurso: "solicitudes",
    columnas: [
      { c: "nombre", t: "Nombre" },
      { c: "servicio", t: "Servicio" },
      { c: "telefono", t: "Teléfono" },
      { c: "email", t: "Email" },
      { c: "estado", t: "Estado", tipo: "tag" },
      { c: "creado", t: "Recibida", tipo: "fecha" }
    ],
    campos: [
      { c: "nombre", t: "Nombre", req: true },
      { c: "email", t: "Email", tipo: "email", mitad: true },
      { c: "telefono", t: "Teléfono", mitad: true },
      { c: "servicio", t: "Servicio", mitad: true },
      { c: "estado", t: "Estado", tipo: "select", ops: ESTADOS_SOL, mitad: true },
      { c: "mensaje", t: "Mensaje", tipo: "area" },
      { c: "notas", t: "Notas internas", tipo: "area" }
    ]
  },

  clientes: {
    titulo: "Clientes", sub: "Quién te contrata", icono: ico.gente, recurso: "clientes",
    columnas: [
      { c: "nombre", t: "Nombre" }, { c: "nif", t: "NIF" },
      { c: "telefono", t: "Teléfono" }, { c: "email", t: "Email" },
      { c: "ciudad", t: "Ciudad" }, { c: "provincia", t: "Provincia" }
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
    campos: [
      { c: "titulo", t: "Título de la obra", req: true },
      { c: "codigo", t: "Código", mitad: true, ayuda: "Referencia interna, p. ej. OB-2026-014" },
      { c: "estado", t: "Estado", tipo: "select", ops: ESTADOS_OBRA, mitad: true },
      { c: "cliente_id", t: "Cliente", tipo: "ref", de: "clientes", mitad: true },
      { c: "direccion", t: "Dirección" },
      { c: "cp", t: "Código postal", mitad: true },
      { c: "provincia", t: "Provincia", tipo: "provincia", mitad: true },
      { c: "ciudad", t: "Ciudad", tipo: "ciudad" },
      { c: "importe_venta", t: "Importe presupuestado al cliente (€)", tipo: "numero" },
      { c: "fecha_inicio", t: "Inicio", tipo: "fecha", mitad: true },
      { c: "fecha_fin_prevista", t: "Fin previsto", tipo: "fecha", mitad: true },
      { c: "fecha_fin_real", t: "Fin real", tipo: "fecha", mitad: true },
      { c: "notas", t: "Notas", tipo: "area" }
    ]
  },

  costes: {
    titulo: "Costes", sub: "Todo lo que sale de caja", icono: ico.euro, recurso: "costes",
    columnas: [
      { c: "fecha", t: "Fecha", tipo: "fecha" },
      { c: "concepto", t: "Concepto" },
      { c: "categoria", t: "Categoría", tipo: "tag" },
      { c: "obra_id", t: "Obra", tipo: "ref", de: "obras" },
      { c: "profesional_id", t: "Profesional", tipo: "ref", de: "profesionales" },
      { c: "importe", t: "Base", tipo: "eur", num: true },
      { c: "pagado", t: "Pago", tipo: "bool", si: "Pagado", no: "Pendiente" }
    ],
    campos: [
      { c: "concepto", t: "Concepto", req: true },
      { c: "categoria", t: "Categoría", tipo: "select", ops: CAT_COSTE, mitad: true },
      { c: "fecha", t: "Fecha", tipo: "fecha", mitad: true, pordefecto: "hoy" },
      { c: "importe", t: "Base imponible (€)", tipo: "numero", mitad: true },
      { c: "iva", t: "IVA (%)", tipo: "numero", mitad: true, pordefecto: 21 },
      { c: "obra_id", t: "Obra", tipo: "ref", de: "obras", mitad: true },
      { c: "profesional_id", t: "Profesional", tipo: "ref", de: "profesionales", mitad: true },
      { c: "proveedor_id", t: "Proveedor", tipo: "ref", de: "proveedores", mitad: true },
      { c: "factura_ref", t: "Nº de factura", mitad: true },
      { c: "pagado", t: "Estado", tipo: "select", ops: [{ v: 0, t: "Pendiente de pago" }, { v: 1, t: "Pagado" }] },
      { c: "notas", t: "Notas", tipo: "area" }
    ]
  },

  ingresos: {
    titulo: "Ingresos", sub: "Facturación a clientes", icono: ico.euro, recurso: "ingresos",
    columnas: [
      { c: "fecha", t: "Fecha", tipo: "fecha" },
      { c: "concepto", t: "Concepto" },
      { c: "obra_id", t: "Obra", tipo: "ref", de: "obras" },
      { c: "cliente_id", t: "Cliente", tipo: "ref", de: "clientes" },
      { c: "factura_ref", t: "Factura" },
      { c: "importe", t: "Base", tipo: "eur", num: true },
      { c: "cobrado", t: "Cobro", tipo: "bool", si: "Cobrado", no: "Pendiente" }
    ],
    campos: [
      { c: "concepto", t: "Concepto", req: true },
      { c: "fecha", t: "Fecha", tipo: "fecha", mitad: true, pordefecto: "hoy" },
      { c: "factura_ref", t: "Nº de factura", mitad: true },
      { c: "importe", t: "Base imponible (€)", tipo: "numero", mitad: true },
      { c: "iva", t: "IVA (%)", tipo: "numero", mitad: true, pordefecto: 21 },
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
      { c: "precio_unitario", t: "Precio ud.", tipo: "eur", num: true },
      { c: "ubicacion", t: "Ubicación" }
    ],
    campos: [
      { c: "nombre", t: "Artículo", req: true },
      { c: "referencia", t: "Referencia", mitad: true },
      { c: "categoria", t: "Categoría", mitad: true },
      { c: "cantidad", t: "Cantidad actual", tipo: "numero", mitad: true },
      { c: "unidad", t: "Unidad", mitad: true, ayuda: "ud, m, m², kg, l…" },
      { c: "minimo", t: "Stock mínimo", tipo: "numero", mitad: true, ayuda: "Avisa cuando baje de aquí" },
      { c: "precio_unitario", t: "Precio unitario (€)", tipo: "numero", mitad: true },
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

  facturas: { titulo: "Facturas", sub: "Lo que has facturado",
              icono: ico.recibo, especial: "documento", tipo: "facturas" },

  contabilidad: { titulo: "Contabilidad", sub: "Resultado, IVA y pendientes", icono: ico.libro, especial: "contabilidad" }
};

var ORDEN_MENU = [
  { sep: null, items: ["dashboard", "solicitudes"] },
  { sep: "Gestión", items: ["obras", "clientes", "profesionales"] },
  { sep: "Economía", items: ["presupuestos", "facturas", "costes", "contabilidad"] },
  { sep: "Recursos", items: ["stock", "proveedores"] }
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

/* ── Router ───────────────────────────────────────────────────────────── */
var vistaActual = "dashboard";

function pintarMenu() {
  var h = "";
  ORDEN_MENU.forEach(function (grupo) {
    if (grupo.sep) h += '<div class="sep">' + esc(grupo.sep) + "</div>";
    grupo.items.forEach(function (k) {
      var m = MODULOS[k];
      h += '<button data-vista="' + k + '"' + (k === vistaActual ? ' class="is-on"' : "") + ">" +
           svg(m.icono) + "<span>" + esc(m.titulo) + "</span></button>";
    });
  });
  $("#menu").innerHTML = h;
  $$("#menu button").forEach(function (b) {
    b.addEventListener("click", function () {
      ir(b.dataset.vista);
      $("#lat").classList.remove("is-open");
    });
  });
}

function ir(k) {
  vistaActual = k;
  location.hash = k;
  pintarMenu();
  var m = MODULOS[k];
  $("#vista-titulo").textContent = m.titulo;
  $("#vista-sub").textContent = m.sub;
  $("#vista-acciones").innerHTML = "";
  $("#vista").innerHTML = '<div class="vacia">Cargando…</div>';

  if (m.especial === "dashboard") return verDashboard();
  if (m.especial === "contabilidad") return verContabilidad();
  if (m.especial === "obras") return verObras();
  if (m.especial === "stock") return verStock();
  if (m.especial === "documento") return verDocumentos(k);
  return verTabla(k);
}

window.addEventListener("hashchange", function () {
  var k = location.hash.replace("#", "");
  if (MODULOS[k] && k !== vistaActual) ir(k);
});

/* ── Vista genérica de tabla ──────────────────────────────────────────── */
function verTabla(clave) {
  var m = MODULOS[clave];
  var refs = [];
  (m.columnas || []).concat(m.campos || []).forEach(function (c) {
    if (c.tipo === "ref" && refs.indexOf(c.de) < 0) refs.push(c.de);
  });

  $("#vista-acciones").innerHTML =
    '<button class="btn btn--amber" id="btn-nuevo">' + svg(ico.mas) + "Nuevo</button>";
  $("#btn-nuevo").addEventListener("click", function () { abrirFormulario(clave, null); });

  Promise.all([api("/api/admin/" + m.recurso)].concat(refs.map(cargarRef)))
    .then(function (res) {
      var filas = res[0];
      $("#vista").innerHTML =
        '<div class="herr"><input type="search" id="buscar" placeholder="Buscar…"></div>' +
        '<div class="tabla-caja"><div class="tabla-scroll" id="caja-tabla"></div></div>';
      pintarFilas(clave, filas);
      $("#buscar").addEventListener("input", function () {
        var q = this.value.toLowerCase().trim();
        pintarFilas(clave, !q ? filas : filas.filter(function (f) {
          return Object.keys(f).some(function (k) {
            return String(f[k] === null ? "" : f[k]).toLowerCase().indexOf(q) >= 0;
          });
        }));
      });
    })
    .catch(error);
}

function celda(col, fila) {
  var v = fila[col.c];
  if (col.tipo === "eur") return v ? eur(v) : "—";
  if (col.tipo === "fecha") return esc(fecha(v));
  if (col.tipo === "ref") return esc(nombreDe(col.de, v)) || "—";
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
  if (col.tipo === "tag") {
    var clase = "";
    if (v === "en curso" || v === "ganada" || v === "terminada") clase = " tag--verde";
    if (v === "nueva" || v === "presupuesto" || v === "presupuestada") clase = " tag--amber";
    if (v === "cancelada" || v === "perdida") clase = " tag--rojo";
    return v ? '<span class="tag' + clase + '">' + esc(v) + "</span>" : "—";
  }
  return esc(v) || "—";
}

function pintarFilas(clave, filas) {
  var m = MODULOS[clave], caja = $("#caja-tabla");
  if (!filas.length) {
    caja.innerHTML = '<div class="vacia">Todavía no hay nada aquí. Pulsa «Nuevo» para empezar.</div>';
    return;
  }
  var h = "<table><thead><tr>";
  m.columnas.forEach(function (c) { h += '<th' + (c.num ? ' class="num"' : "") + ">" + esc(c.t) + "</th>"; });
  h += '<th class="num">Acciones</th></tr></thead><tbody>';
  filas.forEach(function (f) {
    h += "<tr>";
    m.columnas.forEach(function (c) { h += "<td" + (c.num ? ' class="num"' : "") + ">" + celda(c, f) + "</td>"; });
    h += '<td class="acciones">' +
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
  if (esNuevo && v === "" && campo.pordefecto !== undefined) {
    v = (campo.pordefecto === "hoy") ? new Date().toISOString().slice(0, 10)
                                     : campo.pordefecto;
  }
  var h = '<div class="campo">' +
          '<label for="c-' + campo.c + '">' + esc(campo.t) + (campo.req ? " *" : "") + "</label>";
  if (campo.tipo === "area") {
    h += '<textarea id="c-' + campo.c + '" data-c="' + campo.c + '">' + esc(v) + "</textarea>";
  } else if (campo.tipo === "select") {
    h += '<select id="c-' + campo.c + '" data-c="' + campo.c + '">';
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
  } else if (campo.tipo === "ref") {
    h += '<select id="c-' + campo.c + '" data-c="' + campo.c + '"><option value="">— sin asignar —</option>';
    (cache[campo.de] || []).forEach(function (o) {
      h += '<option value="' + o.id + '"' + (String(o.id) === String(v) ? " selected" : "") + ">" +
           esc(o.titulo || o.nombre) + "</option>";
    });
    h += "</select>";
  } else {
    var tipo = campo.tipo === "numero" ? "number" : campo.tipo === "fecha" ? "date"
             : campo.tipo === "email" ? "email" : "text";
    h += '<input id="c-' + campo.c + '" data-c="' + campo.c + '" type="' + tipo + '"' +
         (campo.tipo === "numero" ? ' step="any"' : "") +
         ' value="' + esc(v) + '">';
  }
  if (campo.ayuda) h += '<small style="color:var(--muted-2);font-size:.79rem">' + esc(campo.ayuda) + "</small>";
  return h + "</div>";
}

function abrirFormulario(clave, registro) {
  var m = MODULOS[clave], editando = !!registro;
  var refs = [];
  m.campos.forEach(function (c) { if (c.tipo === "ref" && refs.indexOf(c.de) < 0) refs.push(c.de); });

  Promise.all(refs.map(cargarRef)).then(function () {
    var cuerpo = '<div class="aviso aviso--err" id="f-err" hidden></div><form id="f-form">';
    var buffer = [];
    m.campos.forEach(function (campo) {
      if (campo.mitad) {
        buffer.push(campo);
        if (buffer.length === 2) {
          cuerpo += '<div class="rejilla-2">' +
            campoHTML(buffer[0], registro && registro[buffer[0].c], !editando) +
            campoHTML(buffer[1], registro && registro[buffer[1].c], !editando) + "</div>";
          buffer = [];
        }
      } else {
        if (buffer.length) {
          cuerpo += campoHTML(buffer[0], registro && registro[buffer[0].c], !editando);
          buffer = [];
        }
        cuerpo += campoHTML(campo, registro && registro[campo.c], !editando);
      }
    });
    if (buffer.length) cuerpo += campoHTML(buffer[0], registro && registro[buffer[0].c], !editando);
    cuerpo += "</form>";

    modal((editando ? "Editar " : "Nuevo en ") + m.titulo.toLowerCase(), cuerpo,
      '<button class="btn btn--fant" id="f-cancelar">Cancelar</button>' +
      '<button class="btn btn--amber" id="f-guardar">Guardar</button>');

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

    $("#f-cancelar").addEventListener("click", cerrarModal);
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
        if (campo.tipo === "numero") {
          // Vacío = no se envía. La columna aplica su valor por defecto;
          // mandar null rompería el NOT NULL de iva, importe, etc.
          if (val !== "") datos[el.dataset.c] = Number(val);
        }
        else if (campo.tipo === "ref") datos[el.dataset.c] = val === "" ? null : Number(val);
        else if (campo.tipo === "select" && campo.ops.length && typeof campo.ops[0] === "object")
          datos[el.dataset.c] = Number(val);
        else if (campo.tipo === "fecha") { if (val !== "") datos[el.dataset.c] = val; }
        else datos[el.dataset.c] = val || null;
      });
      if (falta) { var e = $("#f-err"); e.textContent = "Falta: " + falta; e.hidden = false; return; }

      var btn = $("#f-guardar"); btn.disabled = true; btn.textContent = "Guardando…";
      api("/api/admin/" + m.recurso + (editando ? "/" + registro.id : ""),
          { metodo: editando ? "PUT" : "POST", datos: datos })
        .then(function () { invalidar(); cerrarModal(); ir(clave); })
        .catch(function (err) {
          var e = $("#f-err"); e.textContent = err.message; e.hidden = false;
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
      .then(function () { invalidar(); cerrarModal(); ir(clave); })
      .catch(error);
  });
}

function error(err) {
  $("#vista").innerHTML = '<div class="aviso aviso--err">' + esc(err.message || err) + "</div>";
}

/* ── Dashboard ────────────────────────────────────────────────────────── */
function verDashboard() {
  api("/api/admin/dashboard").then(function (d) {
    var c = d.contadores, margen = (d.mes.ingresos || 0) - (d.mes.gastos || 0);

    var h = '<div class="metricas">' +
      metrica(c.obras_activas, "Obras activas", "") +
      metrica(c.solicitudes_nuevas, "Solicitudes sin atender", c.solicitudes_nuevas ? "metrica--azul" : "") +
      metrica(eur(d.mes.ingresos), "Ingresos del mes", "metrica--verde") +
      metrica(eur(d.mes.gastos), "Gastos del mes", "metrica--rojo") +
      metrica(eur(margen), "Margen del mes", margen >= 0 ? "metrica--verde" : "metrica--rojo") +
      metrica(c.stock_bajo, "Artículos bajo mínimo", c.stock_bajo ? "metrica--rojo" : "") +
      "</div>";

    h += '<div class="paneles--3 paneles">';

    // Evolución
    var ev = (d.evolucion || []).slice().reverse();
    var tope = Math.max.apply(null, ev.map(function (m) { return Math.max(m.ingresos || 0, m.gastos || 0); }).concat([1]));
    h += '<div class="tarjeta"><h3>Ingresos y gastos <span>últimos 6 meses</span></h3>';
    if (!ev.length) h += '<div class="vacia">Sin movimientos todavía.</div>';
    else {
      h += '<div class="grafico">';
      ev.forEach(function (m) {
        h += '<div class="barra-col"><div class="barra-par">' +
             '<div class="barra barra--in" style="height:' + Math.max(3, (m.ingresos || 0) / tope * 100) + '%"></div>' +
             '<div class="barra barra--out" style="height:' + Math.max(3, (m.gastos || 0) / tope * 100) + '%"></div>' +
             "</div><small>" + esc(String(m.mes).slice(5) + "/" + String(m.mes).slice(2, 4)) + "</small></div>";
      });
      h += '</div><div class="leyenda"><span><i style="background:var(--verde)"></i>Ingresos</span>' +
           '<span><i style="background:var(--rojo)"></i>Gastos</span></div>';
    }
    h += "</div>";

    // Pendientes
    h += '<div class="tarjeta"><h3>Pendiente</h3>' +
         '<div style="display:grid;gap:14px">' +
         '<div><b style="font-family:var(--ff-h);font-size:1.5rem;color:var(--verde)">' + eur(d.pendientes.cobro) + "</b>" +
         '<div style="font-size:.83rem;color:var(--muted)">Por cobrar a clientes</div></div>' +
         '<div><b style="font-family:var(--ff-h);font-size:1.5rem;color:var(--rojo)">' + eur(d.pendientes.pago) + "</b>" +
         '<div style="font-size:.83rem;color:var(--muted)">Por pagar a proveedores</div></div>' +
         "</div></div>";
    h += "</div>";

    // Obras y solicitudes recientes
    h += '<div class="paneles" style="margin-top:16px">';
    h += '<div class="tarjeta"><h3>Últimas obras</h3>' + (d.obras_recientes.length
      ? '<div class="tabla-scroll"><table><tbody>' + d.obras_recientes.map(function (o) {
          var m2 = (o.importe_venta || 0) - (o.costes || 0);
          return "<tr><td><b>" + esc(o.titulo) + "</b><div style='font-size:.8rem;color:var(--muted)'>" +
                 esc(o.cliente || "sin cliente") + (o.ciudad ? " · " + esc(o.ciudad) : "") + "</div></td>" +
                 '<td><span class="tag">' + esc(o.estado) + "</span></td>" +
                 '<td class="num" style="color:' + (m2 >= 0 ? "var(--verde)" : "var(--rojo)") + '">' + eur(m2) + "</td></tr>";
        }).join("") + "</tbody></table></div>"
      : '<div class="vacia">Sin obras todavía.</div>') + "</div>";

    h += '<div class="tarjeta"><h3>Últimas solicitudes</h3>' + (d.solicitudes_recientes.length
      ? '<div class="tabla-scroll"><table><tbody>' + d.solicitudes_recientes.map(function (s) {
          return "<tr><td><b>" + esc(s.nombre) + "</b><div style='font-size:.8rem;color:var(--muted)'>" +
                 esc(s.servicio || "") + "</div></td>" +
                 '<td><span class="tag ' + (s.estado === "nueva" ? "tag--amber" : "") + '">' + esc(s.estado) + "</span></td>" +
                 '<td class="num" style="font-size:.82rem;color:var(--muted)">' + esc(fecha(s.creado)) + "</td></tr>";
        }).join("") + "</tbody></table></div>"
      : '<div class="vacia">Ninguna todavía.</div>') + "</div>";
    h += "</div>";

    if (d.avisos_stock.length) {
      h += '<div class="tarjeta" style="margin-top:16px"><h3>Material bajo mínimo</h3>' +
        '<div class="tabla-scroll"><table><tbody>' + d.avisos_stock.map(function (a) {
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
function verObras() {
  $("#vista-acciones").innerHTML =
    '<button class="btn btn--amber" id="btn-nuevo">' + svg(ico.mas) + "Nueva obra</button>";
  $("#btn-nuevo").addEventListener("click", function () { abrirFormulario("obras", null); });

  Promise.all([api("/api/admin/informes/obras"), cargarRef("clientes"), cargarRef("obras")])
    .then(function (res) {
      var obras = res[0];
      if (!obras.length) {
        $("#vista").innerHTML = '<div class="tabla-caja"><div class="vacia">Todavía no hay obras. Pulsa «Nueva obra».</div></div>';
        return;
      }
      var h = '<div class="tabla-caja"><div class="tabla-scroll"><table><thead><tr>' +
        "<th>Obra</th><th>Cliente</th><th>Estado</th><th>Equipo</th>" +
        '<th class="num">Presupuestado</th><th class="num">Costes</th><th class="num">Facturado</th>' +
        '<th class="num">Margen</th><th class="num">Acciones</th></tr></thead><tbody>';
      obras.forEach(function (o) {
        var margen = (o.importe_venta || 0) - (o.costes || 0);
        var pct = o.importe_venta ? Math.round(margen / o.importe_venta * 100) : null;
        h += "<tr><td><b>" + esc(o.titulo) + "</b>" +
             (o.codigo ? '<div style="font-size:.78rem;color:var(--muted-2)">' + esc(o.codigo) + "</div>" : "") +
             "</td><td>" + (esc(o.cliente) || "—") + "</td>" +
             '<td><span class="tag ' + (o.estado === "en curso" ? "tag--verde" : o.estado === "cancelada" ? "tag--rojo" : "tag--amber") + '">' + esc(o.estado) + "</span></td>" +
             '<td><button class="btn btn--sm ' + (o.n_profesionales ? "btn--fant" : "btn--amber") +
             '" data-equipo="' + o.id + '" title="Asignar profesionales a esta obra">' +
             svg(ico.equipo) + (o.n_profesionales ? o.n_profesionales + " asignados" : "Asignar") + "</button></td>" +
             '<td class="num">' + eur(o.importe_venta) + '</td><td class="num">' + eur(o.costes) + '</td><td class="num">' + eur(o.facturado) + "</td>" +
             '<td class="num" style="color:' + (margen >= 0 ? "var(--verde)" : "var(--rojo)") + '"><b>' + eur(margen) + "</b>" +
             (pct !== null ? '<div style="font-size:.76rem;color:var(--muted)">' + pct + "%</div>" : "") + "</td>" +
             '<td class="acciones"><button data-editar="' + o.id + '" title="Editar">' + svg(ico.lapiz) + "</button>" +
             '<button class="borrar" data-borrar="' + o.id + '" title="Borrar">' + svg(ico.papelera) + "</button></td></tr>";
      });
      $("#vista").innerHTML = h + "</tbody></table></div></div>";

      $$("[data-editar]").forEach(function (b) {
        b.addEventListener("click", function () {
          api("/api/admin/obras").then(function (todas) {
            abrirFormulario("obras", todas.filter(function (x) { return x.id == b.dataset.editar; })[0]);
          });
        });
      });
      $$("[data-borrar]").forEach(function (b) {
        b.addEventListener("click", function () { confirmarBorrado("obras", b.dataset.borrar); });
      });
      $$("[data-equipo]").forEach(function (b) {
        b.addEventListener("click", function () { verEquipo(b.dataset.equipo); });
      });
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
            return '<option value="' + p.id + '">' + esc(p.nombre) + " — " + esc(p.categoria) + "</option>";
          }).join("") + "</select></div>" +
          '<div class="campo"><label for="eq-rol">Rol en la obra</label><input id="eq-rol" placeholder="Opcional"></div></div>';
      } else {
        cuerpo += '<p style="color:var(--muted-2);font-size:.88rem">No quedan profesionales activos por asignar.</p>';
      }

      modal("Equipo de la obra", cuerpo,
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
    "</select><small style='color:var(--muted-2);font-size:.79rem'>Una salida a obra genera automáticamente su coste de material.</small></div>" +
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

/* ── Presupuestos y facturas ──────────────────────────────────────────── */
var ESTADOS_DOC = {
  presupuestos: ["borrador", "enviado", "aceptado", "rechazado"],
  facturas: ["emitida", "cobrada", "anulada"]
};

function verDocumentos(clave) {
  var m = MODULOS[clave], tipo = m.tipo;
  $("#vista-acciones").innerHTML =
    '<button class="btn btn--amber" id="btn-nuevo">' + svg(ico.mas) +
    (tipo === "facturas" ? "Nueva factura" : "Nuevo presupuesto") + "</button>";
  $("#btn-nuevo").addEventListener("click", function () { editarDocumento(tipo, null); });

  Promise.all([api("/api/admin/documentos/" + tipo), cargarRef("clientes"), cargarRef("obras")])
    .then(function (res) {
      var docs = res[0];
      if (!docs.length) {
        $("#vista").innerHTML = '<div class="tabla-caja"><div class="vacia">Todavía no hay ' +
          esc(m.titulo.toLowerCase()) + ". Pulsa el botón de arriba para crear el primero.</div></div>";
        return;
      }
      var h = '<div class="tabla-caja"><div class="tabla-scroll"><table><thead><tr>' +
        "<th>Número</th><th>Cliente</th><th>Obra</th><th>Fecha</th><th>Estado</th>" +
        '<th class="num">Base</th><th class="num">IVA</th><th class="num">Total</th>' +
        '<th class="num">Acciones</th></tr></thead><tbody>';
      docs.forEach(function (d) {
        var clase = (d.estado === "aceptado" || d.estado === "cobrada") ? "tag--verde"
                  : (d.estado === "rechazado" || d.estado === "anulada") ? "tag--rojo" : "tag--amber";
        h += "<tr><td><b>" + (esc(d.numero) || "#" + d.id) + "</b>" +
             '<div style="font-size:.78rem;color:var(--muted-2)">' + d.n_lineas +
             " línea" + (d.n_lineas === 1 ? "" : "s") + "</div></td>" +
             "<td>" + (esc(d.cliente) || "—") + "</td><td>" + (esc(d.obra) || "—") + "</td>" +
             "<td>" + esc(fecha(d.fecha)) + "</td>" +
             '<td><span class="tag ' + clase + '">' + esc(d.estado) + "</span></td>" +
             '<td class="num">' + eur(d.base) + '</td>' +
             '<td class="num" style="color:var(--muted)">' + eur(d.iva) + "</td>" +
             '<td class="num"><b>' + eur(d.total) + "</b></td>" +
             '<td class="acciones">' +
             (tipo === "presupuestos"
               ? '<button data-facturar="' + d.id + '" title="Convertir en factura">' + svg(ico.recibo) + "</button>"
               : "") +
             '<button data-editar="' + d.id + '" title="Editar">' + svg(ico.lapiz) + "</button>" +
             '<button class="borrar" data-borrar="' + d.id + '" title="Borrar">' + svg(ico.papelera) + "</button>" +
             "</td></tr>";
      });
      var totalGlobal = docs.reduce(function (a, d) { return a + (d.total || 0); }, 0);
      $("#vista").innerHTML = h + "</tbody></table></div>" +
        '<div style="padding:14px 16px;border-top:1px solid var(--line);text-align:right;font-size:.9rem">' +
        "Total acumulado: <b>" + eur(totalGlobal) + "</b></div></div>";

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
            "<p style='color:var(--muted)'>Se creará una factura con las mismas líneas y el presupuesto quedará como <b>aceptado</b>.</p>",
            '<button class="btn btn--fant" id="fa-no">Cancelar</button>' +
            '<button class="btn btn--amber" id="fa-si">Crear factura</button>');
          $("#fa-no").addEventListener("click", cerrarModal);
          $("#fa-si").addEventListener("click", function () {
            api("/api/admin/documentos/presupuestos/" + b.dataset.facturar + "/facturar",
                { metodo: "POST" })
              .then(function () { cerrarModal(); ir("facturas"); })
              .catch(function (e) { cerrarModal(); error(e); });
          });
        });
      });
    }).catch(error);
}

function editarDocumento(tipo, id) {
  var esFactura = tipo === "facturas";
  Promise.all([
    id ? api("/api/admin/documentos/" + tipo + "/" + id) : Promise.resolve(null),
    cargarRef("clientes"), cargarRef("obras")
  ]).then(function (res) {
    var doc = res[0] || {
      lineas: [], estado: ESTADOS_DOC[tipo][0],
      fecha: new Date().toISOString().slice(0, 10)
    };
    var lineas = (doc.lineas || []).slice();
    if (!lineas.length) lineas.push({ concepto: "", cantidad: 1, unidad: "ud", precio: 0, iva: 21 });

    function opciones(lista, sel) {
      return '<option value="">— sin asignar —</option>' + (cache[lista] || []).map(function (o) {
        return '<option value="' + o.id + '"' + (String(o.id) === String(sel) ? " selected" : "") + ">" +
               esc(o.titulo || o.nombre) + "</option>";
      }).join("");
    }

    var cuerpo = '<div class="aviso aviso--err" id="d-err" hidden></div>' +
      '<div class="rejilla-2">' +
        '<div class="campo"><label for="d-numero">Número</label><input id="d-numero" value="' +
          esc(doc.numero) + '" placeholder="' + (esFactura ? "F-2026-001" : "P-2026-001") + '"></div>' +
        '<div class="campo"><label for="d-fecha">Fecha</label><input id="d-fecha" type="date" value="' +
          esc(doc.fecha) + '"></div>' +
      "</div>" +
      '<div class="rejilla-2">' +
        '<div class="campo"><label for="d-cliente">Cliente</label><select id="d-cliente">' +
          opciones("clientes", doc.cliente_id) + "</select></div>" +
        '<div class="campo"><label for="d-obra">Obra</label><select id="d-obra">' +
          opciones("obras", doc.obra_id) + "</select></div>" +
      "</div>" +
      '<div class="rejilla-2">' +
        '<div class="campo"><label for="d-estado">Estado</label><select id="d-estado">' +
          ESTADOS_DOC[tipo].map(function (e) {
            return "<option" + (e === doc.estado ? " selected" : "") + ">" + esc(e) + "</option>";
          }).join("") + "</select></div>" +
        (esFactura
          ? '<div class="campo"><label for="d-venc">Vencimiento</label><input id="d-venc" type="date" value="' + esc(doc.vencimiento) + '"></div>'
          : '<div class="campo"><label for="d-validez">Validez (días)</label><input id="d-validez" type="number" value="' + (doc.validez || 30) + '"></div>') +
      "</div>" +
      '<label style="font-size:.83rem;color:var(--muted);display:block;margin:18px 0 8px">Líneas</label>' +
      '<div class="lineas-cab"><span>Concepto</span><span>Cant.</span><span>Ud.</span>' +
        "<span>Precio</span><span>IVA %</span><span>Importe</span><span></span></div>" +
      '<div class="lineas" id="d-lineas"></div>' +
      '<button class="btn btn--fant btn--sm" id="d-add" style="margin-top:10px">' +
        svg(ico.mas) + "Añadir línea</button>" +
      '<div class="totales" id="d-totales"></div>' +
      '<div class="campo" style="margin-top:16px"><label for="d-notas">Notas</label><textarea id="d-notas">' +
        esc(doc.notas) + "</textarea></div>";

    modal((id ? "Editar " : "Nuevo ") + (esFactura ? "factura" : "presupuesto"), cuerpo,
      '<button class="btn btn--fant" id="d-cancelar">Cancelar</button>' +
      '<button class="btn btn--amber" id="d-guardar">Guardar</button>', true);

    function pintarLineas() {
      $("#d-lineas").innerHTML = lineas.map(function (l, i) {
        return '<div class="linea" data-i="' + i + '">' +
          '<input class="l-concepto" placeholder="Concepto" value="' + esc(l.concepto) + '">' +
          '<input class="l-cant" type="number" step="any" placeholder="Cant." value="' + esc(l.cantidad) + '">' +
          '<input class="l-ud" placeholder="ud" value="' + esc(l.unidad) + '">' +
          '<input class="l-precio" type="number" step="any" placeholder="Precio" value="' + esc(l.precio) + '">' +
          '<input class="l-iva" type="number" step="any" placeholder="IVA" value="' + esc(l.iva) + '">' +
          '<span class="l-total">' + eur((l.cantidad || 0) * (l.precio || 0)) + "</span>" +
          '<button class="l-borrar" title="Quitar línea">' + svg(ico.papelera) + "</button>" +
          "</div>";
      }).join("");
      $$("#d-lineas .linea").forEach(function (fila) {
        var i = Number(fila.dataset.i);
        function leer() {
          lineas[i] = {
            concepto: $(".l-concepto", fila).value,
            cantidad: Number($(".l-cant", fila).value) || 0,
            unidad: $(".l-ud", fila).value || "ud",
            precio: Number($(".l-precio", fila).value) || 0,
            iva: Number($(".l-iva", fila).value) || 0
          };
          $(".l-total", fila).textContent = eur(lineas[i].cantidad * lineas[i].precio);
          pintarTotales();
        }
        $$("input", fila).forEach(function (inp) { inp.addEventListener("input", leer); });
        $(".l-borrar", fila).addEventListener("click", function () {
          lineas.splice(i, 1);
          if (!lineas.length) lineas.push({ concepto: "", cantidad: 1, unidad: "ud", precio: 0, iva: 21 });
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

    $("#d-add").addEventListener("click", function () {
      lineas.push({ concepto: "", cantidad: 1, unidad: "ud", precio: 0, iva: 21 });
      pintarLineas(); pintarTotales();
    });
    $("#d-cancelar").addEventListener("click", cerrarModal);
    $("#d-guardar").addEventListener("click", function () {
      var utiles = lineas.filter(function (l) { return String(l.concepto).trim(); });
      if (!utiles.length) {
        var e = $("#d-err");
        e.textContent = "Añade al menos una línea con concepto.";
        e.hidden = false;
        return;
      }
      var cabecera = {
        numero: $("#d-numero").value.trim() || null,
        fecha: $("#d-fecha").value || null,
        cliente_id: $("#d-cliente").value ? Number($("#d-cliente").value) : null,
        obra_id: $("#d-obra").value ? Number($("#d-obra").value) : null,
        estado: $("#d-estado").value,
        notas: $("#d-notas").value.trim() || null
      };
      if (esFactura) cabecera.vencimiento = $("#d-venc").value || null;
      else cabecera.validez = Number($("#d-validez").value) || 30;

      var btn = $("#d-guardar");
      btn.disabled = true; btn.textContent = "Guardando…";
      api("/api/admin/documentos/" + tipo + (id ? "/" + id : ""),
          { metodo: id ? "PUT" : "POST", datos: { cabecera: cabecera, lineas: utiles } })
        .then(function () { invalidar(); cerrarModal(); ir(tipo); })
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

/* ── Arranque ─────────────────────────────────────────────────────────── */
function arrancar() {
  $("#login").hidden = true;
  $("#app").hidden = false;
  $("#sesion-email").textContent = localStorage.getItem("loureiro_email") || "";
  invalidar();
  var inicial = location.hash.replace("#", "");
  ir(MODULOS[inicial] ? inicial : "dashboard");
}

$("#btn-menu").addEventListener("click", function () { $("#lat").classList.toggle("is-open"); });

if (token) {
  api("/api/admin/dashboard").then(arrancar).catch(function () { salir(true); });
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
