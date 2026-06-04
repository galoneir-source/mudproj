"""
systems/reputation/engine.py

Lógica pura de reputación (sin dependencias de Evennia).
"""
from __future__ import annotations
from .factions import FACCIONES, NIVELES_REP, REP_MINIMA, REP_MAXIMA


def obtener_rep(reputacion: dict, faccion_id: str) -> int:
    """Puntos de rep con una facción (0 si no registrada)."""
    return int(reputacion.get(faccion_id, 0))


def modificar_rep(reputacion: dict, faccion_id: str, delta: int) -> dict:
    """Devuelve nuevo dict con delta aplicado, respetando los límites min/max."""
    reputacion = dict(reputacion)
    actual = reputacion.get(faccion_id, 0)
    reputacion[faccion_id] = max(REP_MINIMA, min(REP_MAXIMA, actual + delta))
    return reputacion


def titulo_reputacion(puntos: int) -> tuple[str, str]:
    """Devuelve (titulo, color_evennia) según los puntos actuales."""
    for umbral, titulo, color in NIVELES_REP:
        if umbral is None or puntos < umbral:
            return titulo, color
    return NIVELES_REP[-1][1], NIVELES_REP[-1][2]


def proximo_umbral(puntos: int) -> tuple[int | None, str]:
    """
    Devuelve (puntos_necesarios_para_avanzar, titulo_siguiente).
    Si ya es Exaltado o está en el nivel máximo, devuelve (None, '').
    """
    for i, (umbral, _titulo, _color) in enumerate(NIVELES_REP):
        if umbral is None or puntos < umbral:
            if i + 1 >= len(NIVELES_REP) or umbral is None:
                return None, ""
            return umbral - puntos, NIVELES_REP[i + 1][1]
    return None, ""


def descuento_tienda(puntos: int) -> float | None:
    """
    Factor de precio según reputación con la facción del comerciante.
    < 1.0 = descuento; > 1.0 = recargo; None = enemigo (niega la venta).
    """
    if puntos >= 12000:   # Exaltado
        return 0.80
    if puntos >= 6000:    # Venerado
        return 0.85
    if puntos >= 3000:    # Honrado
        return 0.90
    if puntos >= 1000:    # Amistoso
        return 0.95
    if puntos >= -1000:   # Neutral
        return 1.00
    if puntos >= -3000:   # Hostil
        return 1.20
    return None           # Enemigo


def es_enemigo(puntos: int) -> bool:
    """True si rep < -3000 (el NPC trata al jugador como enemigo declarado)."""
    return puntos < -3000


def aplicar_rep_quest(reputacion: dict, rep_reward: dict) -> tuple[dict, list]:
    """
    Aplica las recompensas de rep de un quest entregado.

    Devuelve (nueva_reputacion, cambios).
    cambios: lista de (faccion_id, delta, titulo_nuevo, color_nuevo, cambio_titulo).
    cambio_titulo es True si el jugador subió o bajó de rango.
    """
    cambios = []
    for faccion_id, delta in rep_reward.items():
        if faccion_id not in FACCIONES:
            continue
        pts_antes = reputacion.get(faccion_id, 0)
        titulo_antes, _ = titulo_reputacion(pts_antes)
        reputacion = modificar_rep(reputacion, faccion_id, delta)
        pts_despues = reputacion[faccion_id]
        titulo_despues, color_despues = titulo_reputacion(pts_despues)
        cambios.append((faccion_id, delta, titulo_despues, color_despues, titulo_antes != titulo_despues))
    return reputacion, cambios
