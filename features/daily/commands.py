"""
features/daily/commands.py

Comandos del sistema de Desafíos Diarios:
  desafios          — ver los 5 desafíos del día con tu progreso
  desafios racha    — ver tu racha de días consecutivos
"""
from datetime import date

from evennia import Command, CmdSet

from systems.daily.daily import (
    generar_desafios_del_dia,
    formatear_desafios,
    formatear_racha,
)


def _hoy() -> str:
    return date.today().isoformat()


def _progreso_actual(caller, hoy: str) -> tuple:
    """Devuelve (progreso, completados_idx) reseteados si la fecha ha cambiado."""
    fecha_guardada = getattr(caller.db, "fecha_desafios", None)
    if fecha_guardada != hoy:
        caller.db.fecha_desafios = hoy
        caller.db.progreso_desafios = [0, 0, 0, 0, 0]
        caller.db.desafios_completados_hoy = []
    progreso = list(getattr(caller.db, "progreso_desafios", [0, 0, 0, 0, 0]) or [0, 0, 0, 0, 0])
    completados = list(getattr(caller.db, "desafios_completados_hoy", []) or [])
    while len(progreso) < 5:
        progreso.append(0)
    return progreso, completados


class CmdDesafios(Command):
    """
    Ver y seguir los desafíos diarios.

    Uso:
      desafios           — muestra los 5 desafíos de hoy con tu progreso
      desafios racha     — muestra tu racha de días consecutivos

    Los desafíos se renuevan cada día a medianoche (UTC) y son iguales
    para todos los jugadores. Al completar cada uno recibes XP y monedas.
    Si completas los 5 en el mismo día obtienes un bonus extra que escala
    con tu racha de días consecutivos.

    Ejemplo:
      desafios
      desafios racha
    """

    key = "desafios"
    aliases = ["desafio", "challenges", "daily"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        arg = self.args.strip().lower()
        hoy = _hoy()

        if arg == "racha":
            racha = int(getattr(caller.db, "racha_desafios", 0) or 0)
            ultimo = getattr(caller.db, "ultimo_dia_desafios", None) or "nunca"
            total = int(getattr(caller.db, "total_desafios_completados", 0) or 0)
            caller.msg(formatear_racha(racha, ultimo, total))
            return

        desafios = generar_desafios_del_dia(hoy)
        progreso, completados = _progreso_actual(caller, hoy)
        racha = int(getattr(caller.db, "racha_desafios", 0) or 0)
        caller.msg(formatear_desafios(desafios, progreso, completados, racha, hoy))


class DailyCmdSet(CmdSet):
    key = "DailyCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdDesafios())
