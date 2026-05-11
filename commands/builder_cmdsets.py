from evennia import CmdSet, default_cmds
from features.doors.builder import CmdDoor, CmdKeyMake
from features.spawn.commands import SpawnCmdSet


class CmdLimpiarMundo(default_cmds.MuxCommand):
    """
    Elimina todas las salas y salidas excepto #2 (Limbo).

    Uso:
      @limpiar_mundo
      @limpiar_mundo/confirmar

    Sin /confirmar muestra lo que se va a borrar.
    Con /confirmar ejecuta la limpieza.
    Los personajes en salas eliminadas se mueven a #2.
    """
    key = "@limpiar_mundo"
    aliases = ["@cleanworld"]
    locks = "cmd:perm(Builder)"
    help_category = "Builder"

    def func(self):
        from evennia.objects.models import ObjectDB
        caller = self.caller

        limbo_qs = ObjectDB.objects.filter(id=2)
        if not limbo_qs.exists():
            caller.msg("|rNo se encontró #2 (Limbo).|n")
            return
        limbo = limbo_qs[0]

        # Exits: cualquier objeto con db_destination seteado (independiente de typeclass)
        todas_salidas_qs = ObjectDB.objects.filter(db_destination__isnull=False)
        # Salas: excepto #2
        todas_salas_qs = ObjectDB.objects.filter(db_typeclass_path__icontains="room").exclude(id=2)

        if "confirmar" not in self.switches:
            caller.msg(
                f"|yResumen de lo que se borrará:|n\n"
                f"  Salas   : {todas_salas_qs.count()}\n"
                f"  Salidas : {todas_salidas_qs.count()}\n"
                f"\n|wUsa |r@limpiar_mundo/confirmar|w para ejecutar.|n"
            )
            return

        # Mover personajes fuera de salas que se van a borrar
        ids_borrar = set(todas_salas_qs.values_list("id", flat=True))
        for obj in ObjectDB.objects.filter(db_typeclass_path__icontains="character"):
            if obj.location and obj.location.id in ids_borrar:
                obj.move_to(limbo, quiet=True)
                obj.msg("|yTu ubicación fue eliminada. Has sido movido a Limbo.|n")

        # ── Borrar todas las salidas (bulk SQL, sin importar typeclass) ──────
        ids_salidas = list(todas_salidas_qs.values_list("id", flat=True))
        salidas_borradas = len(ids_salidas)
        if ids_salidas:
            ObjectDB.objects.filter(id__in=ids_salidas).delete()

        # ── Borrar salas (bulk SQL) ───────────────────────────────────────
        ids_salas = list(todas_salas_qs.values_list("id", flat=True))
        borradas = len(ids_salas)
        if ids_salas:
            ObjectDB.objects.filter(id__in=ids_salas).delete()

        # ── Limpiar Limbo: borrar todo lo que no sea personaje ni Limbo ──
        # (exits y objetos que Evennia mueve aquí al borrar sus salas)
        ids_caller = {caller.id}
        for _ in range(6):   # hasta 5 rondas para limpiar dependencias en cascada
            ids_sobrantes = list(
                ObjectDB.objects.filter(db_location__id=2)
                .exclude(db_typeclass_path__icontains="character")
                .exclude(id=2)
                .values_list("id", flat=True)
            )
            if not ids_sobrantes:
                break
            ObjectDB.objects.filter(id__in=ids_sobrantes).delete()

        # Restaurar Limbo al estado original
        limbo.key = "Limbo"
        limbo.db.desc = (
            "La sala de inicio vacía. Usa |w@construir_mundo|n para construir el mundo."
        )

        caller.msg(
            f"|gLimpieza completada.|n\n"
            f"  Salas borradas  : {borradas}\n"
            f"  Salidas borradas: {salidas_borradas}\n"
            f"Solo queda #2 (Limbo). Usa |w@construir_mundo|n para construir el mundo."
        )


def _room_exists(name):
    """Devuelve True si ya existe una Room con ese nombre en la BD."""
    from evennia.objects.models import ObjectDB
    return ObjectDB.objects.filter(
        db_key=name,
        db_typeclass_path__contains="rooms.Room",
    ).exists()


class CmdConstruirMundo(default_cmds.MuxCommand):
    """
    Construye el mundo base (Ciudad, Bosque, Calabozo) y las zonas de expansión.

    Uso:
      @construir_mundo

    Solo actúa si la Plaza de la Ciudad no existe todavía.
    Es seguro: no crea duplicados.
    Para las zonas de expansión usa @expandir.
    """
    key = "@construir_mundo"
    aliases = ["@buildworld"]
    locks = "cmd:perm(Builder)"
    help_category = "Builder"

    def func(self):
        caller = self.caller
        if _room_exists("Plaza de la Ciudad"):
            caller.msg(
                "|yEl mundo base ya existe (Plaza de la Ciudad encontrada).|n\n"
                "Para añadir las zonas de expansión usa |w@expandir|n."
            )
            return
        caller.msg("Construyendo el mundo...")
        try:
            from server.conf.at_initial_setup import at_initial_setup
            at_initial_setup()
            caller.msg("|gMundo construido correctamente.|n")
        except Exception as err:
            caller.msg(f"|rError al construir el mundo: {err}|n")
            from evennia.utils import logger
            logger.log_trace()


class CmdExpandir(default_cmds.MuxCommand):
    """
    Construye las zonas de expansión del mundo.

    Uso:
      @expandir

    Añade el Pantano del Troll (norte de la Cueva Oscura) y las
    Catacumbas (bajo la Celda Abandonada) si aún no existen.
    Es seguro ejecutarlo varias veces: omite lo que ya está construido.
    """
    key = "@expandir"
    aliases = ["@expand"]
    locks = "cmd:perm(Builder)"
    help_category = "Builder"

    def func(self):
        from world.build_expansion import construir_expansion
        self.caller.msg("Construyendo zonas de expansión...")
        construir_expansion(self.caller)


class BuilderCmdSet(CmdSet):
    """
    Cmdset adicional que solo se aplica a personajes controlados por Accounts con perm Builder.
    """
    key = "BuilderCmdSet"
    priority = 1
    mergetype = "Union"   # suma comandos sin pisar los básicos

    def at_cmdset_creation(self):
        self.add(CmdDoor())
        self.add(CmdKeyMake())
        self.add(CmdLimpiarMundo())
        self.add(CmdConstruirMundo())
        self.add(CmdExpandir())
        self.add(SpawnCmdSet)