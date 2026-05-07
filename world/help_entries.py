"""
world/help_entries.py

Entradas de ayuda del juego, accesibles con el comando `help <tema>`.

Temas disponibles:
  comenzar, comandos, combate, habilidades, equipamiento,
  inventario, puertas, NPCs, percibir, descansar, stats,
  mundo, loot, respawn
"""

HELP_ENTRY_DICTS = [

    # ------------------------------------------------------------------ #
    #  Guía de inicio
    # ------------------------------------------------------------------ #
    {
        "key": "comenzar",
        "aliases": ["inicio", "empezar", "tutorial", "ayuda"],
        "category": "General",
        "text": """
Bienvenido al juego. Esta guía te explica los primeros pasos.

# Orientarte

Usa |wlook|n (o |wl|n) para ver la sala en la que estás, sus salidas y quién
hay en ella. Muévete escribiendo la dirección: |wnorte|n, |wsur|n, |weste|n,
|woeste|n (o sus abreviaturas |wn|n, |ws|n, |we|n, |wo|n).

# Tu personaje

  |wperfil|n          — ficha completa (nivel, XP, stats, habilidades)
  |wstats|n           — estadísticas de combate y vida
  |winventario|n / |winv|n — lo que llevas encima

# Interactuar con el mundo

  |whablar <NPC>|n              — iniciar conversación con un NPC
  |whablar <NPC> = <tema>|n     — preguntar sobre un tema concreto
  |wpercibir|n                  — examinar la sala en busca de detalles ocultos
  |wdescansar|n                 — recuperar HP fuera de combate

# Combate

  |watacar <objetivo>|n         — iniciar o continuar combate
  |whabilidad <nombre> <obj>|n  — usar una habilidad especial
  |whuir|n                      — intentar escapar
  |wpasar|n                     — pasar tu turno

# Subtemas

  ## Comandos completos
  Escribe |whelp comandos|n para ver la lista completa de comandos.

  ## Combate
  Escribe |whelp combate|n para el sistema de combate detallado.

  ## Equipamiento
  Escribe |whelp equipamiento|n para saber cómo equiparte.
        """,
    },

    # ------------------------------------------------------------------ #
    #  Lista de comandos
    # ------------------------------------------------------------------ #
    {
        "key": "comandos",
        "aliases": ["cmds", "lista comandos"],
        "category": "General",
        "text": """
Lista completa de comandos disponibles.

# Movimiento y exploración

  |wnorte|n / |wn|n, |wsur|n / |ws|n, |weste|n / |we|n, |woeste|n / |wo|n
  |wlook|n / |wl|n               — mirar la sala o un objeto
  |wpercibir|n                  — examinar en busca de detalles ocultos

# Personaje

  |wperfil|n / |wficha|n          — ficha completa del personaje
  |wstats|n / |westado|n          — estadísticas de combate
  |whabilidades|n / |wskills|n    — ver tus habilidades de combate

# Inventario y equipo

  |winventario|n / |winv|n / |wi|n  — ver inventario
  |wequipo|n / |wgear|n           — ver qué tienes equipado
  |wequipar <objeto>|n           — equipar un objeto
  |wdesequipar <slot|objeto>|n   — desequipar

# Combate

  |watacar <objetivo>|n          — atacar (inicia combate si no hay)
  |whabilidad <nombre> <obj>|n   — usar habilidad especial
  |whuir|n                       — intentar escapar del combate
  |wpasar|n                      — pasar tu turno

# Interacción

  |whablar <NPC>|n               — hablar con un NPC
  |whablar <NPC> = <tema>|n      — hablar sobre un tema
  |wdescansar|n / |wrest|n        — recuperar HP (fuera de combate)
  |wdecir <mensaje>|n / |wsay|n  — hablar en voz alta en la sala

# Puertas

  |wabrir <salida>|n             — abrir una puerta
  |wcerrar <salida>|n            — cerrar una puerta
  |wbloquear <salida>|n          — bloquear con llave
  |wdesbloquear <salida>|n       — desbloquear con llave
  |westadobuerta <salida>|n      — ver estado de una puerta
        """,
    },

    # ------------------------------------------------------------------ #
    #  Combate
    # ------------------------------------------------------------------ #
    {
        "key": "combate",
        "aliases": ["luchar", "batalla", "pelea"],
        "category": "Combate",
        "text": """
El combate es por turnos. Cada participante actúa una vez por ronda.

# Iniciar combate

  |watacar <objetivo>|n

Esto inicia un combate contra el objetivo en tu sala. Los NPCs agresivos
pueden también atacarte al entrar en su sala.

# Durante el combate

Cuando sea tu turno verás un aviso. Tienes |w15 segundos|n para actuar;
si no lo haces, se pasa tu turno automáticamente.

  |watacar <objetivo>|n         — ataque básico
  |whabilidad <nombre> <obj>|n  — ataque con habilidad especial
  |whuir|n                      — 50 %% de probabilidad de escapar
  |wpasar|n                     — pasar el turno sin actuar

# Resolución

Cada ataque puede:
  - |gesquivar|n — el defensor evita el golpe (depende de su Destreza)
  - |rcrítico|n  — doble daño (10 %% base + bonus de Destreza del atacante)
  - Daño normal reducido por la Defensa del objetivo

# Al morir

Si derrota a un enemigo ganas |gXP|n y el enemigo suelta su |yloot|n.
Si eres tú quien cae, reapareces en tu sala de inicio con 1 HP.

# Subtemas

  ## Stats de combate
  Escribe |whelp stats|n para ver qué hace cada stat.

  ## Habilidades
  Escribe |whelp habilidades|n para ver las habilidades disponibles.
        """,
    },

    # ------------------------------------------------------------------ #
    #  Stats
    # ------------------------------------------------------------------ #
    {
        "key": "stats",
        "aliases": ["estadisticas", "atributos"],
        "category": "Combate",
        "text": """
Estadísticas de combate de tu personaje.

  |wFuerza|n      — aumenta el daño base de tus ataques.
  |wDestreza|n    — aumenta la probabilidad de crítico y de esquivar ataques.
  |wConstitución|n — determina tu HP máximo base.
  |wInteligencia|n — base del sistema de percepción. A mayor INT, más
                  detalles ocultos puedes detectar.
  |wDefensa|n     — reduce el daño recibido en cada ataque.

  |wHP|n          — puntos de vida actuales / máximos.
  |wNivel|n       — aumenta al acumular suficiente XP.
  |wXP|n          — experiencia ganada derrotando enemigos.

# Al subir de nivel

Cada subida de nivel otorga:
  +1 Fuerza, +1 Constitución, +1 Defensa, +10 HP máximo
  HP restaurado al máximo

# Ver tus stats

  |wstats|n   — resumen rápido
  |wperfil|n  — ficha completa con barras de progreso
        """,
    },

    # ------------------------------------------------------------------ #
    #  Habilidades
    # ------------------------------------------------------------------ #
    {
        "key": "habilidades",
        "aliases": ["skills", "habilidad"],
        "category": "Combate",
        "text": """
Las habilidades especiales modifican tu ataque en combate.

# Habilidades disponibles

  |wgolpe fuerte|n   — x1.5 daño. Sin bonus de velocidad.
  |wgolpe rapido|n   — daño reducido (-2), pero más difícil de esquivar.
  |wembestida|n      — +5 daño base fijo.
  |wcorte|n          — x1.3 daño.
  |wveneno|n         — daño base + 1d4 extra.

# Uso

  |whabilidad golpe fuerte goblin|n
  |whabilidad corte bandido|n

Tu personaje empieza con |wgolpe fuerte|n y |wgolpe rapido|n.
Los NPCs también usan habilidades según su tipo.

# Ver tus habilidades

  |whabilidades|n   — lista tus habilidades con descripción
        """,
    },

    # ------------------------------------------------------------------ #
    #  Equipamiento
    # ------------------------------------------------------------------ #
    {
        "key": "equipamiento",
        "aliases": ["equipo", "gear", "armas", "armadura"],
        "category": "Equipamiento",
        "text": """
Puedes equipar objetos para mejorar tus estadísticas de combate.

# Slots de equipamiento

  |warma|n       — espadas, dagas, hachas…
  |warmadura|n   — armaduras de cuero, cota de malla…
  |waccesorio|n  — anillos, amuletos…

Cada slot admite un objeto a la vez. Si equipas uno nuevo, el anterior
vuelve a tu mochila automáticamente.

# Comandos

  |wequipar <objeto>|n           — equipar un objeto del inventario
  |wdesequipar <slot|objeto>|n   — desequipar por slot o nombre
  |wequipo|n                     — ver qué tienes equipado

# Bonificaciones

Los objetos equipados modifican tus stats directamente:
  |wespada de hierro|n     → Fuerza +3, Destreza +1
  |warmadura de cuero|n    → Defensa +4, HP máx +10
  |wcota de malla|n        → Defensa +8, HP máx +20, Destreza -2
  |wdaga de bronce|n       → Destreza +3, Fuerza +1
  |whacha de guerra|n      → Fuerza +6, Defensa -1
  |wamuleto de fuerza|n    → Fuerza +2, Constitución +2
  |wanillo de destreza|n   → Destreza +3, Inteligencia +1

# Dónde encontrar equipo

El equipo se encuentra en salas del mundo o se obtiene como loot
al derrotar enemigos. Escribe |whelp loot|n para más información.
        """,
    },

    # ------------------------------------------------------------------ #
    #  Inventario
    # ------------------------------------------------------------------ #
    {
        "key": "inventario",
        "aliases": ["mochila", "bolsa"],
        "category": "General",
        "text": """
Tu inventario muestra todo lo que llevas encima.

# Secciones

  |wEQUIPADO|n  — objetos activos en cada slot (arma, armadura, accesorio).
               Sus bonificaciones están activas.
  |wMOCHILA|n   — el resto de objetos que llevas.

# Tipos de objetos en la mochila

  |c[arma]|n, |c[armadura]|n, |c[accesorio]|n  — equipo que aún no llevas puesto.
  |c[llave]|n                           — llaves para puertas cerradas.
  Sin etiqueta                         — objetos misceláneos (monedas, materiales…).

# Comandos relacionados

  |winv|n / |winventario|n  — ver inventario completo
  |wequipar <objeto>|n     — equipar un objeto de la mochila
  |wdesequipar <slot>|n    — desequipar y devolver a la mochila
  |wcoger <objeto>|n       — recoger un objeto del suelo
  |wsoltar <objeto>|n      — dejar un objeto en el suelo
        """,
    },

    # ------------------------------------------------------------------ #
    #  Puertas
    # ------------------------------------------------------------------ #
    {
        "key": "puertas",
        "aliases": ["puerta", "llave", "llaves", "cerrar", "abrir"],
        "category": "General",
        "text": """
Algunas salidas son puertas que pueden estar abiertas, cerradas o bloqueadas.

# Estado de una puerta

  |westadobuerta <salida>|n  — ver si está abierta, cerrada o bloqueada

# Abrir y cerrar

  |wabrir <salida>|n         — abrir una puerta cerrada
  |wcerrar <salida>|n        — cerrar una puerta abierta

# Puertas con llave

Para desbloquear o bloquear necesitas la llave correcta en tu inventario.

  |wdesbloquear <salida>|n   — desbloquear con la llave adecuada
  |wbloquear <salida>|n      — bloquear con la llave adecuada

Las llaves se encuentran en el mundo o como recompensa de misiones.
Algunos NPCs (guardianes) pueden impedir el paso incluso con llave.

# En la descripción de la sala

Las salidas bloqueadas aparecen como |x(cerrada con llave)|n.
Las salidas cerradas aparecen como |x(cerrada)|n.
        """,
    },

    # ------------------------------------------------------------------ #
    #  NPCs
    # ------------------------------------------------------------------ #
    {
        "key": "npcs",
        "aliases": ["npc", "enemigos", "personajes", "monstruos"],
        "category": "General",
        "text": """
El mundo está poblado por personajes no jugadores (NPCs).

# Temperamentos

  |ragresivo|n   — ataca en cuanto entras en su sala.
  |wneutral|n    — no ataca primero. Puede responder a conversación.
  |ycobarde|n    — no ataca primero. Puede huir si le atacas.
  |yguardián|n   — protege una zona. Ataca a quien no sea de su facción.

# Niveles y dificultad aproximada

  Nv. 1-2   Goblins (Bosque)
  Nv. 3     Goblin Jefe (Claro del Bosque), Bandidos (Calabozo)
  Nv. 5     Capitán Bandido (Celda), Guardia (Plaza)
  Nv. 8     Troll (Cueva Oscura)

# Hablar con NPCs

  |whablar <NPC>|n              — ver temas disponibles
  |whablar <NPC> = <tema>|n     — hablar sobre ese tema

  Ejemplo: |whablar guardia = bosque|n

# Al morir un NPC

El NPC suelta loot (monedas, equipo…) y reaparece pasado un tiempo.
Escribe |whelp loot|n o |whelp respawn|n para más detalles.
        """,
    },

    # ------------------------------------------------------------------ #
    #  Percibir
    # ------------------------------------------------------------------ #
    {
        "key": "percibir",
        "aliases": ["percepcion", "oculto", "examinar", "buscar"],
        "category": "General",
        "text": """
El comando |wpercibir|n (o |wexaminar|n) te permite descubrir detalles y
entidades ocultas en la sala actual.

# Nivel de percepción

Tu percepción depende de tu |wInteligencia|n y tu |wNivel|n:
  Percepción = Inteligencia + Nivel ÷ 2

# Qué puedes descubrir

  - Detalles ocultos de la sala (marcas, pasadizos, inscripciones…).
  - NPCs camuflados que normalmente no aparecen con |wlook|n.

  Cada detalle o NPC tiene un umbral mínimo de percepción.
  Si tu nivel es bajo, no verás todo aunque estés en la sala correcta.

# Uso

  |wpercibir|n   — examina la sala

El resultado muestra tu nivel de percepción actual y todo lo que logras
detectar. Cuanto mayor sea tu Inteligencia, más secretos descubrirás.
        """,
    },

    # ------------------------------------------------------------------ #
    #  Descansar
    # ------------------------------------------------------------------ #
    {
        "key": "descansar",
        "aliases": ["recuperar", "rest", "curar", "curarse"],
        "category": "General",
        "text": """
El comando |wdescansar|n permite recuperar puntos de vida fuera de combate.

# Cómo funciona

  - Recupera el |w25 %%|n de tu HP máximo.
  - Solo funciona fuera de combate.
  - Tiene un tiempo de espera de |w60 segundos|n entre usos.

# Uso

  |wdescansar|n

Si estás en combate recibirás un aviso. Si llevas toda la vida,
el juego te lo indicará. Tras descansar verás cuántos HP recuperaste.

# Otras formas de recuperar vida

  - Subir de nivel restaura el HP al máximo.
  - Morir y reaparecer te deja con 1 HP (ten cuidado).
        """,
    },

    # ------------------------------------------------------------------ #
    #  Loot
    # ------------------------------------------------------------------ #
    {
        "key": "loot",
        "aliases": ["botin", "recompensa", "drops"],
        "category": "General",
        "text": """
Cuando derrotas a un enemigo, este puede soltar objetos en la sala.

# Tipos de loot

  |wMonedas|n    — monedas de cobre, plata u oro. Objetos misceláneos.
  |wEquipo|n     — armas, armaduras y accesorios con bonificaciones.
  |wMateriales|n — ingredientes de alquimia u objetos de misión (garras, amuletos…).

# Probabilidades

Algunos objetos tienen una probabilidad de aparecer inferior al 100 %%.
Por ejemplo el goblin tiene un 15 %% de soltar una daga de bronce.

# Recoger el loot

Usa |wcoger <objeto>|n para recoger objetos del suelo.
Después puedes verlos con |winv|n y equiparlos con |wequipar <objeto>|n.

# Loot por enemigo (resumen)

  Goblin        — monedas de cobre, (15%%) daga de bronce
  Goblin Jefe   — monedas de plata, amuleto goblin, (30%%) espada de hierro
  Bandido       — bolsa de monedas, (20%%) armadura de cuero
  Capitán       — monedas, (50%%) hacha de guerra, (25%%) anillo de destreza
  Troll         — garra de troll, (25%%) cota de malla, (15%%) amuleto de fuerza
        """,
    },

    # ------------------------------------------------------------------ #
    #  Respawn
    # ------------------------------------------------------------------ #
    {
        "key": "respawn",
        "aliases": ["reaparecer", "regenerar", "volver"],
        "category": "General",
        "text": """
Los NPCs que mueren en combate reaparecen pasado un tiempo.

# Tiempos de reaparición

  Goblin            — 2 minutos
  Goblin Jefe       — 5 minutos
  Bandido           — 3 minutos
  Capitán Bandido   — 10 minutos
  Guardia           — 5 minutos
  Troll             — 15 minutos

# Comportamiento

  - El NPC reaparece en la misma sala donde murió.
  - Recupera todos sus HP y atributos originales.
  - Si era un NPC patrullero, reanuda su patrulla.
  - Si era un NPC oculto, reaparece sin anuncio.

# NPCs que NO reaparecen

  Los personajes únicos como el mesonero o la mercader no reaparecen
  si mueren. Son personajes irrecuperables.
        """,
    },

    # ------------------------------------------------------------------ #
    #  El mundo
    # ------------------------------------------------------------------ #
    {
        "key": "mundo",
        "aliases": ["mapa", "zonas", "lugares", "zonas del mundo"],
        "category": "General",
        "text": """
El mundo se divide en tres zonas principales conectadas desde la Plaza.

# Zona Ciudad (segura)

  |wPlaza de la Ciudad|n   — sala de inicio. Guardia de nivel 5.
  |wTaberna|n              — al este. Mesonero con información y comida.
  |wMercado|n              — al oeste. Mercader con objetos para vender.

# Zona Bosque (al norte de la Plaza)

  |wBosque del Norte|n     — Nv. 1-2. Goblin patrullero. Goblin espía oculto.
  |wClaro del Bosque|n     — Nv. 3. Campamento del Goblin Jefe.
  |wCueva Oscura|n         — Nv. 8. Guarida del Troll del Pantano.

# Zona Calabozo (al sur de la Plaza)

  |wEntrada al Calabozo|n  — Nv. 3. Primer bandido.
  |wPasillo del Calabozo|n — Nv. 3. Bandido de guardia.
  |wCelda Abandonada|n     — Nv. 5. Capitán Bandido (jefe de zona).

# Progresión recomendada

  Plaza → Bosque del Norte → Claro del Bosque
       → Entrada / Pasillo Calabozo → Celda Abandonada
       → Cueva Oscura (solo con buen equipo)

# Secretos

Usa |wpercibir|n en cada sala para descubrir detalles ocultos,
pasadizos y NPCs camuflados.
        """,
    },

]
