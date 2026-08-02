"""
features/marriage/commands.py

Comandos del sistema de matrimonio entre jugadores:
  proponer <jugador>  — propone matrimonio
  aceptar boda         — acepta una propuesta pendiente
  rechazar boda         — rechaza una propuesta pendiente
  divorciarse           — termina el matrimonio actual
  casado                — muestra tu estado civil
"""
import time

from evennia import Command, CmdSet, search_object

from systems.marriage.marriage import (
    TIMEOUT_PROPUESTA_SEGUNDOS,
    propuesta_expirada,
    puede_proponer,
    puede_divorciarse,
    formatear_propuesta_recibida,
    formatear_boda,
    formatear_divorcio,
    formatear_estado_civil,
)


# --------------------------------------------------------------------------- #
#  Utilidades
# --------------------------------------------------------------------------- #

def _buscar_jugador(nombre: str):
    """Busca un Character por nombre (en línea o no). Devuelve (char, error)."""
    resultados = search_object(nombre, typeclass="typeclasses.characters.Character")
    if not resultados:
        return None, f"|rNo se encontró ningún jugador con el nombre '{nombre}'.|n"
    if len(resultados) > 1:
        nombres = ", ".join(r.key for r in resultados)
        return None, f"|rNombre ambiguo: {nombres}. Sé más específico.|n"
    return resultados[0], ""


def _buscar_por_dbref(dbref_str):
    """Devuelve el objeto Evennia con ese dbref, o None."""
    if not dbref_str:
        return None
    try:
        resultados = search_object(dbref_str, use_dbref=True)
        return resultados[0] if resultados else None
    except Exception:
        return None


def _limpiar_propuesta(char):
    """Elimina todos los atributos de propuesta pendiente del personaje."""
    char.db.propuesta_matrimonio_pendiente = None
    char.db.propuesta_matrimonio_proponente_dbref = None


def _tiene_propuesta_saliente_vigente(char) -> bool:
    """
    True si `char` tiene una propuesta que él mismo lanzó y sigue vigente.
    Si expiró, limpia los atributos de ambos lados y devuelve False.
    """
    pendiente = getattr(char.db, "propuesta_matrimonio_pendiente", None)
    if not pendiente:
        return False
    if propuesta_expirada(pendiente.get("timestamp", 0), time.time()):
        objetivo = _buscar_por_dbref(pendiente.get("objetivo_dbref"))
        _limpiar_propuesta(char)
        if objetivo:
            _limpiar_propuesta(objetivo)
        return False
    return True


def _tiene_propuesta_entrante_vigente(objetivo) -> bool:
    """
    True si `objetivo` tiene una propuesta entrante vigente de otro jugador.
    Si el proponente ya no existe o la propuesta caducó, limpia ambos lados.
    """
    proponente_dbref = getattr(objetivo.db, "propuesta_matrimonio_proponente_dbref", None)
    if not proponente_dbref:
        return False
    proponente = _buscar_por_dbref(proponente_dbref)
    if not proponente:
        _limpiar_propuesta(objetivo)
        return False
    pendiente = getattr(proponente.db, "propuesta_matrimonio_pendiente", None) or {}
    if propuesta_expirada(pendiente.get("timestamp", 0), time.time()):
        _limpiar_propuesta(objetivo)
        _limpiar_propuesta(proponente)
        return False
    return True


# --------------------------------------------------------------------------- #
#  proponer
# --------------------------------------------------------------------------- #

class CmdProponer(Command):
    """
    Proponer matrimonio a otro jugador.

    Uso:
      proponer <jugador>

    Tiene 120 segundos para aceptar o rechazar. Ninguno de los dos puede
    estar ya casado, ni tener otra propuesta pendiente.
    """
    key = "proponer"
    aliases = ["proponer matrimonio"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        nombre = self.args.strip()
        if not nombre:
            caller.msg("Uso: proponer <jugador>")
            return

        objetivo, error = _buscar_jugador(nombre)
        if error:
            caller.msg(error)
            return

        if not bool(getattr(objetivo, "account", None)):
            caller.msg(f"|w{objetivo.key}|n no es un jugador.")
            return

        propio_conyuge = getattr(caller.db, "conyuge_dbref", None)
        objetivo_conyuge = getattr(objetivo.db, "conyuge_dbref", None)

        ok, error = puede_proponer(
            caller.dbref,
            objetivo.dbref,
            propio_conyuge,
            objetivo_conyuge,
            _tiene_propuesta_saliente_vigente(caller),
            _tiene_propuesta_entrante_vigente(objetivo),
        )
        if not ok:
            caller.msg(f"|r{error}|n")
            return

        caller.db.propuesta_matrimonio_pendiente = {
            "objetivo_dbref": objetivo.dbref,
            "timestamp": time.time(),
        }
        objetivo.db.propuesta_matrimonio_proponente_dbref = caller.dbref

        caller.msg(
            f"Le has propuesto matrimonio a |w{objetivo.key}|n. "
            f"Tiene {TIMEOUT_PROPUESTA_SEGUNDOS}s para responder."
        )
        objetivo.msg(formatear_propuesta_recibida(caller.key))


# --------------------------------------------------------------------------- #
#  aceptar boda
# --------------------------------------------------------------------------- #

class CmdAceptarBoda(Command):
    """
    Aceptar una propuesta de matrimonio pendiente.

    Uso:
      aceptar boda
    """
    key = "aceptar boda"
    aliases = ["aceptar matrimonio"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller

        proponente_dbref = getattr(caller.db, "propuesta_matrimonio_proponente_dbref", None)
        if not proponente_dbref:
            caller.msg("No tienes ninguna propuesta de matrimonio pendiente.")
            return

        proponente = _buscar_por_dbref(proponente_dbref)
        if not proponente:
            caller.msg("La persona que te propuso matrimonio ya no está disponible.")
            _limpiar_propuesta(caller)
            return

        pendiente = getattr(proponente.db, "propuesta_matrimonio_pendiente", None) or {}
        timestamp = pendiente.get("timestamp", 0)
        if propuesta_expirada(timestamp, time.time()):
            caller.msg("La propuesta ya ha expirado.")
            _limpiar_propuesta(caller)
            _limpiar_propuesta(proponente)
            return

        if getattr(proponente.db, "conyuge_dbref", None) or getattr(caller.db, "conyuge_dbref", None):
            caller.msg("No se puede completar la boda: uno de los dos ya está casado.")
            _limpiar_propuesta(caller)
            _limpiar_propuesta(proponente)
            return

        ahora = time.time()
        proponente.db.conyuge_dbref = caller.dbref
        proponente.db.fecha_boda = ahora
        caller.db.conyuge_dbref = proponente.dbref
        caller.db.fecha_boda = ahora
        _limpiar_propuesta(caller)
        _limpiar_propuesta(proponente)

        anuncio = formatear_boda(proponente.key, caller.key)
        proponente.msg(anuncio)
        caller.msg(anuncio)
        if caller.location:
            caller.location.msg_contents(anuncio, exclude=[caller, proponente])
        if proponente.location and proponente.location != caller.location:
            proponente.location.msg_contents(anuncio, exclude=[caller, proponente])


# --------------------------------------------------------------------------- #
#  rechazar boda
# --------------------------------------------------------------------------- #

class CmdRechazarBoda(Command):
    """
    Rechazar una propuesta de matrimonio pendiente.

    Uso:
      rechazar boda
    """
    key = "rechazar boda"
    aliases = ["rechazar matrimonio"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller

        proponente_dbref = getattr(caller.db, "propuesta_matrimonio_proponente_dbref", None)
        if not proponente_dbref:
            caller.msg("No tienes ninguna propuesta de matrimonio pendiente.")
            return

        proponente = _buscar_por_dbref(proponente_dbref)
        if proponente:
            proponente.msg(f"|y{caller.key}|n ha rechazado tu propuesta de matrimonio.")
            _limpiar_propuesta(proponente)

        _limpiar_propuesta(caller)
        caller.msg("Has rechazado la propuesta de matrimonio.")


# --------------------------------------------------------------------------- #
#  divorciarse
# --------------------------------------------------------------------------- #

class CmdDivorciarse(Command):
    """
    Termina tu matrimonio actual.

    Uso:
      divorciarse

    No hace falta que el cónyuge esté presente ni que esté de acuerdo.
    """
    key = "divorciarse"
    aliases = ["divorcio"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        conyuge_dbref = getattr(caller.db, "conyuge_dbref", None)

        ok, error = puede_divorciarse(conyuge_dbref)
        if not ok:
            caller.msg(f"|r{error}|n")
            return

        conyuge = _buscar_por_dbref(conyuge_dbref)
        conyuge_nombre = conyuge.key if conyuge else "tu excónyuge"

        caller.db.conyuge_dbref = None
        caller.db.fecha_boda = None
        if conyuge:
            conyuge.db.conyuge_dbref = None
            conyuge.db.fecha_boda = None
            conyuge.msg(formatear_divorcio(caller.key, conyuge.key))

        caller.msg(formatear_divorcio(caller.key, conyuge_nombre))


# --------------------------------------------------------------------------- #
#  casado
# --------------------------------------------------------------------------- #

class CmdCasado(Command):
    """
    Muestra tu estado civil actual.

    Uso:
      casado
    """
    key = "casado"
    aliases = ["estado civil", "conyuge"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        conyuge_dbref = getattr(caller.db, "conyuge_dbref", None)
        conyuge = _buscar_por_dbref(conyuge_dbref) if conyuge_dbref else None
        fecha_boda = getattr(caller.db, "fecha_boda", None)
        fecha_txt = None
        if fecha_boda:
            fecha_txt = time.strftime("%Y-%m-%d", time.localtime(fecha_boda))
        caller.msg(formatear_estado_civil(conyuge.key if conyuge else None, fecha_txt))


class MarriageCmdSet(CmdSet):
    key = "MarriageCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdProponer())
        self.add(CmdAceptarBoda())
        self.add(CmdRechazarBoda())
        self.add(CmdDivorciarse())
        self.add(CmdCasado())
