"""
features/bestiary/commands.py

Comandos del sistema de bestiario:
  bestiario            — lista todas las criaturas del catálogo con estado
  bestiario <nombre>   — detalle de una criatura concreta
"""
from evennia import Command, CmdSet

from systems.bestiary.bestiary import (
    CATALOGO,
    formatear_lista,
    formatear_entrada,
    buscar_en_catalogo,
)


class CmdBestiario(Command):
    """
    Consulta tu bestiario personal de criaturas derrotadas.

    Uso:
      bestiario                — ver todas las criaturas del catálogo
      bestiario <nombre>       — ver el detalle de una criatura concreta

    Ejemplo:
      bestiario
      bestiario goblin
      bestiario liche inmortal
    """
    key = "bestiario"
    aliases = ["bestiary", "enciclopedia", "criaturas"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        bestiary = dict(getattr(caller.db, "bestiary", {}) or {})
        args = self.args.strip()

        if not args:
            caller.msg(formatear_lista(bestiary))
            return

        # Búsqueda por nombre
        coincidencias = buscar_en_catalogo(args)

        if not coincidencias:
            caller.msg(f"|rNo se encontró ninguna criatura que coincida con '|w{args}|r'.|n")
            return

        if len(coincidencias) == 1:
            caller.msg(formatear_entrada(coincidencias[0], bestiary))
            return

        # Múltiples coincidencias: intentar match exacto primero
        args_lower = args.lower()
        exactas = [k for k in coincidencias if CATALOGO[k]["nombre"].lower() == args_lower]
        if len(exactas) == 1:
            caller.msg(formatear_entrada(exactas[0], bestiary))
            return

        nombres = ", ".join(f"|w{CATALOGO[k]['nombre']}|n" for k in coincidencias)
        caller.msg(f"Varias coincidencias: {nombres}. Sé más específico.")


class BestiaryCmdSet(CmdSet):
    key = "BestiaryCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdBestiario())
