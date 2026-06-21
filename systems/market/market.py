"""
systems/market/market.py

Lógica pura del mercado de jugadores (sin dependencias de Evennia).
"""
from __future__ import annotations
import math

# --------------------------------------------------------------------------- #
#  Constantes
# --------------------------------------------------------------------------- #

MAX_LISTINGS_POR_JUGADOR = 10
PRECIO_MIN = 1
PRECIO_MAX = 999_999
COMISION_PCT = 5


# --------------------------------------------------------------------------- #
#  Funciones puras
# --------------------------------------------------------------------------- #

def validar_precio(precio) -> tuple[bool, str]:
    """Valida que precio sea un entero dentro del rango permitido."""
    try:
        n = int(precio)
    except (TypeError, ValueError):
        return False, "El precio debe ser un número entero."
    if n < PRECIO_MIN:
        return False, f"El precio mínimo es {PRECIO_MIN} moneda."
    if n > PRECIO_MAX:
        return False, f"El precio máximo es {_fmt(PRECIO_MAX)} monedas."
    return True, ""


def calcular_comision(precio: int) -> int:
    """Comisión del mercado (redondeada hacia arriba)."""
    return math.ceil(precio * COMISION_PCT / 100)


def calcular_ganancia(precio: int) -> int:
    """Lo que recibe el vendedor tras descontar comisión."""
    return precio - calcular_comision(precio)


def formatear_listing(lid, vendedor_nombre: str, item_nombre: str, precio: int) -> str:
    """Línea de una sola entrada del mercado."""
    precio_txt = f"{_fmt(precio)} m"
    return f"  {lid:>4}  {item_nombre:<32} {precio_txt:>10}   {vendedor_nombre}"


def _fmt(n: int) -> str:
    """Número con separador de miles al estilo español (puntos)."""
    return f"{n:,}".replace(",", ".")
