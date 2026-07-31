"""
systems/fast_travel/fast_travel.py

Lógica pura del sistema de viaje rápido. Sin dependencias de Evennia.

Los destinos válidos son zonas del catálogo de cartografía (ver
systems/cartography/cartography.py) que el jugador ya haya explorado
(su dbref esté en db.salas_exploradas).
"""
from __future__ import annotations

COSTE_VIAJE = 20            # monedas por viaje
COOLDOWN_SEGUNDOS = 30       # segundos entre viajes


# --------------------------------------------------------------------------- #
#  Destinos
# --------------------------------------------------------------------------- #

def destinos_disponibles(
    exploradas: list,
    zonas_a_dbref: dict,
    zonas_info: list,
) -> list[tuple[str, str, str, str]]:
    """
    Devuelve los destinos que el jugador puede usar para viajar: zonas del
    catálogo (zona_id, nombre_sala, area) cuyo dbref ya esté explorado.

    Devuelve lista de (zona_id, nombre_sala, area, dbref).
    """
    exploradas_set = set(exploradas)
    resultado = []
    for zona_id, nombre_sala, area in zonas_info:
        dbref = zonas_a_dbref.get(zona_id)
        if dbref and dbref in exploradas_set:
            resultado.append((zona_id, nombre_sala, area, dbref))
    return resultado


def buscar_destino(
    consulta: str,
    destinos: list[tuple[str, str, str, str]],
) -> tuple[str, str, str, str] | None:
    """
    Busca un destino por nombre de sala (insensible a mayúsculas, permite
    coincidencia parcial). Si hay coincidencia exacta la prioriza sobre
    coincidencias parciales.
    """
    consulta = consulta.strip().lower()
    if not consulta:
        return None

    for destino in destinos:
        if destino[1].lower() == consulta:
            return destino

    coincidencias = [d for d in destinos if consulta in d[1].lower()]
    if len(coincidencias) == 1:
        return coincidencias[0]
    return None


# --------------------------------------------------------------------------- #
#  Validaciones
# --------------------------------------------------------------------------- #

def puede_pagar(monedas: int, coste: int = COSTE_VIAJE) -> tuple[bool, str]:
    """Valida que el jugador tenga monedas suficientes."""
    if monedas < coste:
        return False, f"Necesitas |y{coste}|n monedas para viajar (tienes {monedas})."
    return True, ""


def cooldown_restante(ultimo_viaje: float, ahora: float) -> int:
    """Segundos restantes de cooldown (0 si ya se puede viajar)."""
    transcurrido = ahora - ultimo_viaje
    if transcurrido >= COOLDOWN_SEGUNDOS:
        return 0
    return int(COOLDOWN_SEGUNDOS - transcurrido)


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

def formatear_destinos(destinos: list[tuple[str, str, str, str]]) -> str:
    """Lista de destinos disponibles, agrupados por área."""
    if not destinos:
        return (
            "|rNo tienes ningún destino disponible todavía.|n\n"
            "Explora el mundo con |wmapa|n para desbloquear puntos de viaje rápido."
        )

    sep = "|w" + "─" * 56 + "|n"
    lineas = [f"\n{sep}", "  |cDestinos de viaje rápido|n", sep]

    area_actual = None
    for zona_id, nombre_sala, area, _dbref in destinos:
        if area != area_actual:
            area_actual = area
            lineas.append(f"\n  |y[{area}]|n")
        lineas.append(f"    |g●|n |w{nombre_sala}|n")

    lineas.append(f"\n  Usa |wviajar <nombre>|n para ir a un destino. Coste: {COSTE_VIAJE} monedas.")
    lineas.append(f"{sep}\n")
    return "\n".join(lineas)
