"""
systems/crafting/equipment.py

Lógica pura para calidades de equipo crafteado (sin dependencias de Evennia).
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
#  Umbrales de calidad
# --------------------------------------------------------------------------- #

# (min_objetos, max_objetos_exclusive, nombre, bonus_por_stat)
CALIDADES: list[tuple] = [
    (0,  15, "Normal",    0),
    (15, 30, "Fino",      1),
    (30, None, "Magistral", 2),
]

NOMBRES_CALIDAD = tuple(c[2] for c in CALIDADES)


def calcular_calidad(objetos_crafteados: int) -> tuple[str, int]:
    """
    Devuelve (nombre_calidad, bonus_por_stat) según los objetos crafteados
    hasta el momento.
    """
    n = int(objetos_crafteados or 0)
    for _, max_val, nombre, bonus in CALIDADES:
        if max_val is None or n < max_val:
            return nombre, bonus
    return "Magistral", 2


def aplicar_bonuses_calidad(bonuses: dict, bonus_calidad: int) -> dict:
    """
    Incrementa cada valor numérico de bonuses en bonus_calidad.
    Devuelve un nuevo dict; no modifica el original.
    """
    if bonus_calidad == 0:
        return dict(bonuses)
    return {stat: val + bonus_calidad for stat, val in bonuses.items()}


def nombre_con_calidad(nombre_base: str, calidad: str) -> str:
    """Añade sufijo de calidad al nombre del item. Normal no añade sufijo."""
    if calidad == "Normal":
        return nombre_base
    return f"{nombre_base} ({calidad})"
