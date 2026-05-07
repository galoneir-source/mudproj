# features/doors/typeclasses.py
from evennia import DefaultExit
from evennia.utils.utils import inherits_from

def _find_key_by_id(carrier, key_id: str):
    """
    Devuelve True si el objeto 'carrier' lleva un objeto con db.key_id == key_id
    (o Attribute 'key_id' == key_id). Soporta ambos estilos.

    Si key_id es None o cadena vacía se considera "sin llave requerida" y
    devuelve True directamente — la distinción entre None y "" queda aquí,
    no dispersa por lock()/unlock().
    """
    if not key_id or not str(key_id).strip():
        return True
    for obj in carrier.contents:
        # --- Estilo A: key_id (actual de DoorExit) ---
        if getattr(obj.db, "key_id", None) == key_id:
            return True
        if obj.attributes.get("key_id", default=None) == key_id:
            return True

        # --- Estilo B: llaves "Key" (typeclasses/objects.py) ---
        # master abre todo
        if bool(getattr(obj.db, "is_master", False)):
            return True

        required = str(key_id).strip()
        if not required:
            return True

        # keycode exacto
        keycode = getattr(obj.db, "keycode", None)
        if keycode and str(keycode) == required:
            return True

        # lista de códigos
        keycodes = getattr(obj.db, "keycodes", None) or []
        if required in [str(k) for k in keycodes]:
            return True

        # prefijos
        prefixes = getattr(obj.db, "keyprefixes", None) or []
        for p in prefixes:
            if p and required.startswith(str(p)):
                return True
    return False


class DoorExit(DefaultExit):
    """
    Un Exit que actúa como puerta (abierta/cerrada + bloqueada/desbloqueada).
    Sincroniza estado con el Exit emparejado si existe.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.door = True
        self.db.is_open = False
        self.db.is_locked = False
        self.db.key_id = None         # string opcional
        self.db.paired_exit = None    # referencia a otro Exit (ida/vuelta)

        # nombres "puerta" como alias útil por defecto
        if "puerta" not in self.aliases.all():
            self.aliases.add("puerta")

    # ---------- helpers ----------
    def is_door(self) -> bool:
        return bool(self.db.door)

    def paired(self):
        pe = self.db.paired_exit
        # por si se guardó un dbref como string
        try:
            if isinstance(pe, str) and pe.startswith("#"):
                from evennia import search_object
                found = search_object(pe)
                return found[0] if found else None
        except Exception:
            return None
        return pe

    def _sync_to_pair(self):
        """
        Sincroniza el estado con la puerta emparejada (si existe).
        - Evita reventar si el paired ya no existe.
        - Fuerza que el par se marque como puerta.
        - Mantiene el enlace bidireccional si se ha perdido.
        """
        pair = self.paired()
        if not pair:
            return
        # si el par no es una puerta compatible, no tocamos nada
        if not (getattr(pair.db, "door", False) or inherits_from(pair, DoorExit)):
            return

        # mantener enlace ida/vuelta (si alguien rompió el atributo)
        try:
            if getattr(pair.db, "paired_exit", None) is None:
                pair.db.paired_exit = self
        except Exception:
            return

        pair.db.door = True
        pair.db.is_open = bool(self.db.is_open)
        pair.db.is_locked = bool(self.db.is_locked)
        pair.db.key_id = self.db.key_id

    def open(self, caller=None):
        if self.db.is_locked:
            key_id = getattr(self.db, "key_id", None)
            return False, f"Está bloqueada con llave{(' (' + str(key_id) + ')') if key_id else ''}."
        if self.db.is_open:
            return False, "Ya está abierta."
        self.db.is_open = True
        self._sync_to_pair()
        return True, "Abres la puerta."

    def close(self):
        if not self.db.is_open:
            return False, "Ya está cerrada."
        self.db.is_open = False
        self._sync_to_pair()
        return True, "Cierras la puerta."

    def lock(self, caller):
        if self.db.is_locked:
            return False, "Ya está bloqueada."
        if self.db.is_open:
            return False, "Ciérrala antes de bloquearla."
        # Normalizar: tratar "" igual que None (sin llave configurada)
        key_id = self.db.key_id or None
        # si hay key_id: exige llave; si no hay: permite solo builder
        if key_id:
            if not _find_key_by_id(caller, key_id):
                return False, f"No tienes la llave adecuada{(' (' + str(key_id) + ')') if key_id else ''}."
        else:
            if not caller.check_permstring("Builder"):
                return False, "No tienes permiso para bloquear esta puerta sin llave."
        self.db.is_locked = True
        self._sync_to_pair()
        return True, "Bloqueas la puerta."

    def unlock(self, caller):
        if not self.db.is_locked:
            return False, "No está bloqueada."
        # Normalizar: tratar "" igual que None (sin llave configurada)
        key_id = self.db.key_id or None
        if key_id:
            if not _find_key_by_id(caller, key_id):
                return False, f"No tienes la llave adecuada{(' (' + str(key_id) + ')') if key_id else ''}."
        else:
            if not caller.check_permstring("Builder"):
                return False, "No tienes permiso para desbloquear esta puerta sin llave."
        self.db.is_locked = False
        self._sync_to_pair()
        return True, "Desbloqueas la puerta."

    # ---------- movimiento ----------
    def at_traverse(self, traversing_object, target_location, **kwargs):
        if self.is_door():
            if self.db.is_locked:
                key_id = getattr(self.db, "key_id", None)
                traversing_object.msg("La puerta está cerrada con llave" + (f" ({key_id})" if key_id else "") + ".")
                return
            if not self.db.is_open:
                traversing_object.msg("La puerta está cerrada.")
                return
        return super().at_traverse(traversing_object, target_location, **kwargs)

    def at_object_delete(self):
        """
        Si se elimina esta puerta, limpia el enlace en la puerta emparejada.
        Opcional: borrar también la puerta emparejada para evitar "media puerta".
        """
        paired = self.paired()
        if not paired:
            return
        try:
            if paired.db.paired_exit == self:
                paired.db.paired_exit = None
        except Exception:
            return
