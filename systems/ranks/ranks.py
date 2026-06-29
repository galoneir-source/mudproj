"""
systems/ranks/ranks.py

Lógica pura del sistema de rangos de aventurero.
Sin dependencias de Evennia.

La puntuación refleja la actividad acumulada del personaje en todas
las áreas del juego: combate, misiones, logros y progresión de nivel.
"""
from __future__ import annotations

RANGOS: list[dict] = [
    {"id": "aprendiz", "nombre": "Aprendiz", "puntos": 0,    "color": "|x"},
    {"id": "novicio",  "nombre": "Novicio",  "puntos": 50,   "color": "|w"},
    {"id": "veterano", "nombre": "Veterano", "puntos": 300,  "color": "|y"},
    {"id": "heroe",    "nombre": "Héroe",    "puntos": 700,  "color": "|c"},
    {"id": "campeon",  "nombre": "Campeón",  "puntos": 1400, "color": "|g"},
    {"id": "leyenda",  "nombre": "Leyenda",  "puntos": 2500, "color": "|Y"},
]

_PTS_POR_NIVEL = 15   # × (nivel − 1)
_PTS_POR_QUEST = 10   # × quests entregadas
_PTS_POR_LOGRO = 20   # × logros desbloqueados
_PTS_POR_KILL  = 1    # × kills totales


def calcular_puntuacion(
    nivel: int,
    quests_entregadas: int,
    logros_desbloqueados: int,
    kills_totales: int,
) -> int:
    """Puntuación de rango total para los valores dados."""
    return (
        max(0, nivel - 1) * _PTS_POR_NIVEL
        + max(0, quests_entregadas) * _PTS_POR_QUEST
        + max(0, logros_desbloqueados) * _PTS_POR_LOGRO
        + max(0, kills_totales) * _PTS_POR_KILL
    )


def rango_actual(puntuacion: int) -> dict:
    """Rango correspondiente a la puntuación dada."""
    actual = RANGOS[0]
    for r in RANGOS:
        if puntuacion >= r["puntos"]:
            actual = r
    return actual


def siguiente_rango(puntuacion: int) -> dict | None:
    """Siguiente rango, o None si ya es el máximo."""
    for r in RANGOS:
        if r["puntos"] > puntuacion:
            return r
    return None


def puntos_para_siguiente(puntuacion: int) -> int | None:
    """Puntos que faltan para el siguiente rango, o None en el máximo."""
    sig = siguiente_rango(puntuacion)
    return None if sig is None else sig["puntos"] - puntuacion


def formatear_rango(rango_id: str) -> str:
    """Nombre del rango con su color de Evennia."""
    for r in RANGOS:
        if r["id"] == rango_id:
            return f"{r['color']}{r['nombre']}|n"
    return rango_id


def desglose_puntuacion(
    nivel: int,
    quests_entregadas: int,
    logros_desbloqueados: int,
    kills_totales: int,
) -> dict[str, int]:
    """Puntos aportados por cada fuente."""
    return {
        "nivel":  max(0, nivel - 1) * _PTS_POR_NIVEL,
        "quests": max(0, quests_entregadas) * _PTS_POR_QUEST,
        "logros": max(0, logros_desbloqueados) * _PTS_POR_LOGRO,
        "kills":  max(0, kills_totales) * _PTS_POR_KILL,
    }
