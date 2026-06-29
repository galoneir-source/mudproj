"""
features/arena/commands.py

Comandos del sistema de torneos de arena:
  arena                — estado del torneo actual (inscripciones o bracket)
  arena inscribir      — inscribirse en el torneo (paga 100 monedas)
  arena salir          — retirarse del torneo (reembolso si no ha iniciado)
  arena iniciar        — iniciar el torneo (≥ 2 jugadores inscritos)
"""
from evennia import Command, CmdSet

from features.arena.tournament_script import obtener_torneo_activo, TorneoScript


class CmdArena(Command):
    """
    Participa en los torneos de la Arena de la Ciudad.

    Uso:
      arena               — muestra el estado del torneo activo
      arena inscribir     — te inscribes pagando 100 monedas
      arena salir         — te retiras (reembolso si el torneo no ha empezado)
      arena iniciar       — inicia el torneo (requiere ≥ 2 inscritos)

    Los torneos son de eliminación directa. El campeón se lleva el pot
    completo de las inscripciones. Las inscripciones son globales: puedes
    estar en cualquier sala para inscribirte.

    Ejemplo:
      arena inscribir
      arena iniciar
    """
    key = "arena"
    aliases = ["torneo"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = self.args.strip().lower()

        if not args or args == "estado":
            self._cmd_estado(caller)
        elif args == "inscribir":
            self._cmd_inscribir(caller)
        elif args in ("salir", "retirar", "desinscribir"):
            self._cmd_salir(caller)
        elif args == "iniciar":
            self._cmd_iniciar(caller)
        else:
            caller.msg(
                "Uso: |warena|n, |warena inscribir|n, "
                "|warena salir|n, |warena iniciar|n"
            )

    # ------------------------------------------------------------------ #

    def _cmd_estado(self, caller):
        torneo = obtener_torneo_activo()
        if not torneo:
            caller.msg(
                "\n|cArena de la Ciudad|n\n"
                "No hay ningún torneo activo en este momento.\n"
                "Usa |warena inscribir|n para crear uno e inscribirte."
            )
            return

        from systems.arena.arena import formatear_inscripcion, formatear_bracket

        nombres = dict(torneo.db.nombres or {})
        estado = torneo.db.estado or "inscripcion"

        if estado == "inscripcion":
            inscritos = list(torneo.db.inscritos or [])
            caller.msg(formatear_inscripcion(inscritos, nombres))
        else:
            bracket = dict(torneo.db.bracket or {})
            caller.msg(formatear_bracket(bracket, nombres))

    def _cmd_inscribir(self, caller):
        torneo = obtener_torneo_activo()

        if not torneo:
            # Crear el torneo
            from evennia.utils.create import create_script
            torneo = create_script(
                TorneoScript,
                persistent=False,
                autostart=True,
            )

        ok, msg = torneo.inscribir(caller)
        if ok:
            caller.msg(
                f"|g¡Inscrito en el torneo!|n {msg}\n"
                f"Usa |warena|n para ver el estado. "
                f"Usa |warena iniciar|n cuando haya suficientes jugadores."
            )
        else:
            caller.msg(f"|r{msg}|n")

    def _cmd_salir(self, caller):
        torneo = obtener_torneo_activo()
        if not torneo:
            caller.msg("No hay ningún torneo activo.")
            return

        ok, msg = torneo.desinscribir(caller)
        caller.msg(("|g" if ok else "|r") + msg + "|n")

    def _cmd_iniciar(self, caller):
        torneo = obtener_torneo_activo()
        if not torneo:
            caller.msg(
                "No hay torneo activo. Usa |warena inscribir|n primero."
            )
            return

        ok, msg = torneo.iniciar()
        caller.msg(("|g" if ok else "|r") + msg + "|n")


class ArenaCmdSet(CmdSet):
    key = "ArenaCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdArena())
