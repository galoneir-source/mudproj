"""
systems/time/clock.py

Lógica pura del ciclo día/noche. Sin dependencias de Evennia.

Tiempo de juego: 1 minuto real = 1 hora de juego → ciclo completo cada 24 min reales.

Períodos:
  Amanecer  5–7    |Y
  Mañana    7–12   |y
  Mediodía  12–14  |Y
  Tarde     14–19  |y
  Anochecer 19–21  |r
  Noche     21–5   |x  (también 0–5)
"""
from __future__ import annotations

# (hora_inicio, hora_fin_exclusiva, id, nombre, color_evennia)
PERIODOS = [
    ( 5,  7, "amanecer",  "Amanecer",  "|Y"),
    ( 7, 12, "manana",    "Mañana",    "|y"),
    (12, 14, "mediodia",  "Mediodía",  "|Y"),
    (14, 19, "tarde",     "Tarde",     "|y"),
    (19, 21, "anochecer", "Anochecer", "|r"),
    # El resto (21-24 y 0-5) es noche
]

# Textos que aparecen en la descripción de sala según período y tipo de entorno.
# tipo_ambiente: "exterior_natural" | "exterior_urbano"
TEXTOS_AMBIENTE: dict[str, dict[str, str]] = {
    "amanecer": {
        "exterior_natural": "El cielo se tiñe de naranja y rosa. Los pájaros comienzan a cantar.",
        "exterior_urbano":  "Los primeros comerciantes abren sus puestos. El olor a pan recién horneado flota en el aire.",
    },
    "manana": {
        "exterior_natural": "La luz clara de la mañana ilumina cada detalle. El rocío brilla aún en las hojas.",
        "exterior_urbano":  "La ciudad bulle de actividad. El sol calienta los adoquines.",
    },
    "mediodia": {
        "exterior_natural": "El sol está en lo más alto y el calor es intenso. Las sombras son cortas.",
        "exterior_urbano":  "El sol cae vertical sobre los tejados. Los vendedores buscan la sombra de los toldos.",
    },
    "tarde": {
        "exterior_natural": "La luz dorada de la tarde se filtra entre las ramas. El calor del día remite.",
        "exterior_urbano":  "Las sombras se alargan sobre los adoquines. Los últimos viajeros regresan.",
    },
    "anochecer": {
        "exterior_natural": "El cielo se tiñe de rojo y violeta. Las criaturas nocturnas empiezan a moverse.",
        "exterior_urbano":  "Los comerciantes recogen sus puestos. Las antorchas de la ciudad se encienden una a una.",
    },
    "noche": {
        "exterior_natural": "La oscuridad envuelve el entorno. La luna y las estrellas ofrecen poca luz.",
        "exterior_urbano":  "La ciudad duerme en silencio. Las antorchas proyectan sombras inquietantes.",
    },
}

# Mensaje de broadcast al cambiar de período (se envía a todos los jugadores conectados).
MENSAJES_TRANSICION: dict[str, str] = {
    "amanecer":  "El sol asoma por el horizonte. El amanecer tiñe el cielo de colores cálidos.",
    "manana":    "La mañana se asienta. La luz del sol ilumina el mundo con claridad.",
    "mediodia":  "El sol alcanza su punto más alto. El mediodía quema con fuerza.",
    "tarde":     "El sol comienza su descenso. La tarde proyecta largas sombras doradas.",
    "anochecer": "El sol se hunde en el horizonte. El frescor de la noche se acerca.",
    "noche":     "La oscuridad cae sobre el mundo. Ha llegado la noche.",
}

# Penalización a la percepción según el período del día.
PENALIZACION_PERCEPCION: dict[str, int] = {
    "noche":     -3,
    "anochecer": -1,
    "amanecer":  -1,
    "manana":     0,
    "mediodia":   0,
    "tarde":      0,
}


# --------------------------------------------------------------------------- #
#  Funciones puras
# --------------------------------------------------------------------------- #

def periodo_del_dia(hora: int) -> tuple[str, str, str]:
    """
    Devuelve (id, nombre, color_evennia) para la hora dada (0-23).
    Fuera del rango se normaliza con módulo 24.
    """
    hora = hora % 24
    for inicio, fin, pid, nombre, color in PERIODOS:
        if inicio <= hora < fin:
            return pid, nombre, color
    return "noche", "Noche", "|x"


def penalizacion_percepcion(hora: int) -> int:
    """Penalización (negativa o cero) a la percepción según la hora."""
    pid, _, _ = periodo_del_dia(hora)
    return PENALIZACION_PERCEPCION.get(pid, 0)


def texto_ambiente(hora: int, tipo: str = "exterior_natural") -> str:
    """
    Devuelve el texto de ambiente para la hora y tipo de entorno dados.
    Devuelve '' si el tipo no existe.
    """
    pid, _, _ = periodo_del_dia(hora)
    return TEXTOS_AMBIENTE.get(pid, {}).get(tipo, "")


def hora_a_texto(hora: int) -> str:
    """Devuelve la hora formateada como '08:00'."""
    return f"{hora % 24:02d}:00"
