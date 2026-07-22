"""
features/trade/commands.py

Comandos del sistema de intercambio entre jugadores.

  intercambiar <jugador>         — propone un intercambio
  intercambiar aceptar           — acepta la propuesta recibida
  intercambiar cancelar          — cancela la sesión activa
  intercambiar estado            — muestra el estado actual

  ofrecer <objeto>               — añade un objeto a tu oferta
  ofrecer <cantidad> monedas     — añade monedas a tu oferta
  retirar <objeto>               — elimina un objeto de tu oferta

  confirmar                      — confirma tu parte del intercambio
  cancelar                       — alias de intercambiar cancelar
"""

from evennia import Command, CmdSet, search_object

from features.trade.trade_session import TradeSession
from systems.trade.trade import formatear_intercambio


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _sesion_activa(char) -> "TradeSession | None":
    """Devuelve la TradeSession en la que participa el jugador, o None."""
    return getattr(char.ndb, "trade_session", None)


def _buscar_jugador(caller, nombre: str):
    """Busca un Character en la misma sala por nombre."""
    sala = caller.location
    if not sala:
        return None, "No estás en ninguna sala."
    nombre_l = nombre.lower()
    jugadores = [
        obj for obj in sala.contents
        if obj != caller and hasattr(obj, "account") and obj.account
    ]
    exactos = [obj for obj in jugadores if obj.key.lower() == nombre_l]
    if len(exactos) == 1:
        return exactos[0], ""
    candidatos = [obj for obj in jugadores if nombre_l in obj.key.lower()]
    if not candidatos:
        return None, f"|rNo se encontró ningún jugador con el nombre '{nombre}' en esta sala.|n"
    if len(candidatos) > 1:
        nombres = ", ".join(c.key for c in candidatos)
        return None, f"|rNombre ambiguo: {nombres}. Sé más específico.|n"
    return candidatos[0], ""


def _buscar_objeto_inventario(caller, nombre: str):
    """Busca un objeto en el inventario del jugador."""
    nombre_l = nombre.lower()
    exactos = [obj for obj in caller.contents if obj.key.lower() == nombre_l]
    if len(exactos) == 1:
        return exactos[0], ""
    candidatos = [obj for obj in caller.contents if nombre_l in obj.key.lower()]
    if not candidatos:
        return None, f"|rNo tienes ningún objeto con el nombre '{nombre}'.|n"
    if len(candidatos) > 1:
        nombres = ", ".join(c.key for c in candidatos)
        return None, f"|rNombre ambiguo: {nombres}. Sé más específico.|n"
    return candidatos[0], ""


# --------------------------------------------------------------------------- #
#  Comando principal: intercambiar
# --------------------------------------------------------------------------- #

class CmdIntercambiar(Command):
    """
    Inicia, acepta o gestiona un intercambio con otro jugador.

    Uso:
      intercambiar <jugador>     - Propone un intercambio
      intercambiar aceptar       - Acepta la propuesta que te han hecho
      intercambiar cancelar      - Cancela el intercambio activo
      intercambiar estado        - Muestra el estado del intercambio actual
    """

    key = "intercambiar"
    aliases = ["trade", "intercambio"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        # Sin argumentos: ayuda
        if not args:
            caller.msg(
                "|wUso:|n intercambiar <jugador>\n"
                "       intercambiar aceptar / cancelar / estado"
            )
            return

        lower = args.lower()

        # --- aceptar ---
        if lower == "aceptar":
            pendiente = getattr(caller.ndb, "trade_pending", None)
            if not pendiente:
                caller.msg("|rNo tienes ninguna propuesta de intercambio pendiente.|n")
                return
            pendiente.aceptar(caller)
            caller.ndb.trade_pending = None
            caller.ndb.trade_session = pendiente
            return

        # --- cancelar ---
        if lower in ("cancelar", "cancel"):
            sesion = _sesion_activa(caller) or getattr(caller.ndb, "trade_pending", None)
            if not sesion:
                caller.msg("|xNo tienes ningún intercambio activo.|n")
                return
            sesion.cancelar(caller)
            return

        # --- estado ---
        if lower in ("estado", "status"):
            sesion = _sesion_activa(caller)
            if not sesion:
                caller.msg("|xNo tienes ningún intercambio activo.|n")
                return
            a_chars = search_object(sesion.db.jugador_a)
            b_chars = search_object(sesion.db.jugador_b)
            nombre_a = a_chars[0].name if a_chars else "???"
            nombre_b = b_chars[0].name if b_chars else "???"
            caller.msg(
                formatear_intercambio(
                    nombre_a, sesion.db.lado_a,
                    nombre_b, sesion.db.lado_b,
                )
            )
            return

        # --- proponer intercambio ---
        if _sesion_activa(caller):
            caller.msg("|rYa tienes un intercambio activo. Usa |wcancelar|r primero.|n")
            return

        objetivo, err = _buscar_jugador(caller, args)
        if not objetivo:
            caller.msg(err)
            return

        if objetivo == caller:
            caller.msg("|rNo puedes intercambiar contigo mismo.|n")
            return

        if _sesion_activa(objetivo):
            caller.msg(f"|r{objetivo.name} ya tiene un intercambio activo.|n")
            return

        if getattr(objetivo.ndb, "trade_pending", None):
            caller.msg(f"|r{objetivo.name} ya tiene una propuesta pendiente.|n")
            return

        # Crear sesión en estado pendiente
        from evennia import create_script
        sesion = create_script(
            "features.trade.trade_session.TradeSession",
            key=f"trade_{caller.id}_{objetivo.id}",
            persistent=False,
            autostart=True,
        )
        sesion.iniciar(caller, objetivo)

        # Guardar referencias
        caller.ndb.trade_session = sesion
        objetivo.ndb.trade_pending = sesion

        caller.msg(f"|gProposición de intercambio enviada a |w{objetivo.name}|g...|n")
        objetivo.msg(
            f"|Y{caller.name}|n te propone un intercambio.\n"
            f"Usa |wintercambiar aceptar|n para aceptar o |wintercambiar cancelar|n para rechazar."
        )


# --------------------------------------------------------------------------- #
#  Comando: ofrecer
# --------------------------------------------------------------------------- #

class CmdOfrecer(Command):
    """
    Añade un objeto o monedas a tu oferta de intercambio.

    Uso:
      ofrecer <objeto>              - Añade un objeto de tu inventario
      ofrecer <cantidad> monedas    - Establece las monedas que ofreces
      ofrecer 0 monedas             - Retira tu oferta de monedas
    """

    key = "ofrecer"
    aliases = ["offer"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        sesion = _sesion_activa(caller)
        if not sesion or sesion.db.estado != "activa":
            caller.msg("|xNo tienes ningún intercambio activo.|n")
            return

        args = self.args.strip()
        if not args:
            caller.msg("|rUso: ofrecer <objeto> | ofrecer <cantidad> monedas|n")
            return

        # Detectar "ofrecer N monedas"
        partes = args.split()
        if len(partes) >= 2 and partes[-1].lower() in ("monedas", "moneda", "coins"):
            try:
                cantidad = int(partes[0])
            except ValueError:
                caller.msg("|rEscribe una cantidad numérica. Ejemplo: ofrecer 50 monedas|n")
                return
            sesion.ofrecer_monedas(caller, cantidad)
            return

        # Buscar objeto en inventario
        obj, err = _buscar_objeto_inventario(caller, args)
        if not obj:
            caller.msg(err)
            return

        sesion.ofrecer_objeto(caller, obj)


# --------------------------------------------------------------------------- #
#  Comando: retirar (de la oferta)
# --------------------------------------------------------------------------- #

class CmdRetirarOferta(Command):
    """
    Retira un objeto de tu oferta de intercambio.

    Uso:
      retirar oferta <objeto>
    """

    key = "retirar oferta"
    aliases = ["withdraw offer"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        sesion = _sesion_activa(caller)
        if not sesion or sesion.db.estado != "activa":
            caller.msg("|xNo tienes ningún intercambio activo.|n")
            return

        args = self.args.strip()
        if not args:
            caller.msg("|rUso: retirar oferta <objeto>|n")
            return

        obj, err = _buscar_objeto_inventario(caller, args)
        if not obj:
            caller.msg(err)
            return

        sesion.retirar_objeto(caller, obj)


# --------------------------------------------------------------------------- #
#  Comando: confirmar (intercambio)
# --------------------------------------------------------------------------- #

class CmdConfirmarIntercambio(Command):
    """
    Confirma tu parte del intercambio. Cuando ambos jugadores confirman,
    el intercambio se ejecuta automáticamente.

    Uso:
      confirmar
    """

    key = "confirmar"
    aliases = ["confirm"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        sesion = _sesion_activa(caller)
        if not sesion:
            caller.msg("|xNo tienes ningún intercambio activo. Usa |wconfirmar|x solo durante un intercambio.|n")
            return
        sesion.confirmar_jugador(caller)


# --------------------------------------------------------------------------- #
#  CmdSet
# --------------------------------------------------------------------------- #

class TradeCmdSet(CmdSet):
    key = "TradeCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdIntercambiar)
        self.add(CmdOfrecer)
        self.add(CmdRetirarOferta)
        self.add(CmdConfirmarIntercambio)
