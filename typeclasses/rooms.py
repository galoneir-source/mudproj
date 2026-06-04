"""
Room

Rooms are simple containers that has no location of their own.

"""

from evennia.objects.objects import DefaultRoom
from evennia.utils.utils import inherits_from

from .objects import ObjectParent


def _is_character_object(obj) -> bool:
    """True for player characters and NPCs, False for regular objects/exits."""
    return inherits_from(obj, "evennia.objects.objects.DefaultCharacter")


def _is_exit_object(obj) -> bool:
    """True for exits, including orphan exits without a destination."""
    return inherits_from(obj, "evennia.objects.objects.DefaultExit")


class Room(ObjectParent, DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects.
    """

    def at_object_receive(self, moved_obj, source_location, move_type="move", **kwargs):
        """
        Se llama cuando un objeto entra en esta sala.
        Notifica a los NPCs presentes para que reaccionen.
        """
        super().at_object_receive(moved_obj, source_location, move_type=move_type, **kwargs)
        # Notificar a NPCs en la sala que llegó alguien
        if not hasattr(moved_obj, "has_account") or not moved_obj.has_account:
            return
        from typeclasses.npc import NPC
        for obj in self.contents:
            if obj != moved_obj and isinstance(obj, NPC):
                obj.at_object_arrive(moved_obj, source_location)


    def return_appearance(self, looker, **kwargs):
        """Controla lo que se ve al hacer 'look' en la sala."""
        def format_exit(ex):
            name = ex.key

            is_door = bool(getattr(ex.db, "door", False))
            is_open = bool(getattr(ex.db, "is_open", True))
            is_locked = bool(getattr(ex.db, "is_locked", False))
            key_id = getattr(ex.db, "key_id", None)

            tags = []
            if is_door:
                if is_locked:
                    tags.append("cerrada con llave")
                elif not is_open:
                    tags.append("cerrada")

            # Mostrar key_id solo a Builder/Admin (para no spoilear)
            if key_id:
                can_see_code = looker.check_permstring("Builder") or looker.check_permstring("Admin")
                if can_see_code:
                    tags.append(f"llave: {key_id}")

            if tags:
                return f"{name} ({', '.join(tags)})"
            return name
        if not looker:
            return ""

        # --- Título ---
        title = f"|w{self.get_display_name(looker)}|n"

        # --- Descripción ---
        desc = self.db.desc or ""
        if desc:
            desc = f"\n{desc}"

        # --- Ambiente (ciclo día/noche) ---
        exterior = getattr(self.db, "exterior", True)
        hora_juego = None
        if exterior:
            try:
                from features.time.clock_script import hora_actual
                from systems.time.clock import texto_ambiente
                hora_juego = hora_actual()
                tipo = getattr(self.db, "tipo_ambiente", "exterior_natural")
                amb = texto_ambiente(hora_juego, tipo)
                if amb:
                    desc = desc + f"\n|x{amb}|n"
            except Exception:
                pass

        # --- Salidas ---
        exits = []
        for obj in self.contents:
            # Los exits suelen tener destination. Esto es robusto sin depender de typeclass concreto.
            if hasattr(obj, "destination") and obj.destination:
                exits.append(obj)

        # Clasificamos
        cardinal = {
            "n", "norte", "s", "sur", "e", "este", "o", "oeste",
            "north", "south", "east", "west",
            "u", "arriba", "d", "abajo", "up", "down",
            "b", "bajar", "su", "subir",
        }
        grid_exits = []
        named_exits = []

        for ex in exits:
            label = format_exit(ex)
            key = (ex.key or "").lower()
            if key in cardinal:
                grid_exits.append(label)
            else:
                named_exits.append(label)
        # --- Personajes y NPCs ---
        from systems.perception.perception_manager import PerceptionManager
        _pm = PerceptionManager()

        characters = []
        objects = []
        exit_set = set(exits)
        # IDs de todos los objetos con destination (exits, incluyendo huérfanos sin destination)
        all_exit_ids = {o.id for o in self.contents if _is_exit_object(o)}
        for obj in self.contents:
            if obj == looker or obj in exit_set:
                continue
            # Excluir exits huérfanos (tienen destination=None pero son exits)
            if obj.id in all_exit_ids:
                continue
            # Omitir entidades ocultas que el looker no puede detectar (con penaliz. nocturna)
            if not _pm.puede_detectar(looker, obj, hora=hora_juego):
                continue
            if _is_character_object(obj):
                # Es un personaje (jugador o NPC)
                hp = getattr(obj.db, "hp", None)
                hp_max = getattr(obj.db, "hp_max", None)
                nivel = getattr(obj.db, "nivel", None)
                if hp is not None and hp_max:
                    ratio = hp / max(hp_max, 1)
                    if ratio > 0.75:
                        estado = "|g●|n"
                    elif ratio > 0.50:
                        estado = "|y●|n"
                    elif ratio > 0.25:
                        estado = "|y◐|n"
                    else:
                        estado = "|r●|n"
                    nivel_txt = f" |w(Nv.{nivel})|n" if nivel else ""
                    characters.append(f"  {estado} {obj.get_display_name(looker)}{nivel_txt}")
                else:
                    characters.append(f"  |w{obj.get_display_name(looker)}|n")
            else:
                objects.append(f"  |y{obj.get_display_name(looker)}|n")

        parts = [title + desc]

        if grid_exits:
            parts.append("\n|cDirecciones|n: " + ", ".join(sorted(grid_exits, key=str.lower)))
        if named_exits:
            parts.append("\n|cSalidas|n: " + ", ".join(sorted(named_exits, key=str.lower)))
        if characters:
            parts.append("\n|cPersonajes|n:\n" + "\n".join(characters))
        if objects:
            parts.append("\n|cObjetos|n:\n" + "\n".join(objects))

        return "".join(parts)
