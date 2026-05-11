"""
features/spawn/manager.py

Funciones de spawneo y repoblación de zonas del mundo.
Integra systems/spawn/tables.py con Evennia.
"""
from evennia.utils import logger


def spawn_npc(prototipo_key: str, sala, oculto: bool = False,
              nivel_sigilo: int = 15, key_npc: str = None,
              patrol_sala_key: str = None):
    """
    Crea un NPC desde prototipo y lo coloca en sala.

    Parámetros opcionales:
      oculto         — el NPC no es visible sin percepción
      nivel_sigilo   — umbral de percepción para detectarlo
      key_npc        — nombre personalizado (sobreescribe el del prototipo)
      patrol_sala_key — nombre de la sala destino de patrulla (busca por key)

    Devuelve el NPC creado o None si falla.
    """
    try:
        from evennia.prototypes import spawner
        npc = spawner.spawn(prototipo_key)[0]
        npc.location = sala

        if key_npc:
            npc.key = key_npc

        if oculto:
            npc.db.oculto = True
            npc.db.nivel_sigilo = nivel_sigilo

        if patrol_sala_key:
            import evennia
            destinos = evennia.search_object(
                patrol_sala_key, typeclass="typeclasses.rooms.Room"
            )
            if destinos:
                npc.db.patrol_rooms = [sala.dbref, destinos[0].dbref]
                npc._iniciar_patrulla()

        return npc
    except Exception as err:
        logger.log_err(
            f"spawn_npc: error spawning '{prototipo_key}' en '{sala}': {err}"
        )
        return None


def _contar_npcs_por_prototipo(sala) -> dict[str, int]:
    """Cuenta los NPCs presentes en sala agrupados por db.npc_prototipo."""
    conteo: dict[str, int] = {}
    for obj in sala.contents:
        proto = getattr(obj.db, "npc_prototipo", None)
        if proto:
            conteo[proto] = conteo.get(proto, 0) + 1
    return conteo


def repoblar_sala(sala) -> list:
    """
    Repuebla la sala basándose en ZONAS[sala.db.zona].
    Solo crea los NPCs que faltan; no elimina ni duplica los existentes.
    Devuelve la lista de NPCs creados.
    """
    from systems.spawn.tables import ZONAS, calcular_faltantes

    zona_id = getattr(sala.db, "zona", None)
    if not zona_id or zona_id not in ZONAS:
        return []

    presentes = _contar_npcs_por_prototipo(sala)
    faltantes = calcular_faltantes(zona_id, presentes)
    if not faltantes:
        return []

    creados = []
    for prototipo, cantidad in faltantes.items():
        for _ in range(cantidad):
            npc = spawn_npc(prototipo, sala)
            if npc:
                creados.append(npc)

    return creados


def repoblar_mundo() -> int:
    """
    Repuebla todas las salas del mundo que tengan sala.db.zona configurada.
    Devuelve el total de NPCs creados.
    """
    from systems.spawn.tables import ZONAS
    from evennia.objects.models import ObjectDB

    total = 0
    salas = ObjectDB.objects.filter(db_typeclass_path__contains="rooms.Room")
    for sala in salas:
        zona = getattr(sala.db, "zona", None)
        if not zona or zona not in ZONAS:
            continue
        creados = repoblar_sala(sala)
        if creados:
            total += len(creados)
            logger.log_info(
                f"repoblar_mundo: {len(creados)} NPCs creados en '{sala.key}'."
            )
    return total
