"""
features/duels/commands.py

Comandos de duelos 1v1 entre jugadores:
  retar, aceptar duelo, rechazar duelo, rendirse
"""
import time

from evennia import Command, CmdSet

from systems.duels.duels import DUEL_TIMEOUT, reto_expirado, validar_apuesta


# --------------------------------------------------------------------------- #
#  Utilidad
# --------------------------------------------------------------------------- #

def _get_combat_handler(sala):
    if not sala:
        return None
    for script in sala.scripts.all():
        if script.key == "combat_handler" and getattr(script.db, "activo", False):
            return script
    return None


def _limpiar_duelo(char):
    """Elimina todos los atributos de reto pendiente del personaje."""
    char.db.duelo_pendiente = None
    char.db.duelo_retador_dbref = None
    char.db.duelo_apuesta_pendiente = 0


def _tiene_reto_saliente_vigente(char) -> bool:
    """
    True si `char` tiene un reto que él mismo lanzó y sigue vigente.
    Si el reto ha caducado, limpia los atributos de ambos lados (él y
    su retado) y devuelve False, en vez de bloquear para siempre.
    """
    pendiente = getattr(char.db, "duelo_pendiente", None)
    if not pendiente:
        return False
    if reto_expirado(pendiente.get("timestamp", 0), time.time()):
        retado = _buscar_por_dbref(pendiente.get("retado_dbref"))
        _limpiar_duelo(char)
        if retado:
            _limpiar_duelo(retado)
        return False
    return True


def _tiene_reto_entrante_vigente(objetivo) -> bool:
    """
    True si `objetivo` tiene un reto entrante vigente de otro jugador.
    Si el retador ya no existe o su reto ha caducado, limpia los
    atributos de ambos lados y devuelve False.
    """
    retador_dbref = getattr(objetivo.db, "duelo_retador_dbref", None)
    if not retador_dbref:
        return False
    retador = _buscar_por_dbref(retador_dbref)
    if not retador:
        _limpiar_duelo(objetivo)
        return False
    pendiente = getattr(retador.db, "duelo_pendiente", None) or {}
    if reto_expirado(pendiente.get("timestamp", 0), time.time()):
        _limpiar_duelo(objetivo)
        _limpiar_duelo(retador)
        return False
    return True


# --------------------------------------------------------------------------- #
#  retar
# --------------------------------------------------------------------------- #

class CmdRetar(Command):
    """
    Retar a otro jugador a un duelo.

    Uso:
      retar <jugador>
      retar <jugador> = <monedas>

    El rival tiene 60 segundos para aceptar o rechazar el reto.
    Si se especifica una apuesta, ambos deben disponer de las monedas;
    el perdedor paga al ganador al finalizar el duelo.
    El combate termina cuando uno de los dos llega al 10 % de HP.

    Ejemplo:
      retar Gandalf
      retar Gandalf = 50
    """
    key = "retar"
    aliases = ["desafiar", "challenge"]
    locks = "cmd:all()"
    help_category = "Duelos"

    def func(self):
        caller = self.caller

        if "=" in self.args:
            partes = self.args.split("=", 1)
            nombre_obj = partes[0].strip()
            try:
                apuesta = int(partes[1].strip())
            except ValueError:
                caller.msg("La apuesta debe ser un número entero.")
                return
        else:
            nombre_obj = self.args.strip()
            apuesta = 0

        if not nombre_obj:
            caller.msg("Uso: |wretar <jugador> [= monedas]|n")
            return

        objetivo = caller.search(nombre_obj, location=caller.location)
        if not objetivo:
            return

        if objetivo == caller:
            caller.msg("No puedes retarte a ti mismo.")
            return

        if not bool(getattr(objetivo, "account", None)):
            caller.msg(f"|w{objetivo.key}|n no es un jugador.")
            return

        if getattr(caller.db, "en_combate", False):
            caller.msg("No puedes retar a nadie mientras estás en combate.")
            return

        if getattr(objetivo.db, "en_combate", False):
            caller.msg(f"|w{objetivo.key}|n ya está en combate.")
            return

        if _tiene_reto_saliente_vigente(caller):
            caller.msg("Ya tienes un reto pendiente. Espera a que expire o sea respondido.")
            return

        if _tiene_reto_entrante_vigente(objetivo):
            caller.msg(f"|w{objetivo.key}|n ya tiene un reto pendiente.")
            return

        if apuesta:
            ok, motivo = validar_apuesta(
                getattr(caller.db, "monedas", 0) or 0,
                getattr(objetivo.db, "monedas", 0) or 0,
                apuesta,
            )
            if not ok:
                caller.msg(motivo)
                return

        # Registrar reto
        caller.db.duelo_pendiente = {
            "retado_dbref": objetivo.dbref,
            "apuesta": apuesta,
            "timestamp": time.time(),
        }
        objetivo.db.duelo_retador_dbref = caller.dbref
        objetivo.db.duelo_apuesta_pendiente = apuesta

        apuesta_txt = f" por |Y{apuesta} monedas|n" if apuesta else ""
        caller.msg(
            f"Has retado a |w{objetivo.key}|n{apuesta_txt}. "
            f"Tiene {DUEL_TIMEOUT}s para responder."
        )
        objetivo.msg(
            f"\n|y⚔  {caller.key} te reta a un duelo{apuesta_txt}!|n\n"
            f"  |waceptar duelo|n  — aceptar\n"
            f"  |wrechazar duelo|n — rechazar\n"
            f"(Tienes {DUEL_TIMEOUT} segundos para responder)\n"
        )


# --------------------------------------------------------------------------- #
#  aceptar duelo
# --------------------------------------------------------------------------- #

class CmdAceptarDuelo(Command):
    """
    Aceptar un reto de duelo pendiente.

    Uso:
      aceptar duelo
    """
    key = "aceptar duelo"
    aliases = ["aceptar reto"]
    locks = "cmd:all()"
    help_category = "Duelos"

    def func(self):
        caller = self.caller

        retador_dbref = getattr(caller.db, "duelo_retador_dbref", None)
        if not retador_dbref:
            caller.msg("No tienes ningún reto de duelo pendiente.")
            return

        # Resolver retador por dbref
        retador = _buscar_por_dbref(retador_dbref)
        if not retador:
            caller.msg("El jugador que te retó ya no está disponible.")
            _limpiar_duelo(caller)
            return

        pendiente = getattr(retador.db, "duelo_pendiente", None) or {}
        timestamp = pendiente.get("timestamp", 0)
        if reto_expirado(timestamp, time.time()):
            caller.msg("El reto ya ha expirado.")
            _limpiar_duelo(caller)
            _limpiar_duelo(retador)
            return

        if retador.location != caller.location:
            caller.msg(f"|w{retador.key}|n ya no está aquí.")
            _limpiar_duelo(caller)
            _limpiar_duelo(retador)
            return

        if getattr(retador.db, "en_combate", False) or getattr(caller.db, "en_combate", False):
            caller.msg("No se puede iniciar el duelo: uno de los dos ya está en combate.")
            return

        from features.combat.commands import _get_combat_handler
        if _get_combat_handler(caller.location):
            caller.msg("No se puede iniciar el duelo: ya hay un combate en curso en esta sala.")
            return

        apuesta = pendiente.get("apuesta", 0)
        if apuesta:
            ok, motivo = validar_apuesta(
                getattr(retador.db, "monedas", 0) or 0,
                getattr(caller.db, "monedas", 0) or 0,
                apuesta,
            )
            if not ok:
                caller.msg(f"No se puede iniciar el duelo: {motivo}")
                _limpiar_duelo(caller)
                _limpiar_duelo(retador)
                return

        # Guardar apuesta en ambos y limpiar pendientes
        retador.db.apuesta_duelo = apuesta
        caller.db.apuesta_duelo = apuesta
        _limpiar_duelo(caller)
        _limpiar_duelo(retador)

        # Iniciar combate en modo duelo
        from features.combat.handler import CombatHandler
        sala = caller.location
        handler = sala.scripts.add(CombatHandler)
        handler.db.modo_duelo = True
        handler.iniciar([retador, caller])

        apuesta_txt = f" (apuesta: |Y{apuesta} monedas|n)" if apuesta else ""
        sala.msg_contents(
            f"\n|Y⚔  ¡DUELO INICIADO!|n {retador.key} vs {caller.key}{apuesta_txt}\n"
        )


# --------------------------------------------------------------------------- #
#  rechazar duelo
# --------------------------------------------------------------------------- #

class CmdRechazarDuelo(Command):
    """
    Rechazar un reto de duelo pendiente.

    Uso:
      rechazar duelo
    """
    key = "rechazar duelo"
    aliases = ["rechazar reto"]
    locks = "cmd:all()"
    help_category = "Duelos"

    def func(self):
        caller = self.caller

        retador_dbref = getattr(caller.db, "duelo_retador_dbref", None)
        if not retador_dbref:
            caller.msg("No tienes ningún reto de duelo pendiente.")
            return

        retador = _buscar_por_dbref(retador_dbref)
        if retador:
            retador.msg(f"|y{caller.key}|n ha rechazado tu reto de duelo.")
            _limpiar_duelo(retador)

        _limpiar_duelo(caller)
        caller.msg("Has rechazado el reto de duelo.")


# --------------------------------------------------------------------------- #
#  rendirse
# --------------------------------------------------------------------------- #

class CmdRendirse(Command):
    """
    Rendirse en un duelo activo concediendo la victoria al rival.

    Uso:
      rendirse

    Transfiere la apuesta al ganador si la había.
    Solo funciona en duelos (no en combates normales contra NPCs).
    Para abandonar un combate normal usa |whuir|n.
    """
    key = "rendirse"
    aliases = ["surrender", "ceder"]
    locks = "cmd:all()"
    help_category = "Duelos"

    def func(self):
        caller = self.caller

        if not getattr(caller.db, "en_combate", False):
            caller.msg("No estás en combate.")
            return

        handler = _get_combat_handler(caller.location)
        if not handler:
            caller.msg("No estás en ningún combate activo.")
            return

        if not getattr(handler.db, "modo_duelo", False):
            caller.msg(
                "Solo puedes rendirte en un duelo. "
                "Para salir de un combate normal usa |whuir|n."
            )
            return

        participantes = list(handler.db.participantes or [])
        enemigos = [p for p in participantes if p != caller]
        if not enemigos:
            caller.msg("No hay oponente en el duelo.")
            return

        ganador = enemigos[0]
        caller.location.msg_contents(
            f"|y{caller.key}|n se rinde ante |w{ganador.key}|n."
        )
        handler._fin_duelo(ganador=ganador, perdedor=caller)


# --------------------------------------------------------------------------- #
#  Auxiliar
# --------------------------------------------------------------------------- #

def _buscar_por_dbref(dbref_str: str):
    """Devuelve el objeto Evennia con ese dbref, o None."""
    try:
        import evennia
        results = evennia.search_object(dbref_str, use_dbref=True)
        return results[0] if results else None
    except Exception:
        return None


# --------------------------------------------------------------------------- #
#  CmdSet
# --------------------------------------------------------------------------- #

class DuelCmdSet(CmdSet):
    key = "DuelCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdRetar())
        self.add(CmdAceptarDuelo())
        self.add(CmdRechazarDuelo())
        self.add(CmdRendirse())
