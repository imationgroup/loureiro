"""Test de seguridad: los puntos que se marcan y cómo se puntúan.

Es la guía «Pruebas de seguridad en un cuadro de vivienda»
(guia_pruebas_cuadro.py) puesta en forma de lista para ir marcando en la
vivienda: los mismos grupos A1…B7, con sus mismas fuentes. El bloque C son
los ensayos que la guía deja fuera porque piden otro equipo (megóhmetro,
telurómetro, medidor de bucle y comprobador de diferenciales): se apuntan
cuando se han hecho, y lo que no se haya hecho sale en el informe como
pendiente de completar.

Cada punto está escrito en positivo —lo que tiene que cumplirse— y lleva la
gravedad del defecto si no se cumple, con las tres clases del reglamento
(ITC-BT-05, apartado 6): muy grave, grave y leve. Lo que el reglamento
enumera como grave va como grave; lo que no enumera va como leve. Es el
criterio de esta herramienta: la clasificación final es del instalador.

La cuenta se hace aquí y solo aquí. El panel la pide mientras se rellena y el
PDF la vuelve a hacer al imprimir, así que no hay dos fórmulas que se puedan
ir separando.
"""

MUY_GRAVE, GRAVE, LEVE = "muy_grave", "grave", "leve"
OK, FALLO, NA = "ok", "fallo", "na"

GRAVEDADES = {MUY_GRAVE: "Muy grave", GRAVE: "Grave", LEVE: "Leve"}

# Lo que pesa cada punto en la nota. Un punto muy grave cuenta como cinco
# leves: la nota tiene que moverse con lo que importa, no con lo que abunda.
PESOS = {MUY_GRAVE: 10, GRAVE: 5, LEVE: 2}

# Con un defecto muy grave o grave la nota no pasa de aquí por muchos puntos
# buenos que haya alrededor: veinte comprobaciones correctas no compensan un
# borne en tensión al alcance de la mano.
TOPES = {MUY_GRAVE: 25, GRAVE: 60}

BLOQUES = [
    ("A", "Bloque A · Con el cuadro sin tensión"),
    ("B", "Bloque B · Con el cuadro en tensión"),
    ("C", "Bloque C · Ensayos con comprobador de instalaciones"),
]

# El bloque C es opcional: sin el equipo no se puede hacer, así que un punto
# suyo sin marcar no cuenta como pendiente. Lo que falte se dice en las
# recomendaciones del informe.
OPCIONAL = {"C"}

NOTAS_BLOQUE = {
    "C": "Estos ensayos no se pueden hacer con polímetro y pinza. Apunta aquí los que hayas "
         "hecho con el equipo de medida; los que dejes en blanco no bajan la nota y salen en "
         "el informe como ensayos por completar.",
}


def _punto(clave, texto, gravedad, defecto, recomendacion, porque, na=False, medidas=None,
           auto=False):
    """Un punto de la lista.

    `medidas` son las casillas de valor que lleva al lado (clave, etiqueta,
    unidad). Con `auto` el resultado no se marca a mano: sale de esos valores.
    """
    return {"clave": clave, "texto": texto, "gravedad": gravedad, "defecto": defecto,
            "recomendacion": recomendacion, "porque": porque, "na": na,
            "medidas": [{"clave": c, "etiqueta": e, "unidad": u} for c, e, u in (medidas or [])],
            "auto": auto}


GRUPOS = [
    # ── Bloque A: sin tensión ────────────────────────────────────────────
    {"bloque": "A", "numero": "A1", "titulo": "Composición del cuadro y de las protecciones",
     "fuente": "REBT, ITC-BT-25, apartados 2.1 y 2.3.2; ITC-BT-17, apartados 1.2 y 1.3",
     "puntos": [
         _punto("a1_iga", "Hay interruptor general automático (IGA) de corte omnipolar",
                GRAVE,
                "No hay interruptor general automático de corte omnipolar.",
                "Instalar un IGA de corte omnipolar, con accionamiento manual y protección "
                "contra sobrecargas y cortocircuitos.",
                "Sin IGA no hay nada que proteja la instalación entera contra una sobrecarga "
                "o un cortocircuito, ni una forma de cortar toda la vivienda de un gesto."),
         _punto("a1_iga_a", "El IGA es de 25 A como mínimo",
                LEVE,
                "El IGA es de menos de 25 A.",
                "Sustituir el IGA por uno de 25 A o más, comprobando antes que la derivación "
                "individual lo admite.",
                "25 A es el mínimo que fija el reglamento para una vivienda; por debajo, el "
                "general salta con el uso normal de la casa.",
                medidas=[("iga_a", "IGA", "A")], auto=True),
         _punto("a1_icp", "El IGA es independiente del ICP de la compañía",
                LEVE,
                "El ICP de la compañía está haciendo de interruptor general.",
                "Instalar un IGA propio, aparte del ICP.",
                "El ICP limita la potencia contratada, no protege la instalación: son dos "
                "aparatos distintos y el reglamento pide los dos."),
         _punto("a1_dif", "Todos los circuitos están protegidos por diferencial",
                GRAVE,
                "Hay circuitos sin protección diferencial.",
                "Instalar diferencial en todos los circuitos que no lo tienen.",
                "El diferencial es lo que corta cuando la corriente se deriva a tierra a "
                "través de un aparato averiado o de una persona. Un circuito sin él no tiene "
                "protección contra contactos indirectos."),
         _punto("a1_dif_ma", "Los diferenciales son de 30 mA como máximo",
                GRAVE,
                "Hay diferenciales de sensibilidad superior a 30 mA.",
                "Cambiar los diferenciales por otros de 30 mA.",
                "Por encima de 30 mA el diferencial protege la instalación contra incendios, "
                "pero ya no protege a una persona que toca una parte en tensión.",
                medidas=[("dif_ma", "Sensibilidad (la mayor)", "mA")], auto=True),
         _punto("a1_dif_in", "La intensidad de cada diferencial es igual o mayor que la del IGA",
                LEVE,
                "Hay diferenciales de menos intensidad asignada que el IGA.",
                "Sustituirlos por diferenciales de intensidad igual o superior a la del IGA.",
                "Un diferencial más pequeño que el general puede llegar a llevar más "
                "corriente de la que aguanta sin que nada lo proteja a él."),
         _punto("a1_circ_dif", "Hay al menos un diferencial por cada cinco circuitos",
                LEVE,
                "Hay más de cinco circuitos colgando de un mismo diferencial.",
                "Añadir diferenciales y repartir los circuitos, cinco como mucho en cada uno.",
                "Con demasiados circuitos en un diferencial se suman las fugas de todos y "
                "salta sin avería, y cuando salta deja media casa sin energía.",
                medidas=[("n_circuitos", "Circuitos", ""), ("n_diferenciales", "Diferenciales", "")],
                auto=True),
         _punto("a1_pia", "Cada circuito sale de su propio automático",
                GRAVE,
                "Hay circuitos sin automático propio.",
                "Poner un automático de corte omnipolar a cada circuito, del calibre de su cable.",
                "El automático es lo que protege el cable. Dos circuitos en uno solo dejan "
                "al menos un cable sin la protección que le corresponde."),
     ]},

    {"bloque": "A", "numero": "A2", "titulo": "Protección contra contactos directos",
     "fuente": "REBT, ITC-BT-05, apartado 6.1; ITC-BT-24, apartado 3",
     "puntos": [
         _punto("a2_cuadro", "Cuadro cerrado: tapas en los huecos y ninguna parte activa accesible",
                MUY_GRAVE,
                "En el cuadro hay partes en tensión accesibles sin herramienta.",
                "Cerrar el cuadro: tapas ciegas en los huecos libres y bornes y embarrados "
                "cubiertos. Si la envolvente está rota, cambiarla.",
                "Cualquiera que abra la puerta del cuadro, un niño incluido, puede tocar "
                "230 V con la mano."),
         _punto("a2_mecanismos", "Sin enchufes o mecanismos rotos, cajas sin tapa ni empalmes al aire",
                MUY_GRAVE,
                "Hay mecanismos rotos, cajas sin tapa o empalmes al aire.",
                "Sustituir los mecanismos rotos, tapar las cajas y meter los empalmes en "
                "cajas de registro.",
                "Son partes en tensión al alcance de la mano en el uso diario de la casa."),
         _punto("a2_aislamiento", "Aislamiento de los cables sin daños en la entrada al cuadro",
                MUY_GRAVE,
                "Hay conductores con el aislamiento dañado.",
                "Sustituir los tramos dañados y proteger la entrada de cables al cuadro.",
                "Un cable pelado es una parte activa al descubierto: riesgo de contacto y de "
                "cortocircuito contra la envolvente."),
     ]},

    {"bloque": "A", "numero": "A3", "titulo": "Circuitos mínimos y calibres",
     "fuente": "REBT, ITC-BT-25, apartados 2.3 y 3, tabla 1; ITC-BT-05, apartado 6.2",
     "puntos": [
         _punto("a3_minimos", "Están los cinco circuitos mínimos (C1 a C5)",
                GRAVE,
                "Faltan circuitos de los mínimos de una vivienda.",
                "Separar los circuitos hasta tener al menos C1 iluminación, C2 tomas, C3 "
                "cocina y horno, C4 lavadora, lavavajillas y termo, y C5 baño y cocina.",
                "Con menos circuitos de los debidos se cargan sobre un mismo cable aparatos "
                "que no deberían ir juntos, y el cable trabaja al límite."),
         _punto("a3_calibres", "El calibre de cada automático corresponde a la sección de su cable",
                GRAVE,
                "Hay automáticos de más calibre del que admite la sección de su cable.",
                "Ajustar cada automático a su cable (10 A para 1,5 mm², 16 A para 2,5 mm², "
                "20 A para 4 mm², 25 A para 6 mm²) o aumentar la sección.",
                "Un automático mayor que su cable no salta a tiempo: el cable se calienta "
                "antes de que la protección actúe, y así empiezan los incendios."),
         _punto("a3_extra", "Calefacción, aire acondicionado, secadora o recarga van en circuito aparte",
                LEVE,
                "Hay receptores de mucha potencia colgados de circuitos de uso general.",
                "Sacar un circuito propio para cada uno de esos receptores.",
                "Son aparatos de mucho consumo durante muchas horas: en un circuito "
                "compartido lo sobrecargan y hacen saltar el automático.",
                na=True),
     ]},

    {"bloque": "A", "numero": "A4", "titulo": "Identificación de los conductores",
     "fuente": "REBT, ITC-BT-19, apartado 2.2.4; ITC-BT-05, apartado 6.2",
     "puntos": [
         _punto("a4_colores", "Neutro azul claro y protección amarillo-verde",
                GRAVE,
                "El neutro o el conductor de protección no se reconocen por su color.",
                "Identificar los conductores: sustituirlos o, como mínimo, marcarlos en "
                "todos sus extremos.",
                "Quien toque la instalación después se fía del color. Un conductor mal "
                "identificado acaba conectado donde no es."),
         _punto("a4_av", "El amarillo-verde solo se usa como protección",
                GRAVE,
                "Hay conductores amarillo-verde usados como fase o como neutro.",
                "Sustituir esos conductores por otros del color que corresponde.",
                "El amarillo-verde es el cable que todo el mundo da por seguro: si lleva "
                "tensión, el accidente es cuestión de tiempo."),
     ]},

    {"bloque": "A", "numero": "A5", "titulo": "Sección del conductor de protección",
     "fuente": "REBT, ITC-BT-19, apartado 2.3 y tabla 2; ITC-BT-18, apartado 3.4; "
               "ITC-BT-05, apartado 6.2",
     "puntos": [
         _punto("a5_seccion", "La sección del conductor de protección es suficiente para su fase",
                GRAVE,
                "Hay conductores de protección de sección insuficiente.",
                "Sustituirlos por la sección de la tabla: la misma que la fase hasta 16 mm².",
                "El conductor de protección tiene que aguantar la corriente de un defecto "
                "hasta que salte la protección. Si es corto de sección, se quema antes."),
         _punto("a5_intercalado", "Nada intercalado en el conductor de protección y conexiones accesibles",
                GRAVE,
                "El conductor de protección tiene aparatos intercalados o conexiones que no "
                "se pueden revisar.",
                "Dejar el conductor de protección continuo, sin interruptores ni fusibles, y "
                "con sus conexiones a la vista en cajas.",
                "La tierra no se puede cortar nunca: un interruptor en ese cable deja las "
                "masas sin protección sin que nadie lo note."),
     ]},

    {"bloque": "A", "numero": "A6", "titulo": "Conexiones y aprietes",
     "fuente": "REBT, ITC-BT-19, apartado 2.11; ITC-BT-05, apartado 6.2",
     "puntos": [
         _punto("a6_bornes", "Bornes apretados: ningún conductor se mueve al tirar",
                GRAVE,
                "Hay bornes flojos.",
                "Reapretar todos los bornes del cuadro y rehacer los que estén dañados.",
                "Un borne flojo se calienta con el paso de la corriente. Es la causa más "
                "corriente de un cuadro quemado."),
         _punto("a6_retorcidos", "Sin uniones por retorcimiento o arrollamiento de conductores",
                GRAVE,
                "Hay empalmes hechos retorciendo los conductores.",
                "Rehacer esos empalmes con bornes o regletas de conexión.",
                "El reglamento no los permite en ningún caso: con el tiempo se aflojan, "
                "se calientan y arden dentro de la caja."),
         _punto("a6_cajas", "Los empalmes están dentro de cajas de registro",
                GRAVE,
                "Hay empalmes fuera de caja: dentro de tubos o enterrados en la pared.",
                "Llevar los empalmes a cajas de registro accesibles.",
                "Un empalme que no se puede ver no se puede revisar, y si se calienta lo "
                "hace contra el yeso o dentro del tubo."),
         _punto("a6_calor", "Sin señales de calentamiento (bornes oscuros, aislamiento duro, olor)",
                GRAVE,
                "Hay señales de calentamiento en el cuadro.",
                "Localizar el punto que se calienta, sustituir el aparato o el tramo de "
                "cable afectado y revisar la carga de ese circuito.",
                "El calentamiento ya ha ocurrido: ese punto ha estado trabajando por encima "
                "de lo que aguanta y volverá a hacerlo."),
     ]},

    {"bloque": "A", "numero": "A7", "titulo": "Continuidad del conductor de protección",
     "fuente": "REBT, ITC-BT-05, apartado 6.2; ITC-BT-18, apartado 3.4",
     "puntos": [
         _punto("a7_enchufes", "La tierra llega a todas las bases de enchufe y masas metálicas",
                GRAVE,
                "Hay bases de enchufe o masas metálicas sin continuidad de tierra.",
                "Reponer el conductor de protección hasta esos puntos y revisar sus "
                "conexiones en las cajas intermedias.",
                "Un enchufe sin tierra deja la carcasa del aparato sin protección: si se "
                "deriva, queda en tensión y el diferencial no salta hasta que alguien la toca.",
                medidas=[("pe_ohm", "Peor medida", "Ω")]),
         _punto("a7_bano_cocina", "La tierra llega a los enchufes del baño y de la cocina",
                GRAVE,
                "Falta continuidad de tierra en el baño o en la cocina.",
                "Reponer el conductor de protección en esos circuitos.",
                "Son los sitios donde se juntan agua, suelo mojado y aparatos metálicos: "
                "donde una derivación hace más daño."),
     ]},

    {"bloque": "A", "numero": "A8", "titulo": "Conexiones equipotenciales del cuarto de baño",
     "fuente": "REBT, ITC-BT-27, apartado 2.2; ITC-BT-18, apartado 8; ITC-BT-05, apartado 6.2",
     "puntos": [
         _punto("a8_equip", "Tuberías y partes metálicas del baño unidas a la protección",
                GRAVE,
                "Faltan conexiones equipotenciales en el cuarto de baño.",
                "Unir al conductor de protección las tuberías metálicas, la bañera o el "
                "plato metálicos y las demás partes metálicas accesibles.",
                "Sin esa unión puede aparecer tensión entre dos partes metálicas que se "
                "tocan a la vez con el cuerpo mojado, por ejemplo el grifo y la bañera.",
                na=True),
         _punto("a8_conductor", "El conductor equipotencial existe, está apretado y tiene sección",
                GRAVE,
                "El conductor de equipotencialidad falta, está suelto o es de sección escasa.",
                "Tender un conductor de equipotencialidad de la sección debida y apretar "
                "sus conexiones.",
                "Que haya continuidad «por casualidad» a través de una tubería no vale: el "
                "día que se cambie un tramo por plástico, la unión desaparece.",
                na=True),
     ]},

    {"bloque": "A", "numero": "A9", "titulo": "Línea principal de tierra y punto de puesta a tierra",
     "fuente": "REBT, ITC-BT-26, apartados 3.3 y 3.4; ITC-BT-18",
     "puntos": [
         _punto("a9_continuidad", "Hay continuidad entre el borne de tierra del cuadro y la tierra del edificio",
                GRAVE,
                "El cuadro no tiene continuidad con la puesta a tierra del edificio.",
                "Reponer la línea de tierra entre el cuadro y el punto de puesta a tierra.",
                "Sin esa unión toda la tierra de la vivienda está al aire: los enchufes "
                "tienen su cable, pero no lleva a ningún sitio."),
         _punto("a9_tuberias", "No se usan tuberías de agua, gas o calefacción como tierra",
                GRAVE,
                "Se están usando tuberías como conductor de tierra.",
                "Tender un conductor de tierra propio hasta el punto de puesta a tierra.",
                "El reglamento lo prohíbe expresamente: pone en tensión las tuberías de "
                "toda la finca y deja de funcionar el día que cambian un tramo."),
         _punto("a9_accesible", "El punto de puesta a tierra es accesible y desmontable",
                LEVE,
                "El punto de puesta a tierra no es accesible.",
                "Dejar un borne de puesta a tierra accesible y desmontable.",
                "Sin él no se puede medir la resistencia de tierra, que es una comprobación "
                "obligatoria.",
                na=True),
     ]},

    # ── Bloque B: con tensión ────────────────────────────────────────────
    {"bloque": "B", "numero": "B1", "titulo": "Tensiones en el cuadro",
     "fuente": "REBT, artículo 4; ITC-BT-26, apartado 2. Margen de la tensión de "
               "suministro: Real Decreto 1955/2000, artículo 104",
     "puntos": [
         _punto("b1_fn", "La tensión entre fase y neutro está en 230 V ± 7 %",
                LEVE,
                "La tensión entre fase y neutro está fuera del margen de suministro.",
                "Repetir la medida a distintas horas y, si se mantiene, reclamar a la "
                "empresa distribuidora.",
                "Con la tensión fuera de margen los aparatos trabajan forzados y duran "
                "menos. No es un defecto de la vivienda, sino del suministro.",
                medidas=[("v_fn", "Fase-neutro", "V")], auto=True),
         _punto("b1_ft", "Entre fase y tierra da prácticamente lo mismo que entre fase y neutro",
                GRAVE,
                "La tensión entre fase y tierra es claramente menor que entre fase y neutro.",
                "Revisar la conexión de la tierra del cuadro y la línea principal de tierra.",
                "Es la señal de una tierra mal conectada: está, pero no serviría para "
                "desviar la corriente de un defecto.",
                medidas=[("v_ft", "Fase-tierra", "V")]),
         _punto("b1_nt", "Entre neutro y tierra hay solo unos pocos voltios",
                GRAVE,
                "La tensión entre neutro y tierra es alta.",
                "Revisar el apriete del neutro en el cuadro y en la derivación individual.",
                "Delata un neutro flojo. Un neutro que se suelta deja en la vivienda "
                "tensiones muy por encima de 230 V y quema los aparatos.",
                medidas=[("v_nt", "Neutro-tierra", "V")]),
     ]},

    {"bloque": "B", "numero": "B2", "titulo": "Polaridad y corte omnipolar",
     "fuente": "REBT, ITC-BT-19, apartado 2.7; ITC-BT-25, apartado 2.1",
     "puntos": [
         _punto("b2_neutro", "Ningún interruptor unipolar corta el neutro",
                GRAVE,
                "Hay interruptores unipolares cortando el neutro.",
                "Pasar el corte a la fase o cambiar el aparato por uno omnipolar.",
                "Al cortar solo el neutro el circuito parece apagado, pero la fase sigue "
                "llegando al punto de luz o al enchufe."),
         _punto("b2_omnipolar", "Cada automático corta la fase y el neutro de su circuito",
                LEVE,
                "Hay automáticos que solo cortan la fase.",
                "Sustituirlos por automáticos de corte omnipolar.",
                "El reglamento pide corte omnipolar en el cuadro: con el automático bajado "
                "no debe quedar ningún conductor del circuito unido a la red."),
         _punto("b2_polaridad", "Fase y neutro no están cruzados en las bases comprobadas",
                LEVE,
                "Hay bases con la fase y el neutro cruzados.",
                "Corregir la conexión en la base o en la caja de la que sale.",
                "Indica una conexión hecha sin cuidado, y conviene revisar el resto de ese "
                "circuito."),
     ]},

    {"bloque": "B", "numero": "B3", "titulo": "Ensayo funcional del diferencial",
     "fuente": "REBT, ITC-BT-05, apartado 3 (metodología UNE 20.460-6-61)",
     "puntos": [
         _punto("b3_dispara", "Cada diferencial dispara al pulsar el botón de test",
                GRAVE,
                "Hay diferenciales que no disparan con el botón de test.",
                "Sustituir de inmediato el diferencial que no dispara.",
                "Un diferencial que no dispara con su propio botón no va a disparar con una "
                "derivación real: ese circuito está sin protección."),
         _punto("b3_rearma", "Cada diferencial rearma y vuelve a dar servicio",
                LEVE,
                "Hay diferenciales que no rearman bien.",
                "Sustituir el diferencial y, si salta al rearmar, buscar la fuga del circuito.",
                "Un mecanismo que no rearma bien está al final de su vida, o hay una fuga "
                "real que lo está haciendo saltar."),
     ]},

    {"bloque": "B", "numero": "B4", "titulo": "Corriente de fuga con la pinza",
     "fuente": "REBT, ITC-BT-19, apartado 2.9",
     "puntos": [
         _punto("b4_fuga", "La corriente de fuga está por debajo de la sensibilidad del diferencial",
                GRAVE,
                "La corriente de fuga alcanza o supera la sensibilidad del diferencial.",
                "Medir circuito por circuito hasta localizar la fuga y reparar el cable o "
                "el aparato que la provoca.",
                "Esa corriente se está escapando a tierra por un aislamiento dañado o un "
                "aparato averiado: es el fallo que acaba en una descarga o en un incendio.",
                medidas=[("fuga_ma", "Fuga total", "mA")], auto=True),
     ]},

    {"bloque": "B", "numero": "B5", "titulo": "Corriente de carga de cada circuito",
     "fuente": "REBT, ITC-BT-22, apartado 1.1 a); ITC-BT-25, apartado 3",
     "puntos": [
         _punto("b5_carga", "La corriente de cada circuito queda por debajo de la de su automático",
                LEVE,
                "Hay circuitos trabajando al límite de su automático.",
                "Repartir los aparatos entre circuitos o sacar un circuito nuevo.",
                "Un circuito siempre al límite calienta el cable y los bornes aunque el "
                "automático no llegue a saltar."),
         _punto("b5_total", "La corriente total queda por debajo del IGA",
                LEVE,
                "El consumo total se acerca a la intensidad del IGA o la supera.",
                "Revisar la potencia contratada y el calibre del IGA frente al uso real.",
                "El general salta en cuanto coinciden varios aparatos, y la derivación "
                "individual trabaja al límite.",
                medidas=[("i_total", "Total", "A")]),
     ]},

    {"bloque": "B", "numero": "B6", "titulo": "Equilibrado de cargas (solo trifásico)",
     "fuente": "REBT, ITC-BT-19, apartado 2.5",
     "puntos": [
         _punto("b6_equilibrio", "La carga está repartida entre las tres fases",
                LEVE,
                "Las fases están muy descompensadas.",
                "Repartir los circuitos entre las fases.",
                "Una fase muy cargada y otra casi vacía hacen saltar el general con la "
                "mitad de la potencia contratada.",
                na=True),
     ]},

    {"bloque": "B", "numero": "B7", "titulo": "Caída de tensión",
     "fuente": "REBT, ITC-BT-19, apartado 2.2.2; ITC-BT-25, apartado 3",
     "puntos": [
         _punto("b7_caida", "La caída de tensión hasta el punto más alejado es menor del 3 %",
                GRAVE,
                "La caída de tensión supera el 3 %.",
                "Revisar las conexiones de ese circuito y, si están bien, aumentar la "
                "sección del cable.",
                "Tensión que se pierde es calor en el cable o en un empalme: señal de "
                "sección corta o de una conexión mala.",
                medidas=[("v_cuadro", "En el cuadro", "V"), ("v_lejos", "En el punto más lejano", "V")],
                auto=True),
     ]},

    # ── Bloque C: con comprobador de instalaciones ───────────────────────
    {"bloque": "C", "numero": "C1", "titulo": "Resistencia de aislamiento",
     "falta": "la resistencia de aislamiento",
     "fuente": "REBT, ITC-BT-19, apartado 2.9, tabla 3; ITC-BT-05, apartado 6.2",
     "puntos": [
         _punto("c1_aislamiento", "La resistencia de aislamiento es de 0,5 MΩ como mínimo "
                                  "(megóhmetro, 500 V cc)",
                GRAVE,
                "La resistencia de aislamiento está por debajo de 0,5 MΩ.",
                "Medir circuito por circuito, con los receptores desconectados, hasta dar con "
                "el tramo o el aparato que baja el aislamiento, y sustituirlo.",
                "Un aislamiento bajo es corriente que se escapa por donde no debe: acaba en "
                "una derivación, en disparos del diferencial o en un calentamiento.",
                medidas=[("aisl_mohm", "Peor medida", "MΩ")], auto=True),
     ]},

    {"bloque": "C", "numero": "C2", "titulo": "Resistencia de puesta a tierra",
     "falta": "la resistencia de puesta a tierra",
     "fuente": "REBT, ITC-BT-24, apartado 4.1.2; ITC-BT-18, apartados 9 y 12; "
               "ITC-BT-05, apartado 6.2",
     "puntos": [
         _punto("c2_tierra", "La resistencia de tierra cumple RA × Ia ≤ 50 V con el "
                             "diferencial instalado (telurómetro)",
                GRAVE,
                "La resistencia de puesta a tierra es demasiado alta para el diferencial "
                "instalado.",
                "Mejorar la puesta a tierra (más picas o más conductor enterrado) y revisar "
                "la línea principal de tierra, hasta bajar la resistencia.",
                "Con una tierra alta, la carcasa de un aparato averiado puede quedar a una "
                "tensión peligrosa sin que el diferencial llegue a saltar.",
                medidas=[("tierra_ohm", "Resistencia de tierra", "Ω")], auto=True),
     ]},

    {"bloque": "C", "numero": "C3",
     "titulo": "Impedancia de bucle y corriente de cortocircuito presunta",
     "falta": "la impedancia de bucle",
     "fuente": "REBT, ITC-BT-24, apartado 4.1; ITC-BT-22, apartado 1.1; ITC-BT-05, apartado 6.2",
     "puntos": [
         _punto("c3_bucle", "La impedancia de bucle medida asegura el disparo de las "
                            "protecciones, y su poder de corte cubre el cortocircuito presunto",
                GRAVE,
                "La impedancia de bucle o la corriente de cortocircuito presunta no son "
                "compatibles con las protecciones instaladas.",
                "Revisar las conexiones y la sección de ese circuito, y adecuar las "
                "protecciones a la corriente de cortocircuito medida.",
                "Si el bucle tiene demasiada impedancia, un defecto no hace saltar la "
                "protección a tiempo; si el cortocircuito supera el poder de corte, el "
                "automático no es capaz de abrirlo.",
                medidas=[("zs_ohm", "Impedancia de bucle", "Ω"),
                         ("icc_a", "Cortocircuito presunto", "A")]),
     ]},

    {"bloque": "C", "numero": "C4", "titulo": "Tiempo y corriente de disparo de los diferenciales",
     "falta": "el tiempo y la corriente de disparo de los diferenciales",
     "fuente": "REBT, ITC-BT-24, apartado 4.1; ITC-BT-25, apartado 2.1; ITC-BT-05, apartado 6.2. "
               "Tiempos de disparo: UNE-EN 61008-1",
     "puntos": [
         _punto("c4_corriente", "Cada diferencial dispara sin superar su sensibilidad",
                GRAVE,
                "Hay diferenciales que necesitan más corriente que su sensibilidad para disparar.",
                "Sustituir el diferencial.",
                "Un diferencial de 30 mA que no salta hasta pasados los 30 mA ya no protege "
                "a una persona, aunque el botón de test lo haga disparar.",
                medidas=[("disparo_ma", "Corriente de disparo (la mayor)", "mA")], auto=True),
         _punto("c4_tiempo", "Cada diferencial dispara en el tiempo debido (300 ms como máximo "
                             "a su sensibilidad, en los de tipo general)",
                GRAVE,
                "Hay diferenciales que tardan demasiado en disparar.",
                "Sustituir el diferencial.",
                "La protección de una persona depende de cuánto dura la descarga: un "
                "diferencial lento corta, pero tarde.",
                medidas=[("disparo_ms", "Tiempo de disparo (el mayor)", "ms")]),
     ]},
]

PUNTOS = {p["clave"]: p for g in GRUPOS for p in g["puntos"]}
MEDIDAS = {m["clave"] for p in PUNTOS.values() for m in p["medidas"]}

OPCIONALES = {p["clave"] for g in GRUPOS if g["bloque"] in OPCIONAL for p in g["puntos"]}

# La recomendación que cierra el informe mientras quede algún ensayo del
# bloque C sin hacer; lleva dentro cuáles.
COMPLETAR = "Completar la revisión con un comprobador de instalaciones: falta por medir %s."

NIVELES = {
    "peligro": (
        "Peligro inmediato",
        "Hay defectos muy graves: partes en tensión que se pueden tocar. El reglamento los "
        "define como un peligro inmediato para las personas o los bienes, así que hay que "
        "actuar antes de seguir usando la instalación con normalidad."),
    "deficiente": (
        "Instalación con defectos graves",
        "No hay un peligro inmediato, pero sí defectos graves: los que pasan a serlo en cuanto "
        "se produce un fallo, sea un aparato que se avería, un aislamiento que cede o una "
        "sobrecarga. La instalación funciona, pero ha perdido protecciones con las que cuenta, "
        "y conviene corregirlos sin esperar a que ese fallo llegue."),
    "mejorable": (
        "Instalación aceptable, con defectos leves",
        "Solo se han encontrado defectos leves, que no suponen peligro ni impiden usar la "
        "instalación. Conviene corregirlos igualmente: el reglamento trata la acumulación de "
        "defectos leves como un defecto grave."),
    "correcta": (
        "Sin defectos en lo comprobado",
        "No se ha encontrado ningún defecto en las comprobaciones hechas."),
    "sin_datos": (
        "Sin comprobaciones todavía",
        "Marca los puntos de la lista para obtener la puntuación."),
}


def plantilla() -> dict:
    """La lista tal como la pinta el panel: bloques, grupos y puntos."""
    return {
        "bloques": [{"clave": clave, "titulo": titulo, "nota": NOTAS_BLOQUE.get(clave, ""),
                     "grupos": [g for g in GRUPOS if g["bloque"] == clave]}
                    for clave, titulo in BLOQUES],
        "gravedades": GRAVEDADES,
    }


def limpiar(respuestas) -> dict:
    """Deja solo lo que es de la lista: puntos y medidas conocidos, estados válidos."""
    respuestas = respuestas if isinstance(respuestas, dict) else {}
    estados = respuestas.get("estados") or {}
    valores = respuestas.get("valores") or {}
    return {
        "estados": {k: v for k, v in estados.items()
                    if k in PUNTOS and not PUNTOS[k]["auto"]
                    and (v in (OK, FALLO) or (v == NA and PUNTOS[k]["na"]))},
        "valores": {k: str(v).strip()[:20] for k, v in valores.items()
                    if k in MEDIDAS and str(v or "").strip()},
    }


def _num(texto):
    """El número que se ha escrito, con coma o con punto. None si no lo es."""
    try:
        return float(str(texto).replace(",", ".").replace(" ", ""))
    except (TypeError, ValueError):
        return None


def _es(n: float) -> str:
    return ("%.1f" % n).replace(".", ",").replace(",0", "")


def _automatico(clave: str, valores: dict) -> tuple[str | None, str]:
    """El resultado de un punto que sale de sus medidas, y con qué cuenta sale.

    Sin las medidas hechas no hay resultado: el punto queda sin comprobar.
    """
    v = {k: _num(valores.get(k)) for k in MEDIDAS}

    if clave == "a1_iga_a" and v["iga_a"] is not None:
        return (OK if v["iga_a"] >= 25 else FALLO), "IGA de %s A" % _es(v["iga_a"])

    if clave == "a1_dif_ma" and v["dif_ma"] is not None and v["dif_ma"] > 0:
        return (OK if v["dif_ma"] <= 30 else FALLO), "diferencial de %s mA" % _es(v["dif_ma"])

    if clave == "a1_circ_dif" and v["n_circuitos"] is not None and v["n_diferenciales"]:
        hacen_falta = -(-int(v["n_circuitos"]) // 5)      # uno por cada cinco, hacia arriba
        return ((OK if v["n_diferenciales"] >= hacen_falta else FALLO),
                "%d circuitos y %d %s (%s %d)"
                % (v["n_circuitos"], v["n_diferenciales"],
                   "diferencial" if v["n_diferenciales"] == 1 else "diferenciales",
                   "hace falta" if hacen_falta == 1 else "hacen falta", hacen_falta))

    if clave == "b1_fn" and v["v_fn"] is not None:
        # 230 V ± 7 %: de 213,9 a 246,1 V.
        return (OK if 213.9 <= v["v_fn"] <= 246.1 else FALLO), "%s V" % _es(v["v_fn"])

    if clave == "b4_fuga" and v["fuga_ma"] is not None:
        # Contra la sensibilidad que se haya apuntado en A1; si no, 30 mA.
        limite = v["dif_ma"] if v["dif_ma"] and v["dif_ma"] > 0 else 30
        return ((OK if v["fuga_ma"] < limite else FALLO),
                "%s mA de fuga con diferencial de %s mA" % (_es(v["fuga_ma"]), _es(limite)))

    if clave == "b7_caida" and v["v_cuadro"] is not None and v["v_lejos"] is not None:
        # Sobre 230 V, como en la guía: el 3 % son 6,9 V.
        caida = v["v_cuadro"] - v["v_lejos"]
        return ((OK if caida < 6.9 else FALLO),
                "caen %s V, el %s %%" % (_es(caida), _es(caida / 230 * 100)))

    if clave == "c1_aislamiento":
        # El megóhmetro da «>200» cuando se sale de escala: vale como ese valor.
        escrito = str(valores.get("aisl_mohm") or "").strip()
        aisl = _num(escrito.lstrip(">≥ "))
        if aisl is not None:
            return ((OK if aisl >= 0.5 else FALLO),
                    "%s%s MΩ" % ("más de " if escrito[:1] in (">", "≥") else "", _es(aisl)))

    if clave == "c2_tierra" and v["tierra_ohm"] is not None:
        # RA × Ia ≤ 50 V, con la sensibilidad apuntada en A1; si no, 30 mA.
        ia = v["dif_ma"] if v["dif_ma"] and v["dif_ma"] > 0 else 30
        limite = 50 / (ia / 1000)
        return ((OK if v["tierra_ohm"] <= limite else FALLO),
                "%s Ω con diferencial de %s mA (máximo %s Ω)"
                % (_es(v["tierra_ohm"]), _es(ia), _es(int(limite))))

    if clave == "c4_corriente" and v["disparo_ma"] is not None:
        limite = v["dif_ma"] if v["dif_ma"] and v["dif_ma"] > 0 else 30
        return ((OK if v["disparo_ma"] <= limite else FALLO),
                "dispara a %s mA un diferencial de %s mA" % (_es(v["disparo_ma"]), _es(limite)))

    return None, ""


# Con un solo diferencial en la vivienda el daño es otro: no se queda sin
# energía media casa, sino toda, y no hay forma de acotar dónde está la avería.
UN_DIFERENCIAL = ("Con todos los circuitos en un único diferencial se suman las fugas de todos y "
                  "salta sin avería, y cuando salta deja toda la casa sin energía, dificultando "
                  "además la localización de la avería.")


def _porque(p: dict, valores: dict) -> str:
    """El porqué de un defecto, ajustado a lo medido cuando cambia lo que se dice."""
    if p["clave"] == "a1_circ_dif" and _num(valores.get("n_diferenciales")) == 1:
        return UN_DIFERENCIAL
    return p["porque"]


def _siempre(estados: dict) -> str:
    """Qué ensayos del bloque C quedan por hacer, dicho como recomendación."""
    faltan = [g["falta"] for g in GRUPOS if g["bloque"] in OPCIONAL
              and any(p["clave"] not in estados for p in g["puntos"])]
    if not faltan:
        return ""
    lista = faltan[0] if len(faltan) == 1 else ", ".join(faltan[:-1]) + " y " + faltan[-1]
    return COMPLETAR % lista


def evaluar(respuestas) -> dict:
    """La nota del test, los defectos por gravedad y qué hacer con cada uno."""
    r = limpiar(respuestas)
    estados, detalles = {}, {}
    for clave, p in PUNTOS.items():
        if p["auto"]:
            estado, detalle = _automatico(clave, r["valores"])
            if detalle:
                detalles[clave] = detalle
        else:
            estado = r["estados"].get(clave)
        if estado:
            estados[clave] = estado

    defectos = {MUY_GRAVE: [], GRAVE: [], LEVE: []}
    bien = mal = 0
    for g in GRUPOS:
        for p in g["puntos"]:
            estado = estados.get(p["clave"])
            if estado == OK:
                bien += PESOS[p["gravedad"]]
            elif estado == FALLO:
                mal += PESOS[p["gravedad"]]
                defectos[p["gravedad"]].append({
                    "clave": p["clave"], "numero": g["numero"], "gravedad": p["gravedad"],
                    "defecto": p["defecto"], "recomendacion": p["recomendacion"],
                    "porque": _porque(p, r["valores"]), "fuente": g["fuente"],
                    "detalle": detalles.get(p["clave"], ""),
                })

    # Los ensayos del bloque C cuentan cuando se han hecho; sin hacer no son
    # un punto pendiente, sino una recomendación.
    total = sum(1 for k in PUNTOS if k not in OPCIONALES or k in estados)
    hechas = len(estados)
    aplican = sum(1 for e in estados.values() if e != NA)

    if not aplican:
        nivel, puntuacion = "sin_datos", None
    else:
        puntuacion = round(100 * bien / (bien + mal))
        if defectos[MUY_GRAVE]:
            nivel, puntuacion = "peligro", min(puntuacion, TOPES[MUY_GRAVE])
        elif defectos[GRAVE]:
            nivel, puntuacion = "deficiente", min(puntuacion, TOPES[GRAVE])
        elif defectos[LEVE]:
            nivel = "mejorable"
        else:
            nivel = "correcta"

    titulo, porque = NIVELES[nivel]
    if nivel == "correcta" and hechas == total:
        titulo = "Sin defectos detectados"

    return {
        "puntuacion": puntuacion, "nivel": nivel, "veredicto": titulo, "porque": porque,
        "total": total, "hechas": hechas, "pendientes": total - hechas,
        "defectos": defectos,
        "n": {k: len(v) for k, v in defectos.items()},
        "estados": estados, "detalles": detalles,
        "siempre": _siempre(estados),
    }
