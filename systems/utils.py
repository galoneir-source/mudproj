"""
systems/utils.py

Utilidades de presentación compartidas (sin dependencias de Evennia).
"""
from __future__ import annotations


def barra(actual: int, maximo: int, largo: int = 20, color: str | None = None) -> str:
    """
    Genera una barra de progreso de texto con colores Evennia.

    Parámetros:
      actual  — valor actual
      maximo  — valor máximo
      largo   — anchura en caracteres (default: 20)
      color   — color Evennia explícito (ej: "|g", "|r", "|c").
                Si es None, se elige automáticamente según el porcentaje:
                  > 50 % → |g (verde)
                  > 25 % → |y (amarillo)
                  ≤ 25 % → |r (rojo)

    Devuelve una cadena como:  [|g████████░░░░|n]
    """
    if maximo <= 0:
        maximo = 1
    llena = int((actual / maximo) * largo)
    llena = max(0, min(largo, llena))
    vacia = largo - llena

    if color is None:
        color = "|g" if llena > largo * 0.5 else ("|y" if llena > largo * 0.25 else "|r")

    return f"  [{color}{'█' * llena}|n{'░' * vacia}]"
