"""
systems/weather/weather.py

Lógica pura del sistema de clima dinámico. Sin dependencias de Evennia.

Climas disponibles: despejado, nublado, lluvia, tormenta, niebla.
Tick del script: 10 minutos reales → el clima cambia de forma gradual y
probabilística según la matriz de transiciones.
"""
from __future__ import annotations

import random

# Catálogo de climas con sus metadatos y textos de ambiente por tipo de entorno.
CLIMAS: dict[str, dict] = {
    "despejado": {
        "nombre": "Despejado",
        "color": "|Y",
        "textos": {
            "exterior_natural": "El cielo está despejado. El sol brilla con claridad.",
            "exterior_urbano":  "El cielo está despejado. El sol calienta los adoquines.",
        },
    },
    "nublado": {
        "nombre": "Nublado",
        "color": "|w",
        "textos": {
            "exterior_natural": "Nubes grises cubren el cielo, ocultando el sol.",
            "exterior_urbano":  "El cielo está encapotado. Un viento frío recorre las calles.",
        },
    },
    "lluvia": {
        "nombre": "Lluvia",
        "color": "|c",
        "textos": {
            "exterior_natural": "La lluvia cae sobre el suelo. El olor a tierra mojada se extiende por el aire.",
            "exterior_urbano":  "La lluvia golpea los adoquines. Los transeúntes buscan refugio bajo los aleros.",
        },
    },
    "tormenta": {
        "nombre": "Tormenta",
        "color": "|r",
        "textos": {
            "exterior_natural": "Una tormenta azota la zona. Relámpagos iluminan el cielo entre truenos ensordecedores.",
            "exterior_urbano":  "Una violenta tormenta sacude la ciudad. Las antorchas luchan contra el viento.",
        },
    },
    "niebla": {
        "nombre": "Niebla",
        "color": "|x",
        "textos": {
            "exterior_natural": "Una densa niebla lo envuelve todo. Apenas se distinguen las siluetas cercanas.",
            "exterior_urbano":  "La niebla se arrastra entre los edificios, ocultando calles y rincones.",
        },
    },
}

# Pesos de transición entre climas.
# Las claves externas son el clima actual; las internas, los posibles siguientes.
# Los pesos son relativos (no necesitan sumar 100).
TRANSICIONES: dict[str, dict[str, int]] = {
    "despejado": {"despejado": 60, "nublado": 25, "niebla": 15},
    "nublado":   {"nublado": 40, "despejado": 20, "lluvia": 30, "niebla": 10},
    "lluvia":    {"lluvia": 40, "nublado": 30, "tormenta": 20, "despejado": 10},
    "tormenta":  {"tormenta": 30, "lluvia": 50, "nublado": 20},
    "niebla":    {"niebla": 40, "despejado": 40, "nublado": 20},
}

# Penalización a la percepción según el clima (negativa o cero).
PENALIZACION_PERCEPCION: dict[str, int] = {
    "despejado":  0,
    "nublado":    0,
    "lluvia":    -1,
    "tormenta":  -2,
    "niebla":    -4,
}

# Mensaje de broadcast al cambiar de clima (se envía a todos los jugadores conectados).
MENSAJES_TRANSICION: dict[str, str] = {
    "despejado": "Las nubes se disipan. El sol vuelve a brillar en el cielo.",
    "nublado":   "El cielo se cubre de nubes. El sol desaparece entre los grises.",
    "lluvia":    "Comienza a llover. Las primeras gotas golpean el suelo con suavidad.",
    "tormenta":  "La lluvia arrecia y el cielo estalla en truenos. ¡Una tormenta se desata!",
    "niebla":    "Una densa niebla surge de la tierra, envolviendo el mundo en misterio.",
}


# --------------------------------------------------------------------------- #
#  Funciones puras
# --------------------------------------------------------------------------- #

def siguiente_clima(clima_actual: str) -> str:
    """
    Devuelve el siguiente clima usando la matriz de transiciones.
    Si clima_actual no existe en la tabla, parte desde 'despejado'.
    """
    opciones = TRANSICIONES.get(clima_actual, TRANSICIONES["despejado"])
    climas = list(opciones.keys())
    pesos = list(opciones.values())
    return random.choices(climas, weights=pesos, k=1)[0]


def penalizacion_percepcion(clima: str) -> int:
    """Penalización (negativa o cero) a la percepción según el clima."""
    return PENALIZACION_PERCEPCION.get(clima, 0)


def texto_ambiente_clima(clima: str, tipo: str = "exterior_natural") -> str:
    """
    Devuelve el texto de ambiente para el clima y tipo de entorno dados.
    Devuelve '' si el clima o tipo no existe.
    """
    return CLIMAS.get(clima, {}).get("textos", {}).get(tipo, "")
