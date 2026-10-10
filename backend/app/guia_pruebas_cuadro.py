"""Informe: pruebas en un cuadro de vivienda con polímetro y pinza.

Todo lo que se afirma aquí sale del Reglamento Electrotécnico para Baja
Tensión (Real Decreto 842/2002), del Real Decreto 614/2001 de riesgo
eléctrico o de la nota de aplicación de Fluke que resume la norma de
verificación, y cada punto lleva de dónde sale. Lo que es criterio de obra y
no reglamento va dicho como tal, para no mezclar.

El contenido es datos, no texto libre: los mismos bloques los pinta el panel
en pantalla y los imprime el PDF (ver documentacion_pdf.py). Así no hay dos
versiones del informe que se puedan ir separando una de otra.
"""

# Las fuentes, aparte: se citan por su clave desde cada prueba y se imprimen
# enteras al final. Si algún día cambia una edición, se cambia aquí.
FUENTES = {
    "rebt": {
        "clave": "rebt",
        "titulo": "Reglamento Electrotécnico para Baja Tensión (REBT)",
        "detalle": "Real Decreto 842/2002, de 2 de agosto. Texto consolidado del BOE, "
                   "con sus Instrucciones Técnicas Complementarias (ITC-BT).",
        "url": "https://www.boe.es/buscar/act.php?id=BOE-A-2002-18099",
    },
    "rd614": {
        "clave": "rd614",
        "titulo": "Real Decreto 614/2001, riesgo eléctrico",
        "detalle": "Disposiciones mínimas para la protección de la salud y seguridad de los "
                   "trabajadores frente al riesgo eléctrico. Anexo II, trabajos sin tensión.",
        "url": "https://www.boe.es/buscar/act.php?id=BOE-A-2001-11881",
    },
    "fluke": {
        "clave": "fluke",
        "titulo": "Fluke, «Comprobaciones básicas de instalaciones eléctricas»",
        "detalle": "Nota de aplicación (Pub_ID 10641-spa, 2014). Resume el orden de "
                   "verificación de la IEC 60364-6-61 / UNE 20460 y los equipos de medida "
                   "que exige la serie EN 61557. Es documentación de fabricante, no "
                   "reglamento: aquí se usa solo para el método y el instrumental.",
        "url": "https://www.fluke.com",
    },
}

# Lo que mide cada aparato, para la cabecera del informe.
EQUIPO = [
    ("Polímetro (multímetro)", "Tensión alterna, continuidad y resistencia en ohmios."),
    ("Pinza amperimétrica", "Corriente de carga de cada circuito. Si es pinza de fugas "
                            "(resolución en mA), también la corriente de fuga."),
]


def _prueba(numero, titulo, mide, pasos, criterio, fuente, aviso=None, limite=None):
    return {"tipo": "prueba", "numero": numero, "titulo": titulo, "mide": mide,
            "pasos": pasos, "criterio": criterio, "fuente": fuente,
            "aviso": aviso, "limite": limite}


SECCIONES = [
    # ── 1. Alcance ───────────────────────────────────────────────────────
    {
        "titulo": "Para qué vale este informe y para qué no",
        "bloques": [
            {"tipo": "p", "texto":
                "El REBT dice que las instalaciones de baja tensión **deben verificarse antes de "
                "ponerse en servicio siguiendo la metodología de la norma UNE 20.460-6-61**, y que "
                "esa verificación la hace la empresa instaladora que ejecuta la instalación."},
            {"tipo": "cita", "texto":
                "Las instalaciones eléctricas en baja tensión deberán ser verificadas, previamente a "
                "su puesta en servicio y según corresponda en función de sus características, "
                "siguiendo la metodología de la norma UNE 20.460-6-61.",
             "fuente": "REBT, ITC-BT-05, apartado 3"},
            {"tipo": "p", "texto":
                "Esa metodología empieza por una inspección visual y sigue con ensayos: continuidad "
                "de los conductores de protección, resistencia de aislamiento, protección por "
                "separación de circuitos, resistencia de suelos y paredes, desconexión automática "
                "de la alimentación, polaridad y ensayos funcionales; además, resistencia eléctrica "
                "y caída de tensión."},
            {"tipo": "p", "texto":
                "Varios de esos ensayos exigen equipos concretos de la serie EN 61557 "
                "(megóhmetro, medidor de bucle, comprobador de diferenciales, telurómetro). "
                "**Con un polímetro y una pinza no se completa la verificación reglamentaria**, "
                "pero sí se puede hacer la inspección visual completa y una buena parte de las "
                "comprobaciones, que es donde aparecen la mayoría de los defectos graves."},
            {"tipo": "aviso", "texto":
                "Lo que sigue es una guía de trabajo interna. No sustituye al reglamento ni al "
                "criterio del instalador, y las medidas hechas con polímetro son indicativas: "
                "valen para detectar un problema, no para certificar la instalación."},
        ],
    },

    # ── 2. Antes de empezar ──────────────────────────────────────────────
    {
        "titulo": "Antes de tocar el cuadro",
        "bloques": [
            {"tipo": "p", "texto":
                "Para trabajar sin tensión, el Real Decreto 614/2001 fija cinco etapas, y hasta que "
                "no están las cinco la instalación se considera en tensión:"},
            {"tipo": "pasos", "puntos": [
                "Desconectar.",
                "Prevenir cualquier posible realimentación.",
                "Verificar la ausencia de tensión.",
                "Poner a tierra y en cortocircuito.",
                "Proteger frente a elementos próximos en tensión, en su caso, y establecer una "
                "señalización de seguridad para delimitar la zona de trabajo.",
            ]},
            {"tipo": "p", "texto":
                "La cuarta etapa es obligatoria en alta tensión y, en baja tensión, en las "
                "instalaciones «que, por inducción, o por otras razones, puedan ponerse "
                "accidentalmente en tensión»: en el cuadro de una vivienda normal no es el caso, "
                "pero las otras cuatro sí se cumplen siempre."},
            {"tipo": "lista", "puntos": [
                "La ausencia de tensión se verifica con el polímetro **en el propio punto de "
                "trabajo**, y se comprueba antes y después que el polímetro funciona.",
                "El IGA se bloquea o se señaliza para que nadie lo suba mientras se trabaja.",
                "El polímetro y las puntas tienen que ser de categoría adecuada (CAT III en un "
                "cuadro de vivienda) y estar en buen estado: una punta pelada en un cuadro con "
                "tensión es exactamente el accidente que se quiere evitar.",
                "Las medidas con tensión del bloque B se hacen con el cuadro abierto: guantes, "
                "gafas y nada de pulseras, anillos ni reloj.",
            ]},
            {"tipo": "fuente", "texto": "RD 614/2001, Anexo II, apartado A.1 (trabajos sin tensión)."},
        ],
    },

    # ── 3. Bloque A: sin tensión ─────────────────────────────────────────
    {
        "titulo": "Bloque A · Con el cuadro sin tensión",
        "bloques": [
            {"tipo": "p", "texto":
                "La inspección por examen va antes de los ensayos y se hace normalmente sin "
                "tensión. Es la parte que no necesita ningún aparato y la que más defectos "
                "destapa."},

            _prueba(
                "A1", "Composición del cuadro y de las protecciones",
                "Que estén los dispositivos que el reglamento exige, y con los valores mínimos.",
                ["Comprobar que hay un interruptor general automático (IGA) de corte omnipolar, "
                 "con accionamiento manual, de intensidad nominal mínima 25 A, con protección "
                 "contra sobrecargas y cortocircuitos.",
                 "Comprobar que el IGA es independiente del ICP (el precintado de la compañía) y "
                 "que no está sustituido por él.",
                 "Comprobar que hay uno o varios diferenciales de 30 mA como máximo que protejan "
                 "todos los circuitos, con intensidad asignada igual o mayor que la del IGA.",
                 "Contar circuitos por diferencial: como mínimo un diferencial por cada cinco "
                 "circuitos instalados.",
                 "Comprobar que cada circuito sale de su propio automático de corte omnipolar."],
                "IGA ≥ 25 A, omnipolar e independiente del ICP. Diferenciales de 30 mA como "
                "máximo, con In ≥ In del IGA, y al menos uno por cada cinco circuitos.",
                "REBT, ITC-BT-25, apartados 2.1 y 2.3.2; ITC-BT-17, apartados 1.2 y 1.3",
                limite="El poder de corte del IGA (4.500 A como mínimo, ITC-BT-17 ap. 1.3) se lee "
                       "en el propio aparato; la corriente de cortocircuito real del punto no se "
                       "puede medir sin medidor de bucle."),

            _prueba(
                "A2", "Protección contra contactos directos",
                "Que no haya partes en tensión al alcance de la mano.",
                ["Mirar el cuadro cerrado: tapas ciegas en los huecos libres, embarrados y bornes "
                 "cubiertos, ninguna parte activa accesible sin herramienta.",
                 "Revisar bases de enchufe y mecanismos rotos, cajas sin tapa, empalmes al aire.",
                 "Revisar que los cables no tengan el aislamiento dañado en la entrada al cuadro."],
                "Ninguna parte activa accesible. Un fallo aquí es el defecto más grave que hay: "
                "el reglamento clasifica como **defecto muy grave** el incumplimiento de las "
                "medidas contra contactos directos en cualquier tipo de instalación.",
                "REBT, ITC-BT-05, apartado 6.1; ITC-BT-24, apartado 3"),

            _prueba(
                "A3", "Circuitos mínimos y calibres",
                "Que la vivienda tenga los circuitos que le corresponden y que cada automático "
                "pegue con la sección de su cable.",
                ["Identificar los circuitos del cuadro y compararlos con los mínimos de una "
                 "electrificación básica: C1 iluminación, C2 tomas de uso general y frigorífico, "
                 "C3 cocina y horno, C4 lavadora, lavavajillas y termo, C5 baño y cuarto de cocina.",
                 "Leer en cada automático su intensidad asignada y en el cable su sección, y "
                 "compararlos con la tabla 1 de la ITC-BT-25.",
                 "Si la vivienda pasa de 160 m² o tiene calefacción, aire acondicionado, secadora "
                 "o recarga de vehículo, comprobar que esos circuitos existen aparte."],
                "Los calibres y secciones mínimas de la tabla 1 de la ITC-BT-25 (ver la tabla de "
                "más abajo). La carencia del número de circuitos mínimos es **defecto grave**.",
                "REBT, ITC-BT-25, apartados 2.3 y 3, tabla 1; ITC-BT-05, apartado 6.2"),

            {"tipo": "tabla", "titulo": "Circuitos mínimos de una vivienda (ITC-BT-25, tabla 1)",
             "cabecera": ["Circuito", "Automático", "Sección mínima", "Puntos máx."],
             "filas": [
                 ["C1 · Iluminación", "10 A", "1,5 mm²", "30"],
                 ["C2 · Tomas de uso general y frigorífico", "16 A", "2,5 mm²", "20"],
                 ["C3 · Cocina y horno", "25 A", "6 mm²", "2"],
                 ["C4 · Lavadora, lavavajillas y termo", "20 A", "4 mm²", "3"],
                 ["C5 · Baño y cuarto de cocina", "16 A", "2,5 mm²", "6"],
                 ["C8 · Calefacción", "25 A", "6 mm²", "—"],
                 ["C9 · Aire acondicionado", "25 A", "6 mm²", "—"],
                 ["C10 · Secadora", "16 A", "2,5 mm²", "1"],
                 ["C11 · Automatización", "10 A", "1,5 mm²", "—"],
             ]},

            _prueba(
                "A4", "Identificación de los conductores",
                "Que el neutro y la protección se reconozcan por el color.",
                ["Comprobar el color del aislamiento de cada conductor en el cuadro y en las cajas "
                 "que se abran.",
                 "Azul claro, el neutro. Amarillo-verde, el de protección. Marrón o negro (y gris "
                 "para una tercera fase), las fases.",
                 "Comprobar que el amarillo-verde no se usa para nada que no sea protección."],
                "Neutro azul claro y protección amarillo-verde. La falta de identificación de los "
                "conductores neutro y de protección es **defecto grave**.",
                "REBT, ITC-BT-19, apartado 2.2.4; ITC-BT-05, apartado 6.2"),

            _prueba(
                "A5", "Sección del conductor de protección",
                "Que el cable de tierra sea suficiente para la fase que acompaña.",
                ["Leer la sección de la fase y la del conductor de protección de cada circuito.",
                 "Comparar con la tabla: hasta 16 mm² de fase, la misma sección; de 16 a 35 mm², "
                 "16 mm²; por encima de 35 mm², la mitad de la fase.",
                 "Comprobar también que no hay ningún aparato intercalado en el conductor de "
                 "protección y que sus conexiones son accesibles."],
                "Las secciones de la tabla 2 de la ITC-BT-19, que vale cuando el conductor de "
                "protección es del mismo metal que la fase (si no, la sección se calcula para "
                "una conductividad equivalente). Si el conductor de protección no forma parte de "
                "la canalización de alimentación, el mínimo es 2,5 mm² con protección mecánica "
                "y 4 mm² sin ella. Una sección insuficiente del conductor de protección es "
                "**defecto grave**.",
                "REBT, ITC-BT-19, apartado 2.3 y tabla 2; ITC-BT-18, apartado 3.4; "
                "ITC-BT-05, apartado 6.2"),

            _prueba(
                "A6", "Conexiones y aprietes",
                "Que no haya empalmes improvisados ni bornes flojos.",
                ["Tirar suavemente de cada conductor en su borne: no debe moverse.",
                 "Comprobar que no hay uniones por retorcimiento o arrollamiento de conductores: "
                 "el reglamento no las permite en ningún caso.",
                 "Comprobar que los empalmes están dentro de cajas de registro, no dentro de "
                 "tubos ni enterrados en yeso.",
                 "Mirar señales de calentamiento: bornes oscurecidos, aislamiento endurecido, "
                 "olor a quemado."],
                "Ninguna unión por retorcimiento. Bornes apretados y empalmes en caja. Un punto "
                "de la instalación cuya defectuosa ejecución pueda originar averías es **defecto "
                "grave**.",
                "REBT, ITC-BT-19, apartado 2.11; ITC-BT-05, apartado 6.2"),

            _prueba(
                "A7", "Continuidad del conductor de protección",
                "Que la tierra llegue de verdad a cada punto de uso.",
                ["Cuadro sin tensión. Poner el polímetro en ohmios (o en continuidad con pitido).",
                 "Cortocircuitar las dos puntas y anotar la resistencia que marcan: ese valor hay "
                 "que restarlo de cada medida (en un polímetro suelen ser entre 0,2 y 1 Ω).",
                 "Con un cable auxiliar largo desde el borne de tierra del cuadro, medir contra el "
                 "contacto de tierra de cada base de enchufe, de cada punto de luz con masa "
                 "metálica y de cada aparato de clase I.",
                 "Repetir en el cuarto de baño y en la cocina, que son los puntos que más fallan."],
                "Unos pocos ohmios, y cuanto más bajo mejor. Un circuito abierto (el polímetro no "
                "pita o marca megaohmios) es **falta de continuidad de los conductores de "
                "protección**: defecto grave.",
                "REBT, ITC-BT-05, apartado 6.2; ITC-BT-18, apartado 3.4",
                limite="El ensayo de la norma se hace con un instrumento que da de 4 a 24 V en "
                       "vacío y al menos 0,2 A (EN 61557-4). Un polímetro mide con una corriente "
                       "mucho menor: detecta un conductor cortado o un borne suelto, pero no "
                       "garantiza que la unión aguante la corriente de defecto. Fuente del método: "
                       "nota de aplicación de Fluke."),

            _prueba(
                "A8", "Conexiones equipotenciales del cuarto de baño",
                "Que todo lo metálico del baño esté unido a la protección.",
                ["Medir continuidad desde el borne de tierra hasta las tuberías metálicas de agua "
                 "y desagüe, las de calefacción o aire acondicionado, la bañera o plato metálicos "
                 "y las partes metálicas accesibles de la estructura del edificio.",
                 "Comprobar que el conductor de equipotencialidad existe físicamente y está "
                 "apretado, no solo que haya continuidad por casualidad a través de una tubería.",
                 "Comprobar la sección: el conductor principal de equipotencialidad, no inferior a "
                 "la mitad del conductor de protección de mayor sección de la instalación, con un "
                 "mínimo de 6 mm², reducible a 2,5 mm² si es de cobre."],
                "Continuidad en todos esos elementos. La falta de conexiones equipotenciales, "
                "cuando son exigibles, es **defecto grave**.",
                "REBT, ITC-BT-27, apartado 2.2; ITC-BT-18, apartado 8; ITC-BT-05, apartado 6.2",
                aviso="Si la bañera o el plato son metálicos, cuentan como parte conductora "
                      "externa susceptible de transferir tensiones, salvo que estén aislados del "
                      "edificio (ITC-BT-27, ap. 2.2)."),

            _prueba(
                "A9", "Línea principal de tierra y punto de puesta a tierra",
                "Que el cuadro esté unido a la toma de tierra del edificio.",
                ["Medir continuidad entre el borne principal de tierra del cuadro y el punto de "
                 "puesta a tierra del edificio (centralización de contadores, patio de luces, "
                 "arqueta).",
                 "Comprobar que el punto de puesta a tierra es accesible y desmontable para poder "
                 "medir la tierra.",
                 "Comprobar que no se usan como conductor de tierra tuberías de agua, gas, "
                 "calefacción o desagües: el reglamento lo prohíbe expresamente."],
                "Continuidad franca, de pocos ohmios, y punto de puesta a tierra accesible.",
                "REBT, ITC-BT-26, apartados 3.3 y 3.4; ITC-BT-18",
                limite="Esto comprueba la unión, no la tierra. El valor de la resistencia de "
                       "puesta a tierra necesita telurómetro (ver bloque C)."),
        ],
    },

    # ── 4. Bloque B: con tensión ─────────────────────────────────────────
    {
        "titulo": "Bloque B · Con el cuadro en tensión",
        "bloques": [
            {"tipo": "aviso", "texto":
                "A partir de aquí se trabaja con tensión. Estas medidas se hacen con el cuadro "
                "abierto y con riesgo real de contacto y de arco: solo las hace quien está "
                "autorizado para ello, con EPIs y con el polímetro en la escala correcta antes de "
                "acercar las puntas."},

            _prueba(
                "B1", "Tensiones en el cuadro",
                "Que la alimentación sea la que se espera y que el neutro y la tierra estén sanos.",
                ["Polímetro en tensión alterna. Medir entre fase y neutro a la salida del IGA: una "
                 "vivienda monofásica se alimenta a 230 V en esquema TT.",
                 "Medir entre fase y tierra: tiene que dar prácticamente lo mismo que fase-neutro.",
                 "Medir entre neutro y tierra: normalmente son unos pocos voltios.",
                 "En trifásico, medir las tres fases entre sí (400 V) y cada fase con el neutro "
                 "(230 V)."],
                "Tensión nominal 230 V entre fase y neutro (230/400 V en trifásica), y el mismo "
                "valor entre fase y tierra.",
                "REBT, artículo 4; ITC-BT-26, apartado 2",
                limite="Criterio de obra, no reglamento: una tensión neutro-tierra alta (del orden "
                       "de decenas de voltios) o un fase-tierra mucho menor que el fase-neutro "
                       "delatan neutro flojo o tierra mal conectada, y hay que mirarlo antes de "
                       "seguir. La tolerancia de la tensión de suministro no la fija el REBT, sino "
                       "la normativa de distribución."),

            _prueba(
                "B2", "Polaridad y corte omnipolar",
                "Que los cortes abran también el neutro y que fase y neutro no estén cruzados.",
                ["Con el circuito en tensión, medir fase-tierra y neutro-tierra en una base de "
                 "enchufe: la fase debe dar ~230 V y el neutro, casi cero. Al revés significa que "
                 "están cruzados.",
                 "Bajar el automático de cada circuito y comprobar que desaparece la tensión en "
                 "**los dos** conductores del circuito, no solo en uno.",
                 "Comprobar que ningún interruptor unipolar corta el neutro."],
                "Los dispositivos del cuadro general son de corte omnipolar y «el conductor neutro "
                "o compensador no podrá ser interrumpido salvo cuando el corte se establezca por "
                "interruptores omnipolares».",
                "REBT, ITC-BT-19, apartado 2.7; ITC-BT-25, apartado 2.1"),

            _prueba(
                "B3", "Ensayo funcional del diferencial",
                "Que el mecanismo del diferencial dispare y rearme.",
                ["Avisar antes: se va a cortar la luz de la vivienda.",
                 "Pulsar el botón de test de cada diferencial: tiene que disparar en el acto.",
                 "Rearmar y comprobar que vuelve a dar servicio.",
                 "Repetirlo con cada diferencial del cuadro, uno a uno, anotando el que no "
                 "dispare o el que no rearme."],
                "Dispara al pulsar y rearma. Los ensayos funcionales forman parte de la lista de "
                "verificación de la norma.",
                "REBT, ITC-BT-05, apartado 3 (metodología UNE 20.460-6-61); método: nota de "
                "aplicación de Fluke",
                limite="El botón de test solo prueba el mecanismo: provoca una fuga interna y "
                       "comprueba que el aparato abre. **No mide la sensibilidad real ni el tiempo "
                       "de disparo**, que es lo que exige la norma y lo que necesita un "
                       "comprobador de diferenciales (EN 61557-6). Un diferencial puede pasar el "
                       "botón de test y disparar a 60 mA o tardar demasiado."),

            _prueba(
                "B4", "Corriente de fuga con la pinza",
                "Cuánta corriente se está yendo a tierra, que es lo que hace saltar el diferencial.",
                ["Pinza en corriente alterna, a ser posible de fugas (resolución en mA).",
                 "Abrazar **a la vez** la fase y el neutro aguas abajo del diferencial (en "
                 "trifásico, las tres fases y el neutro). Lo que marque es la fuga.",
                 "Repetir circuito por circuito para localizar de dónde sale.",
                 "Comparar la suma con la sensibilidad del diferencial que los protege."],
                "La norma es taxativa: «Las corrientes de fuga no serán superiores para el "
                "conjunto de la instalación o para cada uno de los circuitos en que ésta pueda "
                "dividirse a efectos de su protección, a la sensibilidad que presenten los "
                "interruptores diferenciales instalados como protección contra los contactos "
                "indirectos». Con diferenciales de 30 mA, la fuga total tiene que quedar por "
                "debajo de 30 mA.",
                "REBT, ITC-BT-19, apartado 2.9",
                limite="Una pinza normal tiene resolución de 0,1 A: no ve 20 mA. Si con una pinza "
                       "corriente abrazando fase y neutro juntos marca algo distinto de cero, la "
                       "fuga ya es de centenares de miliamperios y el problema es gordo. Para "
                       "medir de verdad hace falta pinza de fugas.",
                aviso="Criterio de obra, no reglamento: una instalación sana suele quedarse muy "
                      "por debajo del umbral. Fugas de la mitad de la sensibilidad ya explican "
                      "disparos intempestivos aunque estén «dentro»."),

            _prueba(
                "B5", "Corriente de carga de cada circuito",
                "Que lo que pasa por cada cable esté por debajo de lo que protege su automático.",
                ["Pinza en corriente alterna, abrazando **solo la fase** de cada circuito.",
                 "Poner el circuito en su carga real: la cocina con las placas, el circuito de "
                 "lavadora con la lavadora y el termo, el aire con la máquina en marcha.",
                 "Anotar la corriente y compararla con la intensidad asignada del automático y con "
                 "la sección del cable (tabla de A3).",
                 "Medir también la corriente total a la entrada y compararla con el IGA y con la "
                 "potencia contratada."],
                "La corriente de uso tiene que quedar por debajo de la asignada del automático, y "
                "esa por debajo de la admisible del cable: «El límite de intensidad de corriente "
                "admisible en un conductor ha de quedar en todo caso garantizada por el "
                "dispositivo de protección utilizado».",
                "REBT, ITC-BT-22, apartado 1.1 a); ITC-BT-25, apartado 3"),

            _prueba(
                "B6", "Equilibrado de cargas (solo trifásico)",
                "Que las tres fases lleven una carga parecida.",
                ["Con la vivienda o el local en funcionamiento normal, medir con la pinza la "
                 "corriente de cada fase y la del neutro.",
                 "Anotar las diferencias y repartir circuitos si una fase va muy cargada y otra "
                 "casi vacía."],
                "«Para que se mantenga el mayor equilibrio posible en la carga de los conductores "
                "que forman parte de una instalación, se procurará que aquella quede repartida "
                "entre sus fases o conductores polares».",
                "REBT, ITC-BT-19, apartado 2.5"),

            _prueba(
                "B7", "Caída de tensión",
                "Que el cable no se «coma» la tensión hasta el punto más lejano.",
                ["Medir la tensión fase-neutro en el cuadro con el circuito cargado.",
                 "Sin cambiar la carga, medir la tensión en el punto de utilización más alejado de "
                 "ese circuito (con dos polímetros a la vez es más fiable; con uno, hay que medir "
                 "seguido y no tocar la carga).",
                 "La diferencia entre las dos medidas es la caída de tensión del circuito.",
                 "Pasar a porcentaje sobre 230 V: el 3 % son 6,9 V."],
                "Menos del 3 % de la tensión nominal para cualquier circuito interior de viviendas "
                "(el 3 % para alumbrado y el 5 % para otros usos en el resto de instalaciones "
                "interiores).",
                "REBT, ITC-BT-19, apartado 2.2.2; ITC-BT-25, apartado 3",
                limite="El reglamento define la caída de tensión por cálculo, con el circuito "
                       "cargado a la intensidad nominal de su automático. Medida así, con la carga "
                       "que haya, el resultado es orientativo: sirve para detectar una sección "
                       "corta o una conexión mala, no para sustituir el cálculo de la memoria."),
        ],
    },

    # ── 5. Bloque C: lo que no se puede hacer ────────────────────────────
    {
        "titulo": "Bloque C · Lo que no se puede comprobar con polímetro y pinza",
        "bloques": [
            {"tipo": "p", "texto":
                "Estos ensayos los pide la norma de verificación y **ninguno se puede hacer con "
                "este equipo**. Conviene decirlo por escrito al cliente: lo que se entrega es una "
                "revisión de seguridad, no la verificación reglamentaria completa."},
            {"tipo": "tabla", "titulo": "Ensayos que necesitan otro equipo",
             "cabecera": ["Ensayo", "Equipo", "Lo que exige el reglamento", "Fuente"],
             "filas": [
                 ["Resistencia de aislamiento",
                  "Megóhmetro (EN 61557-2)",
                  "Ensayo a 500 V cc y ≥ 0,5 MΩ en instalaciones de hasta 500 V "
                  "(250 V y ≥ 0,25 MΩ en MBTS/MBTP; 1.000 V y ≥ 1 MΩ por encima de 500 V)",
                  "ITC-BT-19, ap. 2.9, tabla 3"],
                 ["Rigidez dieléctrica",
                  "Equipo de ensayo de tensión",
                  "Resistir 1 minuto a 2U + 1.000 V, con un mínimo de 1.500 V, con los "
                  "receptores desconectados",
                  "ITC-BT-19, ap. 2.9"],
                 ["Resistencia de puesta a tierra",
                  "Telurómetro con picas (EN 61557-5)",
                  "RA × Ia ≤ 50 V en esquema TT. Comprobación al menos anual, en la época en que "
                  "el terreno esté más seco",
                  "ITC-BT-24, ap. 4.1.2; ITC-BT-18, ap. 12"],
                 ["Impedancia del bucle de defecto y corriente de cortocircuito presunta",
                  "Medidor de bucle (EN 61557-3)",
                  "Zs × Ia ≤ U0 en esquema TN, con tiempos de interrupción de 0,4 s a 230 V",
                  "ITC-BT-24, ap. 4.1.1, tabla 1"],
                 ["Tiempo y corriente de disparo del diferencial",
                  "Comprobador de diferenciales (EN 61557-6)",
                  "Que el diferencial corte con su corriente asignada y en el tiempo que exige el "
                  "esquema de la instalación",
                  "ITC-BT-24, ap. 4.1; ITC-BT-25, ap. 2.1"],
                 ["Resistencia de suelos y paredes",
                  "Megóhmetro con electrodo de ensayo",
                  "Solo en los casos en que la protección se basa en ello",
                  "Metodología UNE 20.460-6-61 (ITC-BT-05, ap. 3)"],
             ]},
            {"tipo": "p", "texto":
                "De la condición **RA × Ia ≤ 50 V** sale una cuenta que conviene tener en la "
                "cabeza: con un diferencial de 30 mA, la tierra cumpliría hasta "
                "50 / 0,03 = 1.666 Ω, mientras que con protección de 300 mA el límite baja a "
                "166 Ω. Es aritmética de la propia fórmula del reglamento, no un valor tabulado: "
                "el valor real hay que medirlo con telurómetro."},
        ],
    },

    # ── 6. Defectos ──────────────────────────────────────────────────────
    {
        "titulo": "Cómo se clasifica lo que se encuentra",
        "bloques": [
            {"tipo": "p", "texto":
                "El reglamento clasifica los defectos en muy graves, graves y leves. Usar esta "
                "misma clasificación en el informe que se entrega al cliente ahorra discusiones y "
                "deja claro qué hay que arreglar antes de dar luz."},
            {"tipo": "p", "texto":
                "**Defecto muy grave**: el que constituye un peligro inmediato para la seguridad "
                "de las personas o los bienes. Entre otros, el incumplimiento de las medidas "
                "contra contactos directos en cualquier tipo de instalación."},
            {"tipo": "p", "texto":
                "**Defecto grave**: el que no supone un peligro inmediato pero puede serlo al "
                "originarse un fallo. El reglamento enumera, sin ser exhaustivo:"},
            {"tipo": "lista", "puntos": [
                "Falta de conexiones equipotenciales, cuando éstas fueran requeridas.",
                "Inexistencia de medidas adecuadas de seguridad contra contactos indirectos.",
                "Falta de aislamiento de la instalación.",
                "Falta de protección adecuada contra cortocircuitos y sobrecargas en los "
                "conductores.",
                "Falta de continuidad de los conductores de protección.",
                "Valores elevados de resistencia de tierra en relación con las medidas de "
                "seguridad adoptadas.",
                "Defectos en la conexión de los conductores de protección a las masas.",
                "Sección insuficiente de los conductores de protección.",
                "Existencia de partes o puntos de la instalación cuya defectuosa ejecución pudiera "
                "ser origen de averías o daños.",
                "Naturaleza o características no adecuadas de los conductores utilizados.",
                "Falta de sección de los conductores en relación con las caídas de tensión "
                "admisibles.",
                "Falta de identificación de los conductores «neutro» y «de protección».",
                "Carencia del número de circuitos mínimos estipulados.",
                "La sucesiva reiteración o acumulación de defectos leves.",
            ]},
            {"tipo": "p", "texto":
                "**Defecto leve**: el que no supone peligro, no perturba el funcionamiento y su "
                "desviación respecto de lo reglamentado no tiene valor significativo."},
            {"tipo": "fuente", "texto": "REBT, ITC-BT-05, apartado 6."},
        ],
    },

    # ── 7. Papeles ───────────────────────────────────────────────────────
    {
        "titulo": "Quién verifica y qué papeles salen de aquí",
        "bloques": [
            {"tipo": "lista", "puntos": [
                "**La verificación previa a la puesta en servicio la hace la empresa instaladora "
                "que ejecuta la instalación** (ITC-BT-05, ap. 2.1).",
                "Las **inspecciones** las hacen Organismos de Control acreditados, y solo en las "
                "instalaciones de especial relevancia que lista el reglamento: industriales de más "
                "de 100 kW, locales de pública concurrencia, locales con riesgo de incendio o "
                "explosión, locales mojados de más de 25 kW, piscinas de más de 10 kW, quirófanos, "
                "alumbrado exterior de más de 5 kW y puntos de recarga que requieran proyecto "
                "(ITC-BT-05, ap. 4.1). **La vivienda particular no está en esa lista.**",
                "Las **inspecciones periódicas** son cada 5 años para lo que necesitó inspección "
                "inicial, y cada 10 años para las instalaciones comunes de edificios de viviendas "
                "de más de 100 kW de potencia total instalada (ITC-BT-05, ap. 4.2).",
                "La **puesta a tierra** se comprueba obligatoriamente al dar de alta la "
                "instalación y, después, al menos una vez al año en la época en que el terreno "
                "esté más seco; los electrodos se descubren para examinarlos al menos cada cinco "
                "años cuando el terreno no es favorable (ITC-BT-18, ap. 12).",
            ]},
            {"tipo": "p", "texto":
                "Para emitir el certificado de instalación eléctrica (el boletín) está la pestaña "
                "**Boletines** de este panel. Lo que se mide en una revisión como esta conviene "
                "dejarlo escrito, con fecha y con los valores, en las observaciones del propio "
                "certificado o en un informe aparte para el cliente."},
        ],
    },

    # ── 8. Hoja de campo ─────────────────────────────────────────────────
    {
        "titulo": "Hoja de campo",
        "bloques": [
            {"tipo": "p", "texto":
                "Para imprimir y rellenar a mano en la vivienda. Cada línea es una de las pruebas "
                "de los bloques A y B."},
            {"tipo": "tabla", "titulo": "Pruebas y valores medidos",
             "cabecera": ["Prueba", "Valor medido", "Límite", "¿Correcto?"],
             "filas": [
                 ["A1 · Composición del cuadro", "", "IGA ≥ 25 A · dif. 30 mA", ""],
                 ["A2 · Contactos directos", "", "Nada accesible", ""],
                 ["A3 · Circuitos y calibres", "", "Tabla ITC-BT-25", ""],
                 ["A4 · Colores", "", "Azul / amarillo-verde", ""],
                 ["A5 · Sección de protección", "", "Tabla ITC-BT-19", ""],
                 ["A6 · Conexiones y aprietes", "", "Sin empalmes al aire", ""],
                 ["A7 · Continuidad de protección", "", "Pocos ohmios", ""],
                 ["A8 · Equipotencial del baño", "", "Continuidad", ""],
                 ["A9 · Línea principal de tierra", "", "Continuidad", ""],
                 ["B1 · Tensión fase-neutro", "", "230 V", ""],
                 ["B1 · Tensión fase-tierra", "", "≈ fase-neutro", ""],
                 ["B1 · Tensión neutro-tierra", "", "Pocos voltios", ""],
                 ["B2 · Polaridad y corte omnipolar", "", "Corta fase y neutro", ""],
                 ["B3 · Botón de test del diferencial", "", "Dispara y rearma", ""],
                 ["B4 · Corriente de fuga total", "", "< 30 mA", ""],
                 ["B5 · Corriente por circuito", "", "< In del automático", ""],
                 ["B6 · Equilibrado (trifásico)", "", "Reparto parecido", ""],
                 ["B7 · Caída de tensión", "", "< 6,9 V (3 %)", ""],
             ]},
        ],
    },
]


DOCUMENTO = {
    "slug": "pruebas-cuadro-electrico-rebt",
    "titulo": "Pruebas de seguridad en un cuadro de vivienda",
    "subtitulo": "Qué se puede comprobar con polímetro y pinza amperimétrica, y qué exige el REBT",
    "resumen": "Las comprobaciones que se pueden hacer en el cuadro de una vivienda sin "
               "comprobador multifunción, con lo que pide el reglamento en cada una, qué cuenta "
               "como defecto grave y qué ensayos se quedan fuera por falta de equipo.",
    "actualizado": "2026-10-10",
    "equipo": EQUIPO,
    "secciones": SECCIONES,
    "fuentes": [FUENTES["rebt"], FUENTES["rd614"], FUENTES["fluke"]],
    "aviso": "Documento interno de Loureiro Soluciones. Recoge y cita el reglamento, pero no lo "
             "sustituye: ante cualquier duda manda el texto del REBT. Las medidas hechas con "
             "polímetro y pinza son indicativas y no completan la verificación reglamentaria "
             "previa a la puesta en servicio.",
}
