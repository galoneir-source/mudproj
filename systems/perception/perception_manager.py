"""
systems/perception/perception_manager.py

Sistema de percepción puro (sin dependencias de Evennia).

Conceptos:
  - nivel_percepcion: calculado a partir de inteligencia + nivel del observador.
  - detalles_ocultos: lista de dicts en room.db.detalles_ocultos.
      Cada dict: {"texto": str, "req_percepcion": int}
  - entidades ocultas: objetos/NPCs con db.oculto=True y db.nivel_sigilo=int.
      Solo se ven si nivel_percepcion >= nivel_sigilo.

Uso desde comandos/hooks:
    pm = PerceptionManager()
    nivel = pm.nivel_percepcion(personaje)
    detalles = pm.revelar_detalles(sala, personaje)
    visible = pm.puede_detectar(personaje, npc_oculto)
"""

from __future__ import annotations
from typing import Any


class PerceptionManager:
    """
    Punto único de entrada para lógica de percepción.
    """

    # Stat que se usa como base de percepción
    STAT_BASE = "inteligencia"

    # ------------------------------------------------------------------ #
    #  Cálculo de nivel de percepción
    # ------------------------------------------------------------------ #

    def nivel_percepcion(self, observer: Any, hora: int = None) -> int:
        """
        Devuelve el nivel de percepción del observador.
        Fórmula: inteligencia + nivel // 2 [+ penalización nocturna si hora dado]
        Si observer es None devuelve 10 (valor neutro).
        """
        if observer is None:
            return 10
        inteligencia = getattr(observer.db, self.STAT_BASE, 10) or 10
        nivel = getattr(observer.db, "nivel", 1) or 1
        base = int(inteligencia + nivel // 2)
        if hora is not None:
            from systems.time.clock import penalizacion_percepcion
            base += penalizacion_percepcion(hora)
        return max(1, base)

    # ------------------------------------------------------------------ #
    #  Detalles ocultos de sala
    # ------------------------------------------------------------------ #

    def revelar_detalles(self, room: Any, observer: Any, hora: int = None) -> list[str]:
        """
        Devuelve los textos de detalles ocultos de la sala que el observador
        puede percibir.

        La sala debe tener:
          room.db.detalles_ocultos = [
              {"texto": "Hay una grieta en la pared.", "req_percepcion": 12},
              ...
          ]
        """
        detalles = getattr(room.db, "detalles_ocultos", None) or []
        nivel = self.nivel_percepcion(observer, hora=hora)
        return [
            d["texto"]
            for d in detalles
            if isinstance(d, dict) and nivel >= d.get("req_percepcion", 0)
        ]

    # ------------------------------------------------------------------ #
    #  Detección de entidades ocultas
    # ------------------------------------------------------------------ #

    def puede_detectar(self, observer: Any, obj: Any, hora: int = None) -> bool:
        """
        Devuelve True si el observador puede ver al objeto/NPC.

        Un objeto es oculto si obj.db.oculto es True.
        Para detectarlo se necesita nivel_percepcion >= obj.db.nivel_sigilo.
        Los objetos no ocultos siempre son visibles.
        hora — si se pasa, aplica la penalización nocturna a la percepción.
        """
        if not getattr(obj.db, "oculto", False):
            return True
        nivel_sigilo = getattr(obj.db, "nivel_sigilo", 15) or 15
        return self.nivel_percepcion(observer, hora=hora) >= nivel_sigilo

    def filtrar_visibles(self, observer: Any, objetos: list, hora: int = None) -> list:
        """
        Filtra una lista de objetos devolviendo solo los que el observador
        puede detectar.
        """
        return [o for o in objetos if self.puede_detectar(observer, o, hora=hora)]

    # ------------------------------------------------------------------ #
    #  Procesado de texto (pipeline de mensajes)
    # ------------------------------------------------------------------ #

    def process(self, text: str, source: Any = None, receiver: Any = None) -> str:
        """
        Procesa un texto antes de enviarlo al receptor.
        Actualmente devuelve el texto sin modificar.
        Punto de extensión para accesibilidad, triggers de cliente, etc.
        """
        return text
