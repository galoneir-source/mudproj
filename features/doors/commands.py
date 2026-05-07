# mygame/features/doors/commands.py
from evennia import Command
from .utils import find_door_exit_in_room


class CmdOpenDoor(Command):
    key = "abrir"
    aliases = ["open"]
    locks = "cmd:all()"
    help_category = "Doors"

    def func(self):
        door, err = find_door_exit_in_room(self.caller, self.args)
        if err:
            self.caller.msg(err); return
        ok, msg = door.open(self.caller)
        self.caller.msg(msg)


class CmdCloseDoor(Command):
    key = "cerrar"
    aliases = ["close"]
    locks = "cmd:all()"
    help_category = "Doors"

    def func(self):
        door, err = find_door_exit_in_room(self.caller, self.args)
        if err:
            self.caller.msg(err); return
        ok, msg = door.close()
        self.caller.msg(msg)


class CmdLockDoor(Command):
    key = "bloquear"
    aliases = ["lock"]
    locks = "cmd:all()"
    help_category = "Doors"

    def func(self):
        door, err = find_door_exit_in_room(self.caller, self.args)
        if err:
            self.caller.msg(err); return
        ok, msg = door.lock(self.caller)
        self.caller.msg(msg)


class CmdUnlockDoor(Command):
    key = "desbloquear"
    aliases = ["unlock"]
    locks = "cmd:all()"
    help_category = "Doors"

    def func(self):
        door, err = find_door_exit_in_room(self.caller, self.args)
        if err:
            self.caller.msg(err); return
        ok, msg = door.unlock(self.caller)
        self.caller.msg(msg)
class CmdDoorStatus(Command):
    """
    Ver estado de una puerta.

    Uso:
      estadopuerta [<puerta|dirección>]
      estado puerta
      estado norte
    Alias:
      estadopuerta, doorstatus
    """
    key = "estadopuerta"
    aliases = ["doorstatus"]
    locks = "cmd:all()"
    help_category = "Doors"

    def func(self):
        caller = self.caller
        target = self.args.strip() if self.args else ""

        door, err = find_door_exit_in_room(caller, target or None)
        if err:
            caller.msg(err)
            return

        is_open = bool(getattr(door.db, "is_open", True))
        is_locked = bool(getattr(door.db, "is_locked", False))
        key_id = getattr(door.db, "key_id", None)

        # Destino (si existe)
        dest = getattr(door, "destination", None)
        dest_name = dest.key if dest else "¿(sin destino?)"

        # Estado textual
        estado_apertura = "abierta" if is_open else "cerrada"
        estado_cerrojo = "bloqueada" if is_locked else "desbloqueada"
        req_llave = f"requiere llave ({key_id})" if key_id else "no requiere llave"

        caller.msg(
            f"|wPuerta:|n {door.key}\n"
            f"|wDestino:|n {dest_name}\n"
            f"|wEstado:|n {estado_apertura}, {estado_cerrojo} — {req_llave}"
        )
