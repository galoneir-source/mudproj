"""
features/combat/states_script.py

Script que aplica ticks de estados (veneno, sangrado, regeneracion)
fuera de combate. Se añade al personaje cuando adquiere un estado activo
y se elimina automáticamente cuando todos los estados expiran.
"""
from evennia import DefaultScript
from systems.combat.states import tick_estados

TICK_INTERVAL = 5  # segundos entre ticks fuera de combate


class EstadosScript(DefaultScript):
    """Script periódico que procesa estados activos fuera de combate."""

    def at_script_creation(self):
        self.key = "estados_script"
        self.desc = "Procesa estados de combate activos"
        self.interval = TICK_INTERVAL
        self.persistent = False

    def at_repeat(self):
        obj = self.obj
        if not obj:
            self.delete()
            return

        # El CombatHandler gestiona los ticks en combate
        if getattr(obj.db, "en_combate", False):
            return

        estados = dict(getattr(obj.db, "estados", {}) or {})
        if not estados:
            self.delete()
            return

        hp = getattr(obj.db, "hp", 1) or 1
        hp_max = getattr(obj.db, "hp_max", 100) or 100
        nuevos_estados, nuevo_hp, mensajes = tick_estados(estados, hp, hp_max)

        obj.db.estados = nuevos_estados
        # Fuera de combate el HP no baja de 1 para evitar muertes silenciosas
        obj.db.hp = max(1, nuevo_hp)

        for msg in mensajes:
            obj.msg(msg)

        if not nuevos_estados:
            self.delete()


def programar_estados_script(obj):
    """Añade EstadosScript al objeto si no tiene ya uno activo."""
    existing = [s for s in obj.scripts.all() if s.key == "estados_script"]
    if not existing:
        obj.scripts.add(EstadosScript)
