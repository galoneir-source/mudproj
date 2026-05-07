import re
from evennia.utils.utils import inherits_from
from .typeclasses import DoorExit


def _safe_aliases(obj):
    try:
        return [a.lower() for a in (obj.aliases.all() or [])]
    except Exception:
        return []


def list_doors_in_room(room):
    """
    Devuelve una lista de exits que son puertas en una room.
    Se consideran puertas si:
      - ex.db.door == True, o
      - inherits_from(ex, DoorExit)
    """
    if not room:
        return []
    exits = list(getattr(room, "exits", []) or [])
    doors = [
        ex for ex in exits
        if ex and (getattr(ex.db, "door", False) or inherits_from(ex, DoorExit))
    ]
    return doors


def find_door_exit(room, name):
    """
    Busca una puerta (DoorExit) en la sala por key o alias.
    Devuelve la exit o None.
    """
    if not room:
        return None
    if not name:
        return None
    needle = name.strip().lower()
    for ex in list_doors_in_room(room):
        if needle == (ex.key or "").strip().lower():
            return ex
        if needle in _safe_aliases(ex):
            return ex
    return None


def find_door_exit_in_room(caller, name: str | None):
    """
    Resolver "la puerta objetivo" en la room del caller.
    Reglas:
      - Si no hay name:
          - si hay 1 puerta -> esa
          - si hay >1 -> error con listado
      - Si hay name:
          - permite "puerta 2", "2", "#2" para escoger por índice (1-based)
          - si no es índice, busca por key/alias
    Devuelve: (door, errstr|None)
    """
    room = getattr(caller, "location", None)
    if not room:
        return None, "No estás en ningún lugar válido."

    doors = list_doors_in_room(room)
    if not doors:
        return None, "Aquí no veo ninguna puerta."

    raw = (name or "").strip()
    if not raw:
        if len(doors) == 1:
            return doors[0], None
        listado = ", ".join(f"{i+1}:{d.key}" for i, d in enumerate(doors))
        return None, (
            "Hay varias puertas aquí. Especifica cuál (ej: abrir norte, abrir puerta 2). "
            f"Puertas: {listado}"
        )

    n = raw.lower()

    # Selección por índice: "puerta 2", "2", "#2"
    m = re.match(r"^(?:puerta\s*)?#?(\d+)$", n)
    if m:
        idx = int(m.group(1))
        if 1 <= idx <= len(doors):
            return doors[idx - 1], None
        return None, f"Número de puerta fuera de rango. Hay {len(doors)} puerta(s) aquí."

    # Búsqueda por key/alias
    matches = []
    for d in doors:
        key = (d.key or "").lower()
        aliases = _safe_aliases(d)
        if n == key or n in aliases:
            matches.append(d)

    if not matches:
        # Match por prefijo si es único (ej: "nor" -> "norte")
        prefix = n
        prefix_matches = []
        for d in doors:
            key = (d.key or "").lower()
            aliases = _safe_aliases(d)
            if key.startswith(prefix) or any(a.startswith(prefix) for a in aliases):
                prefix_matches.append(d)
        if len(prefix_matches) == 1:
            return prefix_matches[0], None
        if len(prefix_matches) > 1:
            return None, f"'{raw}' coincide con varias puertas: " + ", ".join(d.key for d in prefix_matches)

        return None, f"No encuentro la puerta '{raw}'. Puertas: " + ", ".join(d.key for d in doors)

    if len(matches) > 1:
        return None, f"'{raw}' coincide con varias puertas: " + ", ".join(d.key for d in matches)
    return matches[0], None
