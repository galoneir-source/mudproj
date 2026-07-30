"""
features/events/event_script.py

EventoMundialScript: script global que gestiona el ciclo de vida de los
eventos mundiales (inicio, duración, fin y cooldown).

Tick cada 60 segundos:
  - Si hay evento activo y expiró → terminarlo y anunciar fin.
  - Si no hay evento activo → 20 % de probabilidad de disparar uno elegible.

El script es persistente y se crea una sola vez (idempotente).
"""
import time as _time

import evennia
from evennia.scripts.scripts import DefaultScript


class EventoMundialScript(DefaultScript):
    """Script global persistente que gestiona los eventos mundiales."""

    def at_script_creation(self):
        self.key = "evento_mundial"
        self.desc = "Script global de eventos mundiales"
        self.persistent = True
        self.interval = 60             # tick cada minuto
        self.db.evento_activo = None   # event_id activo o None
        self.db.evento_inicio = 0.0    # timestamp Unix de inicio
        self.db.ultimo_por_evento = {} # {event_id: timestamp_fin}

    def at_repeat(self):
        ahora = _time.time()

        if self.db.evento_activo:
            self._comprobar_fin(ahora)
        else:
            self._intentar_iniciar(ahora)

    # ------------------------------------------------------------------ #
    #  Lógica interna
    # ------------------------------------------------------------------ #

    def _comprobar_fin(self, ahora: float):
        from systems.events.events import EVENTOS
        ev_id = self.db.evento_activo
        ev = EVENTOS.get(ev_id)
        if not ev:
            self.db.evento_activo = None
            return
        duracion = ev.get("duracion", 0)
        inicio = self.db.evento_inicio or 0.0
        if ahora - inicio >= duracion:
            self._terminar_evento(ev_id, ahora)

    def _intentar_iniciar(self, ahora: float):
        import random
        from systems.events.events import eventos_elegibles, elegir_evento

        if random.random() > 0.20:   # 20 % de probabilidad por tick
            return

        ultimo = dict(self.db.ultimo_por_evento or {})
        elegibles = eventos_elegibles(ultimo, ahora)
        if not elegibles:
            return

        ev_id = elegir_evento(elegibles, random.random())
        if ev_id:
            self._iniciar_evento(ev_id, ahora)

    def _iniciar_evento(self, ev_id: str, ahora: float):
        from systems.events.events import EVENTOS
        ev = EVENTOS.get(ev_id)
        if not ev:
            return
        self.db.evento_activo = ev_id
        self.db.evento_inicio = ahora
        color = ev.get("color", "|n")
        self._broadcast(f"\n{color}{ev['mensaje_inicio']}|n\n")

    def _terminar_evento(self, ev_id: str, ahora: float):
        from systems.events.events import EVENTOS
        ev = EVENTOS.get(ev_id, {})
        self.db.evento_activo = None
        self.db.evento_inicio = 0.0
        ultimo = dict(self.db.ultimo_por_evento or {})
        ultimo[ev_id] = ahora
        self.db.ultimo_por_evento = ultimo
        color = ev.get("color", "|n")
        self._broadcast(f"\n{color}{ev['mensaje_fin']}|n\n")

    def _broadcast(self, msg: str):
        try:
            for session in evennia.SESSION_HANDLER.get_sessions():
                puppet = session.get_puppet()
                if puppet:
                    puppet.msg(msg)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Utilidades de acceso global
# ---------------------------------------------------------------------------

def obtener_evento_script() -> EventoMundialScript | None:
    """
    Devuelve el EventoMundialScript activo, creándolo si no existe.
    Idempotente: nunca crea duplicados.
    """
    try:
        from evennia.scripts.models import ScriptDB
        script = ScriptDB.objects.filter(db_key="evento_mundial").first()
        if script:
            return script
    except Exception:
        pass
    return evennia.create_script(
        "features.events.event_script.EventoMundialScript"
    )


def obtener_evento_activo() -> str | None:
    """Devuelve el event_id activo o None. Seguro ante scripts no iniciados."""
    try:
        from evennia.scripts.models import ScriptDB
        script = ScriptDB.objects.filter(db_key="evento_mundial").first()
        if script:
            return script.db.evento_activo or None
    except Exception:
        pass
    return None


def tiempo_restante_evento() -> int:
    """Devuelve los segundos que quedan en el evento activo (0 si no hay evento)."""
    try:
        from evennia.scripts.models import ScriptDB
        script = ScriptDB.objects.filter(db_key="evento_mundial").first()
        if not script:
            return 0
        ev_id = script.db.evento_activo
        if not ev_id:
            return 0
        from systems.events.events import EVENTOS
        duracion = EVENTOS.get(ev_id, {}).get("duracion", 0)
        inicio = script.db.evento_inicio or 0.0
        return max(0, int(duracion - (_time.time() - inicio)))
    except Exception:
        pass
    return 0
