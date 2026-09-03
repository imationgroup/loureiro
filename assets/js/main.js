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
  var EMAIL = "info@loureirosoluciones.es";

  var $ = function (s, r) { return (r || document).querySelector(s); };
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
        say("Revisa los campos marcados antes de enviar.", "err");
      }
      return;
    }

    var fd = new FormData(form);
    var data = {
      name: (fd.get("name") || "").trim(),
      email: (fd.get("email") || "").trim(),
      phone: (fd.get("phone") || "").trim(),
      service: fd.get("service") || "",
      message: (fd.get("message") || "").trim(),
      website: fd.get("website") || ""
    };

    // Honeypot relleno = bot. Fingimos éxito y no mandamos nada.
    if (data.website) { say("Gracias, te contactaremos pronto.", "ok"); form.reset(); return; }

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

    fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (out) {
        if (!out || out.sent !== true) throw new Error("no enviado");
        form.reset();
        say("¡Recibido! Te respondemos lo antes posible.", "ok");
        submit.textContent = "Solicitud enviada";
      })
      .catch(giveUp);
  });
})();
