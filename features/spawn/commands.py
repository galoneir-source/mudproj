"""
features/spawn/commands.py

Comandos de builder para spawn manual y repoblación de zonas.
Se añaden al BuilderCmdSet de commands/builder_cmdsets.py.
"""
from evennia import CmdSet, default_cmds


class CmdSpawn(default_cmds.MuxCommand):
    """
    Crea un NPC en la sala actual usando un prototipo.

    Uso:
      @spawn <prototipo>
      @spawn <prototipo> <cantidad>

    El prototipo debe estar definido en world/prototypes.py.
    El NPC hereda todos los atributos del prototipo (stats, loot, respawn…).

    Ejemplos:
      @spawn GOBLIN
      @spawn GOBLIN 3
      @spawn BANDIDO_CAPITAN
      @spawn SERPIENTE_PANTANO 2
    """
    key = "@spawn"
    aliases = ["@spawnear"]
    locks = "cmd:perm(Builder)"
    help_category = "Builder"

    def func(self):
        caller = self.caller
        args = self.args.strip().split()

        if not args:
            caller.msg("Uso: |w@spawn <prototipo> [cantidad]|n")
            return

        prototipo_key = args[0].upper()
        try:
            cantidad = int(args[1]) if len(args) > 1 else 1
            if cantidad < 1 or cantidad > 20:
                caller.msg("La cantidad debe estar entre 1 y 20.")
                return
        except ValueError:
            caller.msg(f"Cantidad inválida: '{args[1]}'.")
            return

        sala = caller.location
        if not sala:
            caller.msg("No estás en ninguna sala.")
            return

        from features.spawn.manager import spawn_npc
        creados = []
        for _ in range(cantidad):
            npc = spawn_npc(prototipo_key, sala)
            if npc:
                creados.append(npc.key)

        if creados:
            nombres = ", ".join(f"|y{n}|n" for n in creados)
            caller.msg(f"|g{len(creados)} NPC(s) creados|n: {nombres}")
        else:
            caller.msg(
                f"|rNo se pudo crear el prototipo '|w{prototipo_key}|r'.|n\n"
                f"Comprueba que el prototipo exista en world/prototypes.py."
            )


class CmdRepoblar(default_cmds.MuxCommand):
    """
    Repuebla una sala o todo el mundo con los NPCs definidos en su zona.

    Uso:
      @repoblar           — repuebla la sala actual
      @repoblar/mundo     — repuebla todas las salas con zona configurada

    La sala debe tener el atributo |wdb.zona|n asignado (se configura al
    construir el mundo con @construir_mundo / @expandir).
    Solo crea los NPCs que faltan; no duplica los ya existentes.

    Ejemplos:
      @repoblar
      @repoblar/mundo
    """
    key = "@repoblar"
    aliases = ["@repopulate"]
    locks = "cmd:perm(Builder)"
    help_category = "Builder"

    def func(self):
        caller = self.caller

        if "mundo" in self.switches:
            from features.spawn.manager import repoblar_mundo
            caller.msg("Repoblando todas las zonas del mundo…")
            total = repoblar_mundo()
            caller.msg(
                f"|g¡Repoblación completada!|n "
                f"{total} NPC(s) creados en total."
            )
            return

        sala = caller.location
        if not sala:
            caller.msg("No estás en ninguna sala.")
            return

        zona_id = getattr(sala.db, "zona", None)
        if not zona_id:
            caller.msg(
                f"|yEsta sala no tiene zona configurada.|n\n"
                f"Asigna |wdb.zona = '<zona_id>'|n o usa |w@construir_mundo|n."
            )
            return

        from features.spawn.manager import repoblar_sala
        creados = repoblar_sala(sala)

        if creados:
            nombres = ", ".join(f"|y{npc.key}|n" for npc in creados)
            caller.msg(
                f"|g{len(creados)} NPC(s) creados|n en |w{sala.key}|n "
                f"(zona: {zona_id}): {nombres}"
            )
        else:
            caller.msg(
                f"|wLa zona '|n{zona_id}|w' ya está correctamente poblada.|n"
            )


class SpawnCmdSet(CmdSet):
    key = "SpawnCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdSpawn())
        self.add(CmdRepoblar())
