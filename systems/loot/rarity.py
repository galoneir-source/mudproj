"""
systems/loot/rarity.py — Lógica pura de rareza de loot.

Tres niveles:
  - común  (70%) — sin modificador, color amarillo estándar
  - raro   (25%) — ×1.2 en todos los bonuses, color cian
  - épico   (5%) — ×1.5 en todos los bonuses, color magenta
"""

import random as _random

RAREZAS = {
    "comun": {"peso": 70, "mult": 1.0, "color": "|y", "label": ""},
    "raro":  {"peso": 25, "mult": 1.2, "color": "|c", "label": "Raro"},
    "epico": {"peso":  5, "mult": 1.5, "color": "|m", "label": "Épico"},
}

_IDS = list(RAREZAS)          # orden fijo: comun, raro, epico
_PESOS = [RAREZAS[k]["peso"] for k in _IDS]
_TOTAL = sum(_PESOS)           # 100


def tirar_rareza(rng=None) -> str:
    """Devuelve 'comun', 'raro' o 'epico' según los pesos configurados."""
    r = (rng or _random).randint(1, _TOTAL)
    acum = 0
    for id_rareza, peso in zip(_IDS, _PESOS):
        acum += peso
        if r <= acum:
            return id_rareza
    return "comun"


def aplicar_rareza_bonuses(bonuses: dict, rareza: str) -> dict:
    """
    Devuelve un nuevo dict con los valores multiplicados por el factor de rareza.
    Los bonuses negativos no escalan (se devuelven sin cambio).
    """
    mult = RAREZAS.get(rareza, RAREZAS["comun"])["mult"]
    if mult == 1.0:
        return dict(bonuses)
    return {
        k: max(1, int(round(v * mult))) if v > 0 else v
        for k, v in bonuses.items()
    }


def nombre_con_rareza(nombre: str, rareza: str) -> str:
    """Devuelve el nombre con sufijo de rareza si corresponde."""
    label = RAREZAS.get(rareza, {}).get("label", "")
    return f"{nombre} ({label})" if label else nombre


def color_rareza(rareza: str) -> str:
    """Código de color Evennia para la rareza dada."""
    return RAREZAS.get(rareza, RAREZAS["comun"])["color"]


def es_notable(rareza: str) -> bool:
    """True si la rareza merece un anuncio especial (raro o épico)."""
    return rareza in ("raro", "epico")


def formatear_drop(nombre_base: str, rareza: str) -> str:
    """Nombre coloreado listo para mostrar en un mensaje de sala."""
    color = color_rareza(rareza)
    nombre = nombre_con_rareza(nombre_base, rareza)
    return f"{color}{nombre}|n"
