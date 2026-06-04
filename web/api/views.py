"""
web/api/views.py

API REST del juego. Devuelve JSON puro usando Django JsonResponse.

Endpoints públicos (no requieren autenticación):
  GET /api/status/   — estado del servidor
  GET /api/who/      — jugadores conectados

Endpoints protegidos (requieren Account con perm Builder o superior):
  GET /api/rooms/           — lista de todas las salas
  GET /api/rooms/<dbref>/   — detalle de una sala
"""

import time
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
from evennia.utils.utils import inherits_from


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _error(msg: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": msg}, status=status)


def _require_builder(request) -> bool:
    """
    Devuelve True si el usuario Django autenticado tiene perm Builder o Admin.
    """
    if not request.user or not request.user.is_authenticated:
        return False
    try:
        account = request.user.db_object
        return account.check_permstring("Builder") or account.check_permstring("Admin")
    except Exception:
        return False


def _is_character_object(obj) -> bool:
    """True for player characters and NPCs, False for regular objects/exits."""
    return inherits_from(obj, "evennia.objects.objects.DefaultCharacter")


def _uptime_str() -> str:
    """Devuelve el uptime del proceso como string legible."""
    try:
        import evennia
        started = evennia.SERVER_SESSION_HANDLER.server.start_time
        delta = int(time.time() - started)
        h, m = divmod(delta // 60, 60)
        s = delta % 60
        if h:
            return f"{h}h {m}m {s}s"
        return f"{m}m {s}s"
    except Exception:
        return "desconocido"


# --------------------------------------------------------------------------- #
#  GET /api/status/
# --------------------------------------------------------------------------- #

@require_GET
def api_status(request):
    """
    Estado general del servidor.

    Respuesta:
      {
        "server": "mygame",
        "online": 2,
        "uptime": "1h 23m 5s",
        "version": "4.x.x"
      }
    """
    try:
        import evennia
        from evennia.utils import get_evennia_version
        session_handler = evennia.SERVER_SESSION_HANDLER
        online = len([s for s in session_handler.values() if s.logged_in])
        version = get_evennia_version("short")
    except Exception:
        online = 0
        version = "?"

    from django.conf import settings
    return JsonResponse({
        "server": getattr(settings, "SERVERNAME", "mygame"),
        "online": online,
        "uptime": _uptime_str(),
        "version": version,
    })


# --------------------------------------------------------------------------- #
#  GET /api/who/
# --------------------------------------------------------------------------- #

@require_GET
def api_who(request):
    """
    Lista de jugadores actualmente conectados.

    Respuesta:
      {
        "count": 2,
        "players": [
          {
            "name": "Aragorn",
            "location": "Plaza de la Ciudad",
            "location_dbref": "#2",
            "level": 5
          }
        ]
      }
    """
    try:
        import evennia
        sessions = [s for s in evennia.SERVER_SESSION_HANDLER.values() if s.logged_in]
    except Exception:
        sessions = []

    players = []
    seen = set()
    for session in sessions:
        try:
            char = session.get_puppet()
            if not char or char.id in seen:
                continue
            seen.add(char.id)
            loc = char.location
            players.append({
                "name": char.key,
                "location": loc.key if loc else None,
                "location_dbref": loc.dbref if loc else None,
                "level": getattr(char.db, "nivel", 1),
            })
        except Exception:
            continue

    return JsonResponse({"count": len(players), "players": players})


# --------------------------------------------------------------------------- #
#  GET /api/rooms/
# --------------------------------------------------------------------------- #

@require_GET
def api_rooms(request):
    """
    Lista de todas las salas del juego.
    Requiere autenticación con perm Builder o Admin.

    Respuesta:
      {
        "count": 9,
        "rooms": [
          {
            "dbref": "#2",
            "name": "Plaza de la Ciudad",
            "desc": "Una amplia plaza..."
          }
        ]
      }
    """
    if not _require_builder(request):
        return _error("Se requiere autenticación con perm Builder.", status=403)

    try:
        from evennia import ObjectDB
        rooms_qs = ObjectDB.objects.filter(
            db_typeclass_path__contains="rooms.Room"
        ).order_by("id")
    except Exception as e:
        return _error(f"Error consultando base de datos: {e}", status=500)

    rooms = []
    for room in rooms_qs:
        desc = getattr(room.db, "desc", "") or ""
        rooms.append({
            "dbref": room.dbref,
            "name": room.key,
            "desc": desc[:120] + ("..." if len(desc) > 120 else ""),
        })

    return JsonResponse({"count": len(rooms), "rooms": rooms})


# --------------------------------------------------------------------------- #
#  GET /api/rooms/<dbref>/
# --------------------------------------------------------------------------- #

@require_GET
def api_room_detail(request, dbref: str):
    """
    Detalle de una sala: descripción, exits, personajes y objetos presentes.
    Requiere autenticación con perm Builder o Admin.

    Parámetro: dbref sin '#', ej: /api/rooms/2/

    Respuesta:
      {
        "dbref": "#2",
        "name": "Plaza de la Ciudad",
        "desc": "...",
        "exits": [
          {"name": "norte", "destination": "Bosque del Norte", "destination_dbref": "#5"}
        ],
        "characters": [
          {"name": "guardia de la ciudad", "dbref": "#12", "level": 5, "is_player": false}
        ],
        "objects": [
          {"name": "espada de hierro", "dbref": "#20"}
        ]
      }
    """
    if not _require_builder(request):
        return _error("Se requiere autenticación con perm Builder.", status=403)

    try:
        from evennia import ObjectDB
        room = ObjectDB.objects.get(id=int(dbref))
    except (ValueError, ObjectDB.DoesNotExist):
        return _error(f"Sala #{dbref} no encontrada.", status=404)
    except Exception as e:
        return _error(str(e), status=500)

    exits = []
    characters = []
    objects_list = []

    for obj in room.contents:
        # Exits
        if getattr(obj, "destination", None):
            dest = obj.destination
            exits.append({
                "name": obj.key,
                "destination": dest.key if dest else None,
                "destination_dbref": dest.dbref if dest else None,
            })
            continue

        # Personajes: jugadores y NPCs heredan de DefaultCharacter.
        if _is_character_object(obj):
            characters.append({
                "name": obj.key,
                "dbref": obj.dbref,
                "level": getattr(obj.db, "nivel", 1),
                "hp": getattr(obj.db, "hp", None),
                "hp_max": getattr(obj.db, "hp_max", None),
                "is_player": bool(obj.has_account),
            })
            continue

        # Objetos
        objects_list.append({
            "name": obj.key,
            "dbref": obj.dbref,
            "typeclass": obj.typeclass_path.split(".")[-1],
        })

    desc = getattr(room.db, "desc", "") or ""
    return JsonResponse({
        "dbref": room.dbref,
        "name": room.key,
        "desc": desc,
        "exits": exits,
        "characters": characters,
        "objects": objects_list,
    })
