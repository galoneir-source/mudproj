"""
features/bounty/commands.py

Comandos del sistema de cazarrecompensas:
  recompensa [tablon]          — ver tablón de recompensas
  recompensa mias              — ver mis recompensas puestas/recibidas
  recompensa poner <j> <cant>  — poner una recompensa sobre un jugador
  recompensa cancelar <j>      — retirar tu recompensa
  cazar <jugador>              — desafiar a duelo a alguien con recompensa
"""
import time

from evennia import Command, CmdSet

from features.bounty.bounty_script import obtener_recompensas_script
from systems.bounty.bounty import (
    MIN_RECOMPENSA, MAX_RECOMPENSA,
    puede_poner, puede_cancelar, hay_recompensa,
    añadir_bounty, cancelar_bounty,
    formatear_tablon, formatear_mi_estado,
)


class CmdRecompensa(Command):
    """
    Gestionar recompensas sobre jugadores.

    Uso:
      recompensa              — muestra el tablón de recompensas
      recompensa tablon       — ídem
      recompensa mias         — ver tus recompensas puestas y recibidas
      recompensa poner <jugador> <cantidad>   — poner una recompensa
      recompensa cancelar <jugador>           — retirar tu recompensa

    La cantidad debe estar entre {min} y {max} monedas.

    Ejemplo:
      recompensa poner Valeria 200
      recompensa cancelar Valeria
    """.format(min=MIN_RECOMPENSA, max=MAX_RECOMPENSA)

    key = "recompensa"
    aliases = ["recompensas", "bounty", "tablonrecompensas"]
    locks = "cmd:all()"
    help_category = "Jugador"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args or args.lower() == "tablon":
            script = obtener_recompensas_script()
            bounties = list(script.db.bounties or [])
            caller.msg(formatear_tablon(bounties))
            return

        if args.lower() == "mias":
            script = obtener_recompensas_script()
            bounties = list(script.db.bounties or [])
            caller.msg(formatear_mi_estado(bounties, caller.dbref, caller.key))
            return

        partes = args.split(None, 1)
        subcmd = partes[0].lower()

        if subcmd == "poner":
            self._poner(partes[1] if len(partes) > 1 else "")
        elif subcmd == "cancelar":
            self._cancelar(partes[1] if len(partes) > 1 else "")
        else:
            caller.msg(
                "Uso: |wrecompensa [tablon|mias|poner <j> <cant>|cancelar <j>]|n"
            )

    def _poner(self, rest):
        caller = self.caller
        partes = rest.strip().rsplit(None, 1)
        if len(partes) != 2:
            caller.msg("Uso: |wrecompensa poner <jugador> <cantidad>|n")
            return

        nombre_obj, cant_str = partes
        try:
            cantidad = int(cant_str)
        except ValueError:
            caller.msg("|rLa cantidad debe ser un número entero.|n")
            return

        # Buscar jugador
        objetivos = caller.search(nombre_obj, global_search=True, quiet=True)
        if not objetivos:
            caller.msg(f"No se encontró ningún jugador llamado '|w{nombre_obj}|n'.")
            return
        objetivo = objetivos[0] if isinstance(objetivos, list) else objetivos
        if not getattr(objetivo, "has_account", False):
            caller.msg("|rSolo puedes poner recompensas sobre otros jugadores.|n")
            return

        script = obtener_recompensas_script()
        bounties = list(script.db.bounties or [])
        monedas = getattr(caller.db, "monedas", 0) or 0

        ok, msg = puede_poner(caller.dbref, objetivo.dbref, monedas, cantidad, bounties)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return

        # Cobrar monedas
        caller.db.monedas = monedas - cantidad

        nueva = {
            "objetivo_dbref":  objetivo.dbref,
            "objetivo_nombre": objetivo.key,
            "emisor_dbref":    caller.dbref,
            "emisor_nombre":   caller.key,
            "recompensa":      cantidad,
            "fecha":           time.time(),
        }
        script.db.bounties = añadir_bounty(bounties, nueva)

        caller.msg(
            f"|yRecompensa publicada.|n  |r{cantidad} monedas|n sobre "
            f"|w{objetivo.key}|n han sido depositadas."
        )
        # Avisar al objetivo si está conectado
        if getattr(objetivo, "sessions", None) and objetivo.sessions.count():
            objetivo.msg(
                f"\n|r¡Han puesto precio a tu cabeza!|n  "
                f"|w{caller.key}|n ofrece |r{cantidad} monedas|n por derrotarte.\n"
                f"  (usa |wrecompensa tablon|n para ver los detalles)"
            )

        # Incrementar contador en objetivo
        objetivo.db.recompensas_recibidas = (
            getattr(objetivo.db, "recompensas_recibidas", 0) or 0
        ) + 1
        try:
            from features.achievements.commands import comprobar_y_notificar
            comprobar_y_notificar(objetivo)
        except Exception:
            pass

    def _cancelar(self, rest):
        caller = self.caller
        nombre_obj = rest.strip()
        if not nombre_obj:
            caller.msg("Uso: |wrecompensa cancelar <jugador>|n")
            return

        objetivos = caller.search(nombre_obj, global_search=True, quiet=True)
        if not objetivos:
            caller.msg(f"No se encontró ningún jugador llamado '|w{nombre_obj}|n'.")
            return
        objetivo = objetivos[0] if isinstance(objetivos, list) else objetivos

        script = obtener_recompensas_script()
        bounties = list(script.db.bounties or [])

        ok, msg = puede_cancelar(caller.dbref, objetivo.dbref, bounties)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return

        nueva_lista, reembolso = cancelar_bounty(bounties, caller.dbref, objetivo.dbref)
        script.db.bounties = nueva_lista
        caller.db.monedas = (getattr(caller.db, "monedas", 0) or 0) + reembolso

        caller.msg(
            f"|yRecompensa cancelada.|n  Se te devuelven |w{reembolso} monedas|n."
        )


class CmdCazar(Command):
    """
    Desafiar a un jugador con recompensa a un duelo de caza.

    Uso:
      cazar <jugador>

    Si ganas el duelo, cobras automáticamente todas las recompensas
    activas sobre ese jugador. El duelo comienza de inmediato sin
    necesidad de aceptación (ya que es una caza autorizada por el tablón).

    Solo puedes cazar a alguien que tenga una recompensa activa.
    """
    key = "cazar"
    aliases = ["hunt", "cazarrecompensa"]
    locks = "cmd:all()"
    help_category = "Jugador"

    def func(self):
        caller = self.caller
        nombre = self.args.strip()
        if not nombre:
            caller.msg("Uso: |wcazar <jugador>|n")
            return

        objetivos = caller.search(nombre, global_search=True, quiet=True)
        if not objetivos:
            caller.msg(f"No se encontró ningún jugador llamado '|w{nombre}|n'.")
            return
        objetivo = objetivos[0] if isinstance(objetivos, list) else objetivos

        if objetivo == caller:
            caller.msg("No puedes cazarte a ti mismo.")
            return
        if not getattr(objetivo, "has_account", False):
            caller.msg("|rSolo puedes cazar jugadores.|n")
            return

        script = obtener_recompensas_script()
        bounties = list(script.db.bounties or [])

        if not hay_recompensa(objetivo.dbref, bounties):
            caller.msg(
                f"|w{objetivo.key}|n no tiene ninguna recompensa activa.\n"
                f"Usa |wrecompensa tablon|n para ver los objetivos disponibles."
            )
            return

        # Verificar que ambos están en la misma sala
        if caller.location != objetivo.location:
            caller.msg("|rDebes estar en la misma sala que el objetivo para cazarlo.|n")
            return

        # Verificar que no haya un combate en curso
        sala = caller.location
        if not sala:
            caller.msg("No puedes iniciar un duelo aquí.")
            return

        from systems.bounty.bounty import total_sobre_objetivo
        total = total_sobre_objetivo(objetivo.dbref, bounties)

        sala.msg_contents(
            f"\n|r¡CAZA DE RECOMPENSA!|n  "
            f"|w{caller.key}|n persigue a |w{objetivo.key}|n "
            f"por |r{total} monedas|n en recompensas.\n"
        )

        try:
            from evennia.utils.create import create_script
            from features.combat.handler import CombatHandler
            handler = create_script(CombatHandler, obj=sala, persistent=False, autostart=False)
            handler.db.modo_duelo = True
            handler.db.es_caza_recompensa = True
            handler.db.cazador_dbref = caller.dbref
            handler.iniciar([caller, objetivo])
            handler.start()
        except Exception as e:
            from evennia.utils import logger
            logger.log_err(f"CmdCazar error al crear duelo: {e}")
            sala.msg_contents("|rError al iniciar la caza. Inténtalo de nuevo.|n")


class BountyCmdSet(CmdSet):
    key = "BountyCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdRecompensa())
        self.add(CmdCazar())
