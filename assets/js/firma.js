/* ═══════════════════════════════════════════════════════════════════════
   Firma del presupuesto por el cliente.

   El enlace lleva el token en el fragmento (…/firmar/#TOKEN) y no en la
   ruta: el fragmento no se manda al servidor, así que el enlace no queda
   escrito en los registros de acceso ni viaja en la cabecera Referer.
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
"use strict";

var API = location.hostname === "127.0.0.1" || location.hostname === "localhost"
  ? "http://127.0.0.1:8005"
  : "https://api.loureirosoluciones.es";

var $ = function (s, r) { return (r || document).querySelector(s); };

function esc(v) {
  if (v === null || v === undefined) return "";
  return String(v).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
function eur(n) {
  return (Number(n) || 0).toLocaleString("es-ES", { style: "currency", currency: "EUR" });
}
function num(n) { return (Number(n) || 0).toLocaleString("es-ES", { maximumFractionDigits: 2 }); }
function fecha(f) { return f ? String(f).slice(0, 10).split("-").reverse().join("/") : ""; }

var token = location.hash.replace("#", "").trim();
var datos = null;

function pedir(ruta, cuerpo) {
  return fetch(API + ruta, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo)
  }).then(function (r) {
    return r.json().then(function (j) {
      if (!r.ok) throw new Error((j && j.detail) || "No se ha podido completar la operación.");
      return j;
    }, function () { throw new Error("No hemos podido conectar. Inténtalo de nuevo."); });
  });
}

function fallo(mensaje) {
  $("#fi-cargando").hidden = true;
  var caja = $("#fi-error");
  caja.textContent = mensaje;
  caja.hidden = false;
}

/* Condiciones: primera línea de cada bloque como título, el resto como texto. */
function condicionesHTML(txt) {
  return String(txt || "").replace(/\r\n/g, "\n").split("\n\n").map(function (bloque) {
    var lineas = bloque.split("\n").filter(function (l) { return l.trim(); });
    if (!lineas.length) return "";
    var cuerpo = lineas.slice(1).join(" ").trim();
    return "<h3>" + esc(lineas[0].trim()) + "</h3>" + (cuerpo ? "<p>" + esc(cuerpo) + "</p>" : "");
  }).join("");
}

function pintar() {
  var d = datos, c = d.cliente || {};
  var lugar = [c.direccion, c.cp, c.ciudad].filter(Boolean).join(", ");
  var h = '<div class="fi__tarjeta">' +
    '<div class="fi__enc"><h1 class="fi__num">Presupuesto ' + esc(d.numero) + "</h1>" +
    '<span class="fi__meta">' + esc(fecha(d.fecha)) +
      (d.validez ? " · válido " + esc(d.validez) + " días" : "") + "</span></div>" +
    '<div class="fi__partes">' +
      '<div class="fi__parte"><h4>De</h4><p><b>' + esc(d.empresa.nombre) + "</b><br>" +
        (d.empresa.nif ? "NIF " + esc(d.empresa.nif) + "<br>" : "") +
        esc(d.empresa.direccion) + "<br>" + esc(d.empresa.telefono) + "</p></div>" +
      '<div class="fi__parte"><h4>Para</h4><p><b>' + (esc(c.nombre) || "—") + "</b>" +
        (c.nif ? "<br>NIF " + esc(c.nif) : "") + (lugar ? "<br>" + esc(lugar) : "") + "</p></div>" +
    "</div>" +
    '<table class="fi__tabla"><thead><tr><th>Concepto</th><th class="num">Cant.</th>' +
      '<th class="num">Precio</th><th class="num">IVA</th><th class="num">Importe</th></tr></thead><tbody>';

  d.lineas.forEach(function (l) {
    h += '<tr><td class="fi__concepto">' + esc(l.concepto) + "</td>" +
      '<td class="num" data-et="Cantidad">' + num(l.cantidad) + " " + esc(l.unidad || "") + "</td>" +
      '<td class="num" data-et="Precio">' + eur(l.precio) + "</td>" +
      '<td class="num" data-et="IVA">' + num(l.iva) + " %</td>" +
      '<td class="num" data-et="Importe">' + eur((l.cantidad || 0) * (l.precio || 0)) + "</td></tr>";
  });

  h += "</tbody></table>" +
    '<div class="fi__totales">' +
      "<div><span>Base imponible</span><b>" + eur(d.totales.base) + "</b></div>" +
      "<div><span>IVA</span><b>" + eur(d.totales.iva) + "</b></div>" +
      '<div class="fi__total"><span>Total</span><span>' + eur(d.totales.total) + "</span></div>" +
    "</div>" +
    (d.notas ? '<h3>Notas</h3><p>' + esc(d.notas).replace(/\n/g, "<br>") + "</p>" : "") +
    "</div>";

  h += '<div class="fi__tarjeta"><h2>Condiciones de contratación</h2>' +
       '<div class="fi__cond">' + condicionesHTML(d.condiciones) + "</div></div>";

  if (d.firmado_el) {
    h += '<div class="fi__aviso fi__aviso--ok">Este presupuesto ya está firmado' +
      (d.firmante_nombre ? " por <b>" + esc(d.firmante_nombre) + "</b>" : "") +
      ". Te hemos enviado una copia por correo. Si necesitas algo, llámanos al 603 905 128.</div>";
    $("#fi-doc").innerHTML = h;
    return;
  }
  if (d.estado === "cancelado") {
    h += '<div class="fi__aviso fi__aviso--info">Este presupuesto está cancelado y ya no se puede ' +
      "firmar. Si ha sido un error, llámanos al 603 905 128.</div>";
    $("#fi-doc").innerHTML = h;
    return;
  }

  h += '<div class="fi__tarjeta"><h2>Firmar y aceptar</h2>' +
    '<div class="fi__aviso fi__aviso--err" id="fi-form-err" hidden></div>' +
    '<div class="fi__campo"><label for="fi-nombre">Nombre y apellidos *</label>' +
      '<input id="fi-nombre" autocomplete="name" value="' + esc(c.nombre || "") + '"></div>' +
    '<div class="fi__campo"><label for="fi-nif">DNI o NIF</label>' +
      '<input id="fi-nif" autocomplete="off" value="' + esc(c.nif || "") + '">' +
      "<small>No es obligatorio, pero deja la firma mejor identificada.</small></div>" +
    '<div class="fi__campo"><label for="fi-firma">Tu firma *</label>' +
      '<canvas id="fi-firma" class="fi__firma" height="180"></canvas>' +
      '<div class="fi__firma-pie"><span>Firma con el dedo o con el ratón</span>' +
      '<button type="button" class="fi__borrar" id="fi-limpiar">Borrar y repetir</button></div></div>' +
    '<label class="fi__check"><input type="checkbox" id="fi-acepta">' +
      "<span>He leído y acepto este presupuesto y las condiciones de contratación.</span></label>" +
    '<label class="fi__check"><input type="checkbox" id="fi-inicio">' +
      "<span>Quiero que empecéis los trabajos <b>antes</b> de que pasen " + esc(d.dias_desistimiento) +
      " días naturales. Sé que, si luego me echo atrás, tendré que abonar lo ya hecho y los gastos " +
      "justificados.</span></label>" +
    '<button class="btn btn--amber btn--full fi__enviar" id="fi-enviar">Firmar el presupuesto</button>' +
    '<p class="fi__legal">Al firmar se guardan la fecha y hora, tu dirección IP y el documento tal ' +
      "como lo firmas, como prueba de la aceptación. Si eres consumidor, dispones de " +
      esc(d.dias_desistimiento) + " días naturales para desistir del contrato comunicándolo a " +
      esc(d.empresa.email) + "; si pides que empecemos antes de ese plazo y luego desistes, " +
      "abonarás la parte ya ejecutada y los gastos justificados.</p>" +
    "</div>";

  $("#fi-doc").innerHTML = h;
  prepararFirma();
  $("#fi-enviar").addEventListener("click", enviar);
}

/* ── El lienzo de la firma ─────────────────────────────────────────────── */
var lienzo, ctx, hayTrazo = false;

function prepararFirma() {
  lienzo = $("#fi-firma");
  var ancho = lienzo.parentNode.clientWidth;
  var escala = window.devicePixelRatio || 1;
  lienzo.style.width = ancho + "px";
  lienzo.style.height = "180px";
  lienzo.width = ancho * escala;
  lienzo.height = 180 * escala;
  ctx = lienzo.getContext("2d");
  ctx.scale(escala, escala);
  ctx.lineWidth = 2.4;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.strokeStyle = "#14161A";

  var pintando = false;
  var punto = function (e) {
    var caja = lienzo.getBoundingClientRect();
    return { x: e.clientX - caja.left, y: e.clientY - caja.top };
  };
  lienzo.addEventListener("pointerdown", function (e) {
    pintando = true;
    lienzo.setPointerCapture(e.pointerId);
    var p = punto(e);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    e.preventDefault();
  });
  lienzo.addEventListener("pointermove", function (e) {
    if (!pintando) return;
    var p = punto(e);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
    hayTrazo = true;
    e.preventDefault();
  });
  ["pointerup", "pointercancel", "pointerleave"].forEach(function (ev) {
    lienzo.addEventListener(ev, function () { pintando = false; });
  });

  $("#fi-limpiar").addEventListener("click", function () {
    ctx.clearRect(0, 0, lienzo.width, lienzo.height);
    hayTrazo = false;
  });
}

function enviar() {
  var err = $("#fi-form-err"), btn = $("#fi-enviar");
  var mal = function (texto) { err.textContent = texto; err.hidden = false; err.scrollIntoView({ block: "center" }); };
  var nombre = $("#fi-nombre").value.trim();

  if (nombre.length < 3) return mal("Escribe tu nombre y apellidos.");
  if (!hayTrazo) return mal("Firma en el recuadro antes de enviar.");
  if (!$("#fi-acepta").checked) return mal("Tienes que aceptar el presupuesto y las condiciones.");

  err.hidden = true;
  btn.disabled = true;
  btn.textContent = "Firmando…";
  pedir("/api/firma", {
    token: token,
    nombre: nombre,
    nif: $("#fi-nif").value.trim(),
    imagen: lienzo.toDataURL("image/png"),
    acepta: true,
    inicio_inmediato: $("#fi-inicio").checked
  }).then(function (r) {
    $("#fi-doc").innerHTML =
      '<div class="fi__aviso fi__aviso--ok"><b>Presupuesto ' + esc(r.numero) + " firmado.</b><br>" +
      "Te hemos enviado una copia firmada a tu correo. Nos pondremos en contacto para concretar " +
      "las fechas de los trabajos.</div>" +
      '<div class="fi__tarjeta"><p>Gracias por confiar en nosotros. Si necesitas cualquier cosa, ' +
      'llámanos al <a href="tel:+34603905128">603 905 128</a>.</p></div>';
    window.scrollTo({ top: 0, behavior: "smooth" });
  }).catch(function (e) {
    mal(e.message);
    btn.disabled = false;
    btn.textContent = "Firmar el presupuesto";
  });
}

/* ── Arranque ─────────────────────────────────────────────────────────── */
if (!token) {
  fallo("Este enlace no es válido. Pídenos uno nuevo al 603 905 128.");
} else {
  pedir("/api/firma/ver", { token: token }).then(function (d) {
    datos = d;
    $("#fi-cargando").hidden = true;
    $("#fi-doc").hidden = false;
    $("#fi-empresa").textContent = d.empresa.nombre +
      (d.empresa.nif ? " · NIF " + d.empresa.nif : "") + " · " + d.empresa.direccion;
    document.title = "Presupuesto " + d.numero + " · Loureiro Soluciones";
    pintar();
  }).catch(function (e) { fallo(e.message); });
}
})();
