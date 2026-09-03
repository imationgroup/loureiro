/* ═══════════════════════════════════════════════════════════════════════
   Comparador antes / después.
   Un <input type="range"> transparente encima hace todo el trabajo: sale
   gratis el arrastre con ratón, el táctil y el manejo por teclado, y es
   accesible sin añadir nada.

   Estructura esperada:
     <div class="ba">
       <div class="ba__layer"><!-- antes --></div>
       <div class="ba__layer ba__after"><!-- después --></div>
       <span class="ba__tag ba__tag--b">Antes</span>
       <span class="ba__tag ba__tag--a">Después</span>
       <input class="ba__range" type="range" min="0" max="100" value="50"
              aria-label="Comparar antes y después">
       <div class="ba__handle"></div>
     </div>
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  var comparadores = document.querySelectorAll(".ba");
  if (!comparadores.length) return;

  Array.prototype.forEach.call(comparadores, function (ba) {
    var range = ba.querySelector(".ba__range");
    if (!range) return;

    var pintar = function () {
      ba.style.setProperty("--pos", range.value + "%");
    };

    pintar();
    range.addEventListener("input", pintar);

    // Doble clic para volver al centro
    ba.addEventListener("dblclick", function () {
      range.value = 50;
      pintar();
    });
  });
})();
