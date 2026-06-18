"""
Prototypes

Un prototipo es una forma de crear instancias individualizadas de una
typeclass. Es un diccionario con nombres de clave específicos.

Uso: spawn GOBLIN   (en el juego, como Builder o Admin)

Ver: https://github.com/evennia/evennia/wiki/Prototypes
"""

# --------------------------------------------------------------------------- #
#  Equipo: armas
# --------------------------------------------------------------------------- #

ESPADA_HIERRO = {
    "prototype_key": "ESPADA_HIERRO",
    "key": "espada de hierro",
    "typeclass": "typeclasses.objects.Equipo",
    "desc": "Una espada de hierro con el filo algo mellado pero funcional.",
    "attrs": [
        ("slot", "arma"),
        ("bonuses", {"fuerza": 3, "destreza": 1}),
        ("valor", 40),
    ],
}

DAGA_BRONCE = {
    "prototype_key": "DAGA_BRONCE",
    "key": "daga de bronce",
    "typeclass": "typeclasses.objects.Equipo",
    "desc": "Una daga ligera de bronce. Rápida y discreta.",
    "attrs": [
        ("slot", "arma"),
        ("bonuses", {"destreza": 3, "fuerza": 1}),
        ("valor", 25),
    ],
}

HACHA_GUERRA = {
    "prototype_key": "HACHA_GUERRA",
    "key": "hacha de guerra",
    "typeclass": "typeclasses.objects.Equipo",
    "desc": "Un hacha de guerra pesada con doble hoja. Requiere fuerza para manejarla.",
    "attrs": [
        ("slot", "arma"),
        ("bonuses", {"fuerza": 6, "defensa": -1}),
        ("valor", 60),
    ],
}

# --------------------------------------------------------------------------- #
#  Equipo: armaduras
# --------------------------------------------------------------------------- #

ARMADURA_CUERO = {
    "prototype_key": "ARMADURA_CUERO",
    "key": "armadura de cuero",
    "typeclass": "typeclasses.objects.Equipo",
    "desc": "Armadura ligera de cuero endurecido. Buen equilibrio entre protección y movilidad.",
    "attrs": [
        ("slot", "armadura"),
        ("bonuses", {"defensa": 4, "hp_max": 10}),
        ("valor", 50),
    ],
}

COTA_MALLA = {
    "prototype_key": "COTA_MALLA",
    "key": "cota de malla",
    "typeclass": "typeclasses.objects.Equipo",
    "desc": "Una cota de malla de acero. Pesada pero muy resistente.",
    "attrs": [
        ("slot", "armadura"),
        ("bonuses", {"defensa": 8, "hp_max": 20, "destreza": -2}),
        ("valor", 80),
    ],
}

# --------------------------------------------------------------------------- #
#  Equipo: accesorios
# --------------------------------------------------------------------------- #

AMULETO_FUERZA = {
    "prototype_key": "AMULETO_FUERZA",
    "key": "amuleto de fuerza",
    "typeclass": "typeclasses.objects.Equipo",
    "desc": "Un amuleto tallado en piedra roja. Se siente caliente al tacto.",
    "attrs": [
        ("slot", "accesorio"),
        ("bonuses", {"fuerza": 2, "constitucion": 2}),
        ("valor", 35),
    ],
}

ANILLO_DESTREZA = {
    "prototype_key": "ANILLO_DESTREZA",
    "key": "anillo de destreza",
    "typeclass": "typeclasses.objects.Equipo",
    "desc": "Un anillo de plata con una gema verde. Parece facilitar los movimientos.",
    "attrs": [
        ("slot", "accesorio"),
        ("bonuses", {"destreza": 3, "inteligencia": 1}),
        ("valor", 35),
    ],
}

# --------------------------------------------------------------------------- #
#  Consumibles: pociones y elixires
# --------------------------------------------------------------------------- #

POCION_VIDA = {
    "prototype_key": "POCION_VIDA",
    "key": "poción de vida",
    "typeclass": "typeclasses.objects.Consumible",
    "desc": "Un frasco de cristal con líquido rojo brillante. Restaura la vitalidad.",
    "attrs": [
        ("efecto", "curar_hp"),
        ("potencia", 30),
        ("usos", 1),
        ("valor", 15),
    ],
}

POCION_VIDA_MAYOR = {
    "prototype_key": "POCION_VIDA_MAYOR",
    "key": "poción de vida mayor",
    "typeclass": "typeclasses.objects.Consumible",
    "desc": "Un frasco grande de líquido carmesí que parece brillar desde dentro. Restaura mucha vitalidad.",
    "attrs": [
        ("efecto", "curar_hp"),
        ("potencia", 60),
        ("usos", 1),
        ("valor", 30),
    ],
}

ELIXIR_RESTAURACION = {
    "prototype_key": "ELIXIR_RESTAURACION",
    "key": "elixir de restauración",
    "typeclass": "typeclasses.objects.Consumible",
    "desc": "Un vial de líquido dorado que emana una leve luz cálida. Restaura toda la vitalidad.",
    "attrs": [
        ("efecto", "curar_maximo"),
        ("potencia", 0),
        ("usos", 1),
        ("valor", 75),
    ],
}

ANTIDOTO = {
    "prototype_key": "ANTIDOTO",
    "key": "antídoto",
    "typeclass": "typeclasses.objects.Consumible",
    "desc": "Una mezcla de hierbas destiladas en un frasco verde. Neutraliza venenos.",
    "attrs": [
        ("efecto", "curar_veneno"),
        ("potencia", 0),
        ("usos", 1),
        ("valor", 20),
    ],
}

# --------------------------------------------------------------------------- #
#  NPCs de combate
# --------------------------------------------------------------------------- #

GOBLIN = {
    "prototype_key": "GOBLIN",
    "key": "goblin",
    "typeclass": "typeclasses.npc.NPC",
    "desc": "Un goblin de piel verdosa con ojos amarillentos. Parece hambriento.",
    "attrs": [
        ("nivel", 1),
        ("hp", 30), ("hp_max", 30),
        ("fuerza", 8), ("destreza", 12), ("constitucion", 8),
        ("inteligencia", 6), ("defensa", 3),
        ("experiencia", 0),
        ("temperamento", "agresivo"),
        ("habilidades", ["golpe rapido"]),
        ("loot", [
            {"key": "monedas de cobre", "cantidad": 3,
             "desc": "Unas pocas monedas de cobre melladas."},
            {"prototype_key": "DAGA_BRONCE", "cantidad": 1, "chance": 0.15},
        ]),
        ("faction", "goblins"),
        ("faccion", "horda_salvaje"),
        ("npc_prototipo", "GOBLIN"),
        ("respawn_tiempo", 120),
    ],
}

GOBLIN_JEFE = {
    "prototype_key": "GOBLIN_JEFE",
    "key": "goblin jefe",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "Un goblin más corpulento que los demás, con una corona de huesos "
        "y una mueca feroz. Sus seguidores le temen y obedecen."
    ),
    "attrs": [
        ("nivel", 3),
        ("hp", 70), ("hp_max", 70),
        ("fuerza", 13), ("destreza", 14), ("constitucion", 11),
        ("inteligencia", 8), ("defensa", 5),
        ("experiencia", 0),
        ("temperamento", "agresivo"),
        ("habilidades", ["golpe rapido", "golpe fuerte"]),
        ("loot", [
            {"key": "monedas de plata", "cantidad": 5,
             "desc": "Monedas de plata con la cara de algún rey olvidado."},
            {"key": "amuleto goblin", "cantidad": 1,
             "desc": "Un amuleto tosco tallado en hueso. Los goblins lo consideran sagrado."},
            {"prototype_key": "ESPADA_HIERRO", "cantidad": 1, "chance": 0.30},
        ]),
        ("faction", "goblins"),
        ("faccion", "horda_salvaje"),
        ("npc_prototipo", "GOBLIN_JEFE"),
        ("respawn_tiempo", 300),
    ],
}

BANDIDO = {
    "prototype_key": "BANDIDO",
    "key": "bandido",
    "typeclass": "typeclasses.npc.NPC",
    "desc": "Un bandido de aspecto sucio con una capa raída. Te mira con recelo.",
    "attrs": [
        ("nivel", 3),
        ("hp", 60), ("hp_max", 60),
        ("fuerza", 13), ("destreza", 11), ("constitucion", 11),
        ("inteligencia", 9), ("defensa", 6),
        ("experiencia", 0),
        ("temperamento", "agresivo"),
        ("habilidades", ["corte", "golpe fuerte"]),
        ("loot", [
            {"key": "bolsa de monedas", "cantidad": 1,
             "desc": "Una bolsa de cuero con monedas mixtas."},
            {"prototype_key": "ARMADURA_CUERO", "cantidad": 1, "chance": 0.20},
        ]),
        ("faction", "bandidos"),
        ("faccion", "horda_salvaje"),
        ("dialogo", {"dinero": "Dame todo lo que tienes!", "piedad": "No hay piedad aqui."}),
        ("npc_prototipo", "BANDIDO"),
        ("respawn_tiempo", 180),
    ],
}

BANDIDO_CAPITAN = {
    "prototype_key": "BANDIDO_CAPITAN",
    "key": "capitán bandido",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "Un hombre de cicatrices profundas y mirada fría. "
        "Viste una armadura de cuero maltratada y lleva dos espadas cortas. "
        "Es el que manda entre los bandidos del calabozo."
    ),
    "attrs": [
        ("nivel", 5),
        ("hp", 120), ("hp_max", 120),
        ("fuerza", 16), ("destreza", 14), ("constitucion", 13),
        ("inteligencia", 11), ("defensa", 9),
        ("experiencia", 0),
        ("temperamento", "agresivo"),
        ("habilidades", ["corte", "golpe fuerte", "embestida"]),
        ("loot", [
            {"key": "bolsa de monedas", "cantidad": 3,
             "desc": "Una bolsa de cuero bien cargada con monedas variadas."},
            {"prototype_key": "HACHA_GUERRA", "cantidad": 1, "chance": 0.50},
            {"prototype_key": "ANILLO_DESTREZA", "cantidad": 1, "chance": 0.25},
        ]),
        ("faction", "bandidos"),
        ("faccion", "horda_salvaje"),
        ("dialogo", {
            "rendirse": "Nadie se rinde ante mí. Los débiles mueren.",
            "capitan": "Así es. Y tú has cometido el error de encontrarme.",
        }),
        ("npc_prototipo", "BANDIDO_CAPITAN"),
        ("respawn_tiempo", 600),
    ],
}

GUARDIA = {
    "prototype_key": "GUARDIA",
    "key": "guardia de la ciudad",
    "typeclass": "typeclasses.npc.NPC",
    "desc": "Un guardia con armadura de cuero reforzada. Observa a todos los que entran.",
    "attrs": [
        ("nivel", 5),
        ("hp", 100), ("hp_max", 100),
        ("fuerza", 14), ("destreza", 10), ("constitucion", 14),
        ("inteligencia", 10), ("defensa", 10),
        ("experiencia", 0),
        ("temperamento", "guardian"),
        ("habilidades", ["embestida", "golpe fuerte"]),
        ("faction", "ciudad"),
        ("faccion", "ciudadanos"),
        ("dialogo", {
            "hola": "Que pases un buen dia, ciudadano.",
            "ayuda": "Si tienes problemas, habla con el Capitan.",
            "criminal": "Alto! Ningun criminal pasa por aqui.",
            "calabozo": "Ten cuidado al sur. Hay bandidos merodeando.",
            "bosque": "El bosque del norte es peligroso. Los goblins atacan sin avisar.",
        }),
        ("npc_prototipo", "GUARDIA"),
        ("respawn_tiempo", 300),
    ],
}

TROLL = {
    "prototype_key": "TROLL",
    "key": "troll del pantano",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "Una criatura enorme de piel grisácea y verrugas. "
        "Sus ojos rojos brillan con ferocidad y sus brazos largos "
        "podrían derribar un árbol de un solo golpe."
    ),
    "attrs": [
        ("nivel", 8),
        ("hp", 200), ("hp_max", 200),
        ("fuerza", 20), ("destreza", 7), ("constitucion", 18),
        ("inteligencia", 5), ("defensa", 12),
        ("experiencia", 0),
        ("temperamento", "agresivo"),
        ("habilidades", ["embestida", "golpe fuerte", "veneno"]),
        ("loot", [
            {"key": "garra de troll", "cantidad": 1,
             "desc": "Una garra enorme y afilada. Los alquimistas la pagan bien."},
            {"prototype_key": "COTA_MALLA", "cantidad": 1, "chance": 0.25},
            {"prototype_key": "AMULETO_FUERZA", "cantidad": 1, "chance": 0.15},
        ]),
        ("faccion", "sombras_pantano"),
        ("npc_prototipo", "TROLL"),
        ("respawn_tiempo", 900),
    ],
}

# --------------------------------------------------------------------------- #
#  NPCs civiles / neutrales
# --------------------------------------------------------------------------- #

MESONERO = {
    "prototype_key": "MESONERO",
    "key": "Gareth el mesonero",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "Un hombre robusto de delantal manchado y sonrisa amplia. "
        "Limpia un vaso con un trapo mientras te observa llegar."
    ),
    "attrs": [
        ("nivel", 1),
        ("hp", 50), ("hp_max", 50),
        ("fuerza", 10), ("destreza", 10), ("constitucion", 10),
        ("inteligencia", 10), ("defensa", 2),
        ("experiencia", 0),
        ("temperamento", "neutral"),
        ("habilidades", []),
        ("faction", "ciudad"),
        ("faccion", "ciudadanos"),
        ("dialogo", {
            "hola": "Bienvenido a El Jabali Borracho! Que te pongo?",
            "bebida": "Tengo cerveza oscura y vino de la region. Tres cobres la jarra.",
            "comida": "Hoy hay estofado de jabali y pan de centeno. Cinco cobres.",
            "descanso": "Una cama para pasar la noche? Diez cobres, sin preguntas.",
            "noticias": "Se dice que los bandidos del calabozo tienen a alguien secuestrado.",
            "calabozo": "Yo no bajo ahi ni loco. Esa gente es peligrosa.",
        }),
        ("tienda", [
            {"key": "cerveza oscura",    "precio": 3,  "cantidad": -1, "valor": 3,
             "desc": "Una jarra de cerveza oscura y espumosa. Caliente el cuerpo."},
            {"key": "vino de la región", "precio": 5,  "cantidad": -1, "valor": 5,
             "desc": "Un vaso de vino tinto afrutado, cosecha local."},
            {"key": "estofado de jabalí","precio": 5,  "cantidad": -1, "valor": 5,
             "desc": "Un cuenco humeante con trozos de jabalí y verduras de temporada."},
            {"key": "pan de centeno",    "precio": 2,  "cantidad": -1, "valor": 2,
             "desc": "Una hogaza densa de pan de centeno. Llena el estómago."},
            {"key": "poción de vida",    "prototype_key": "POCION_VIDA",
             "precio": 15, "cantidad": -1},
            {"key": "antídoto",          "prototype_key": "ANTIDOTO",
             "precio": 20, "cantidad": -1},
        ]),
        ("npc_prototipo", "MESONERO"),
        ("respawn_tiempo", 300),
    ],
}

MERCADER = {
    "prototype_key": "MERCADER",
    "key": "Mira la mercader",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "Una mujer de mediana edad con ropas coloridas y muchos collares. "
        "Revisa sus mercancías con ojo experto."
    ),
    "attrs": [
        ("nivel", 1),
        ("hp", 40), ("hp_max", 40),
        ("fuerza", 8), ("destreza", 10), ("constitucion", 9),
        ("inteligencia", 14), ("defensa", 1),
        ("experiencia", 0),
        ("temperamento", "neutral"),
        ("habilidades", []),
        ("faction", "ciudad"),
        ("faccion", "ciudadanos"),
        ("dialogo", {
            "hola": "Buen dia! Tengo todo lo que un aventurero necesita.",
            "comprar": "Dime que buscas y vere que puedo hacer.",
            "vender": "Siempre estoy interesada en objetos raros. Que tienes?",
            "precios": "Los precios son justos, te lo juro por los dioses.",
            "garra": "Una garra de troll? Eso vale bastante. Los alquimistas la pagan bien.",
            "goblin": "Los amuletos goblin traen mala suerte. No los quiero cerca.",
            "pantano": "El pantano al norte de la cueva es muy peligroso. Cuentan que hay algo peor que trolls.",
            "catacumbas": "Las catacumbas bajo el calabozo llevan siglos selladas. Quien las abrio no volvio.",
            "escama": "Escamas de hombre lagarto? Son resistentes al fuego. Te las pago bien.",
            "grimorio": "Un grimorio del nigromante? Eso es magia oscura. No lo quiero... pero te lo compro igual.",
        }),
        ("tienda", [
            {"key": "espada de hierro",       "prototype_key": "ESPADA_HIERRO",       "precio": 40, "cantidad": -1},
            {"key": "daga de bronce",         "prototype_key": "DAGA_BRONCE",         "precio": 25, "cantidad": -1},
            {"key": "armadura de cuero",      "prototype_key": "ARMADURA_CUERO",      "precio": 50, "cantidad": -1},
            {"key": "amuleto de fuerza",      "prototype_key": "AMULETO_FUERZA",      "precio": 35, "cantidad": -1},
            {"key": "anillo de destreza",     "prototype_key": "ANILLO_DESTREZA",     "precio": 35, "cantidad": -1},
            {"key": "poción de vida mayor",   "prototype_key": "POCION_VIDA_MAYOR",   "precio": 30, "cantidad": -1},
            {"key": "elixir de restauración", "prototype_key": "ELIXIR_RESTAURACION", "precio": 75, "cantidad": -1},
        ]),
        ("npc_prototipo", "MERCADER"),
        ("respawn_tiempo", 300),
    ],
}

# --------------------------------------------------------------------------- #
#  Equipo: expansión de zonas
# --------------------------------------------------------------------------- #

BACULO_ARCANO_ANTIGUO = {
    "prototype_key": "BACULO_ARCANO_ANTIGUO",
    "key": "báculo arcano antiguo",
    "typeclass": "typeclasses.objects.Equipo",
    "desc": (
        "Un báculo de madera oscura con un cristal azulado engastado en la punta. "
        "Vibra levemente al tocarlo, como si almacenara energía arcana."
    ),
    "attrs": [
        ("slot", "arma"),
        ("bonuses", {"inteligencia": 6, "defensa": -1}),
        ("valor", 75),
    ],
}

ESCUDO_ROBLE = {
    "prototype_key": "ESCUDO_ROBLE",
    "key": "escudo de roble",
    "typeclass": "typeclasses.objects.Equipo",
    "desc": (
        "Un escudo circular de madera de roble reforzada con remaches de hierro. "
        "Ligero y resistente, ideal para aventureros que empiezan."
    ),
    "attrs": [
        ("slot", "armadura"),
        ("bonuses", {"defensa": 5, "hp_max": 8}),
        ("valor", 35),
    ],
}

LANZA_HUESO = {
    "prototype_key": "LANZA_HUESO",
    "key": "lanza de hueso",
    "typeclass": "typeclasses.objects.Equipo",
    "desc": "Una lanza tallada con hueso de criatura desconocida. Ligera pero resistente.",
    "attrs": [
        ("slot", "arma"),
        ("bonuses", {"fuerza": 4, "destreza": 2}),
        ("valor", 30),
    ],
}

GRIMORIO_NIGROMANTE = {
    "prototype_key": "GRIMORIO_NIGROMANTE",
    "key": "grimorio del nigromante",
    "typeclass": "typeclasses.objects.Equipo",
    "desc": (
        "Un tomo encuadernado en cuero oscuro con páginas de pergamino amarillento. "
        "Los símbolos inscritos pulsan con una luz fría. "
        "Quien lo porta siente que algo lo observa desde las páginas."
    ),
    "attrs": [
        ("slot", "accesorio"),
        ("bonuses", {"inteligencia": 5, "defensa": 2, "hp_max": -10}),
        ("valor", 80),
    ],
}

# --------------------------------------------------------------------------- #
#  NPCs de expansión: Pantano del Troll
# --------------------------------------------------------------------------- #

SERPIENTE_PANTANO = {
    "prototype_key": "SERPIENTE_PANTANO",
    "key": "serpiente del pantano",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "Una serpiente gruesa de escamas verde oscuro y ojos amarillos. "
        "Se desliza silenciosamente entre los juncos."
    ),
    "attrs": [
        ("nivel", 2),
        ("hp", 25), ("hp_max", 25),
        ("fuerza", 9), ("destreza", 14), ("constitucion", 8),
        ("inteligencia", 3), ("defensa", 3),
        ("experiencia", 0),
        ("temperamento", "agresivo"),
        ("habilidades", ["veneno"]),
        ("loot", [
            {"key": "piel de serpiente", "cantidad": 1,
             "desc": "Una piel de serpiente en buen estado. Los curtidores la usan."},
            {"key": "veneno de pantano", "cantidad": 1, "chance": 0.30,
             "desc": "Un frasco con veneno extraído de una serpiente del pantano."},
        ]),
        ("faccion", "sombras_pantano"),
        ("npc_prototipo", "SERPIENTE_PANTANO"),
        ("respawn_tiempo", 90),
    ],
}

HOMBRE_LAGARTO = {
    "prototype_key": "HOMBRE_LAGARTO",
    "key": "hombre lagarto",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "Una criatura bípeda de piel escamosa verde y marrón, con ojos de reptil. "
        "Empuña una lanza de hueso y te observa con desconfianza territorial."
    ),
    "attrs": [
        ("nivel", 4),
        ("hp", 80), ("hp_max", 80),
        ("fuerza", 14), ("destreza", 12), ("constitucion", 13),
        ("inteligencia", 7), ("defensa", 7),
        ("experiencia", 0),
        ("temperamento", "guardian"),
        ("habilidades", ["embestida", "corte"]),
        ("faction", "pantano"),
        ("faccion", "sombras_pantano"),
        ("loot", [
            {"key": "escama de lagarto", "cantidad": 2,
             "desc": "Escamas duras arrancadas de un hombre lagarto. Resistentes al fuego."},
            {"prototype_key": "LANZA_HUESO", "cantidad": 1, "chance": 0.35},
        ]),
        ("dialogo", {
            "paz": "Ssss... forastero no pertenece aqui. Irse.",
            "pantano": "Pantano es nuestro. Ancestros lo guardaron. Nosotros lo guardamos.",
            "troll": "Troll vive mas al fondo. Es viejo. Muy viejo. No despertarlo.",
        }),
        ("npc_prototipo", "HOMBRE_LAGARTO"),
        ("respawn_tiempo", 240),
    ],
}

# --------------------------------------------------------------------------- #
#  NPCs de expansión: Catacumbas
# --------------------------------------------------------------------------- #

ESQUELETO = {
    "prototype_key": "ESQUELETO",
    "key": "esqueleto guerrero",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "Un esqueleto animado con restos de armadura oxidada. "
        "Se mueve con una rigidez inquietante y sus cuencas oculares brillan con luz roja."
    ),
    "attrs": [
        ("nivel", 3),
        ("hp", 45), ("hp_max", 45),
        ("fuerza", 12), ("destreza", 8), ("constitucion", 14),
        ("inteligencia", 3), ("defensa", 6),
        ("experiencia", 0),
        ("temperamento", "agresivo"),
        ("habilidades", ["golpe fuerte"]),
        ("loot", [
            {"key": "hueso roto", "cantidad": 1,
             "desc": "Un hueso de dudosa procedencia. No parece tener uso inmediato."},
            {"prototype_key": "ARMADURA_CUERO", "cantidad": 1, "chance": 0.10},
        ]),
        ("faccion", "legion_oscura"),
        ("npc_prototipo", "ESQUELETO"),
        ("respawn_tiempo", 150),
    ],
}

LICHE_MENOR = {
    "prototype_key": "LICHE_MENOR",
    "key": "liche menor",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "Una figura encapuchada que flota varios centímetros sobre el suelo. "
        "Bajo la capucha no hay rostro, solo oscuridad absoluta y dos puntos de luz azul. "
        "Emana un frío sobrenatural y el aire a su alrededor parece muerto."
    ),
    "attrs": [
        ("nivel", 6),
        ("hp", 110), ("hp_max", 110),
        ("fuerza", 10), ("destreza", 13), ("constitucion", 15),
        ("inteligencia", 18), ("defensa", 8),
        ("experiencia", 0),
        ("temperamento", "agresivo"),
        ("habilidades", ["veneno", "corte", "golpe rapido"]),
        ("loot", [
            {"key": "fragmento de alma", "cantidad": 1,
             "desc": "Un cristal oscuro que pulsa débilmente. Los nigromantes lo usan en rituales."},
            {"prototype_key": "GRIMORIO_NIGROMANTE", "cantidad": 1, "chance": 0.60},
            {"prototype_key": "COTA_MALLA", "cantidad": 1, "chance": 0.20},
        ]),
        ("dialogo", {
            "alma": "Tu alma... sera mia pronto.",
            "nigromante": "Fui el mas grande nigromante de esta era. Ahora soy eterno.",
            "sello": "El sello rojo... lo reconozco. Era de mi discipulo. El capitan.",
            "grimorio": "Ese grimorio contiene poder que tu mente no puede contener.",
        }),
        ("faccion", "legion_oscura"),
        ("npc_prototipo", "LICHE_MENOR"),
        ("respawn_tiempo", 600),
    ],
}

# --------------------------------------------------------------------------- #
#  NPCs de expansión: Ruinas del Templo
# --------------------------------------------------------------------------- #

ESPECTRO = {
    "prototype_key": "ESPECTRO",
    "key": "espectro",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "Una figura etérea de niebla blanquecina con contornos vagamente humanos. "
        "Sus ojos son dos puntos de luz azul helada y se mueve sin tocar el suelo. "
        "Emite un lamento apenas audible que hiela la sangre."
    ),
    "attrs": [
        ("nivel", 4),
        ("hp", 50), ("hp_max", 50),
        ("fuerza", 8), ("destreza", 13), ("constitucion", 9),
        ("inteligencia", 16), ("defensa", 4),
        ("experiencia", 0),
        ("temperamento", "agresivo"),
        ("habilidades", ["dardo magico", "veneno"]),
        ("loot", [
            {"key": "cristal sagrado", "cantidad": 1, "chance": 0.60,
             "desc": "Un cristal que emite una tenue luz dorada. Los sacerdotes lo usan en rituales de purificación."},
            {"key": "símbolo sagrado", "cantidad": 1, "chance": 0.40,
             "desc": "Un símbolo de metal bendito con runas protectoras. Parece importante."},
        ]),
        ("faccion", "legion_oscura"),
        ("npc_prototipo", "ESPECTRO"),
        ("respawn_tiempo", 120),
    ],
}

CABALLERO_OSCURO = {
    "prototype_key": "CABALLERO_OSCURO",
    "key": "caballero oscuro",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "Una figura imponente enfundada en una armadura negra sin brillo, "
        "coronada por un yelmo con visera cerrada. No respira. "
        "Empuña una espada de metal oscuro que absorbe la luz a su alrededor. "
        "Sus movimientos son lentos pero devastadores."
    ),
    "attrs": [
        ("nivel", 8),
        ("hp", 180), ("hp_max", 180),
        ("fuerza", 20), ("destreza", 11), ("constitucion", 17),
        ("inteligencia", 9), ("defensa", 14),
        ("experiencia", 0),
        ("temperamento", "agresivo"),
        ("habilidades", ["golpe fuerte", "embestida", "golpe maestro"]),
        ("loot", [
            {"key": "monedas de oro", "cantidad": 15,
             "desc": "Monedas de oro antiguas con el escudo del Barón Morthis."},
            {"prototype_key": "ESCUDO_ROBLE", "cantidad": 1},
            {"prototype_key": "BACULO_ARCANO_ANTIGUO", "cantidad": 1, "chance": 0.30},
        ]),
        ("dialogo", {
            "baron": "Fui el Barón Morthis. Ahora soy la muerte encarnada.",
            "templo": "Este templo me pertenece. Y tú pronto serás uno de mis siervos.",
            "rendirse": "La muerte no conoce la rendición.",
        }),
        ("faccion", "legion_oscura"),
        ("npc_prototipo", "CABALLERO_OSCURO"),
        ("respawn_tiempo", 900),
    ],
}

BANQUERO = {
    "prototype_key": "BANQUERO",
    "key": "Cornelio el Banquero",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "Un hombre de aspecto metódico, con un libro de cuentas bajo el brazo "
        "y gafas de media luna. Su ropa es discreta pero de buena calidad. "
        "Te observa con cortesía profesional."
    ),
    "attrs": [
        ("nivel", 1),
        ("hp", 60), ("hp_max", 60),
        ("fuerza", 8), ("destreza", 9), ("constitucion", 9),
        ("inteligencia", 14), ("defensa", 2),
        ("experiencia", 0),
        ("temperamento", "neutral"),
        ("habilidades", []),
        ("faction", "ciudad"),
        ("faccion", "ciudadanos"),
        ("es_banquero", True),
        ("dialogo", {
            "hola": "Buenos días. ¿Desea depositar o retirar sus objetos?",
            "banco": "Su bóveda personal está a su disposición. Acceso seguro, sin coste.",
            "depositar": "Use el comando 'depositar <objeto>' para guardar sus pertenencias.",
            "retirar": "Use el comando 'retirar <objeto>' para recuperar sus objetos.",
            "seguridad": "Su bóveda es completamente privada. Nadie puede acceder excepto usted.",
            "interés": "No cobramos comisiones. Es un servicio de la ciudad para sus ciudadanos.",
        }),
        ("npc_prototipo", "BANQUERO"),
        ("respawn_tiempo", 300),
    ],
}

# --------------------------------------------------------------------------- #
#  Equipo: Minas de Hierro Viejo
# --------------------------------------------------------------------------- #

PICO_HIERRO = {
    "prototype_key": "PICO_HIERRO",
    "key": "pico de minero",
    "typeclass": "typeclasses.objects.Equipo",
    "desc": "Un pico de minero reconvertido en arma de combate. Pesado pero con buen filo en la punta.",
    "attrs": [
        ("slot", "arma"),
        ("bonuses", {"fuerza": 5, "constitucion": 1}),
        ("valor", 45),
    ],
}

ANILLO_CONSTITUCION = {
    "prototype_key": "ANILLO_CONSTITUCION",
    "key": "anillo de constitución",
    "typeclass": "typeclasses.objects.Equipo",
    "desc": (
        "Un anillo forjado con mineral de la mina, cálido al tacto. "
        "Quien lo porta siente una resistencia sobrenatural."
    ),
    "attrs": [
        ("slot", "accesorio"),
        ("bonuses", {"constitucion": 4, "hp_max": 15}),
        ("valor", 55),
    ],
}

# --------------------------------------------------------------------------- #
#  NPCs de expansión: Minas de Hierro Viejo
# --------------------------------------------------------------------------- #

ARANA_CUEVA = {
    "prototype_key": "ARANA_CUEVA",
    "key": "araña de cueva",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "Una araña de patas largas y abdomen oscuro, del tamaño de un perro mediano. "
        "Sus ocho ojos reflectantes te siguen con frialdad calculada. "
        "Hilo plateado cuelga de sus quelíceros."
    ),
    "attrs": [
        ("nivel", 3),
        ("hp", 55), ("hp_max", 55),
        ("fuerza", 11), ("destreza", 16), ("constitucion", 10),
        ("inteligencia", 4), ("defensa", 5),
        ("experiencia", 0),
        ("temperamento", "agresivo"),
        ("habilidades", ["corte", "veneno"]),
        ("loot", [
            {"key": "hilo de araña", "cantidad": 2,
             "desc": "Hilo de araña resistente y fino. Útil en alquimia y artesanía."},
            {"key": "colmillo de araña", "cantidad": 1, "chance": 0.40,
             "desc": "Un colmillo hueco de araña de cueva. Aún rezuma veneno."},
        ]),
        ("faccion", "horda_salvaje"),
        ("npc_prototipo", "ARANA_CUEVA"),
        ("respawn_tiempo", 120),
    ],
}

MINERO_MALDITO = {
    "prototype_key": "MINERO_MALDITO",
    "key": "minero maldito",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "El cadáver animado de un minero cuya piel está gris como la piedra. "
        "Empuña un pico oxidado con manos rígidas. "
        "Sus ojos no reflejan luz alguna y arrastra los pies con cada paso."
    ),
    "attrs": [
        ("nivel", 4),
        ("hp", 80), ("hp_max", 80),
        ("fuerza", 15), ("destreza", 8), ("constitucion", 16),
        ("inteligencia", 3), ("defensa", 7),
        ("experiencia", 0),
        ("temperamento", "agresivo"),
        ("habilidades", ["golpe fuerte", "embestida"]),
        ("loot", [
            {"key": "mineral de hierro", "cantidad": 1, "chance": 0.60,
             "desc": "Un trozo de mineral de hierro sin procesar. De buen color y peso sólido."},
            {"key": "gema en bruto", "cantidad": 1, "chance": 0.20,
             "desc": "Una gema sin tallar de color violáceo. Los joyeros la pagarían bien."},
            {"prototype_key": "PICO_HIERRO", "cantidad": 1, "chance": 0.15},
        ]),
        ("faccion", "legion_oscura"),
        ("npc_prototipo", "MINERO_MALDITO"),
        ("respawn_tiempo", 180),
    ],
}

GOLEM_PIEDRA = {
    "prototype_key": "GOLEM_PIEDRA",
    "key": "gólem de piedra",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "Una colosal figura de roca y arcilla que ocupa casi toda la caverna. "
        "Su cuerpo está surcado de venas de mineral que brillan con un resplandor rojizo. "
        "Cada paso hace temblar el suelo. No tiene rostro, "
        "solo dos grietas luminosas donde deberían estar los ojos."
    ),
    "attrs": [
        ("nivel", 7),
        ("hp", 200), ("hp_max", 200),
        ("fuerza", 22), ("destreza", 5), ("constitucion", 20),
        ("inteligencia", 3), ("defensa", 16),
        ("experiencia", 0),
        ("temperamento", "agresivo"),
        ("habilidades", ["golpe fuerte", "embestida", "golpe maestro"]),
        ("loot", [
            {"key": "núcleo de piedra", "cantidad": 1,
             "desc": "El núcleo arcano que animaba al gólem. Emana calor y vibra levemente."},
            {"prototype_key": "PICO_HIERRO", "cantidad": 1},
            {"prototype_key": "ANILLO_CONSTITUCION", "cantidad": 1, "chance": 0.30},
        ]),
        ("faccion", "legion_oscura"),
        ("npc_prototipo", "GOLEM_PIEDRA"),
        ("respawn_tiempo", 900),
    ],
}

BUSCADOR_TESOROS = {
    "prototype_key": "BUSCADOR_TESOROS",
    "key": "Torben el buscador de tesoros",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "Un hombre de mediana edad con ropa de cuero desgastada y varias bolsas colgando del cinturón. "
        "Sus ojos brillan con entusiasmo cuando habla de riquezas enterradas. "
        "Consulta un mapa hecho jirones que guarda con celo."
    ),
    "attrs": [
        ("nivel", 1),
        ("hp", 60), ("hp_max", 60),
        ("fuerza", 10), ("destreza", 12), ("constitucion", 10),
        ("inteligencia", 12), ("defensa", 2),
        ("experiencia", 0),
        ("temperamento", "neutral"),
        ("habilidades", []),
        ("faction", "aventureros"),
        ("faccion", "gremio_aventureros"),
        ("dialogo", {
            "hola": "¡Bienvenido! Tengo información valiosa sobre las minas al oeste del bosque.",
            "minas": "Las Minas de Hierro Viejo llevan siglos abandonadas. Digo yo que hay algo interesante ahí dentro.",
            "mineral": "El mineral de hierro de esas minas es de la mejor calidad. Tráeme algunos y te compensaré.",
            "gólem": "Hay un gólem guardián en las profundidades. Quien lo derrote será famoso en el Gremio.",
            "gremio": "Soy miembro del Gremio de Aventureros. Siempre buscamos valientes para explorar lugares peligrosos.",
            "araña": "Las arañas de cueva son el menor de los problemas. Lo que hay más adentro... eso sí que es peligroso.",
            "comprar": "Tengo equipo para exploradores. ¿Qué necesitas?",
        }),
        ("tienda", [
            {"key": "pico de minero",  "prototype_key": "PICO_HIERRO",  "precio": 45, "cantidad": -1},
            {"key": "antídoto",        "prototype_key": "ANTIDOTO",      "precio": 20, "cantidad": -1},
            {"key": "poción de vida",  "prototype_key": "POCION_VIDA",   "precio": 15, "cantidad": -1},
        ]),
        ("npc_prototipo", "BUSCADOR_TESOROS"),
        ("respawn_tiempo", 300),
    ],
}

SACERDOTE = {
    "prototype_key": "SACERDOTE",
    "key": "Hermano Aldric el sacerdote",
    "typeclass": "typeclasses.npc.NPC",
    "desc": (
        "Un hombre de mediana edad con hábito gris y un símbolo sagrado colgado al cuello. "
        "Sus ojos transmiten calma pero hay preocupación en su frente. "
        "Murmura oraciones en voz baja mientras contempla el horizonte norte."
    ),
    "attrs": [
        ("nivel", 1),
        ("hp", 60), ("hp_max", 60),
        ("fuerza", 9), ("destreza", 9), ("constitucion", 10),
        ("inteligencia", 13), ("defensa", 2),
        ("experiencia", 0),
        ("temperamento", "neutral"),
        ("habilidades", []),
        ("faction", "ciudad"),
        ("faccion", "ciudadanos"),
        ("dialogo", {
            "hola": "Que los dioses te guarden, viajero. Soy Hermano Aldric.",
            "templo": "El antiguo templo al norte del bosque fue profanado hace siglos. Los espectros lo habitan ahora.",
            "espectros": "Seres de niebla y odio. Los cristales que portan son restos de almas atrapadas.",
            "caballero": "El Barón Morthis... un guerrero que cayó en la oscuridad. Su espíritu gobierna a los espectros.",
            "cristales": "Los cristales sagrados tienen propiedades curativas si se procesan correctamente.",
            "bendición": "La Luz te proteja en tu camino hacia el norte.",
            "misión": "Necesito ayuda urgente con el templo. ¿Te interesa escuchar?",
            "comprar": "Tengo artículos que pueden ayudarte.",
        }),
        ("tienda", [
            {"key": "poción de vida",        "prototype_key": "POCION_VIDA",          "precio": 15, "cantidad": -1},
            {"key": "elixir de restauración","prototype_key": "ELIXIR_RESTAURACION",  "precio": 75, "cantidad": -1},
            {"key": "báculo arcano antiguo", "prototype_key": "BACULO_ARCANO_ANTIGUO","precio": 80, "cantidad": 3},
            {"key": "escudo de roble",        "prototype_key": "ESCUDO_ROBLE",         "precio": 30, "cantidad": -1},
        ]),
        ("npc_prototipo", "SACERDOTE"),
        ("respawn_tiempo", 300),
    ],
}
