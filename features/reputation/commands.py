"""
features/reputation/commands.py

Comandos del sistema de reputación.
"""
from evennia import Command, CmdSet


class CmdReputacion(Command):
    """
    Ver tu reputación con las facciones del mundo.

    Uso:
      reputación
      facciones
      rep

    Muestra el nivel de reputación con cada facción, los puntos
    actuales y cuánto falta para alcanzar el rango siguiente.

    Rangos (de menor a mayor):
      Enemigo → Hostil → Neutral → Amistoso → Honrado → Venerado → Exaltado
    """
    key = "reputación"
    aliases = ["reputacion", "facciones", "rep"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        from systems.reputation.factions import FACCIONES
        from systems.reputation.engine import obtener_rep, titulo_reputacion, proximo_umbral

        caller = self.caller
        rep = dict(getattr(caller.db, "reputacion", {}) or {})

        lineas = [
            f"\n|w{'─' * 52}|n",
            f"  |cReputación con las Facciones|n",
            f"|w{'─' * 52}|n",
        ]

        for faccion_id, datos in FACCIONES.items():
            puntos = obtener_rep(rep, faccion_id)
            titulo, color = titulo_reputacion(puntos)
            faltan, sig_titulo = proximo_umbral(puntos)

            signo = "+" if puntos >= 0 else ""
            pts_txt = f"({signo}{puntos})"

            if faltan is not None:
                sig_txt = f"  |x→ {sig_titulo} en {faltan} pts|n"
            else:
                sig_txt = f"  |Y(rango máximo)|n"

            lineas.append(
                f"  |w{datos['nombre']:<26}|n {color}{titulo:<9}|n |x{pts_txt:>10}|n{sig_txt}"
            )

        lineas.append(f"|w{'─' * 52}|n\n")
        caller.msg("\n".join(lineas))


class ReputationCmdSet(CmdSet):
    key = "ReputationCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdReputacion())
