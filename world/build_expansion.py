"""
world/build_expansion.py

Construye las zonas de expansión del mundo:

  Pantano del Troll (norte de la Cueva Oscura):
    Senda Fangosa → Pantano Cenagoso → Guarida del Troll

  Catacumbas (bajo la Celda Abandonada):
    Túnel de Acceso → Sala de las Tumbas → Cámara del Nigromante

Es idempotente: si las salas ya existen, las omite.

Uso como Builder en el juego:
  @expandir

Uso manual desde la consola Django:
  from world.build_expansion import construir_expansion
  construir_expansion()
"""

import evennia
from evennia.utils.logger import log_info


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _room(key, desc):
    room = evennia.create_object("typeclasses.rooms.Room", key=key, nohome=True)
    room.db.desc = desc
    return room


def _exit(key, aliases, src, dst):
    evennia.create_object(
        "typeclasses.exits.Exit",
        key=key,
        aliases=aliases,
        location=src,
        destination=dst,
    )


def _link(key_a, alias_a, key_b, alias_b, room_a, room_b):
    _exit(key_a, [alias_a], room_a, room_b)
    _exit(key_b, [alias_b], room_b, room_a)


def _spawn(prototype_key, location):
    from evennia.prototypes import spawner
    npc = spawner.spawn(prototype_key)[0]
    npc.location = location
    return npc


def _find_room(name):
    """Busca una sala por nombre. Devuelve la primera Room coincidente o None."""
    results = evennia.search_object(name)
    rooms = [r for r in results if r.is_typeclass("typeclasses.rooms.Room", exact=False)]
    return rooms[0] if rooms else None


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def construir_expansion(caller=None):
    """
    Añade las zonas de expansión al mundo existente.

    caller — objeto Evennia que recibe mensajes de progreso (puede ser None).
    """
    def msg(text):
        if caller:
            caller.msg(text)
        log_info(f"build_expansion: {text}")

    # Verificar que el mundo base existe
    cueva = _find_room("Cueva Oscura")
    celda = _find_room("Celda Abandonada")

    if not cueva or not celda:
        msg(
            "|rError: el mundo base no está construido. "
            "Ejecuta at_initial_setup o usa @batchcode antes.|n"
        )
        return

    salas_creadas = 0
    npcs_creados = 0

    # -----------------------------------------------------------------------
    # ZONA 1: PANTANO DEL TROLL
    # -----------------------------------------------------------------------

    if _find_room("Senda Fangosa"):
        msg("|yZona 'Pantano del Troll' ya existe. Omitida.|n")
    else:
        senda = _room(
            "Senda Fangosa",
            (
                "Un sendero de tierra blanda que se hunde bajo tus pies con cada paso. "
                "El aire huele a humedad y podredumbre. "
                "Entre los juncos crecen hongos de colores extraños. "
                "Al |csur|n está la Cueva Oscura; "
                "al |cnorte|n, el corazón del pantano."
            ),
        )
        senda.db.zona = "senda_fangosa"

        pantano = _room(
            "Pantano Cenagoso",
            (
                "Una extensión de agua estancada y barro espeso rodea un islote de tierra firme. "
                "Las ranas croan en la oscuridad y luciérnagas verdes iluminan el ambiente. "
                "El olor es insoportable. "
                "Al |csur|n, la Senda Fangosa; al |cnorte|n, la oscura guarida."
            ),
        )
        pantano.db.zona = "pantano_cenagoso"

        guarida = _room(
            "Guarida del Troll",
            (
                "Una caverna natural cubierta de limo y huesos de animales. "
                "El techo gotea y el suelo está inundado en varios palmos de agua putrefacta. "
                "Restos de presas anteriores decoran las paredes. "
                "Al |csur|n está el pantano."
            ),
        )
        guarida.db.zona = "guarida_troll"
        guarida.db.exterior = False   # interior: caverna

        senda.db.detalles_ocultos = [
            {
                "texto": "Huellas enormes se hunden en el barro. Algo muy pesado pasó por aquí hace poco.",
                "req_percepcion": 10,
            },
            {
                "texto": "Los hongos del sendero son bioluminiscentes. Los alquimistas los buscan.",
                "req_percepcion": 13,
            },
        ]
        pantano.db.detalles_ocultos = [
            {
                "texto": "Bajo el agua hay una corriente subterránea. Podría haber una salida... si no fuera por las serpientes.",
                "req_percepcion": 12,
            },
            {
                "texto": "En el islote hay marcas de un ritual antiguo grabadas en las piedras. Los hombres lagarto lo realizan en luna llena.",
                "req_percepcion": 15,
            },
        ]
        guarida.db.detalles_ocultos = [
            {
                "texto": "Entre los huesos hay un brazalete de oro enterrado en el barro.",
                "req_percepcion": 14,
            },
            {
                "texto": "Las paredes tienen inscripciones en un idioma desconocido. Son muy antiguas, anteriores a los hombres lagarto.",
                "req_percepcion": 16,
            },
        ]

        # Conectar al mundo: Cueva → Senda → Pantano → Guarida
        _link("norte", "n", "sur", "s", cueva, senda)
        _link("norte", "n", "sur", "s", senda, pantano)
        _link("norte", "n", "sur", "s", pantano, guarida)

        # Actualizar descripción de la cueva para reflejar la nueva salida
        cueva.db.desc = (
            "Una cueva húmeda de paredes cubiertas de musgo brillante. "
            "El suelo está encharcado y la oscuridad es casi total. "
            "Un olor putrefacto impregna el aire. "
            "Al |coeste|n, la salida hacia el Bosque del Norte. "
            "Al |cnorte|n, una senda fangosa se adentra en el pantano."
        )

        # NPCs
        _spawn("SERPIENTE_PANTANO", senda)
        _spawn("SERPIENTE_PANTANO", pantano)
        _spawn("HOMBRE_LAGARTO", pantano)
        troll = _spawn("TROLL", guarida)
        # Patrulla del hombre lagarto entre pantano y senda
        lagarto = _find_room("Pantano Cenagoso")  # ya creado arriba, pero lo buscamos por si acaso
        # El hombre lagarto lo encontramos en pantano.contents
        for obj in pantano.contents:
            if getattr(obj.db, "npc_prototipo", None) == "HOMBRE_LAGARTO":
                obj.db.patrol_rooms = [pantano.dbref, senda.dbref]
                obj._iniciar_patrulla()
                break

        salas_creadas += 3
        npcs_creados += 4
        msg("|gZona 'Pantano del Troll' creada (3 salas, 4 NPCs).|n")

    # -----------------------------------------------------------------------
    # ZONA 2: CATACUMBAS
    # -----------------------------------------------------------------------

    if _find_room("Túnel de Acceso"):
        msg("|yZona 'Catacumbas' ya existe. Omitida.|n")
    else:
        tunel = _room(
            "Túnel de Acceso",
            (
                "Un pasaje estrecho de piedra tallada que desciende en espiral. "
                "El aire está cargado de polvo y el silencio es sepulcral. "
                "Antorchas extintas cuelgan de las paredes. "
                "Al |csur|n (subir) está la celda; al |cnorte|n (bajar), las tumbas."
            ),
        )

        tumbas = _room(
            "Sala de las Tumbas",
            (
                "Una cámara amplia con nichos funerarios tallados en las paredes. "
                "Algunos sarcófagos de piedra están abiertos y vacíos. "
                "Una luz verdosa y espectral ilumina el lugar sin fuente aparente. "
                "Al |csur|n (subir) está el túnel; al |cnorte|n (bajar), una cámara más profunda."
            ),
        )
        tumbas.db.zona = "sala_tumbas"
        tumbas.db.exterior = False

        camara = _room(
            "Cámara del Nigromante",
            (
                "Una sala circular con un altar de obsidiana en el centro. "
                "Símbolos arcanos brillan en el suelo con una luz azulada. "
                "El aire vibra con una energía oscura que dificulta respirar. "
                "Al |csur|n (subir) está la sala de las tumbas."
            ),
        )
        camara.db.zona = "camara_nigromante"
        camara.db.exterior = False

        tunel.db.detalles_ocultos = [
            {
                "texto": "Las paredes tienen inscripciones de advertencia: 'Lo que duerme no debe despertar'.",
                "req_percepcion": 11,
            },
        ]
        tumbas.db.detalles_ocultos = [
            {
                "texto": "La luz espectral proviene de hongos parásitos que crecen en los sarcófagos. Son muy raros.",
                "req_percepcion": 12,
            },
            {
                "texto": "Uno de los sarcófagos tiene un compartimento secreto. Contiene un fragmento de un mapa.",
                "req_percepcion": 14,
            },
        ]
        camara.db.detalles_ocultos = [
            {
                "texto": "El altar tiene un receptáculo con la forma de un sello. El sello del capitán bandido podría encajar aquí.",
                "req_percepcion": 13,
            },
            {
                "texto": "Bajo el altar hay una caja de metal con un cierre arcano. Está sellada con magia.",
                "req_percepcion": 16,
            },
        ]

        # Conectar: Celda ↕ Túnel ↕ Tumbas ↕ Cámara
        _link("bajar", "b", "subir", "su", celda, tunel)
        _link("bajar", "b", "subir", "su", tunel, tumbas)
        _link("bajar", "b", "subir", "su", tumbas, camara)

        # NPCs
        _spawn("ESQUELETO", tumbas)
        _spawn("ESQUELETO", tumbas)
        _spawn("LICHE_MENOR", camara)

        # Equipo especial en la cámara
        from evennia.prototypes import spawner
        grimorio = spawner.spawn("GRIMORIO_NIGROMANTE")[0]
        grimorio.location = camara

        salas_creadas += 3
        npcs_creados += 3
        msg("|gZona 'Catacumbas' creada (3 salas, 3 NPCs + 1 grimorio).|n")

    # -----------------------------------------------------------------------
    # ZONA 3: RUINAS DEL TEMPLO
    # -----------------------------------------------------------------------

    if _find_room("Ruinas del Templo"):
        msg("|yZona 'Ruinas del Templo' ya existe. Omitida.|n")
    else:
        claro = _find_room("Claro del Bosque")
        if not claro:
            msg("|rError: no se encontró el Claro del Bosque. Omitiendo zona del Templo.|n")
        else:
            camino = _room(
                "Camino al Templo",
                (
                    "Un sendero de losas de piedra antigua, cubiertas de musgo y quebradas por el tiempo. "
                    "A ambos lados crecen árboles retorcidos que proyectan sombras inquietantes. "
                    "Se siente una presencia extraña en el aire. "
                    "Al |csur|n está el Claro del Bosque; "
                    "al |cnorte|n, las ruinas de un templo olvidado."
                ),
            )
            camino.db.zona = "camino_templo"

            ruinas = _room(
                "Ruinas del Templo",
                (
                    "Las paredes del antiguo templo se desmoronan lentamente. "
                    "Columnas caídas yacen entre hierbas altas y el silencio es casi total. "
                    "Una energía espectral y fría impregna cada piedra. "
                    "Al |csur|n está el camino de vuelta; "
                    "al |cnorte|n, una cripta sellada bajo el altar."
                ),
            )
            ruinas.db.zona = "ruinas_templo"

            cripta = _room(
                "Cripta del Barón",
                (
                    "Una cámara funeraria bajo el altar mayor. "
                    "Los relieves de las paredes representan batallas antiguas y figuras encapuchadas. "
                    "Un sarcófago de piedra negra en el centro ha sido violado desde dentro. "
                    "El aire es helado y parece resistirse a ser respirado. "
                    "Al |csur|n (subir) están las ruinas del templo."
                ),
            )
            cripta.db.zona = "cripta_baron"
            cripta.db.exterior = False

            camino.db.detalles_ocultos = [
                {
                    "texto": "Las losas del suelo llevan inscripciones borrosas. Son avisos grabados por clérigos que nunca regresaron.",
                    "req_percepcion": 11,
                },
                {
                    "texto": "Entre los árboles hay una piedra con el símbolo de una orden clerical antigua. Alguien la dejó como advertencia.",
                    "req_percepcion": 14,
                },
            ]
            ruinas.db.detalles_ocultos = [
                {
                    "texto": "En el altar roto hay restos de un ritual reciente. Los espectros obedecen a alguien.",
                    "req_percepcion": 12,
                },
                {
                    "texto": "Bajo una columna caída hay un nicho con una ranura. El símbolo sagrado encajaría perfectamente aquí.",
                    "req_percepcion": 15,
                },
            ]
            cripta.db.detalles_ocultos = [
                {
                    "texto": "El sarcófago tiene una inscripción: 'El Barón Morthis, Guardián del Sello Eterno. Que descanse en paz eterna'.",
                    "req_percepcion": 10,
                },
                {
                    "texto": "En la pared hay un panel de piedra que se mueve. Detrás solo hay polvo y huesos muy antiguos.",
                    "req_percepcion": 16,
                },
            ]

            # Conectar: Claro del Bosque ↕ Camino ↕ Ruinas ↕ Cripta
            _link("norte", "n", "sur", "s", claro, camino)
            _link("norte", "n", "sur", "s", camino, ruinas)
            _link("bajar", "b", "subir", "su", ruinas, cripta)

            # NPCs de combate
            _spawn("ESPECTRO", camino)
            _spawn("ESPECTRO", ruinas)
            _spawn("ESPECTRO", ruinas)
            _spawn("CABALLERO_OSCURO", cripta)

            salas_creadas += 3
            npcs_creados += 4
            msg("|gZona 'Ruinas del Templo' creada (3 salas, 4 NPCs).|n")

    # -----------------------------------------------------------------------
    # ZONA 4: MINAS DE HIERRO VIEJO
    # -----------------------------------------------------------------------

    if _find_room("Boca de la Mina"):
        msg("|yZona 'Minas de Hierro Viejo' ya existe. Omitida.|n")
    else:
        bosque = _find_room("Bosque del Norte")
        if not bosque:
            msg("|rError: no se encontró el Bosque del Norte. Omitiendo zona de las Minas.|n")
        else:
            boca = _room(
                "Boca de la Mina",
                (
                    "La entrada a las antiguas Minas de Hierro Viejo se abre en la ladera de una colina rocosa. "
                    "Un cartel de madera podrida advierte 'PELIGRO — MINA CLAUSURADA'. "
                    "El aire que sale desde el interior huele a piedra húmeda y óxido. "
                    "Al |ceste|n está el Bosque del Norte; "
                    "al |cnorte|n, los túneles de la mina."
                ),
            )
            boca.db.zona = "boca_mina"

            galeria = _room(
                "Galería Principal",
                (
                    "Un túnel amplio sostenido por vigas de madera podrida. "
                    "Las paredes brillan con venas de mineral de hierro que recogen la escasa luz. "
                    "Telas de araña cubren cada rincón y algo se mueve entre las sombras. "
                    "Al |csur|n está la boca de la mina; "
                    "al |cnorte|n, un pasaje que desciende más en las profundidades."
                ),
            )
            galeria.db.zona = "galeria_principal"
            galeria.db.exterior = False

            caverna = _room(
                "Caverna del Coloso",
                (
                    "Una enorme caverna natural en el corazón de la montaña. "
                    "El suelo está cubierto de polvo rojizo y las paredes emiten un calor inusual. "
                    "Herramientas de minero antiguas yacen rotas a los lados. "
                    "En el centro de la sala, algo colosal aguarda en silencio. "
                    "Al |csur|n está la galería principal."
                ),
            )
            caverna.db.zona = "caverna_coloso"
            caverna.db.exterior = False

            boca.db.detalles_ocultos = [
                {
                    "texto": "Las marcas en la roca alrededor de la entrada sugieren que la mina fue sellada desde dentro, no desde fuera.",
                    "req_percepcion": 11,
                },
                {
                    "texto": "Hay huellas recientes de algo enorme cerca de la entrada. El polvo está removido.",
                    "req_percepcion": 14,
                },
            ]
            galeria.db.detalles_ocultos = [
                {
                    "texto": "Una de las vigas tiene tallado un mensaje: 'Día 47. El gólem despertó. No saldremos de aquí'.",
                    "req_percepcion": 12,
                },
                {
                    "texto": "Hay una grieta en la pared que revela una veta de gemas sin explotar. Alguien debería volver con más tiempo.",
                    "req_percepcion": 15,
                },
            ]
            caverna.db.detalles_ocultos = [
                {
                    "texto": "El suelo bajo el gólem tiene grabados círculos rúnicos. Es una invocación de guardián, obra de un mago muy poderoso.",
                    "req_percepcion": 13,
                },
                {
                    "texto": "En un rincón hay un cofre aplastado por una roca. Dentro hay huesos y un diario ilegible.",
                    "req_percepcion": 16,
                },
            ]

            # Conectar: Bosque → oeste → Boca → norte → Galería → norte → Caverna
            _link("oeste", "o", "este", "e", bosque, boca)
            _link("norte", "n", "sur",  "s", boca,   galeria)
            _link("norte", "n", "sur",  "s", galeria, caverna)

            # Actualizar descripción del Bosque del Norte para reflejar la nueva salida
            bosque.db.desc = (
                "Un denso bosque donde la luz apenas penetra entre las copas. "
                "El suelo está cubierto de hojas secas y ramas caídas. "
                "Se escuchan ruidos inquietantes entre los arbustos. "
                "Al |csur|n se ve la Plaza de la Ciudad; "
                "al |cnorte|n, un claro iluminado; "
                "al |ceste|n, una cueva oscura; "
                "al |coeste|n, una colina rocosa con la boca de una mina antigua."
            )

            # NPCs
            _spawn("ARANA_CUEVA", boca)
            _spawn("ARANA_CUEVA", boca)
            _spawn("MINERO_MALDITO", galeria)
            _spawn("MINERO_MALDITO", galeria)
            _spawn("GOLEM_PIEDRA", caverna)

            salas_creadas += 3
            npcs_creados += 5
            msg("|gZona 'Minas de Hierro Viejo' creada (3 salas, 5 NPCs).|n")

    # -----------------------------------------------------------------------
    # ZONA 5: TORRE DEL MAGO CAÍDO
    # -----------------------------------------------------------------------

    if _find_room("Base de la Torre"):
        msg("|yZona 'Torre del Mago Caído' ya existe. Omitida.|n")
    else:
        claro = _find_room("Claro del Bosque")
        if not claro:
            msg("|rError: no se encontró el Claro del Bosque. Omitiendo zona de la Torre.|n")
        else:
            base = _room(
                "Base de la Torre",
                (
                    "Una estructura cilíndrica de piedra negra se alza al borde del claro, "
                    "parcialmente cubierta de enredaderas muertas. "
                    "La puerta de entrada, de madera chamuscada, cuelga abierta de un gozne. "
                    "Inscripciones arcanas en el dintel brillan con una luz azulada intermitente. "
                    "Al |coeste|n está el Claro del Bosque; "
                    "al |cnorte|n (entrar), la planta baja de la torre."
                ),
            )
            base.db.zona = "base_torre"

            biblioteca = _room(
                "Biblioteca del Archimago",
                (
                    "Una estancia circular atestada de estanterías derruidas. "
                    "Los libros se han convertido en polvo o ceniza "
                    "y el suelo está cubierto de pergaminos quemados. "
                    "Círculos arcanos grabados en el suelo emiten una luz verdosa débil. "
                    "El aire sabe a ozono y quemado. "
                    "Al |csur|n (salir) está la base de la torre; "
                    "al |cnorte|n, una escalera de piedra sube hacia las alturas."
                ),
            )
            biblioteca.db.zona = "biblioteca_archimago"
            biblioteca.db.exterior = False

            camara = _room(
                "Cámara del Ritual",
                (
                    "La sala superior de la torre, circular y de techo abovedado. "
                    "Un ritual inconcluso lleva décadas grabado en el suelo con polvo de runas. "
                    "Desde las ventanas rajadas se ve el bosque en todas direcciones. "
                    "En el centro de la sala, una figura flotante aguarda inmóvil. "
                    "Al |csur|n (bajar) está la biblioteca."
                ),
            )
            camara.db.zona = "camara_ritual"
            camara.db.exterior = False

            base.db.detalles_ocultos = [
                {
                    "texto": "Las inscripciones del dintel son un sello de contención. Fue roto desde dentro hace décadas.",
                    "req_percepcion": 11,
                },
                {
                    "texto": "Hay huellas de botas en la tierra alrededor de la torre. Alguien sale a patrullar regularmente.",
                    "req_percepcion": 14,
                },
            ]
            biblioteca.db.detalles_ocultos = [
                {
                    "texto": "En una estantería derruida hay un diario parcialmente legible. El último entrada dice: 'El sello cedió. Ya no puedo parar'.",
                    "req_percepcion": 12,
                },
                {
                    "texto": "Bajo los pergaminos quemados hay un panel de suelo que no encaja bien. Contiene un frasco de antídoto intacto.",
                    "req_percepcion": 15,
                },
            ]
            camara.db.detalles_ocultos = [
                {
                    "texto": "El círculo del suelo es una jaula arcana, no un altar. Vexthar está atrapado aquí, no es su elección permanecer.",
                    "req_percepcion": 13,
                },
                {
                    "texto": "En la pared hay una placa de metal: 'Archimago Vexthar, primer grado del Gremio Arcano. Desaparecido en el año 847'.",
                    "req_percepcion": 16,
                },
            ]

            # Conectar: Claro → este → Base → norte → Biblioteca → norte → Cámara
            _link("este", "e", "oeste", "o", claro, base)
            _link("norte", "n", "sur",  "s", base, biblioteca)
            _link("norte", "n", "sur",  "s", biblioteca, camara)

            # Actualizar descripción del Claro para reflejar la nueva salida
            claro.db.desc = (
                "Un pequeño claro donde los rayos de sol logran atravesar las ramas. "
                "En el suelo hay huellas de criaturas pequeñas y restos de fogatas. "
                "Al |csur|n está el Bosque del Norte; "
                "al |cnorte|n, el camino hacia las ruinas del templo; "
                "al |ceste|n, la silueta de una torre de piedra negra entre los árboles."
            )

            # NPCs
            _spawn("GUARDIAN_ARCANO", base)
            _spawn("APRENDIZ_CORRUPTO", biblioteca)
            _spawn("APRENDIZ_CORRUPTO", biblioteca)
            _spawn("ARCHIMAGO_VEXTHAR", camara)

            salas_creadas += 3
            npcs_creados += 4
            msg("|gZona 'Torre del Mago Caído' creada (3 salas, 4 NPCs).|n")

    # -----------------------------------------------------------------------
    # ZONA 6: CIUDADELA OSCURA
    # -----------------------------------------------------------------------

    if _find_room("Portal de la Ciudadela"):
        msg("|yZona 'Ciudadela Oscura' ya existe. Omitida.|n")
    else:
        cripta = _find_room("Cripta del Barón")
        if not cripta:
            msg("|rError: no se encontró la Cripta del Barón. Omitiendo zona de la Ciudadela.|n")
        else:
            portal = _room(
                "Portal de la Ciudadela",
                (
                    "Un arco de piedra negra de más de cuatro metros de altura marca la entrada a la ciudadela. "
                    "Runas de maldición grabadas en cada piedra brillan con una luz rojiza pulsante. "
                    "El aire al cruzarlo se vuelve pesado, frío, y cargado de una energía de no-muerte. "
                    "Al |csur|n (salir) está la Cripta del Barón; "
                    "al |cnorte|n, el imponente salón del trono de la Legión Oscura."
                ),
            )
            portal.db.zona = "portal_ciudadela"
            portal.db.exterior = False

            salon = _room(
                "Salón del Trono",
                (
                    "Una sala monumental con columnas de mármol negro que sostienen un techo abovedado. "
                    "Estandartes desgarrados de la Legión Oscura cuelgan de las paredes. "
                    "Esqueletos de guerreros caídos forman dos filas desde la entrada hasta el trono vacío. "
                    "La magia oscura hace vibrar el aire y el suelo. "
                    "Al |csur|n está el portal de entrada; "
                    "al |cnorte|n, el altar del liche."
                ),
            )
            salon.db.zona = "salon_trono"
            salon.db.exterior = False

            altar = _room(
                "Altar del Liche",
                (
                    "La cámara más profunda de la ciudadela, circular y de piedra negra pulida. "
                    "Un altar de obsidiana en el centro irradia una energía de no-muerte de intensidad aplastante. "
                    "Símbolos de necromancia cubren el suelo, el techo y cada centímetro de las paredes. "
                    "La temperatura es varios grados bajo cero y el aliento forma nubes visibles. "
                    "En el trono de huesos ante el altar aguarda la figura del liche. "
                    "Al |csur|n (salir) está el salón del trono."
                ),
            )
            altar.db.zona = "altar_liche"
            altar.db.exterior = False

            portal.db.detalles_ocultos = [
                {
                    "texto": "Las runas del arco son un sello de vinculación. Cualquiera que muera aquí dentro podría levantarse como no-muerto.",
                    "req_percepcion": 12,
                },
                {
                    "texto": "En el suelo hay marcas de arrastre recientes. Algo enorme pasó hacia dentro hace pocas horas.",
                    "req_percepcion": 15,
                },
            ]
            salon.db.detalles_ocultos = [
                {
                    "texto": "Los estandartes muestran el escudo de cuatro reinos distintos. La Legión Oscura ha conquistado todo eso.",
                    "req_percepcion": 11,
                },
                {
                    "texto": "Bajo los esqueletos de guardia hay runas de animación. Si el liche muere, estos guerreros también caerán.",
                    "req_percepcion": 14,
                },
            ]
            altar.db.detalles_ocultos = [
                {
                    "texto": "El altar contiene una filoacteria, el receptáculo del alma del liche. Si se destruye, él muere de verdad.",
                    "req_percepcion": 14,
                },
                {
                    "texto": "Las paredes registran su historia: un rey corrompido por el deseo de inmortalidad hace cuatro siglos.",
                    "req_percepcion": 16,
                },
            ]

            # Conectar: Cripta del Barón → norte → Portal → norte → Salón → norte → Altar
            _link("norte", "n", "sur", "s", cripta, portal)
            _link("norte", "n", "sur", "s", portal, salon)
            _link("norte", "n", "sur", "s", salon,  altar)

            # Actualizar descripción de la Cripta para reflejar la nueva salida
            cripta.db.desc = (
                "Una cámara funeraria bajo el altar mayor. "
                "Los relieves de las paredes representan batallas antiguas y figuras encapuchadas. "
                "Un sarcófago de piedra negra en el centro ha sido violado desde dentro. "
                "El aire es helado y parece resistirse a ser respirado. "
                "Al |csur|n (subir) están las ruinas del templo; "
                "al |cnorte|n, un arco de piedra oscura de proporciones monumentales."
            )

            # NPCs
            _spawn("CABALLERO_MUERTE", portal)
            _spawn("CABALLERO_MUERTE", portal)
            _spawn("CABALLERO_MUERTE", salon)
            _spawn("HECHICERO_SOMBRIO", salon)
            _spawn("HECHICERO_SOMBRIO", salon)
            _spawn("LICHE_INMORTAL", altar)

            salas_creadas += 3
            npcs_creados += 6
            msg("|gZona 'Ciudadela Oscura' creada (3 salas, 6 NPCs).|n")

    # -----------------------------------------------------------------------
    # ZONA 7: ORILLA DEL RÍO (zona de pesca)
    # -----------------------------------------------------------------------

    if _find_room("Orilla del Río"):
        msg("|yZona 'Orilla del Río' ya existe. Omitida.|n")
    else:
        plaza = _find_room("Plaza de la Ciudad")
        if not plaza:
            msg("|rError: no se encontró la Plaza de la Ciudad. Omitiendo zona del Río.|n")
        else:
            orilla = _room(
                "Orilla del Río",
                (
                    "El río que bordea la ciudad fluye lento y cristalino aquí. "
                    "Los juncos crecen en las orillas y el sonido del agua invita a la calma. "
                    "Ocasionalmente una sombra plateada cruza bajo la superficie. "
                    "Al |ceste|n está la Plaza de la Ciudad."
                ),
            )
            orilla.db.zona = "orilla_rio"
            orilla.db.exterior = True

            orilla.db.detalles_ocultos = [
                {
                    "texto": "Bajo el agua hay una corriente más profunda. Los peces grandes descansan ahí.",
                    "req_percepcion": 10,
                },
                {
                    "texto": "En el barro de la orilla hay rastros de un animal acuático de gran tamaño. Quizás no solo peces viven aquí.",
                    "req_percepcion": 14,
                },
            ]

            _link("oeste", "o", "este", "e", plaza, orilla)

            salas_creadas += 1
            msg("|gZona 'Orilla del Río' creada (1 sala, zona de pesca).|n")

    # -----------------------------------------------------------------------
    # BUSCADOR DE TESOROS EN EL MERCADO
    # -----------------------------------------------------------------------

    mercado_obj = _find_room("Mercado de la Ciudad")
    if mercado_obj:
        buscador_existe = any(
            getattr(o.db, "npc_prototipo", None) == "BUSCADOR_TESOROS"
            for o in mercado_obj.contents
            if hasattr(o, "db")
        )
        if not buscador_existe:
            _spawn("BUSCADOR_TESOROS", mercado_obj)
            npcs_creados += 1
            msg("|gTorben el buscador de tesoros añadido al Mercado de la Ciudad.|n")

    # -----------------------------------------------------------------------
    # SACERDOTE EN LA PLAZA
    # -----------------------------------------------------------------------

    plaza = _find_room("Plaza de la Ciudad")
    if plaza:
        sacerdote_existe = any(
            getattr(o.db, "npc_prototipo", None) == "SACERDOTE"
            for o in plaza.contents
            if hasattr(o, "db")
        )
        if not sacerdote_existe:
            _spawn("SACERDOTE", plaza)
            npcs_creados += 1
            msg("|gHermano Aldric el sacerdote añadido a la Plaza de la Ciudad.|n")

    # -----------------------------------------------------------------------
    # ZONA 8: VESTÍBULO DEL PORTAL (acceso a mazmorras instanciadas)
    # -----------------------------------------------------------------------

    if _find_room("Vestíbulo del Portal"):
        msg("|yVestíbulo del Portal ya existe. Omitido.|n")
    else:
        plaza = _find_room("Plaza de la Ciudad")
        if not plaza:
            msg("|rError: no se encontró la Plaza de la Ciudad. Omitiendo Vestíbulo del Portal.|n")
        else:
            vestibulo = _room(
                "Vestíbulo del Portal",
                (
                    "Una sala circular de piedra antigua con tres arcos de piedra negra en las paredes. "
                    "Cada arco emana una energía inquietante: frío mortal desde uno, calor abrasador desde otro, "
                    "y una oscuridad absoluta desde el tercero. "
                    "Un guardián encapuchado custodia el centro de la sala. "
                    "Al |csur|n está la Plaza de la Ciudad."
                ),
            )
            vestibulo.db.zona = "vestibulo_portal"
            vestibulo.db.exterior = False

            _link("norte", "n", "sur", "s", plaza, vestibulo)

            guardian_existe = any(
                getattr(o.db, "npc_prototipo", None) == "GUARDIAN_PORTAL"
                for o in vestibulo.contents
                if hasattr(o, "db")
            )
            if not guardian_existe:
                _spawn("GUARDIAN_PORTAL", vestibulo)
                npcs_creados += 1

            salas_creadas += 1
            msg("|gZona 'Vestíbulo del Portal' creada (1 sala, guardián).|n")

    # -----------------------------------------------------------------------
    # ZONA 9: ARENA DE LA CIUDAD (torneos PvP)
    # -----------------------------------------------------------------------

    if _find_room("Arena de la Ciudad"):
        msg("|yArena de la Ciudad ya existe. Omitida.|n")
    else:
        plaza = _find_room("Plaza de la Ciudad")
        if not plaza:
            msg("|rError: no se encontró la Plaza de la Ciudad. Omitiendo Arena.|n")
        else:
            arena = _room(
                "Arena de la Ciudad",
                (
                    "Una arena circular de arena dorada, rodeada por gradas de piedra tallada. "
                    "Las paredes están grabadas con los nombres de los campeones pasados. "
                    "El suelo muestra las marcas de incontables batallas. "
                    "Aquí los guerreros demuestran su valía ante los dioses y el pueblo. "
                    "Al |coeste|n está la Plaza de la Ciudad."
                ),
            )
            arena.db.zona      = "arena_ciudad"
            arena.db.exterior  = False

            _link("este", "e", "oeste", "o", plaza, arena)

            maestro_existe = any(
                getattr(o.db, "npc_prototipo", None) == "MAESTRO_ARENA"
                for o in arena.contents
                if hasattr(o, "db")
            )
            if not maestro_existe:
                _spawn("MAESTRO_ARENA", arena)
                npcs_creados += 1

            salas_creadas += 1
            msg("|gZona 'Arena de la Ciudad' creada (1 sala, maestro de arena).|n")

    # -----------------------------------------------------------------------
    # Resumen
    # -----------------------------------------------------------------------

    if salas_creadas:
        msg(
            f"\n|gExpansión completada.|n\n"
            f"  Salas nuevas : {salas_creadas}\n"
            f"  NPCs nuevos  : {npcs_creados}\n"
        )
    else:
        msg("|yNo se creó nada nuevo (todo ya existía).|n")
