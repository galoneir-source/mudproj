"""
features/ranks/commands.py

Comando del sistema de rangos de aventurero:
  rango  — muestra tu rango actual, puntuación y progreso al siguiente

También expone verificar_subida_rango(), que detecta subidas de rango
y notifica al jugador. Se llama desde comprobar_y_notificar().
"""
from evennia import Command, CmdSet

from systems.ranks.ranks import (
    RANGOS,
    calcular_puntuacion,
    desglose_puntuacion,
    formatear_rango,
    puntos_para_siguiente,
    rango_actual,
    siguiente_rango,
)
from systems.utils import barra as _barra


def _datos_rango(caller) -> tuple[int, int, int, int]:
    """Extrae (nivel, quests_entregadas, logros, kills) del personaje."""
    nivel = int(getattr(caller.db, "nivel", 1) or 1)
    quests = dict(getattr(caller.db, "quests", {}) or {})
    quests_entregadas = sum(
        1 for q in quests.values() if q.get("estado") == "entregada"
    )
    logros = len(list(getattr(caller.db, "logros", []) or []))
    kills = int(getattr(caller.db, "kills_totales", 0) or 0)
    return nivel, quests_entregadas, logros, kills


def verificar_subida_rango(caller) -> None:
    """
    Comprueba si el personaje ha subido de rango y lo notifica.
    Llama esta función después de cualquier evento que aumente la puntuación.
    """
    nivel, quests, logros, kills = _datos_rango(caller)
    puntuacion = calcular_puntuacion(nivel, quests, logros, kills)
    rango_nuevo = rango_actual(puntuacion)
    rango_viejo = getattr(caller.db, "rango", "aprendiz") or "aprendiz"

    if rango_nuevo["id"] == rango_viejo:
        return

    ids = [r["id"] for r in RANGOS]
    if ids.index(rango_nuevo["id"]) <= ids.index(rango_viejo):
        return

    caller.db.rango = rango_nuevo["id"]
    color = rango_nuevo["color"]
    caller.msg(
        f"\n|Y✦ ¡RANGO ALCANZADO!|n  "
        f"{color}{rango_nuevo['nombre']}|n\n"
        f"   Puntuación de aventurero: |w{puntuacion}|n\n"
    )
    if caller.location:
        caller.location.msg_contents(
            f"{caller.key} ha alcanzado el rango de "
            f"{color}{rango_nuevo['nombre']}|n.",
            exclude=caller,
        )


class CmdRango(Command):
    """
    Ver tu rango de aventurero y el progreso hacia el siguiente.

    Uso:
      rango

    El rango refleja tu experiencia acumulada como aventurero, calculada
    a partir de tu nivel, misiones entregadas, logros y kills totales.

    Rangos: Aprendiz → Novicio → Veterano → Héroe → Campeón → Leyenda
    """
    key = "rango"
    aliases = ["rank", "aventurero"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        nivel, quests, logros, kills = _datos_rango(caller)
        puntuacion = calcular_puntuacion(nivel, quests, logros, kills)
        r = rango_actual(puntuacion)
        sig = siguiente_rango(puntuacion)
        faltan = puntos_para_siguiente(puntuacion)
        desglose = desglose_puntuacion(nivel, quests, logros, kills)

        color = r["color"]
        sep = "|w" + "─" * 44 + "|n"

        nombre_sig = (
            f"  →  |x{sig['nombre']}|n" if sig else "  |Y(rango máximo)|n"
        )
        lineas = [
            f"\n{sep}",
            f"  |cRango de Aventurero|n",
            sep,
            f"",
            f"  {color}{r['nombre']}|n{nombre_sig}",
            f"",
            f"  Puntuación total:  |w{puntuacion}|n",
        ]

        if sig:
            avance = puntuacion - r["puntos"]
            tramo = sig["puntos"] - r["puntos"]
            barra = _barra(avance, tramo, 24, color)
            lineas += [
                f"  {barra}",
                f"  Faltan |w{faltan}|n puntos para "
                f"{sig['color']}{sig['nombre']}|n",
            ]
        else:
            lineas.append(f"  {_barra(1, 1, 24, color)}")

        lineas += [
            f"",
            f"  |xDesglose:|n",
            f"    Nivel    : |w{desglose['nivel']:>4}|n pts  "
            f"(nivel {nivel})",
            f"    Misiones : |w{desglose['quests']:>4}|n pts  "
            f"({quests} entregadas)",
            f"    Logros   : |w{desglose['logros']:>4}|n pts  "
            f"({logros} desbloqueados)",
            f"    Combate  : |w{desglose['kills']:>4}|n pts  "
            f"({kills} kills)",
            f"",
            f"  |xAprendiz → Novicio → Veterano → Héroe → Campeón → Leyenda|n",
            sep + "\n",
        ]

        caller.msg("\n".join(lineas))


class RankCmdSet(CmdSet):
    key = "RankCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdRango())
