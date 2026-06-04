"""
features/time/clock_script.py

Script global RelojMundial y utilidades de acceso al tiempo de juego.

1 tick (1 min real) = 1 hora de juego → ciclo completo cada 24 min reales.
El reloj comienza a las 8:00 al crearse por primera vez.
"""
import evennia
from evennia.scripts.scripts import DefaultScript


class RelojMundial(DefaultScript):
    """
    Script global persistente que gestiona el tiempo del juego.
    Se crea una sola vez en el servidor; no está ligado a ningún objeto.
    """

    def at_script_creation(self):
        self.key = "reloj_mundial"
        self.desc = "Reloj global del mundo"
        self.persistent = True
        self.interval = 60      # 1 minuto real por tick
        self.db.hora = 8        # comienza a las 8:00

    def at_repeat(self):
        hora_anterior = int(self.db.hora or 8)
        hora_nueva = (hora_anterior + 1) % 24
        self.db.hora = hora_nueva

        from systems.time.clock import periodo_del_dia
        if periodo_del_dia(hora_anterior)[0] != periodo_del_dia(hora_nueva)[0]:
            self._anunciar_cambio_periodo(hora_nueva)

    def _anunciar_cambio_periodo(self, hora: int):
        from systems.time.clock import periodo_del_dia, MENSAJES_TRANSICION
        pid, _nombre, color = periodo_del_dia(hora)
        msg = MENSAJES_TRANSICION.get(pid, "")
        if not msg:
            return
        msg_formateado = f"\n{color}{msg}|n\n"
        try:
            for session in evennia.SESSION_HANDLER.get_sessions():
                puppet = session.get_puppet()
                if puppet:
                    puppet.msg(msg_formateado)
        except Exception:
            pass


# --------------------------------------------------------------------------- #
#  Utilidades de acceso
# --------------------------------------------------------------------------- #

def hora_actual() -> int:
    """
    Devuelve la hora actual del mundo (0-23).
    Fallback a 8 (mañana) si el reloj no está activo.
    """
    try:
        from evennia.scripts.models import ScriptDB
        qs = ScriptDB.objects.filter(db_key="reloj_mundial")
        if qs.exists():
            return int(qs.first().db.hora or 8)
    except Exception:
        pass
    return 8


def obtener_reloj():
    """
    Devuelve el RelojMundial activo, creándolo si no existe.
    Idempotente: nunca crea duplicados.
    """
    try:
        from evennia.scripts.models import ScriptDB
        qs = ScriptDB.objects.filter(db_key="reloj_mundial")
        if qs.exists():
            return qs.first()
    except Exception:
        pass
    return evennia.create_script("features.time.clock_script.RelojMundial")
