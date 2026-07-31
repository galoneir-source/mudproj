"""
systems/auctions/auctions.py

Lógica pura de la casa de subastas. Sin dependencias de Evennia.

Distinta del mercado (features/market/, comando 'mercado'): el mercado es
de precio fijo (compra inmediata al precio publicado); aquí se puja al
alza durante un tiempo límite y se la lleva el mejor postor al cerrar.

Cada subasta es un dict con los siguientes campos:
  vendedor_dbref        str  — dbref del vendedor
  vendedor_nombre       str  — nombre del vendedor
  item_dbref            str  — dbref del objeto (en limbo mientras dure)
  item_nombre           str  — nombre del objeto
  precio_inicial        int  — precio de salida
  precio_actual         int  — mejor puja actual (== precio_inicial si nadie pujó)
  mejor_pujador_dbref   str | None
  mejor_pujador_nombre  str | None
  timestamp_inicio      float — unix time de publicación
"""
from __future__ import annotations
import math

MAX_SUBASTAS_POR_JUGADOR = 3
PRECIO_MIN = 1
PRECIO_MAX = 999_999
DURACION_SEGUNDOS = 1800     # 30 minutos
INCREMENTO_MINIMO_PCT = 5    # % mínimo de incremento sobre la puja actual
COMISION_PCT = 5             # comisión de la casa de subastas al vendedor


# --------------------------------------------------------------------------- #
#  Validaciones
# --------------------------------------------------------------------------- #

def validar_precio_inicial(precio) -> tuple[bool, str]:
    """Valida que el precio de salida sea un entero dentro del rango permitido."""
    try:
        n = int(precio)
    except (TypeError, ValueError):
        return False, "El precio de salida debe ser un número entero."
    if n < PRECIO_MIN:
        return False, f"El precio de salida mínimo es {PRECIO_MIN} moneda."
    if n > PRECIO_MAX:
        return False, f"El precio de salida máximo es {_fmt(PRECIO_MAX)} monedas."
    return True, ""


def puja_minima(precio_actual: int) -> int:
    """Puja mínima aceptada: precio actual + al menos INCREMENTO_MINIMO_PCT%."""
    incremento = max(1, math.ceil(precio_actual * INCREMENTO_MINIMO_PCT / 100))
    return precio_actual + incremento


def validar_puja(monto, precio_actual: int, monedas_pujador: int) -> tuple[bool, str]:
    """Valida una puja: entero, alcanza el mínimo, el pujador puede pagarla."""
    try:
        n = int(monto)
    except (TypeError, ValueError):
        return False, "La puja debe ser un número entero."
    minimo = puja_minima(precio_actual)
    if n < minimo:
        return False, f"La puja mínima es {_fmt(minimo)} monedas."
    if monedas_pujador < n:
        return False, f"No tienes suficientes monedas (necesitas {_fmt(n)})."
    return True, ""


def subasta_expirada(timestamp_inicio: float, ahora: float, duracion: int = DURACION_SEGUNDOS) -> bool:
    return ahora - timestamp_inicio >= duracion


def calcular_comision(precio: int) -> int:
    return math.ceil(precio * COMISION_PCT / 100)


def calcular_ganancia(precio: int) -> int:
    return precio - calcular_comision(precio)


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

def tiempo_restante_txt(timestamp_inicio: float, ahora: float, duracion: int = DURACION_SEGUNDOS) -> str:
    restante = max(0, int(duracion - (ahora - timestamp_inicio)))
    minutos, segundos = divmod(restante, 60)
    return f"{minutos}m {segundos:02d}s"


def formatear_subasta(aid, entry: dict, ahora: float) -> str:
    """Línea de una sola entrada de la casa de subastas."""
    pujador = entry.get("mejor_pujador_nombre") or "(sin pujas)"
    precio_txt = f"{_fmt(entry['precio_actual'])} m"
    restante = tiempo_restante_txt(entry["timestamp_inicio"], ahora)
    return (
        f"  {aid:>4}  {entry['item_nombre']:<28} {precio_txt:>10}   "
        f"{pujador:<16} {restante:>8}"
    )


def _fmt(n: int) -> str:
    """Número con separador de miles al estilo español (puntos)."""
    return f"{n:,}".replace(",", ".")
