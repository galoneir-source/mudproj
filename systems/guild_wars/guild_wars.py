"""
systems/guild_wars/guild_wars.py

Lógica pura de guerras entre gremios. Sin dependencias de Evennia.

El PvP en sí ya es libre en todo momento (cualquier 'atacar' contra otro
jugador ya inicia combate real, ver features/combat/handler.py) — una
guerra de gremios no habilita nada nuevo en el combate, solo declara un
periodo de tiempo en el que las bajas entre dos gremios concretos se
cuentan en un marcador, con un ganador al cierre.

Un reto pendiente es un dict: {gremio_retador, timestamp}.
Una guerra activa es un dict con los siguientes campos:
  gremio_a, gremio_b       str   — nombres de los gremios en guerra
  kills_a, kills_b         int   — bajas causadas por cada bando
  timestamp_inicio         float — unix time de inicio
"""
from __future__ import annotations

TIMEOUT_RETO_SEGUNDOS  = 300    # 5 minutos para aceptar/rechazar
DURACION_GUERRA_SEGUNDOS = 3600  # 1 hora


# --------------------------------------------------------------------------- #
#  Retos
# --------------------------------------------------------------------------- #

def reto_expirado(timestamp: float, ahora: float) -> bool:
    return (ahora - timestamp) >= TIMEOUT_RETO_SEGUNDOS


# --------------------------------------------------------------------------- #
#  Guerras
# --------------------------------------------------------------------------- #

def guerra_expirada(timestamp_inicio: float, ahora: float) -> bool:
    return (ahora - timestamp_inicio) >= DURACION_GUERRA_SEGUNDOS


def rival_de(entry: dict, gremio_nombre: str) -> str | None:
    """Devuelve el nombre del gremio rival en la guerra, o None si no participa."""
    if entry["gremio_a"] == gremio_nombre:
        return entry["gremio_b"]
    if entry["gremio_b"] == gremio_nombre:
        return entry["gremio_a"]
    return None


def registrar_kill(entry: dict, gremio_asesino: str) -> dict:
    """Devuelve una copia de entry con el contador del gremio asesino incrementado."""
    nuevo = dict(entry)
    if gremio_asesino == entry["gremio_a"]:
        nuevo["kills_a"] = entry.get("kills_a", 0) + 1
    elif gremio_asesino == entry["gremio_b"]:
        nuevo["kills_b"] = entry.get("kills_b", 0) + 1
    return nuevo


def determinar_ganador(entry: dict) -> str | None:
    """Nombre del gremio con más bajas, o None si hay empate."""
    ka, kb = entry.get("kills_a", 0), entry.get("kills_b", 0)
    if ka > kb:
        return entry["gremio_a"]
    if kb > ka:
        return entry["gremio_b"]
    return None


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

def tiempo_restante_txt(timestamp_inicio: float, ahora: float) -> str:
    restante = max(0, int(DURACION_GUERRA_SEGUNDOS - (ahora - timestamp_inicio)))
    minutos, segundos = divmod(restante, 60)
    return f"{minutos}m {segundos:02d}s"


def formatear_estado(entry: dict, ahora: float) -> str:
    restante = tiempo_restante_txt(entry["timestamp_inicio"], ahora)
    return (
        f"\n|w── Guerra de Gremios ──|n\n"
        f"  |c{entry['gremio_a']}|n: |w{entry.get('kills_a', 0)}|n bajas\n"
        f"  |c{entry['gremio_b']}|n: |w{entry.get('kills_b', 0)}|n bajas\n"
        f"  Tiempo restante: |y{restante}|n\n"
    )


def formatear_resultado(entry: dict) -> str:
    ganador = determinar_ganador(entry)
    ka, kb = entry.get("kills_a", 0), entry.get("kills_b", 0)
    lineas = [
        "\n|Y⚔ ¡GUERRA DE GREMIOS TERMINADA!|n",
        f"|c{entry['gremio_a']}|n: |w{ka}|n bajas — |c{entry['gremio_b']}|n: |w{kb}|n bajas",
    ]
    if ganador:
        lineas.append(f"|Y¡{ganador} es el vencedor!|n")
    else:
        lineas.append("|yLa guerra termina en empate.|n")
    return "\n".join(lineas) + "\n"
