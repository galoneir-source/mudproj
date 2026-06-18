"""
at_initial_setup

Se ejecuta UNA SOLA VEZ al arrancar el servidor por primera vez.
Construye el mundo inicial: salas, exits y NPCs.

Mapa del mundo inicial:

                [Claro del Bosque]
                    (goblin jefe)
                       |n/s
      [Cueva Oscura] - [Bosque del Norte]
                   e/o    (goblin, patrulla)
                       |n/s
    [Mercado] - [Plaza de la Ciudad] - [Taberna]
      (mercader) o/e   (guardia)   e/o (mesonero)
                       |n/s
                [Entrada al Calabozo]
                    (bandido)
                       |n/s
                [Pasillo del Calabozo]
                    (bandido)
                       |n/s
                [Celda Abandonada]
                  (capitán bandido)

Nota: los errores en este módulo se ignoran silenciosamente por Evennia,
así que es importante que el código esté bien probado.
"""

import evennia
from evennia.utils.logger import log_info


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _room(key, desc):
    """Crea una sala con typeclass del juego."""
    room = evennia.create_object("typeclasses.rooms.Room", key=key, nohome=True)
    room.db.desc = desc
    return room


def _exit(key, aliases, src, dst):
    """Crea un exit unidireccional."""
    evennia.create_object(
        "typeclasses.exits.Exit",
        key=key,
        aliases=aliases,
        location=src,
        destination=dst,
    )


def _link(key_a, alias_a, key_b, alias_b, room_a, room_b):
    """Crea exits bidireccionales entre dos salas."""
    _exit(key_a, [alias_a], room_a, room_b)
    _exit(key_b, [alias_b], room_b, room_a)


def _spawn(prototype_key, location):
    """Spawnea un NPC y lo coloca en la sala indicada."""
    from evennia.prototypes import spawner
    npc = spawner.spawn(prototype_key)[0]
    npc.location = location
    return npc


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def _mundo_base_existe() -> bool:
    """True si la Plaza de la Ciudad ya está en la BD."""
    from evennia.objects.models import ObjectDB
    return ObjectDB.objects.filter(
        db_key="Plaza de la Ciudad",
        db_typeclass_path__contains="rooms.Room",
    ).exists()


def at_initial_setup():
    """
    Construye el mundo inicial al primer arranque del servidor.
    Es idempotente: si el mundo ya existe, no hace nada.
    """
    if _mundo_base_existe():
        log_info("at_initial_setup: mundo ya construido, omitiendo.")
        return

    from world.prototypes import (
        GUARDIA, GOBLIN, GOBLIN_JEFE, BANDIDO, BANDIDO_CAPITAN,
        MESONERO, MERCADER, BANQUERO,
        ESPADA_HIERRO, DAGA_BRONCE, ARMADURA_CUERO, AMULETO_FUERZA,
    )

    # -----------------------------------------------------------------------
    # ZONA CIUDAD
    # -----------------------------------------------------------------------

    # Plaza de la Ciudad — reutilizamos Limbo (#2) como sala de inicio
    # para que DEFAULT_HOME y START_LOCATION sigan apuntando correctamente.
    limbo_list = evennia.search_object("Limbo")
    if limbo_list:
        plaza = limbo_list[0]
        plaza.key = "Plaza de la Ciudad"
    else:
        plaza = evennia.create_object(
            "typeclasses.rooms.Room", key="Plaza de la Ciudad", nohome=True
        )
    plaza.db.desc = (
        "Una amplia plaza empedrada en el corazón de la ciudad. "
        "Una fuente de piedra ocupa el centro y el rumor del agua calma los nervios. "
        "Comerciantes pregonan sus mercancías. "
        "Al |cnorte|n comienza el Bosque del Norte; "
        "al |csur|n, las sombrías entradas al Calabozo. "
        "Al |ceste|n está la Taberna; al |coeste|n, el Mercado."
    )
    plaza.db.zona = "plaza_ciudad"
    plaza.db.tipo_ambiente = "exterior_urbano"

    taberna = _room(
        "Taberna El Jabalí Borracho",
        (
            "El interior de madera oscura huele a cerveza y estofado. "
            "Una chimenea crepita en el rincón y varias mesas de roble "
            "están ocupadas por viajeros. Detrás de la barra, el mesonero "
            "te observa con una sonrisa. "
            "Al |coeste|n está la Plaza de la Ciudad."
        ),
    )
    taberna.db.zona = "taberna"
    taberna.db.exterior = False   # interior: edificio

    mercado = _room(
        "Mercado de la Ciudad",
        (
            "Una hilera de puestos coloridos llena esta zona de la ciudad. "
            "Se venden herramientas, telas, especias y objetos de dudosa procedencia. "
            "El bullicio es constante y los vendedores compiten a voces. "
            "Al |ceste|n está la Plaza de la Ciudad."
        ),
    )
    mercado.db.zona = "mercado"
    mercado.db.tipo_ambiente = "exterior_urbano"

    # Exits ciudad (norte/sur con bosque y calabozo se añaden más abajo)
    _link("este", "e", "oeste", "o", plaza, taberna)
    _link("oeste", "o", "este", "e", plaza, mercado)

    # -----------------------------------------------------------------------
    # ZONA BOSQUE
    # -----------------------------------------------------------------------

    bosque = _room(
        "Bosque del Norte",
        (
            "Un denso bosque donde la luz apenas penetra entre las copas. "
            "El suelo está cubierto de hojas secas y ramas caídas. "
            "Se escuchan ruidos inquietantes entre los arbustos. "
            "Al |csur|n se ve la Plaza de la Ciudad; "
            "al |cnorte|n, un claro iluminado; "
            "al |ceste|n, una cueva oscura."
        ),
    )
    bosque.db.zona = "bosque_norte"

    claro = _room(
        "Claro del Bosque",
        (
            "Un pequeño claro donde los rayos de sol logran atravesar las ramas. "
            "En el suelo hay huellas de criaturas pequeñas y restos de fogatas. "
            "Parece un campamento goblin. "
            "Al |csur|n está el Bosque del Norte."
        ),
    )
    claro.db.zona = "claro_bosque"

    cueva = _room(         # exterior=False se fija después de crearla
        "Cueva Oscura",
        (
            "Una cueva húmeda de paredes cubiertas de musgo brillante. "
            "El suelo está encharcado y la oscuridad es casi total. "
            "Un olor putrefacto impregna el aire. "
            "Al |coeste|n, la salida hacia el Bosque del Norte."
        ),
    )

    cueva.db.exterior = False   # interior: caverna subterránea

    # Detalles ocultos — Bosque
    bosque.db.detalles_ocultos = [
        {"texto": "Hay marcas de garras en los troncos. Algo grande por aquí.", "req_percepcion": 11},
        {"texto": "Entre las hojas ves un sendero apenas visible que lleva al este.", "req_percepcion": 13},
    ]
    claro.db.detalles_ocultos = [
        {"texto": "Las cenizas de la hoguera aún están calientes. Los goblins estuvieron aquí hace poco.", "req_percepcion": 10},
        {"texto": "Bajo una piedra grande hay un pequeño cofre de madera mal escondido.", "req_percepcion": 14},
    ]
    cueva.db.detalles_ocultos = [
        {"texto": "Las paredes tienen runas grabadas. Alguien vivió aquí antes que el troll.", "req_percepcion": 12},
        {"texto": "En el fondo de la cueva hay una fisura en la roca que podría ser una salida secreta.", "req_percepcion": 16},
    ]

    # Exits bosque
    _link("norte", "n", "sur", "s", plaza, bosque)
    _link("norte", "n", "sur", "s", bosque, claro)
    _link("este", "e", "oeste", "o", bosque, cueva)

    # -----------------------------------------------------------------------
    # ZONA CALABOZO
    # -----------------------------------------------------------------------

    calabozo_entrada = _room(
        "Entrada al Calabozo",
        (
            "Una escalera de piedra desciende hacia la oscuridad. "
            "El aire húmedo y frío sube desde las profundidades. "
            "Las paredes están cubiertas de musgo y las antorchas parpadean. "
            "Al |cnorte|n está la Plaza de la Ciudad; "
            "al |csur|n, el pasillo interior del calabozo."
        ),
    )
    calabozo_entrada.db.zona = "calabozo_entrada"
    calabozo_entrada.db.exterior = False

    calabozo_pasillo = _room(
        "Pasillo del Calabozo",
        (
            "Un pasillo estrecho de piedra tallada. Las antorchas en las paredes "
            "apenas iluminan las grietas del suelo. Se escuchan voces lejanas. "
            "Al |cnorte|n está la entrada; "
            "al |csur|n, el fondo del calabozo."
        ),
    )
    calabozo_pasillo.db.zona = "calabozo_pasillo"
    calabozo_pasillo.db.exterior = False

    calabozo_celda = _room(
        "Celda Abandonada",
        (
            "Una celda de barrotes oxidados, con paja podrida en el suelo. "
            "En el rincón hay marcas de garras en la pared. "
            "Este parece ser el cuartel general de los bandidos. "
            "Al |cnorte|n está el pasillo."
        ),
    )
    calabozo_celda.db.zona = "calabozo_celda"
    calabozo_celda.db.exterior = False

    # Detalles ocultos — Calabozo
    calabozo_entrada.db.detalles_ocultos = [
        {"texto": "Hay una inscripción en la pared: 'El capitán guarda el sello rojo'.", "req_percepcion": 12},
    ]
    calabozo_pasillo.db.detalles_ocultos = [
        {"texto": "Una de las antorchas es falsa. Detrás hay un nicho con monedas viejas.", "req_percepcion": 15},
    ]
    calabozo_celda.db.detalles_ocultos = [
        {"texto": "Bajo la paja hay una trampilla. Podría llevar a un nivel inferior.", "req_percepcion": 13},
        {"texto": "El capitán lleva un sello rojo cosido en la capa. Parece importante.", "req_percepcion": 11},
    ]

    # Exits calabozo
    _link("sur", "s", "norte", "n", plaza, calabozo_entrada)
    _link("sur", "s", "norte", "n", calabozo_entrada, calabozo_pasillo)
    _link("sur", "s", "norte", "n", calabozo_pasillo, calabozo_celda)

    # -----------------------------------------------------------------------
    # SPAWN DE NPCs
    # -----------------------------------------------------------------------

    from evennia.prototypes import spawner

    # Ciudad
    guardia = spawner.spawn(GUARDIA)[0]
    guardia.location = plaza

    banquero = spawner.spawn(BANQUERO)[0]
    banquero.location = plaza

    mesonero = spawner.spawn(MESONERO)[0]
    mesonero.location = taberna

    mercader = spawner.spawn(MERCADER)[0]
    mercader.location = mercado

    # Bosque — goblin patrulla entre bosque y claro
    goblin = spawner.spawn(GOBLIN)[0]
    goblin.location = bosque
    goblin.db.patrol_rooms = [bosque.dbref, claro.dbref]
    goblin._iniciar_patrulla()

    # Goblin espía oculto en el bosque (solo detectable con percepción >= 13)
    espia = spawner.spawn(GOBLIN)[0]
    espia.key = "goblin espía"
    espia.db.desc = "Un goblin delgado y silencioso, camuflado entre las sombras de los árboles."
    espia.db.oculto = True
    espia.db.nivel_sigilo = 13
    espia.db.respawn_tiempo = 180
    espia.location = bosque

    goblin_jefe = spawner.spawn(GOBLIN_JEFE)[0]
    goblin_jefe.location = claro

    # Calabozo
    bandido_entrada = spawner.spawn(BANDIDO)[0]
    bandido_entrada.location = calabozo_entrada

    bandido_pasillo = spawner.spawn(BANDIDO)[0]
    bandido_pasillo.location = calabozo_pasillo

    capitan = spawner.spawn(BANDIDO_CAPITAN)[0]
    capitan.location = calabozo_celda

    # -----------------------------------------------------------------------
    # EQUIPO INICIAL EN EL MUNDO
    # -----------------------------------------------------------------------

    # Espada y daga en la taberna (para nuevos jugadores)
    espada = spawner.spawn(ESPADA_HIERRO)[0]
    espada.location = taberna

    daga = spawner.spawn(DAGA_BRONCE)[0]
    daga.location = taberna

    # Armadura de cuero en el mercado
    armadura = spawner.spawn(ARMADURA_CUERO)[0]
    armadura.location = mercado

    # Amuleto en la celda del calabozo (recompensa del boss)
    amuleto = spawner.spawn(AMULETO_FUERZA)[0]
    amuleto.location = calabozo_celda

    log_info(
        "at_initial_setup: Mundo base creado — "
        "9 salas, 9 NPCs, 4 items de equipo. "
        "Zonas: Ciudad (plaza/taberna/mercado), "
        "Bosque (bosque/claro/cueva), "
        "Calabozo (entrada/pasillo/celda)."
    )

    # -----------------------------------------------------------------------
    # ZONAS DE EXPANSIÓN
    # -----------------------------------------------------------------------
    from world.build_expansion import construir_expansion
    construir_expansion()
