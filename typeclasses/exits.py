"""
Exits

Exits are connectors between Rooms. An exit always has a destination property
set and has a single command defined on itself with the same name as its key,
for allowing Characters to traverse the exit to its destination.

"""

from evennia.objects.objects import DefaultExit
from evennia.utils.utils import inherits_from

from .objects import ObjectParent


class Exit(ObjectParent, DefaultExit):
    """
    Exits are connectors between rooms. Exits are normal Objects except
    they defines the `destination` property and overrides some hooks
    and methods to represent the exits.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects child classes like this.

    """

    pass

class SmartExit(DefaultExit):
    """
    Exit con estado locked y (opcionalmente) llave requerida.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.locked = False
        self.db.lock_msg = "Está cerrado."
        self.db.pass_msg = None

        # --- Sistema de llaves ---
        self.db.keycode_required = None      # ej: "bronce-01"
        self.db.need_key_msg = "Necesitas una llave."
        self.db.unlock_msg = "Abres con la llave."
        self.db.fail_key_msg = "Esa llave no sirve."

    def _has_required_key(self, character, required_code: str) -> bool:
        """
        Soporta el modelo de llaves Key (typeclasses/objects.py):
          - is_master
          - keycode / keycodes / keyprefixes
        """
        if not required_code:
            return True
        required = str(required_code).strip()
        if not required:
            return True
        for obj in character.contents:
            if bool(getattr(obj.db, "is_master", False)):
                return True
            keycode = getattr(obj.db, "keycode", None)
            if keycode and str(keycode) == required:
                return True
            keycodes = getattr(obj.db, "keycodes", None) or []
            if required in [str(k) for k in keycodes]:
                return True
            prefixes = getattr(obj.db, "keyprefixes", None) or []
            for p in prefixes:
                if p and required.startswith(str(p)):
                    return True
        return False

    def at_traverse(self, traversing_object, target_location, **kwargs):
        required = getattr(self.db, "keycode_required", None)

        # si está locked, solo se pasa si hay llave (cuando se exige)
        if self.db.locked:
            if required:
                if self._has_required_key(traversing_object, required):
                    traversing_object.msg(self.db.unlock_msg or "Abres con la llave.")
                else:
                    traversing_object.msg(self.db.fail_key_msg or "Esa llave no sirve.")
                    return
            else:
                traversing_object.msg(self.db.lock_msg or "No puedes pasar.")
                return

        if self.db.pass_msg:
            traversing_object.msg(self.db.pass_msg)

        super().at_traverse(traversing_object, target_location, **kwargs)
