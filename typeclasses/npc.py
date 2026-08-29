"""
typeclasses/npc.py

Typeclass base para NPCs con IA reactiva compleja.
Los NPCs pueden:
  - Patrullar salas
  - Agredir jugadores si están en modo agresivo
  - Responder a ser atacados
  - Usar habilidades especiales
  - Tener distintos 'temperamentos': neutral, agresivo, cobarde, guardián
"""
from evennia.objects.objects import DefaultCharacter
from evennia.utils import logger
from systems.combat.engine import STAT_DEFAULTS


class NPC(DefaultCharacter):
    """
    NPC base con stats de combate e IA reactiva.

    Atributos importantes (db.*):
      temperamento : 'neutral' | 'agresivo' | 'cobarde' | 'guardian'
      habilidades  : lista de nombres de habilidades
      loot         : lista de dicts {typeclass, key, ...} para generar al morir
      faction      : string de facción (NPCs de la misma facción no se atacan)
      patrol_rooms : lista de #dbrefs de salas por las que patrulla
      dialogo      : dict {keyword: respuesta} para responder a 'decir'
      enraged      : True si está en modo furia
      nivel        : nivel de combate
    """

    def at_object_creation(self):
        super().at_object_creation()
        # --- Stats de combate ---
        for key, val in STAT_DEFAULTS.items():
            if getattr(self.db, key, None) is None:
                setattr(self.db, key, val)

        # --- Configuración de IA ---
        self.db.temperamento = "neutral"    # neutral | agresivo | cobarde | guardian
        self.db.habilidades = []
        self.db.loot = []
        self.db.faction = None   # para lógica guardian (NPCs de la misma faction no se atacan)
        self.db.faccion = None   # facción para el sistema de reputación
        self.db.patrol_rooms = []
        self.db.dialogo = {}
        self.db.enraged = False
        self.db.en_combate = False
        self.db.estados = {}

        # Script de patrulla (se añade si patrol_rooms no está vacío)
        # Se inicia manualmente o desde at_init

    def at_init(self):
        """Se llama al cargar el NPC desde BD. Inicia scripts si necesario."""
        super().at_init()
        if self.db.patrol_rooms:
            self._iniciar_patrulla()

    # ------------------------------------------------------------------ #
    #  Reacciones a eventos del mundo
    # ------------------------------------------------------------------ #

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """
        Este hook se llama cuando un objeto entra DENTRO de este NPC
        (lo cual normalmente no ocurre). No es útil aquí.
        La reacción a jugadores entrando en la sala se gestiona en at_post_move
        de los jugadores, o en el hook de la sala.
        Se deja para compatibilidad pero no hace nada.
        """
        super().at_object_receive(moved_obj, source_location, **kwargs)

    def at_object_arrive(self, moved_obj, source_location, **kwargs):
        """
        Evennia llama este hook en todos los objetos de la sala cuando algo llega.
        Aquí el NPC reacciona a jugadores que entran en su sala.
        """
        if not hasattr(moved_obj, "has_account"):
            return
        if not moved_obj.has_account:
            return
        self._reaccionar_a_presencia(moved_obj)

    def at_msg_receive(self, msg, from_obj=None, **kwargs):
        """Responder a mensajes de 'decir'."""
        result = super().at_msg_receive(msg, from_obj=from_obj, **kwargs)
        # Solo reaccionar a mensajes de jugadores reales para evitar
        # que spam de combate active palabras clave del diálogo
        if from_obj and isinstance(msg, str) and getattr(from_obj, "has_account", False):
            self._reaccionar_a_dialogo(msg, from_obj)
        return result

    # ------------------------------------------------------------------ #
    #  Lógica de IA
    # ------------------------------------------------------------------ #

    def _reaccionar_a_presencia(self, jugador):
        """
        Decide si agredir al jugador según el temperamento y la reputación.
        """
        temperamento = self.db.temperamento or "neutral"

        # Reputación: NPCs con faccion agred en si el jugador es Enemigo (rep < -3000),
        # independientemente del temperamento (excepto cobardes).
        if temperamento != "cobarde":
            faccion = getattr(self.db, "faccion", None)
            if faccion:
                from systems.reputation.engine import obtener_rep, es_enemigo
                rep = getattr(jugador.db, "reputacion", {}) or {}
                if es_enemigo(obtener_rep(rep, faccion)):
                    self._agredir(jugador)
                    return

        if temperamento == "agresivo":
            self._agredir(jugador)
        elif temperamento == "guardian":
            # Solo agrede si el jugador pertenece a una facción explícitamente distinta.
            # Un jugador sin facción (None) es un aventurero neutral y no se ataca.
            faction_jugador = getattr(jugador.db, "faction", None)
            mi_faction = self.db.faction
            if mi_faction and faction_jugador and faction_jugador != mi_faction:
                self._agredir(jugador)
        # neutral y cobarde no atacan primero

    def _agredir(self, objetivo):
        """Inicia combate contra el objetivo."""
        if self.db.en_combate:
            return
        from features.combat.commands import _get_combat_handler, _iniciar_combate
        handler = _get_combat_handler(self.location)
        if handler:
            if not handler.agregar_participante(self):
                # Combate en curso es un duelo PvP privado: no se le puede
                # arrastrar a un tercero ajeno (ver agregar_participante()).
                return
            handler.agregar_participante(objetivo)
            self.location.msg_contents(f"|r{self.key} se une al combate!|n")
        else:
            self.location.msg_contents(f"|r{self.key} te ataca!|n")
            _iniciar_combate(self, objetivo)

    def _reaccionar_a_dialogo(self, msg: str, interlocutor):
        """Responder a palabras clave en mensajes de 'decir'."""
        dialogo = self.db.dialogo or {}
        msg_lower = msg.lower()
        for keyword, respuesta in dialogo.items():
            if keyword.lower() in msg_lower:
                self.execute_cmd(f"say {respuesta}")
                return

    # ------------------------------------------------------------------ #
    #  Patrulla
    # ------------------------------------------------------------------ #

    def _iniciar_patrulla(self):
        existing = [s for s in self.scripts.all() if s.key == 'patrol_script']
        if not existing:
            from features.combat.patrol import PatrolScript
            self.scripts.add(PatrolScript)


    # ------------------------------------------------------------------ #
    #  Apariencia
    # ------------------------------------------------------------------ #

    def return_appearance(self, looker, **kwargs):
        hp = getattr(self.db, "hp", 100) or 100
        hp_max = getattr(self.db, "hp_max", 100) or 100
        nivel = getattr(self.db, "nivel", 1) or 1
        temperamento = self.db.temperamento or "neutral"

        desc = self.db.desc or f"Un {self.key} que te observa."
        estado = self._estado_hp_texto(hp, hp_max)

        temp_color = {
            "agresivo": "|r",
            "guardian": "|y",
            "cobarde": "|c",
            "neutral": "|w",
        }.get(temperamento, "|w")

        return (
            f"|w{self.key}|n (Nivel {nivel}) — {temp_color}{temperamento}|n\n"
            f"{desc}\n"
            f"Estado: {estado}"
        )

    def _estado_hp_texto(self, hp, hp_max) -> str:
        ratio = hp / max(hp_max, 1)
        if ratio > 0.75:
            return "|gEn perfectas condiciones.|n"
        elif ratio > 0.50:
            return "|yLigeramente herido.|n"
        elif ratio > 0.25:
            return "|yMuy herido.|n"
        else:
            return "|rAl borde de la muerte.|n"
