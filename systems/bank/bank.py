"""
systems/bank/bank.py

Lógica pura del banco (sin dependencias de Evennia).
"""
from __future__ import annotations


def puede_depositar(item, equipamiento: dict) -> tuple[bool, str]:
    """
    Comprueba si un item puede depositarse en el banco.

    item        : objeto de juego con atributo .key
    equipamiento: dict {"arma": item|None, "armadura": item|None, ...}

    Devuelve (puede, razon_error).
    """
    if item is None:
        return False, "El objeto no existe."

    equipados = {it for it in equipamiento.values() if it is not None}
    if item in equipados:
        return False, f"Tienes |w{item.key}|n equipado. Desequípalo antes de depositarlo."

    return True, ""


def limpiar_banco(banco: list) -> list:
    """
    Elimina referencias muertas (objetos borrados) de la lista del banco.
    Devuelve una nueva lista limpia.
    """
    limpias = []
    for item in banco:
        try:
            _ = item.key
            limpias.append(item)
        except Exception:
            pass
    return limpias
