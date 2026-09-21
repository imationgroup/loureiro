/* ═══════════════════════════════════════════════════════════════════════
   Loureiro Soluciones — JS de la web
   Vanilla, sin dependencias. Todo degrada bien si algo falla.
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  /* ── Config ─────────────────────────────────────────────────────────
     Endpoint del backend de contacto. Si lo dejas vacío, el formulario
     cae automáticamente a abrir el cliente de correo del visitante.     */
  var API = "https://api.loureirosoluciones.es/api/contact";
  var EMAIL = "contacto@loureirosoluciones.es";
  // Página a la que se sale tras un envío correcto. Es la que mide Google
  // Ads como solicitud conseguida, así que solo se llega a ella cuando el
  // servidor confirma el envío.
  var GRACIAS = "/gracias.html";

  var $ = function (s, r) { return (r || document).querySelector(s); };

  /* ── Datos de la empresa en las páginas legales ─────────────────────
     El NIF vive en el .env del servidor, no en el HTML: así se cambia en un
     solo sitio y sale igual aquí que en los PDF. La fila está oculta hasta
     que llega el dato, para no enseñar un hueco si la API no responde.   */
  var huecos = document.querySelectorAll("[data-empresa]");
  if (huecos.length && API && window.fetch) {
    fetch(API.slice(0, API.lastIndexOf("/")) + "/empresa")
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (datos) {
        Array.prototype.forEach.call(huecos, function (el) {
          var v = datos[el.getAttribute("data-empresa")];
          if (!v) return;
          el.textContent = v;
          var fila = el.closest("[data-empresa-fila]");
          if (fila) fila.hidden = false;
        });
      })
      .catch(function () {});
  }
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ── Año del footer ─────────────────────────────────────────────── */
  var year = $("#year");
  if (year) year.textContent = new Date().getFullYear();

  /* ── Header: sombra al hacer scroll ─────────────────────────────── */
  var hdr = $("#hdr");
  if (hdr) {
    var onScroll = function () { hdr.classList.toggle("is-stuck", window.scrollY > 8); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ── Menú móvil ─────────────────────────────────────────────────── */
  var burger = $("#burger");
  var nav = $("#nav");
  if (burger && nav) {
    var setMenu = function (open) {
      nav.classList.toggle("is-open", open);
      burger.setAttribute("aria-expanded", String(open));
      burger.setAttribute("aria-label", open ? "Cerrar menú" : "Abrir menú");
    };
    burger.addEventListener("click", function () {
      setMenu(burger.getAttribute("aria-expanded") !== "true");
    });
    // Cerrar al navegar o pulsar Escape
    nav.addEventListener("click", function (e) {
      if (e.target.closest("a")) setMenu(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") setMenu(false);
    });
  }

  /* ── Animaciones de entrada ─────────────────────────────────────── */
  var targets = $$(".reveal, .steps li");
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (reduce || !("IntersectionObserver" in window)) {
    targets.forEach(function (el) { el.classList.add("is-in"); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-in");
        io.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.1 });

    // Escalona los hermanos dentro de una misma rejilla
    targets.forEach(function (el) {
      var sibs = Array.prototype.indexOf.call(el.parentNode.children, el);
      el.style.transitionDelay = Math.min(sibs, 5) * 70 + "ms";
      io.observe(el);
    });
  }

  /* ── FAQ: solo un desplegable abierto a la vez ──────────────────── */
  var faqs = $$(".faq details");
  faqs.forEach(function (d) {
    d.addEventListener("toggle", function () {
      if (!d.open) return;
      faqs.forEach(function (o) { if (o !== d) o.open = false; });
    });
  });

  /* ── Formulario de contacto ─────────────────────────────────────── */
  var form = $("#form");
  if (!form) return;

  var msg = $("#form-msg");
  var submit = $("#submit");

  // Los canales de «¿Cómo nos conociste?» se editan en el panel, así que se
  // piden al servidor. Si no contesta, se quedan los que trae el HTML: el
  // campo es opcional y no puede impedir que se mande la solicitud.
  var origen = $("#f-origin");
  if (origen && API) {
    fetch(API.replace(/contact$/, "origenes")).then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d || !d.items || !d.items.length) return;
        var elegido = origen.value;
        origen.length = 1;
        d.items.forEach(function (nombre) {
          origen.add(new Option(nombre, nombre, false, nombre === elegido));
        });
      })
      .catch(function () { /* se queda la lista del HTML */ });
  }

  // Qué decir según el campo que falla, tanto si lo detecta el navegador como
  // si lo rechaza el servidor. Un "revisa los campos" a secas no dice nada.
  var AVISOS_CAMPO = {
    name: "Escribe tu nombre.",
    email: "Revisa el correo: tiene que ser del tipo nombre@dominio.com.",
    phone: "Revisa el teléfono: es demasiado largo.",
    service: "Elige el servicio que necesitas.",
    message: "Cuéntanos un poco más en el mensaje (al menos 4 caracteres).",
    privacy: "Tienes que aceptar la política de privacidad para enviarlo.",
    _: "Revisa los datos del formulario e inténtalo de nuevo."
  };

  var say = function (text, kind) {
    msg.textContent = text;
    msg.className = "form__msg" + (kind ? " " + kind : "");
  };

  /* Compone un mailto como plan B si el backend no responde. */
  var mailtoFallback = function (data) {
    var body = [
      "Nombre: " + data.name,
      "Email: " + data.email,
      "Teléfono: " + (data.phone || "-"),
      "Servicio: " + data.service,
      "Nos conoció: " + (data.origin || "no lo ha dicho"),
      "",
      data.message
    ].join("\n");
    return "mailto:" + EMAIL +
      "?subject=" + encodeURIComponent("Solicitud de presupuesto - " + data.service) +
      "&body=" + encodeURIComponent(body);
  };

  form.addEventListener("submit", function (e) {
    e.preventDefault();

    // Marca visualmente el primer campo inválido en vez de depender del
    // tooltip nativo, que en móvil se ve fatal.
    $$("[required]", form).forEach(function (f) { f.classList.remove("is-err"); });
    if (!form.checkValidity()) {
      var bad = $(":invalid", form);
      if (bad) {
        bad.classList.add("is-err");
        bad.focus();
        say(AVISOS_CAMPO[bad.name] || "Revisa los campos marcados antes de enviar.", "err");
      }
      return;
    }

    var fd = new FormData(form);
    var data = {
      name: (fd.get("name") || "").trim(),
      email: (fd.get("email") || "").trim(),
      phone: (fd.get("phone") || "").trim(),
      service: fd.get("service") || "",
      origin: fd.get("origin") || "",
      message: (fd.get("message") || "").trim(),
      website: fd.get("website") || ""
    };

    // Honeypot relleno = bot. Fingimos éxito y no mandamos nada.
    if (data.website) { say("Gracias, te contactaremos pronto.", "ok"); form.reset(); return; }

    // El navegador no comprueba lo mismo que el servidor: minlength cuenta los
    // espacios y aquí se envía el texto recortado, así que "ok  " pasaría el
    // navegador y el servidor lo rechazaría. Se comprueba lo que se envía.
    var corto = !data.name ? "name" : (data.message.length < 4 ? "message" : null);
    if (corto) {
      var campoCorto = form.elements[corto];
      campoCorto.classList.add("is-err");
      campoCorto.focus();
      say(AVISOS_CAMPO[corto], "err");
      return;
    }

    submit.disabled = true;
    submit.textContent = "Enviando…";
    say("");

    var giveUp = function () {
      say("No hemos podido enviarlo. Abrimos tu correo para que nos escribas directamente.", "err");
      window.location.href = mailtoFallback(data);
      submit.disabled = false;
      submit.textContent = "Enviar solicitud";
    };

    if (!API) { giveUp(); return; }

    // Error que el visitante puede corregir: se le dice qué pasa y se deja el
    // botón listo para reintentar, sin tocar lo que ha escrito.
    var reintentar = function (texto, campo) {
      say(texto, "err");
      submit.disabled = false;
      submit.textContent = "Enviar solicitud";
      if (campo) { campo.classList.add("is-err"); campo.focus(); }
    };

    fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    })
      .then(function (res) {
        // 422 = datos que el servidor no acepta; 429 = demasiados envíos
        // seguidos. Ninguno es "la web está caída", así que no se manda al
        // visitante a su correo: eso queda para los fallos de verdad.
        if (res.status === 422) {
          return res.json().catch(function () { return {}; }).then(function (j) {
            var loc = (j && j.detail && j.detail[0] && j.detail[0].loc) || [];
            var err = new Error("validacion");
            err.campo = loc[loc.length - 1];
            throw err;
          });
        }
        if (res.status === 429) {
          var lim = new Error("limite");
          lim.limite = true;
          throw lim;
        }
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (out) {
        if (!out || out.sent !== true) throw new Error("no enviado");
        form.reset();
        say("¡Recibido! Te respondemos lo antes posible.", "ok");
        submit.textContent = "Solicitud enviada";
        // Se sale a una página propia en vez de quedarse aquí: el formulario
        // no recarga, así que sin una URL de destino no hay forma de medir el
        // envío en Google Ads. El aviso de arriba queda visible mientras
        // carga, y si la navegación no llegase a ocurrir, el visitante sigue
        // viendo que su mensaje se envió.
        window.location.assign(GRACIAS);
      })
      .catch(function (err) {
        if (err && err.limite) {
          reintentar("Has enviado varias solicitudes seguidas. Espera un rato o llámanos al 603 905 128.");
        } else if (err && err.message === "validacion") {
          reintentar(AVISOS_CAMPO[err.campo] || AVISOS_CAMPO._,
                     err.campo ? form.elements[err.campo] : null);
        } else {
          giveUp();
        }
      });
  });
})();
