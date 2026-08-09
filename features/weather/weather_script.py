"""
features/weather/weather_script.py

Script global ClimaScript y utilidades de acceso al clima de juego.

El clima cambia de forma probabilística cada 10 minutos reales.
El script es persistente y se crea una sola vez; nunca se duplica.
"""
import evennia
from evennia.scripts.scripts import DefaultScript


class ClimaScript(DefaultScript):
    """
    Script global persistente que gestiona el clima dinámico del mundo.
    No está ligado a ningún objeto concreto.
    """

    def at_script_creation(self):
        self.key = "clima_mundial"
        self.desc = "Script global de clima dinámico"
        self.persistent = True
        self.interval = 600     # 10 minutos reales por tick
        # Sin start_delay=True, Evennia dispara el primer at_repeat() de
        # inmediato al crear el script (no tras 600s), rifando un cambio
        # de clima en el instante de creación en vez de esperar el tick.
        self.start_delay = True
        self.db.clima = "despejado"

    def at_repeat(self):
        from systems.weather.weather import siguiente_clima
        clima_anterior = str(self.db.clima or "despejado")
        clima_nuevo = siguiente_clima(clima_anterior)
        self.db.clima = clima_nuevo
        if clima_anterior != clima_nuevo:
            self._anunciar_cambio(clima_nuevo)

    def _anunciar_cambio(self, clima: str):
        from systems.weather.weather import CLIMAS, MENSAJES_TRANSICION
        msg = MENSAJES_TRANSICION.get(clima, "")
        if not msg:
            return
        color = CLIMAS.get(clima, {}).get("color", "|n")
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

def clima_actual() -> str:
    """
    Devuelve el clima actual del mundo.
    Fallback a 'despejado' si el script no está activo.
    """
    try:
        from evennia.scripts.models import ScriptDB
        script = ScriptDB.objects.filter(db_key="clima_mundial").first()
        if script:
            return str(script.db.clima or "despejado")
    except Exception:
        pass
    return "despejado"


def obtener_clima_script():
    """
    Devuelve el ClimaScript activo, creándolo si no existe.
    Idempotente: nunca crea duplicados.
    """
    try:
        from evennia.scripts.models import ScriptDB
        script = ScriptDB.objects.filter(db_key="clima_mundial").first()
        if script:
            return script
    except Exception:
        pass
    return evennia.create_script("features.weather.weather_script.ClimaScript")
