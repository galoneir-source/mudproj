# features/doors/builder.py
import ast
from evennia import create_object, default_cmds
from evennia.utils.utils import inherits_from
from evennia.utils.search import search_object

from .typeclasses import DoorExit


class CmdDoor(default_cmds.MuxCommand):
    """
    @door[/open][/locked][/key:<id>] <dir> = <destino> ; <dir_vuelta>

    Ejemplos:
      @door north = Cocina ; south
      @door/open east = Taller ; west
      @door/locked/key:cobre_123 down = Sótano ; up
    """
    key = "@door"
    locks = "cmd:perm(Builder)"
    help_category = "Builder"

    def parse(self):

        try:
            super().parse()
        except Exception:
            self.switches = []
            self.lhs = ""
            self.rhs = ""
            self.args = getattr(self, "args", "")
            self.key_id = None
            return
        raw_switches = getattr(self, "switches", None) or []
        self.switches = [str(s).lower() for s in raw_switches]

        self.key_id = None
        for sw in self.switches:
            if sw.startswith("key:"):
                self.key_id = sw.split("key:", 1)[1].strip() or None
                break
        # Nota: NO soportamos /key <id> porque MuxCommand ya parseó lhs/rhs.
        # Se debe usar siempre /key:<id>.
    # ---------------------------
    # Helpers
    # ---------------------------
    def _exit_name_conflicts(self, location, name: str):
        if not location or not name:
            return False
        target = name.strip().lower()
        for ex in getattr(location, "exits", []) or []:
            if not ex:
                continue
            if (ex.key or "").strip().lower() == target:
                return True
            try:
                aliases = [a.strip().lower() for a in (ex.aliases.all() or [])]
            except Exception:
                aliases = []
            if target in aliases:
                return True
        return False

    def _resolve_destination_room(self, caller, destname: str):
        """
        Resuelve el destino como Room.
        - Acepta #dbref.
        - Si hay 0 rooms -> None (y msg).
        - Si hay >1 -> None (y lista opciones).
        """
        destname = (destname or "").strip()
        if not destname:
            caller.msg("El destino no puede estar vacío.")
            return None
        exact = False
        if destname.startswith("#"):
            exact = True
        found = search_object(destname, exact=exact) or []
        rooms = [o for o in found if o and inherits_from(o, "evennia.objects.objects.DefaultRoom")]
        if not rooms:
            caller.msg(f"No encuentro una room destino para '{destname}'. (Tip: usa un #dbref si hay duda.)")
            return None
        if len(rooms) > 1:
            # Lista de opciones (limitada para no spamear)
            lines = ["Destino ambiguo. He encontrado varias rooms:"]
            for r in rooms[:10]:
                lines.append(f"  - {r.key} (#{r.id})")
            if len(rooms) > 10:
                lines.append(f"  ... y {len(rooms) - 10} más.")
            lines.append("Usa un #dbref para concretar. Ej: @door north = #123 ; south")
            caller.msg("\n".join(lines))
            return None
        return rooms[0]

    def func(self):
        caller = self.caller
        room = caller.location

        lhs = (getattr(self, "lhs", "") or "").strip()
        rhs = (getattr(self, "rhs", "") or "").strip()
        key_id = getattr(self, "key_id", None)
        if not lhs or not rhs:
            caller.msg("Uso: @door[/open][/locked][/key:<id>] <dir> = <destino> ; <dir_vuelta>")
            return

        # Detectar uso erróneo de /key (sin :)
        if "key" in (getattr(self, "switches", []) or []) and not key_id:
            caller.msg("Uso de llave: /key:<id>. Ej: @door/locked/key:cobre_123 north = Cocina ; south")
            return

        dir_out = lhs
        if ";" not in rhs:
            caller.msg("Falta '; <dir_vuelta>'. Ej: @door north = Cocina ; south")
            return

        destname, dir_back = [p.strip() for p in rhs.split(";", 1)]
        if not destname or not dir_back:
            caller.msg("Destino y dir_vuelta no pueden estar vacíos.")
            return

        # Resolver destino (solo Rooms, y mejor manejo de ambigüedad)
        dest = self._resolve_destination_room(caller, destname)
        if not dest:
            return

        # Validación: evitar colisiones de exits
        if self._exit_name_conflicts(room, dir_out):
            caller.msg(f"Ya existe un exit en {room.key} con nombre/alias '{dir_out}'. Elige otro dir.")
            return
        if self._exit_name_conflicts(dest, dir_back):
            caller.msg(f"Ya existe un exit en {dest.key} con nombre/alias '{dir_back}'. Elige otro dir_vuelta.")
            return

        start_open = "open" in self.switches
        start_locked = "locked" in self.switches
        if start_locked and start_open:
            caller.msg("No puedes crear una puerta /open y /locked a la vez.")
            return

        exit_out = create_object(DoorExit, key=dir_out, location=room, destination=dest)
        exit_back = create_object(DoorExit, key=dir_back, location=dest, destination=room)

        for ex in (exit_out, exit_back):
            ex.db.door = True
            ex.db.is_open = bool(start_open)
            ex.db.is_locked = bool(start_locked)
            ex.db.key_id = key_id
            if "puerta" not in ex.aliases.all():
                ex.aliases.add("puerta")

        exit_out.db.paired_exit = exit_back
        exit_back.db.paired_exit = exit_out

        caller.msg(
            f"Puerta creada: {room.key} --({dir_out})--> {dest.key} "
            f"y vuelta --({dir_back})--> {room.key}. "
            f"Estado: {'abierta' if start_open else 'cerrada'}"
            f"{' y bloqueada' if start_locked else ''}"
            f"{f' (key_id={key_id})' if key_id else ''}."
        )


class CmdKeyMake(default_cmds.MuxCommand):
    """
    Crea llaves (typeclasses.objects.Key) en tu inventario.

    Uso:
      @keymake <nombre> = <keycode>
      @keymake/list <nombre> = ["code-1","code-2"]
      @keymake/prefix <nombre> = ["zona-","ciudad-"]
      @keymake/master <nombre>
      @keymake/full <nombre> = {"keycode":"x","keycodes":[...],"prefixes":[...],"master":false}

    Ejemplos:
      @keymake Llave_Bronce = bronce-01
      @keymake/list Llave_Lista = ["ciudad-01","ciudad-03"]
      @keymake/prefix Llave_Zonas = ["ciudad-","base-"]
      @keymake/master Llave_Master
      @keymake/full Llave_Mixta = {"keycode":"bronce-01","keycodes":["ciudad-03"],"prefixes":["mina-"],"master":false}
    """
    key = "@keymake"
    locks = "cmd:perm(Builder) or perm(Admin)"
    help_category = "Builder"
    switch_options = ("list", "prefix", "master", "full")

    def func(self):
        caller = self.caller
        switches = set(self.switches or [])
        name = (self.lhs or "").strip()
        rhs = (self.rhs or "").strip()

        if not name:
            caller.msg(
                "Uso:\n"
                "  @keymake <nombre> = <keycode>\n"
                "  @keymake/list <nombre> = [\"a\",\"b\"]\n"
                "  @keymake/prefix <nombre> = [\"zona-\",\"ciudad-\"]\n"
                "  @keymake/master <nombre>\n"
                "  @keymake/full <nombre> = {\"keycode\":\"x\",\"keycodes\":[...],\"prefixes\":[...],\"master\":false}"
            )
            return

        keyobj = create_object("typeclasses.objects.Key", key=name, location=caller)

        def abort(msg):
            keyobj.delete()
            caller.msg(msg)

        if "master" in switches:
            keyobj.db.is_master = True
            caller.msg(f"Creada llave maestra total: {keyobj.key}")
            return

        if "full" in switches:
            if not rhs:
                abort("Uso: @keymake/full <nombre> = {\"keycode\":\"x\",\"keycodes\":[...],\"prefixes\":[...],\"master\":false}")
                return
            try:
                data = ast.literal_eval(rhs)
                if not isinstance(data, dict):
                    raise ValueError
            except Exception:
                abort("Formato inválido. Usa un diccionario Python.")
                return
            keycode = data.get("keycode")
            keycodes = data.get("keycodes")
            prefixes = data.get("prefixes", data.get("keyprefixes"))
            master = data.get("master", False)
            if keycode:
                keyobj.db.keycode = keycode
            if keycodes is not None:
                keyobj.db.keycodes = list(keycodes)
            if prefixes is not None:
                keyobj.db.keyprefixes = list(prefixes)
            keyobj.db.is_master = bool(master)
            caller.msg(
                f"Creada llave mixta: {keyobj.key} "
                f"(master={keyobj.db.is_master}, keycode={keyobj.db.keycode}, "
                f"keycodes={keyobj.db.keycodes}, prefixes={keyobj.db.keyprefixes})"
            )
            return

        if "list" in switches or "prefix" in switches:
            if not rhs:
                abort("Debes dar una lista, ej: [\"a\",\"b\"]")
                return
            try:
                value = ast.literal_eval(rhs)
                if not isinstance(value, (list, tuple)) or not all(isinstance(x, str) for x in value):
                    raise ValueError
                value = list(value)
            except Exception:
                abort("Formato inválido. Usa una lista de strings.")
                return
            if "list" in switches:
                keyobj.db.keycodes = value
                caller.msg(f"Creada llave (lista): {keyobj.key} -> {value}")
            else:
                keyobj.db.keyprefixes = value
                caller.msg(f"Creada llave (prefijos): {keyobj.key} -> {value}")
            return

        # Modo normal: keycode exacto
        if not rhs:
            abort("Uso: @keymake <nombre> = <keycode>")
            return
        keyobj.db.keycode = rhs
        caller.msg(f"Creada llave: {keyobj.key} (keycode={rhs})")
