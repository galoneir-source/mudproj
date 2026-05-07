"""
features/combat/patrol.py

Script de patrulla para NPCs.
Mueve al NPC por sus patrol_rooms cada cierto tiempo.
"""
from evennia import DefaultScript
import random


class PatrolScript(DefaultScript):
    """
    Hace que un NPC se mueva entre sus salas de patrulla.
    Se añade automáticamente si el NPC tiene patrol_rooms definido.
    """

    def at_script_creation(self):
        self.key = "patrol_script"
        self.desc = "Script de patrulla de NPC"
        self.interval = 30       # segundos entre movimientos
        self.persistent = True
        self.db.patrol_index = 0

    def at_repeat(self):
        npc = self.obj
        if not npc:
            self.delete()
            return

        # No patrullar si está en combate.
        # Si en_combate está activo pero no existe ningún CombatHandler vivo
        # en la sala (p. ej. el servidor se cayó durante un combate), lo
        # reseteamos para evitar que el NPC quede bloqueado indefinidamente.
        if getattr(npc.db, "en_combate", False):
            handler_activo = any(
                s.key == "combat_handler" and getattr(s.db, "activo", False)
                for s in (npc.location.scripts.all() if npc.location else [])
            )
            if not handler_activo:
                npc.db.en_combate = False
                npc.db.enraged = False
            else:
                return

        patrol_rooms = getattr(npc.db, "patrol_rooms", []) or []
        if not patrol_rooms:
            return

        idx = self.db.patrol_index or 0
        destino_ref = patrol_rooms[idx % len(patrol_rooms)]

        # Buscar sala destino
        from evennia import search_object
        resultados = search_object(destino_ref)
        if not resultados:
            return

        destino = resultados[0]
        if destino == npc.location:
            # Ya estamos aquí, avanzar al siguiente índice y esperar el próximo tick
            self.db.patrol_index = (idx + 1) % len(patrol_rooms)
            return

        # Moverse silenciosamente (teletransporte entre salas, no hay exit real)
        npc.move_to(destino, quiet=True)
        if not getattr(npc.db, "oculto", False):
            npc.location.msg_contents(f"{npc.key} aparece en la sala.")
        self.db.patrol_index = (idx + 1) % len(patrol_rooms)
