"""
features/quests/hooks.py

Funciones de integración entre el sistema de quests y el resto del juego.
Se llaman desde el CombatHandler y otros sistemas de Evennia.
"""
from systems.quests.quests import QUESTS, registrar_kill, kills_actuales


def on_npc_muerte(asesino, npc):
    """
    Llamado desde CombatHandler._procesar_muerte cuando muere un NPC.
    Actualiza el progreso de kill quests del asesino y notifica completadas.
    """
    if not asesino or not getattr(asesino, "has_account", False):
        return

    quests = dict(getattr(asesino.db, "quests", {}) or {})
    if not quests:
        return

    npc_key_lower = npc.key.lower()
    modificado = False

    for quest_id, datos in list(quests.items()):
        if datos.get("estado") != "activa":
            continue
        quest = QUESTS.get(quest_id)
        if not quest or quest["tipo"] != "kill":
            continue
        target = quest["objetivo"]["target"].lower()
        if target not in npc_key_lower:
            continue

        quests = registrar_kill(quest_id, quests)
        modificado = True

        kills = kills_actuales(quest_id, quests)
        total = quest["objetivo"]["cantidad"]
        nuevo_estado = quests[quest_id].get("estado")

        if nuevo_estado == "completada":
            asesino.msg(
                f"|g¡Misión completada!|n |c{quest['titulo']}|n\n"
                f"  Usa |wentregar {quest['titulo']}|n para reclamar tu recompensa."
            )
        else:
            asesino.msg(
                f"|y[Misión]|n {quest['titulo']}: "
                f"{kills}/{total} {quest['objetivo']['target']}."
            )

    if modificado:
        asesino.db.quests = quests
