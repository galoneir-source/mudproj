"""
features/buffs/commands.py — Comando para ver buffs activos del personaje.
"""

from evennia import Command, CmdSet


class CmdBuffs(Command):
    """
    Muestra los buffs temporales activos del personaje.

    Uso:
      buffs
    """

    key = "buffs"
    aliases = ["mis buffs", "estado buffs"]
    locks = "cmd:all()"
    help_category = "Personaje"

    def func(self):
        from systems.buffs.buffs import formatear_buffs, buffs_vigentes
        buffs_raw = list(getattr(self.caller.db, "buffs_activos", None) or [])
        vigentes = buffs_vigentes(buffs_raw)

        # Limpiar expirados silenciosamente
        if len(vigentes) < len(buffs_raw):
            self.caller.db.buffs_activos = vigentes

        if not vigentes:
            self.caller.msg("|xNo tienes ningún buff activo.|n")
            return

        lineas = formatear_buffs(vigentes)
        self.caller.msg("|wBuffs activos:|n")
        for linea in lineas:
            self.caller.msg(f"  {linea}")


class BuffsCmdSet(CmdSet):
    key = "BuffsCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdBuffs)
