"""
features/housing/commands.py

Comandos del sistema de vivienda:
  vivienda                       — muestra estado de tu vivienda
  vivienda comprar               — compra una vivienda (500 monedas, una sola vez)
  vivienda abandonar             — devuelve la vivienda (no reembolsable)
  vivienda acceso dar <jugador>  — concede acceso
  vivienda acceso quitar <jugador> — revoca acceso
  casa / hogar                   — teletransporta a tu vivienda
  visitar <jugador>              — visita la vivienda de otro jugador (si tienes acceso)
  decorar <texto>                — cambia la descripción de tu vivienda (debes estar en ella)
"""
from evennia import Command, CmdSet

from features.housing.housing_script import obtener_gestor_script


class CmdVivienda(Command):
    """
    Gestiona tu vivienda personal.

    Uso:
      vivienda                         — ver estado de tu vivienda
      vivienda comprar                 — comprar una vivienda (500 monedas)
      vivienda abandonar               — devolver la vivienda (sin reembolso)
      vivienda acceso dar <jugador>    — conceder acceso
      vivienda acceso quitar <jugador> — revocar acceso

    La vivienda es una sala privada y permanente. Solo tú y los jugadores
    a quienes hayas dado acceso podéis entrar. Usa |wcasa|n para ir
    directamente a ella desde cualquier lugar.
    """
    key = "vivienda"
    aliases = ["housing", "hogar info"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = self.args.strip()
        partes = args.split(None, 2)
        sub = partes[0].lower() if partes else ""

        if not sub or sub == "estado":
            self._cmd_estado(caller)
        elif sub == "comprar":
            self._cmd_comprar(caller)
        elif sub == "abandonar":
            self._cmd_abandonar(caller)
        elif sub == "acceso":
            if len(partes) < 3:
                caller.msg("Uso: |wvivienda acceso dar <jugador>|n  o  |wvivienda acceso quitar <jugador>|n")
                return
            accion = partes[1].lower()
            nombre = partes[2]
            if accion == "dar":
                self._cmd_acceso_dar(caller, nombre)
            elif accion in ("quitar", "revocar"):
                self._cmd_acceso_quitar(caller, nombre)
            else:
                caller.msg("Uso: |wvivienda acceso dar <jugador>|n  o  |wvivienda acceso quitar <jugador>|n")
        else:
            caller.msg(
                "Uso: |wvivienda|n, |wvivienda comprar|n, |wvivienda abandonar|n,\n"
                "     |wvivienda acceso dar <jugador>|n, |wvivienda acceso quitar <jugador>|n"
            )

    # ------------------------------------------------------------------ #

    def _cmd_estado(self, caller):
        from systems.housing.housing import formatear_estado, formatear_sin_vivienda

        gestor = obtener_gestor_script()
        sala = gestor.obtener_sala(caller)
        if not sala:
            caller.msg(formatear_sin_vivienda())
            return

        invitados_dbrefs = list(sala.db.invitados or [])
        nombres_invitados = []
        for dbref in invitados_dbrefs:
            import evennia
            results = evennia.search_object(dbref, use_dbref=True)
            nombres_invitados.append(results[0].key if results else "???")

        caller.msg(formatear_estado(
            caller.key,
            nombres_invitados,
            sala.db.desc_personalizada,
            sala.key,
        ))

    def _cmd_comprar(self, caller):
        gestor = obtener_gestor_script()
        ok, resultado = gestor.comprar(caller)
        if not ok:
            caller.msg(f"|r{resultado}|n")
            return

        sala = resultado
        caller.msg(
            f"|g¡Vivienda comprada!|n Se ha creado |w{sala.key}|n.\n"
            f"Usa |wcasa|n para ir a ella en cualquier momento.\n"
            f"Usa |wdecorar <texto>|n (desde dentro) para personalizarla."
        )
        try:
            from features.achievements.commands import comprobar_y_notificar
            comprobar_y_notificar(caller)
        except Exception:
            pass

    def _cmd_abandonar(self, caller):
        gestor = obtener_gestor_script()
        if not gestor.tiene_vivienda(caller):
            caller.msg("No tienes vivienda.")
            return

        # Pedir confirmación simple
        ndb = caller.ndb
        if not getattr(ndb, "confirmar_abandonar_vivienda", False):
            ndb.confirmar_abandonar_vivienda = True
            caller.msg(
                "|yAtención:|n Perderás tu vivienda de forma permanente y |rno recibirás reembolso|n.\n"
                "Los objetos que haya dentro pasarán al Barrio Residencial.\n"
                "Escribe |wvivienda abandonar|n de nuevo para confirmar."
            )
            return

        ndb.confirmar_abandonar_vivienda = False
        ok, msg = gestor.abandonar(caller)
        caller.msg(("|g" if ok else "|r") + msg + "|n")

    def _cmd_acceso_dar(self, caller, nombre):
        objetivo = caller.search(nombre, global_search=True)
        if not objetivo:
            return

        gestor = obtener_gestor_script()
        ok, msg = gestor.dar_acceso(caller, objetivo)
        caller.msg(("|g" if ok else "|r") + msg + "|n")
        if ok:
            objetivo.msg(f"|w{caller.key}|n te ha dado acceso a su vivienda. Usa |wvisitar {caller.key}|n.")

    def _cmd_acceso_quitar(self, caller, nombre):
        objetivo = caller.search(nombre, global_search=True)
        if not objetivo:
            return

        gestor = obtener_gestor_script()
        ok, msg = gestor.quitar_acceso(caller, objetivo)
        caller.msg(("|g" if ok else "|r") + msg + "|n")
        if ok:
            objetivo.msg(f"|w{caller.key}|n te ha retirado el acceso a su vivienda.")


class CmdCasa(Command):
    """
    Teletranspórtate a tu vivienda.

    Uso:
      casa
      hogar
    """
    key = "casa"
    aliases = ["hogar", "home"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        gestor = obtener_gestor_script()
        sala = gestor.obtener_sala(caller)

        if not sala:
            caller.msg(
                "No tienes vivienda. Visita el |wBarrio Residencial|n y usa "
                "|wvivienda comprar|n."
            )
            return

        if caller.location == sala:
            caller.msg("Ya estás en tu vivienda.")
            return

        caller.move_to(sala, quiet=False)
        caller.msg("Llegas a tu vivienda.")


class CmdVisitar(Command):
    """
    Visita la vivienda de otro jugador (necesitas acceso previo).

    Uso:
      visitar <jugador>
    """
    key = "visitar"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        if not self.args.strip():
            caller.msg("Uso: |wvisitar <jugador>|n")
            return

        objetivo = caller.search(self.args.strip(), global_search=True)
        if not objetivo:
            return

        if objetivo == caller:
            caller.msg("Usa |wcasa|n para ir a tu propia vivienda.")
            return

        gestor = obtener_gestor_script()
        ok, resultado = gestor.puede_visitar(caller, objetivo)
        if not ok:
            caller.msg(f"|r{resultado}|n")
            return

        sala = resultado
        if caller.location == sala:
            caller.msg("Ya estás en esa vivienda.")
            return

        caller.move_to(sala, quiet=False)
        caller.msg(f"Llegas a la vivienda de |w{objetivo.key}|n.")
        objetivo.msg(f"|w{caller.key}|n ha llegado a tu vivienda.")


class CmdDecorar(Command):
    """
    Cambia la descripción de tu vivienda. Debes estar dentro de ella.

    Uso:
      decorar <nueva descripción>

    Ejemplo:
      decorar Una habitación luminosa con estantes de madera y una chimenea
              de piedra que crepita suavemente.
    """
    key = "decorar"
    aliases = ["redecorate"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller

        if not self.args.strip():
            caller.msg("Uso: |wdecorar <nueva descripción>|n")
            return

        gestor = obtener_gestor_script()
        ok, msg = gestor.decorar(caller, self.args)

        caller.msg(("|g" if ok else "|r") + msg + "|n")
        if ok:
            caller.location.msg_contents(
                f"|w{caller.key}|n redecorar la habitación.", exclude=caller
            )
            try:
                from features.achievements.commands import comprobar_y_notificar
                comprobar_y_notificar(caller)
            except Exception:
                pass


class HousingCmdSet(CmdSet):
    key = "HousingCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdVivienda())
        self.add(CmdCasa())
        self.add(CmdVisitar())
        self.add(CmdDecorar())
