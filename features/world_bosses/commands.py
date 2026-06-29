"""
features/world_bosses/commands.py

  jefes / jefesMundo   — muestra estado de los jefes de mundo
"""

from evennia import Command, CmdSet

from systems.world_bosses.world_bosses import formatear_lista_jefes


class CmdJefesMundo(Command):
    """
    Muestra el estado actual de los jefes de mundo: si están vivos,
    derrotados, y cuándo vuelven a aparecer.

    Uso:
      jefes
    """

    key = "jefes"
    aliases = ["jefesMundo", "worldboss", "worldbosses"]
    locks = "cmd:all()"

    def func(self):
        try:
            from features.world_bosses.world_boss_script import obtener_world_boss_script
            script = obtener_world_boss_script()
            estados_vivo, ultimos = script.estado_jefes()
        except Exception:
            estados_vivo, ultimos = {}, {}

        self.caller.msg(formatear_lista_jefes(estados_vivo, ultimos))


class WorldBossCmdSet(CmdSet):
    key = "WorldBossCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdJefesMundo)
