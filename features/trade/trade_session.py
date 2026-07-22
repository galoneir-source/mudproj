"""
features/trade/trade_session.py

TradeSession — script temporal que gestiona una sesión de intercambio entre
dos jugadores. No usa interval/timeout propio: se cancela en at_stop si el
server se recarga, y los comandos comprueban que los jugadores siguen en la
misma sala.

Ciclo de vida:
  1. Jugador A usa `intercambiar <B>` → se crea el script.
  2. B acepta con `intercambiar aceptar` → sesión activa.
  3. Cada uno usa `ofrecer` / `retirar` / `ofrecer monedas`.
  4. Ambos usan `confirmar` → se ejecuta el intercambio.
  5. `cancelar` (cualquiera) → se aborta.
"""

from evennia import DefaultScript

from systems.trade.trade import (
    nuevo_lado,
    agregar_objeto,
    retirar_objeto,
    establecer_monedas,
    confirmar,
    ambos_confirmados,
    validar_monedas,
    formatear_intercambio,
    formatear_oferta_simple,
)


class TradeSession(DefaultScript):

    def at_script_creation(self):
        self.key = "trade_session"
        self.desc = "Sesión de intercambio activa"
        self.persistent = False   # Se limpia en reload
        self.interval = 120       # Auto-cancela tras 2 min de inactividad
        self.start_delay = True
        self.db.jugador_a = None  # dbref del iniciador
        self.db.jugador_b = None  # dbref del otro
        self.db.lado_a = nuevo_lado()
        self.db.lado_b = nuevo_lado()
        self.db.estado = "pendiente"  # "pendiente" | "activa" | "cerrada"

    # ---------------------------------------------------------------------- #
    #  Setup inicial
    # ---------------------------------------------------------------------- #

    def iniciar(self, jugador_a, jugador_b):
        self.db.jugador_a = jugador_a.dbref
        self.db.jugador_b = jugador_b.dbref
        self.db.estado = "pendiente"

    # ---------------------------------------------------------------------- #
    #  Aceptación
    # ---------------------------------------------------------------------- #

    def aceptar(self, jugador):
        if self.db.estado != "pendiente":
            jugador.msg("|rEsta sesión ya no está pendiente.|n")
            return
        if jugador.dbref != self.db.jugador_b:
            jugador.msg("|rNo eres el destinatario de este intercambio.|n")
            return
        self.db.estado = "activa"
        a, b = self._chars()
        if a:
            a.msg(f"|g{jugador.name} ha aceptado el intercambio.|n")
        b.msg("|gIntercambio iniciado. Usa |wofrecer|g para añadir tu oferta.|n")
        self._mostrar_estado_a_ambos()

    # ---------------------------------------------------------------------- #
    #  Ofrecer objetos / monedas
    # ---------------------------------------------------------------------- #

    def ofrecer_objeto(self, jugador, obj):
        lado = self._lado_de(jugador)
        if lado is None:
            return
        if self.db.estado != "activa":
            jugador.msg("|rEl intercambio no está activo.|n")
            return
        if obj.location != jugador:
            jugador.msg("|rEse objeto no está en tu inventario.|n")
            return
        ok, err = agregar_objeto(lado, obj.dbref, obj.key)
        if not ok:
            jugador.msg(f"|r{err}|n")
            return
        self._guardar_lado(jugador, lado)
        self._desconfirmar_otro(jugador)
        otro = self._otro(jugador)
        nombre_oferta = formatear_oferta_simple(lado)
        if otro:
            otro.msg(f"|y{jugador.name}|n añade a su oferta: |w{obj.key}|n")
        jugador.msg(f"|gAñadiste |w{obj.key}|n a tu oferta.|n")
        self._mostrar_estado_a_ambos()

    def retirar_objeto(self, jugador, obj):
        lado = self._lado_de(jugador)
        if lado is None:
            return
        ok, err = retirar_objeto(lado, obj.dbref)
        if not ok:
            jugador.msg(f"|r{err}|n")
            return
        self._guardar_lado(jugador, lado)
        self._desconfirmar_otro(jugador)
        otro = self._otro(jugador)
        if otro:
            otro.msg(f"|y{jugador.name}|n retira |w{obj.key}|n de su oferta.")
        jugador.msg(f"|gRetiraste |w{obj.key}|n de tu oferta.|n")
        self._mostrar_estado_a_ambos()

    def ofrecer_monedas(self, jugador, cantidad: int):
        lado = self._lado_de(jugador)
        if lado is None:
            return
        if self.db.estado != "activa":
            jugador.msg("|rEl intercambio no está activo.|n")
            return
        ok, err = establecer_monedas(lado, cantidad)
        if not ok:
            jugador.msg(f"|r{err}|n")
            return
        self._guardar_lado(jugador, lado)
        self._desconfirmar_otro(jugador)
        otro = self._otro(jugador)
        if otro:
            otro.msg(f"|y{jugador.name}|n ajusta su oferta de monedas a |w{cantidad}|n.")
        jugador.msg(f"|gEstableciste tu oferta de monedas: |w{cantidad}|n.|n")
        self._mostrar_estado_a_ambos()

    # ---------------------------------------------------------------------- #
    #  Confirmar
    # ---------------------------------------------------------------------- #

    def confirmar_jugador(self, jugador):
        if self.db.estado != "activa":
            jugador.msg("|rEl intercambio no está activo.|n")
            return
        lado = self._lado_de(jugador)
        if lado is None:
            return
        confirmar(lado)
        self._guardar_lado(jugador, lado)
        otro = self._otro(jugador)
        if otro:
            otro.msg(f"|g{jugador.name} ha confirmado el intercambio.|n")
        jugador.msg("|gHas confirmado. Esperando confirmación del otro jugador...|n")

        lado_a = self.db.lado_a
        lado_b = self.db.lado_b
        if ambos_confirmados(lado_a, lado_b):
            self._ejecutar()

    # ---------------------------------------------------------------------- #
    #  Cancelar
    # ---------------------------------------------------------------------- #

    def cancelar(self, jugador=None):
        self.db.estado = "cerrada"
        a, b = self._chars()
        mensaje = (
            f"|r{jugador.name} ha cancelado el intercambio.|n"
            if jugador
            else "|rEl intercambio ha sido cancelado.|n"
        )
        for char in (a, b):
            if char:
                char.msg(mensaje)
                # Limpiar referencias al script (una propuesta pendiente aún
                # no aceptada solo tiene trade_pending, no trade_session).
                char.ndb.trade_session = None
                char.ndb.trade_pending = None
        self.delete()

    # ---------------------------------------------------------------------- #
    #  Timeout
    # ---------------------------------------------------------------------- #

    def at_repeat(self):
        self.cancelar()

    def at_server_reload(self):
        self.cancelar()

    # ---------------------------------------------------------------------- #
    #  Ejecución del intercambio
    # ---------------------------------------------------------------------- #

    def _ejecutar(self):
        self.db.estado = "cerrada"
        a, b = self._chars()
        if not (a and b):
            return

        lado_a = self.db.lado_a
        lado_b = self.db.lado_b

        # Validar monedas
        ok_a, err_a = validar_monedas(lado_a, a.db.monedas or 0)
        ok_b, err_b = validar_monedas(lado_b, b.db.monedas or 0)
        if not ok_a:
            a.msg(f"|r{err_a}|n")
            b.msg(f"|r{a.name} ya no tiene suficientes monedas. Intercambio cancelado.|n")
            self._limpiar_refs()
            self.delete()
            return
        if not ok_b:
            b.msg(f"|r{err_b}|n")
            a.msg(f"|r{b.name} ya no tiene suficientes monedas. Intercambio cancelado.|n")
            self._limpiar_refs()
            self.delete()
            return

        # Validar que los objetos siguen en el inventario
        for entrada in lado_a["objetos"]:
            obj = self._buscar_obj(entrada["id"], a)
            if obj is None:
                a.msg(f"|rEl objeto '{entrada['nombre']}' ya no está en tu inventario. Intercambio cancelado.|n")
                b.msg(f"|r{a.name} ya no tiene '{entrada['nombre']}'. Intercambio cancelado.|n")
                self._limpiar_refs()
                self.delete()
                return
        for entrada in lado_b["objetos"]:
            obj = self._buscar_obj(entrada["id"], b)
            if obj is None:
                b.msg(f"|rEl objeto '{entrada['nombre']}' ya no está en tu inventario. Intercambio cancelado.|n")
                a.msg(f"|r{b.name} ya no tiene '{entrada['nombre']}'. Intercambio cancelado.|n")
                self._limpiar_refs()
                self.delete()
                return

        # Transferir objetos A → B
        for entrada in lado_a["objetos"]:
            obj = self._buscar_obj(entrada["id"], a)
            if obj:
                obj.location = b

        # Transferir objetos B → A
        for entrada in lado_b["objetos"]:
            obj = self._buscar_obj(entrada["id"], b)
            if obj:
                obj.location = a

        # Transferir monedas
        if lado_a["monedas"] > 0:
            a.db.monedas = (a.db.monedas or 0) - lado_a["monedas"]
            b.db.monedas = (b.db.monedas or 0) + lado_a["monedas"]
        if lado_b["monedas"] > 0:
            b.db.monedas = (b.db.monedas or 0) - lado_b["monedas"]
            a.db.monedas = (a.db.monedas or 0) + lado_b["monedas"]

        # Notificar
        resumen_a = formatear_oferta_simple(lado_a) or "(nada)"
        resumen_b = formatear_oferta_simple(lado_b) or "(nada)"
        a.msg(
            f"\n|g¡Intercambio completado!|n\n"
            f"  Diste: |w{resumen_a}|n\n"
            f"  Recibiste: |w{resumen_b}|n"
        )
        b.msg(
            f"\n|g¡Intercambio completado!|n\n"
            f"  Diste: |w{resumen_b}|n\n"
            f"  Recibiste: |w{resumen_a}|n"
        )
        self._limpiar_refs()
        self.delete()

    # ---------------------------------------------------------------------- #
    #  Helpers
    # ---------------------------------------------------------------------- #

    def _chars(self):
        from evennia import search_object
        a_list = search_object(self.db.jugador_a) if self.db.jugador_a else []
        b_list = search_object(self.db.jugador_b) if self.db.jugador_b else []
        return (a_list[0] if a_list else None), (b_list[0] if b_list else None)

    def _otro(self, jugador):
        a, b = self._chars()
        if jugador.dbref == self.db.jugador_a:
            return b
        return a

    def _lado_de(self, jugador):
        if jugador.dbref == self.db.jugador_a:
            return self.db.lado_a
        if jugador.dbref == self.db.jugador_b:
            return self.db.lado_b
        jugador.msg("|rNo eres parte de este intercambio.|n")
        return None

    def _guardar_lado(self, jugador, lado):
        if jugador.dbref == self.db.jugador_a:
            self.db.lado_a = lado
        else:
            self.db.lado_b = lado

    def _desconfirmar_otro(self, jugador):
        """
        Si el otro jugador ya había confirmado, se desconfirma: los términos
        del intercambio acaban de cambiar y no debe ejecutarse sobre una
        confirmación dada a una oferta distinta.
        """
        if jugador.dbref == self.db.jugador_a:
            otro_lado = self.db.lado_b
        else:
            otro_lado = self.db.lado_a
        if not otro_lado.get("confirmado"):
            return
        otro_lado["confirmado"] = False
        if jugador.dbref == self.db.jugador_a:
            self.db.lado_b = otro_lado
        else:
            self.db.lado_a = otro_lado

    def _mostrar_estado_a_ambos(self):
        a, b = self._chars()
        if not (a and b):
            return
        lado_a = self.db.lado_a
        lado_b = self.db.lado_b
        texto = formatear_intercambio(a.name, lado_a, b.name, lado_b)
        a.msg(texto)
        b.msg(texto)

    def _buscar_obj(self, dbref: str, jugador):
        from evennia import search_object
        resultados = search_object(dbref)
        if resultados and resultados[0].location == jugador:
            return resultados[0]
        return None

    def _limpiar_refs(self):
        a, b = self._chars()
        for char in (a, b):
            if char:
                char.ndb.trade_session = None
