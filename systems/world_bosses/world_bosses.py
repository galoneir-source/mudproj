"""
systems/world_bosses/world_bosses.py

Catálogo puro de jefes de mundo. Sin dependencias de Evennia.

Tres jefes que reaparecen en zonas fijas del mapa tras un cooldown real:
  - TITAN_PANTANO   → pantano_cenagoso  (6h cooldown, nv.req 4)
  - GUARDIAN_FORJA  → caverna_coloso    (7h cooldown, nv.req 6)
  - DRAGON_CENIZA   → claro_bosque      (8h cooldown, nv.req 8)

Cuando un jefe muere, se reparten recompensas proporcionales al daño
infligido por cada jugador participante.
"""
from __future__ import annotations
import time

# --------------------------------------------------------------------------- #
#  Catálogo
# --------------------------------------------------------------------------- #

JEFES_MUNDO: dict[str, dict] = {
    "TITAN_PANTANO": {
        "nombre":         "Titán del Pantano",
        "sala_zona":      "pantano_cenagoso",
        "cooldown":       6 * 3600,   # 6 horas en segundos
        "nivel_req":      4,
        "xp_total":       600,
        "monedas_total":  150,
        "loot_unico":     "ESCAMA_TITAN",
        "desc_aparicion": (
            "|r⚠ ¡EL TITÁN DEL PANTANO HA EMERGIDO del fango del Pantano Cenagoso!|n\n"
            "|yAventureros, id allí para detenerlo antes de que todo quede sepultado.|n"
        ),
        "desc_muerte": (
            "|g¡El Titán del Pantano ha sido derrotado!|n "
            "El pantano recupera su calma... por ahora."
        ),
    },
    "GUARDIAN_FORJA": {
        "nombre":         "Guardián de la Forja",
        "sala_zona":      "caverna_coloso",
        "cooldown":       7 * 3600,
        "nivel_req":      6,
        "xp_total":       1000,
        "monedas_total":  250,
        "loot_unico":     "NUCLEO_GUARDIAN",
        "desc_aparicion": (
            "|r⚠ ¡EL GUARDIÁN DE LA FORJA ha despertado en la Caverna del Coloso!|n\n"
            "|yLas paredes tiemblan. Los mineros huyen despavoridos.|n"
        ),
        "desc_muerte": (
            "|g¡El Guardián de la Forja ha caído!|n "
            "El calor sobrenatural remite y la caverna recupera el silencio."
        ),
    },
    "DRAGON_CENIZA": {
        "nombre":         "Dragón de Ceniza",
        "sala_zona":      "claro_bosque",
        "cooldown":       8 * 3600,
        "nivel_req":      8,
        "xp_total":       1800,
        "monedas_total":  450,
        "loot_unico":     "GARRA_DRAGON",
        "desc_aparicion": (
            "|r⚠ ¡¡EL DRAGÓN DE CENIZA DESCIENDE sobre el Claro del Bosque!!|n\n"
            "|yEl cielo se oscurece de ceniza. Solo los más valientes sobrevivirán.|n"
        ),
        "desc_muerte": (
            "|g¡¡El Dragón de Ceniza ha sido vencido!!|n "
            "Las cenizas se dispersan. La leyenda de sus cazadores perdurará."
        ),
    },
}

# --------------------------------------------------------------------------- #
#  Funciones puras
# --------------------------------------------------------------------------- #

def puede_aparecer(boss_id: str, ultimo_muerte: float | None) -> bool:
    """True si el cooldown ha pasado (o el jefe nunca ha aparecido)."""
    if ultimo_muerte is None:
        return True
    datos = JEFES_MUNDO.get(boss_id, {})
    cooldown = datos.get("cooldown", 6 * 3600)
    return (time.time() - ultimo_muerte) >= cooldown


def tiempo_hasta_respawn(boss_id: str, ultimo_muerte: float | None) -> int:
    """Segundos que faltan para el próximo spawn. 0 si ya puede aparecer."""
    if ultimo_muerte is None:
        return 0
    datos = JEFES_MUNDO.get(boss_id, {})
    cooldown = datos.get("cooldown", 6 * 3600)
    restante = cooldown - (time.time() - ultimo_muerte)
    return max(0, int(restante))


def calcular_recompensas_participante(
    boss_id: str,
    dano_jugador: int,
    dano_total: int,
) -> tuple[int, int]:
    """
    Devuelve (xp, monedas) proporcionales al daño infligido.
    Garantiza un mínimo del 10% aunque el daño sea muy bajo.
    """
    datos = JEFES_MUNDO.get(boss_id, {})
    xp_total = datos.get("xp_total", 300)
    mon_total = datos.get("monedas_total", 100)

    if dano_total <= 0:
        return 0, 0

    fraccion = max(0.10, dano_jugador / dano_total)
    xp  = max(1, int(xp_total * fraccion))
    mon = max(1, int(mon_total * fraccion))
    return xp, mon


def formatear_estado(boss_id: str, npc_vivo: bool, ultimo_muerte: float | None) -> str:
    """Línea de estado para el comando `jefes`."""
    datos = JEFES_MUNDO.get(boss_id, {})
    nombre = datos.get("nombre", boss_id)
    zona   = datos.get("sala_zona", "?")
    nv_req = datos.get("nivel_req", 1)

    if npc_vivo:
        estado = "|r[VIVO — ¡ve allí!]|n"
    elif puede_aparecer(boss_id, ultimo_muerte):
        estado = "|y[Listo para aparecer]|n"
    else:
        secs = tiempo_hasta_respawn(boss_id, ultimo_muerte)
        h, m = divmod(secs // 60, 60)
        estado = f"|x[Reaparece en {h}h {m:02d}m]|n"

    return f"  |c{nombre}|n ({zona}) — Nv.req |w{nv_req}|n  {estado}"


def formatear_lista_jefes(
    estados_vivo: dict[str, bool],
    ultimos_muertos: dict[str, float | None],
) -> str:
    lineas = ["|wJefes de Mundo:|n"]
    for bid in JEFES_MUNDO:
        vivo  = estados_vivo.get(bid, False)
        ult   = ultimos_muertos.get(bid, None)
        lineas.append(formatear_estado(bid, vivo, ult))
    lineas.append(
        "\n|xCuando un jefe aparece se anuncia globalmente. "
        "Requieren varios jugadores para ser derrotados.|n"
    )
    return "\n".join(lineas)
