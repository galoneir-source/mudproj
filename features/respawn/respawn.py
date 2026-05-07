"""
features/respawn/respawn.py

Sistema de reaparición de NPCs muertos.

Cuando un NPC muere en combate, se programa un RespawnScript en su sala.
Pasado el tiempo configurado (npc.db.respawn_tiempo, default 120s), el NPC
reaparece desde su prototipo original con todos los atributos restaurados.

El script preserva:
  - npc_prototipo  — clave del prototipo para recrear al NPC
  - patrol_rooms   — lista de salas de patrulla
  - oculto / nivel_sigilo — para NPCs con sigilo
"""

import time

from evennia import DefaultScript
from evennia.utils import logger


RESPAWN_DEFAULT = 120   # segundos si el NPC no tiene respawn_tiempo definido
RESPAWN_TICK = 10       # intervalo de comprobación en segundos


class RespawnScript(DefaultScript):
    """
    Script temporal que vive en una sala y recrea un NPC tras un delay.
    Se auto-elimina al completarse o si la sala desaparece.

    Usa un timestamp absoluto (db.respawn_at) en lugar de un contador
    decremental, de modo que el intervalo de tick puede ser holgado (10s)
    sin perder precisión en el momento de reaparición.
    """

    def at_script_creation(self):
        self.key = "respawn_script"
        self.desc = "Respawn de NPC pendiente"
        self.interval = RESPAWN_TICK
        self.persistent = True
        self.db.npc_prototipo = None
        self.db.sala_dbref = None
        self.db.respawn_at = time.time() + RESPAWN_DEFAULT  # timestamp absoluto
        self.db.patrol_rooms = []
        self.db.oculto = False
        self.db.nivel_sigilo = 15
        self.db.npc_key = None          # nombre del NPC (para el anuncio)

    def at_repeat(self):
        if time.time() >= (self.db.respawn_at or 0):
            self._respawnear()

    def _respawnear(self):
        """Crea el NPC en la sala y limpia el script."""
        prototipo = self.db.npc_prototipo
        if not prototipo:
            self.delete()
            return

        # Obtener la sala
        sala = self.obj
        if not sala:
            self.delete()
            return

        try:
            from evennia.prototypes import spawner
            npc = spawner.spawn(prototipo)[0]
            npc.location = sala

            # Restaurar nombre personalizado (ej: "goblin espía" en lugar de "goblin")
            npc_key = self.db.npc_key
            if npc_key and npc_key != npc.key:
                npc.key = npc_key

            # Restaurar atributos especiales
            patrol_rooms = self.db.patrol_rooms or []
            if patrol_rooms:
                npc.db.patrol_rooms = patrol_rooms
                npc._iniciar_patrulla()

            if self.db.oculto:
                npc.db.oculto = True
                npc.db.nivel_sigilo = self.db.nivel_sigilo or 15
            else:
                # Anunciar la reaparición solo si no está oculto
                sala.msg_contents(f"|y{npc.key} ha aparecido.|n")

        except Exception as err:
            logger.log_err(f"RespawnScript: error recreando '{prototipo}': {err}")

        self.delete()


def programar_respawn(sala, npc):
    """
    Registra un RespawnScript en la sala para recrear al NPC dado.

    Parámetros:
      sala — Room donde reaparecerá el NPC
      npc  — el NPC que acaba de morir (leemos sus atributos antes de delete)
    """
    prototipo = getattr(npc.db, "npc_prototipo", None)
    if not prototipo:
        return  # NPC sin prototipo → no reaparece

    tiempo = int(getattr(npc.db, "respawn_tiempo", RESPAWN_DEFAULT) or RESPAWN_DEFAULT)
    patrol_rooms = list(getattr(npc.db, "patrol_rooms", []) or [])
    oculto = bool(getattr(npc.db, "oculto", False))
    nivel_sigilo = int(getattr(npc.db, "nivel_sigilo", 15) or 15)

    script = sala.scripts.add(RespawnScript)
    script.db.npc_prototipo = prototipo
    script.db.sala_dbref = sala.dbref
    script.db.respawn_at = time.time() + tiempo
    script.db.patrol_rooms = patrol_rooms
    script.db.oculto = oculto
    script.db.nivel_sigilo = nivel_sigilo
    script.db.npc_key = npc.key

    minutos = tiempo // 60
    segundos = tiempo % 60
    tiempo_txt = f"{minutos}m {segundos}s" if minutos else f"{segundos}s"
    logger.log_info(f"Respawn programado: {npc.key} en {sala.key} en {tiempo_txt}.")
