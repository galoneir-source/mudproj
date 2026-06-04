"""
systems/reputation/factions.py

Definición de facciones y umbrales de reputación. Sin dependencias de Evennia.
"""

FACCIONES = {
    "ciudadanos": {
        "nombre": "Ciudadanos",
        "desc": "Los habitantes de la ciudad: comerciantes, posaderos y la guardia.",
    },
    "gremio_aventureros": {
        "nombre": "Gremio de Aventureros",
        "desc": "Exploradores y cazadores de recompensas que gestionan los encargos del mundo.",
    },
    "horda_salvaje": {
        "nombre": "Horda Salvaje",
        "desc": "Goblins y bandidos que asolan los caminos y el bosque norte.",
    },
    "sombras_pantano": {
        "nombre": "Sombras del Pantano",
        "desc": "Trolls, serpientes y hombres lagarto que dominan el pantano cenagoso.",
    },
    "legion_oscura": {
        "nombre": "Legión Oscura",
        "desc": "Los no-muertos de las catacumbas, guiados por el liche menor.",
    },
}

# (umbral_superior_exclusivo, titulo, color_evennia)
# La primera entrada en la que puntos < umbral determina el nivel actual.
# La última entrada tiene umbral=None (sin tope superior) → Exaltado.
NIVELES_REP = [
    (-3000, "Enemigo",  "|r"),
    (-1000, "Hostil",   "|R"),
    ( 1000, "Neutral",  "|w"),
    ( 3000, "Amistoso", "|g"),
    ( 6000, "Honrado",  "|G"),
    (12000, "Venerado", "|c"),
    ( None, "Exaltado", "|Y"),
]

REP_MINIMA = -6000
REP_MAXIMA = 21000
