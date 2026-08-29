"""
features/arena/tournament_script.py

TorneoScript: gestiona un torneo de arena de principio a fin.

Estados del torneo:
  "inscripcion" — abierto a inscripciones, todavía no iniciado
  "activo"      — combates en curso
  "terminado"   — tiene campeón declarado (el script se auto-destruye)

El script NO es persistente: se crea al inscribirse el primer jugador y se
elimina al terminar el torneo o si pasan TIMEOUT_INSCRIPCION segundos sin
que se inicie (devolución de inscripciones).
"""
from evennia import DefaultScript
from evennia.utils import logger, delay


TIMEOUT_INSCRIPCION = 600   # 10 min; si no inicia, el torneo se cancela
TIMEOUT_COMBATE     = 300   # 5 min por combate; si no pasa nada, se cancela


def obtener_torneo_activo():
    """Devuelve el TorneoScript activo, o None si no hay torneo en curso."""
    from evennia.scripts.models import ScriptDB
    scripts = ScriptDB.objects.filter(db_key="torneo_arena")
    for s in scripts:
        return s
    return None


def notificar_resultado_torneo(torneo_script_id: int, ganador, perdedor):
    """
    Llamado por CombatHandler._fin_duelo() cuando termina un combate de torneo.
    Busca el TorneoScript por ID y registra el resultado.
    """
    try:
        from evennia.scripts.models import ScriptDB
        torneo = ScriptDB.objects.get(id=torneo_script_id)
        torneo.registrar_resultado(ganador, perdedor)
    except Exception as err:
        logger.log_err(f"notificar_resultado_torneo: {err}")


class TorneoScript(DefaultScript):

    def at_script_creation(self):
        self.key = "torneo_arena"
        self.desc = "Torneo activo de la Arena"
        self.persistent = False
        self.interval = TIMEOUT_INSCRIPCION
        self.start_delay = True
        self.db.estado     = "inscripcion"
        self.db.inscritos  = []   # lista de dbrefs
        self.db.nombres    = {}   # {dbref: nombre}
        self.db.bracket    = None
        self.db.pot        = 0
        self.db.sala_arena = None   # dbref de la sala arena

    # ------------------------------------------------------------------ #
    #  Fase de inscripción
    # ------------------------------------------------------------------ #

    def inscribir(self, jugador) -> tuple:
        """Inscribe al jugador. Devuelve (ok, mensaje)."""
        from systems.arena.arena import puede_inscribirse, INSCRIPCION_FEE, MIN_JUGADORES

        estado = self.db.estado or "inscripcion"
        if estado != "inscripcion":
            return False, "El torneo ya ha comenzado."

        inscritos = list(self.db.inscritos or [])
        ok, msg = puede_inscribirse(inscritos, jugador.dbref)
        if not ok:
            return False, msg

        monedas = int(getattr(jugador.db, "monedas", 0) or 0)
        if monedas < INSCRIPCION_FEE:
            return False, (
                f"La inscripción cuesta |w{INSCRIPCION_FEE} monedas|n. "
                f"Tienes {monedas}."
            )

        jugador.db.monedas = monedas - INSCRIPCION_FEE
        inscritos.append(jugador.dbref)
        self.db.inscritos = inscritos
        nombres = dict(self.db.nombres or {})
        nombres[jugador.dbref] = jugador.key
        self.db.nombres = nombres
        self.db.pot = (self.db.pot or 0) + INSCRIPCION_FEE

        _anunciar_global(
            f"|cArena:|n |w{jugador.key}|n se ha inscrito en el torneo. "
            f"({len(inscritos)} inscritos — usa |warena|n para ver estado)"
        )

        return True, f"Inscrito. Cuota: {INSCRIPCION_FEE} monedas."

    def desinscribir(self, jugador) -> tuple:
        """Cancela la inscripción y devuelve la cuota."""
        from systems.arena.arena import INSCRIPCION_FEE

        if (self.db.estado or "inscripcion") != "inscripcion":
            return False, "El torneo ya comenzó; no puedes retirarte."

        inscritos = list(self.db.inscritos or [])
        if jugador.dbref not in inscritos:
            return False, "No estás inscrito en el torneo."

        inscritos.remove(jugador.dbref)
        self.db.inscritos = inscritos
        nombres = dict(self.db.nombres or {})
        nombres.pop(jugador.dbref, None)
        self.db.nombres = nombres
        self.db.pot = max(0, (self.db.pot or 0) - INSCRIPCION_FEE)
        jugador.db.monedas = (getattr(jugador.db, "monedas", 0) or 0) + INSCRIPCION_FEE

        _anunciar_global(
            f"|cArena:|n |w{jugador.key}|n se ha retirado del torneo. "
            f"({len(inscritos)} inscritos)"
        )

        if not inscritos:
            self.delete()

        return True, f"Desinscrito. Cuota de {INSCRIPCION_FEE} monedas devuelta."

    # ------------------------------------------------------------------ #
    #  Inicio del torneo
    # ------------------------------------------------------------------ #

    def iniciar(self) -> tuple:
        """Inicia el torneo. Devuelve (ok, mensaje)."""
        from systems.arena.arena import MIN_JUGADORES, generar_bracket

        if (self.db.estado or "inscripcion") != "inscripcion":
            return False, "El torneo ya está en curso."

        inscritos = list(self.db.inscritos or [])
        if len(inscritos) < MIN_JUGADORES:
            return False, (
                f"Se necesitan al menos {MIN_JUGADORES} jugadores. "
                f"Hay {len(inscritos)}."
            )

        # Localizar sala arena
        sala = _buscar_sala_arena()
        if not sala:
            return False, "|rError: no se encontró la sala Arena. Avisa a un admin.|n"

        self.db.sala_arena = sala.dbref
        self.db.bracket    = generar_bracket(inscritos)
        self.db.estado     = "activo"
        # No basta con "self.interval = TIMEOUT_COMBATE": eso solo actualiza el
        # campo db_interval persistido, pero el LoopingCall de Twisted ya en
        # marcha (arrancado en at_script_creation con TIMEOUT_INSCRIPCION) sigue
        # corriendo con el intervalo viejo hasta que se reinicia explícitamente.
        # self.start()/self.restart() sí para y relanza el timer real.
        self.start(interval=TIMEOUT_COMBATE)

        nombres = dict(self.db.nombres or {})
        _anunciar_global(
            f"\n|Y⚔ ¡EL TORNEO DE LA ARENA HA COMENZADO!|n\n"
            f"Participantes: {', '.join(nombres.get(d,'???') for d in inscritos)}\n"
            f"Premio: |Y{self.db.pot} monedas|n\n"
            f"¡Que comience el espectáculo!"
        )

        delay(1, self._siguiente_combate)
        return True, "Torneo iniciado."

    # ------------------------------------------------------------------ #
    #  Lógica de combates
    # ------------------------------------------------------------------ #

    def _siguiente_combate(self):
        """Inicia el próximo combate del bracket o declara al campeón."""
        from systems.arena.arena import siguiente_combate, registrar_ganador, campeon

        # TIMEOUT_COMBATE es "por combate", no un presupuesto total para todo
        # el torneo: hay que reiniciar el timer real en cada ronda (igual que
        # en iniciar()), o un torneo de varias rondas que en conjunto supere
        # los 5 min se cancelaría entero aunque los combates vayan con normalidad.
        self.start(interval=TIMEOUT_COMBATE)

        bracket = dict(self.db.bracket or {})
        if not bracket:
            return

        combate = siguiente_combate(bracket)
        if combate is None:
            self._declarar_campeon(bracket)
            return

        p1_ref, p2_ref = combate

        # Bye: avanzar automáticamente
        if p2_ref is None:
            _anunciar_global(
                f"|cArena:|n |w{self.db.nombres.get(p1_ref,'???')}|n avanza automáticamente."
            )
            bracket = registrar_ganador(bracket, p1_ref)
            self.db.bracket = bracket
            champ = campeon(bracket)
            if champ:
                self._declarar_campeon(bracket)
            else:
                delay(1, self._siguiente_combate)
            return

        # Resolver objetos
        p1 = _resolver_jugador(p1_ref)
        p2 = _resolver_jugador(p2_ref)
        nombres = dict(self.db.nombres or {})

        # Forfeit si algún jugador no está disponible
        if not p1 and not p2:
            bracket = registrar_ganador(bracket, p1_ref)  # arbitrario
            self.db.bracket = bracket
            delay(1, self._siguiente_combate)
            return
        if not p1:
            _anunciar_global(
                f"|cArena:|n {nombres.get(p1_ref,'???')} no está disponible. "
                f"Forfeit → |w{nombres.get(p2_ref,'???')}|n avanza."
            )
            bracket = registrar_ganador(bracket, p2_ref)
            self.db.bracket = bracket
            delay(1, self._siguiente_combate)
            return
        if not p2:
            _anunciar_global(
                f"|cArena:|n {nombres.get(p2_ref,'???')} no está disponible. "
                f"Forfeit → |w{nombres.get(p1_ref,'???')}|n avanza."
            )
            bracket = registrar_ganador(bracket, p1_ref)
            self.db.bracket = bracket
            delay(1, self._siguiente_combate)
            return

        # Si alguno de los dos sigue en otro combate (p.ej. peleando contra
        # un monstruo mientras esperaba su turno de bracket), esperar a que
        # se libere en vez de arrastrarlo a la fuerza: eso dejaría su
        # combate anterior con un participante fantasma (su turno se
        # auto-pasa por timeout, pero el handler nunca lo elimina) y, al
        # terminar el duelo de torneo, _fin_duelo() pondría en_combate=False
        # para ambos, desincronizando ese flag del handler anterior -- que
        # seguiría activo y listándolo como participante.
        if getattr(p1.db, "en_combate", False) or getattr(p2.db, "en_combate", False):
            delay(5, self._siguiente_combate)
            return

        # Teleportar a la arena
        sala = _buscar_sala_arena()
        if not sala:
            self._cancelar("Error interno: sala arena no encontrada.")
            return

        for j in [p1, p2]:
            if j.location != sala:
                j.move_to(sala, quiet=False)

        _anunciar_global(
            f"\n|Y⚔ COMBATE DE TORNEO:|n "
            f"|w{p1.key}|n  vs  |w{p2.key}|n\n"
            f"Dirígete a la Arena para presenciar el combate."
        )

        # Iniciar duelo en la sala arena
        delay(2, self._iniciar_duelo_torneo, p1, p2)

    def _iniciar_duelo_torneo(self, p1, p2):
        """Crea el CombatHandler en modo duelo para el combate de torneo."""
        from evennia.utils.create import create_script
        from features.combat.handler import CombatHandler

        sala = _buscar_sala_arena()
        if not sala:
            return

        # Comprobar que no hay ya un combate activo
        for s in sala.scripts.all():
            if s.key == "combat_handler" and getattr(s.db, "activo", False):
                delay(3, self._iniciar_duelo_torneo, p1, p2)
                return

        handler = create_script(
            CombatHandler,
            obj=sala,
            persistent=False,
            autostart=False,
        )
        handler.db.modo_duelo     = True
        handler.db.torneo_script_id = self.id
        handler.iniciar([p1, p2])
        handler.start()

    def registrar_resultado(self, ganador, perdedor):
        """Llamado por CombatHandler cuando termina el duelo de torneo."""
        from systems.arena.arena import registrar_ganador, campeon

        bracket = dict(self.db.bracket or {})
        nombres = dict(self.db.nombres or {})

        _anunciar_global(
            f"|cArena:|n |w{ganador.key}|n vence a |w{perdedor.key}|n y avanza al torneo."
        )

        bracket = registrar_ganador(bracket, ganador.dbref)
        self.db.bracket = bracket

        champ = campeon(bracket)
        if champ:
            delay(1, self._declarar_campeon, bracket)
        else:
            delay(3, self._siguiente_combate)

    def _declarar_campeon(self, bracket: dict):
        """Declara al campeón, entrega el premio y cierra el torneo."""
        from systems.arena.arena import campeon as get_campeon
        champ_ref = get_campeon(bracket) or (
            list(self.db.inscritos or [])[0] if self.db.inscritos else None
        )
        nombres = dict(self.db.nombres or {})
        pot = int(self.db.pot or 0)

        champ_obj = _resolver_jugador(champ_ref) if champ_ref else None

        if champ_obj:
            champ_obj.db.monedas = (getattr(champ_obj.db, "monedas", 0) or 0) + pot
            champ_obj.db.torneos_ganados = (
                getattr(champ_obj.db, "torneos_ganados", 0) or 0
            ) + 1
            try:
                from features.achievements.commands import comprobar_y_notificar
                comprobar_y_notificar(champ_obj)
            except Exception:
                pass

        nombre_champ = nombres.get(champ_ref, "???") if champ_ref else "???"

        _anunciar_global(
            f"\n|Y🏆 ¡EL TORNEO DE LA ARENA HA TERMINADO!|n\n"
            f"|w{nombre_champ}|n es el nuevo |YCampeón de la Arena|n!\n"
            f"Premio: |Y{pot} monedas|n entregadas.\n"
            f"¡Felicidades al vencedor!"
        )

        self.db.estado = "terminado"
        self.delete()

    # ------------------------------------------------------------------ #
    #  Cancelación y timeouts
    # ------------------------------------------------------------------ #

    def _cancelar(self, razon: str = "Tiempo agotado."):
        """Cancela el torneo devolviendo las inscripciones."""
        inscritos = list(self.db.inscritos or [])
        from systems.arena.arena import INSCRIPCION_FEE
        for dbref in inscritos:
            obj = _resolver_jugador(dbref)
            if obj:
                obj.db.monedas = (getattr(obj.db, "monedas", 0) or 0) + INSCRIPCION_FEE

        _anunciar_global(
            f"|cArena:|n El torneo ha sido cancelado. {razon} "
            f"Inscripciones devueltas."
        )
        self.delete()

    def at_repeat(self):
        """Timeout: cancelar si lleva demasiado tiempo sin actividad."""
        estado = self.db.estado or "inscripcion"
        if estado == "inscripcion":
            self._cancelar("Tiempo de inscripción agotado.")
        elif estado == "activo":
            self._cancelar("Tiempo de combate agotado.")


# --------------------------------------------------------------------------- #
#  Helpers internos del módulo
# --------------------------------------------------------------------------- #

def _buscar_sala_arena():
    import evennia
    results = evennia.search_object("Arena de la Ciudad")
    for r in results:
        if r.is_typeclass("typeclasses.rooms.Room", exact=False):
            return r
    return None


def _resolver_jugador(dbref: str):
    """Devuelve el objeto Character del dbref, o None si no está disponible."""
    if not dbref:
        return None
    try:
        import evennia
        results = evennia.search_object(dbref)
        if results:
            obj = results[0]
            # Solo jugadores con sesión activa o al menos con cuenta
            if getattr(obj, "has_account", False):
                return obj
    except Exception:
        pass
    return None


def _anunciar_global(mensaje: str):
    """Envía un mensaje a todos los jugadores conectados."""
    try:
        from evennia.utils import logger
        from evennia import SESSION_HANDLER
        for session in SESSION_HANDLER.get_sessions():
            puppet = session.get_puppet()
            if puppet:
                puppet.msg(mensaje)
    except Exception as err:
        logger.log_err(f"_anunciar_global: {err}")
