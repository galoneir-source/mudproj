"""
features/cartography/commands.py

Comandos del sistema de cartografía:
  mapa            — muestra el progreso de exploración por zona
  explorado       — muestra cuántas salas has visitado (resumen rápido)
"""
from evennia import Command, CmdSet

from systems.cartography.cartography import ZONAS_INFO, formatear_mapa, total_exploradas


def _zonas_a_dbref() -> dict:
    """
    Devuelve {zona_id: dbref} para todas las salas del mundo que tengan zona.
    Excluye salas instanciadas (mazmorra) y privadas (vivienda).
    """
    from evennia.objects.models import ObjectDB

    resultado = {}
    salas_db = ObjectDB.objects.filter(
        db_typeclass_path__contains="rooms.Room"
    )
    for sala in salas_db:
        try:
            if getattr(sala.db, "es_mazmorra", False):
                continue
            if getattr(sala.db, "es_vivienda", False):
                continue
            zona = getattr(sala.db, "zona", None)
            if zona:
                resultado[zona] = sala.dbref
        except Exception:
            pass
    return resultado


class CmdMapa(Command):
    """
    Consulta tu mapa de exploración del mundo.

    Uso:
      mapa            — muestra todas las zonas con estado explorado/pendiente
      mapa resumen    — solo el conteo global
    """
    key = "mapa"
    aliases = ["map", "explorado", "explorados", "cartografia"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        exploradas = list(getattr(caller.db, "salas_exploradas", []) or [])
        exploradas_set = set(exploradas)
        args = self.args.strip().lower()

        if args == "resumen":
            total = total_exploradas(exploradas)
            caller.msg(f"Has explorado |w{total}|n salas únicas.")
            return

        zonas = _zonas_a_dbref()
        caller.msg(formatear_mapa(exploradas_set, zonas))


class CartographyCmdSet(CmdSet):
    key = "CartographyCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdMapa())
