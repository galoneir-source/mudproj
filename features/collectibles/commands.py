"""
features/collectibles/commands.py

Comandos del sistema de coleccionables:
  buscar          — busca un tesoro oculto en la sala actual
  buscar pistas   — muestra pistas de tesoros aún no hallados
  coleccion       — progreso de coleccionables
"""
import time

from evennia import Command, CmdSet

from systems.collectibles.collectibles import (
    TESOROS,
    tesoro_de_zona,
    ya_encontrado,
    puede_buscar,
    formatear_coleccion,
    formatear_pistas,
)

_COOLDOWN = 30  # segundos entre búsquedas


class CmdBuscar(Command):
    """
    Busca un tesoro oculto en la sala actual.

    Uso:
      buscar          — registra si hay un tesoro en esta sala
      buscar pistas   — muestra pistas de tesoros que aún no has hallado

    Algunos tesoros requieren haber derrotado al guardián del lugar.
    Hay un tiempo de espera de 30 segundos entre búsquedas.
    """
    key = "buscar"
    aliases = ["search", "rastrear", "escarbar", "registrar"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = self.args.strip().lower()

        if args in ("pistas", "pista", "hints", "hint"):
            encontrados = list(getattr(caller.db, "tesoros_encontrados", []) or [])
            caller.msg(formatear_pistas(encontrados))
            return

        # Cooldown anti-spam
        ahora = time.time()
        ultimo = getattr(caller.ndb, "buscar_ultimo", 0) or 0
        restante = _COOLDOWN - (ahora - ultimo)
        if restante > 0:
            caller.msg(f"Necesitas esperar |w{int(restante) + 1}s|n antes de volver a buscar.")
            return
        caller.ndb.buscar_ultimo = ahora

        # Verificar sala
        sala = caller.location
        if not sala:
            caller.msg("No puedes buscar aquí.")
            return

        zona = getattr(sala.db, "zona", None)
        tesoro_id = tesoro_de_zona(zona)

        if not tesoro_id:
            caller.msg("Buscas minuciosamente pero no encuentras nada especial aquí.")
            return

        encontrados = list(getattr(caller.db, "tesoros_encontrados", []) or [])

        if ya_encontrado(tesoro_id, encontrados):
            t = TESOROS[tesoro_id]
            caller.msg(f"Ya encontraste |w{t['nombre']}|n aquí en el pasado.")
            return

        nivel = int(getattr(caller.db, "nivel", 1) or 1)
        bestiary = dict(getattr(caller.db, "bestiary", {}) or {})

        ok, msg = puede_buscar(tesoro_id, nivel, bestiary, encontrados)
        if not ok:
            caller.msg(f"|x{msg}|n")
            return

        # ¡Tesoro hallado!
        t = TESOROS[tesoro_id]
        caller.db.tesoros_encontrados = encontrados + [tesoro_id]
        recompensa = t["recompensa"]
        monedas_ganadas = recompensa.get("monedas", 0)
        if monedas_ganadas:
            caller.db.monedas = (getattr(caller.db, "monedas", 0) or 0) + monedas_ganadas

        caller.msg(
            f"\n|Y✦ ¡Tesoro hallado!|n  |w{t['nombre']}|n\n"
            f"  {t['descripcion']}\n"
            f"  |g+{monedas_ganadas} monedas|n\n"
        )
        # Avisar a la sala
        caller.location.msg_contents(
            f"|Y{caller.name}|n encontró un tesoro oculto: |w{t['nombre']}|n.",
            exclude=caller,
        )

        from features.achievements.commands import comprobar_y_notificar
        comprobar_y_notificar(caller)


class CmdColeccion(Command):
    """
    Muestra tu progreso de coleccionables y tesoros hallados.

    Uso:
      coleccion       — progreso general
      coleccion pistas — pistas de tesoros pendientes
    """
    key = "coleccion"
    aliases = ["tesoros", "coleccionables", "hallazgos"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = self.args.strip().lower()
        encontrados = list(getattr(caller.db, "tesoros_encontrados", []) or [])

        if args in ("pistas", "pista", "hints"):
            caller.msg(formatear_pistas(encontrados))
        else:
            caller.msg(formatear_coleccion(encontrados))


class CollectiblesCmdSet(CmdSet):
    key = "CollectiblesCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdBuscar())
        self.add(CmdColeccion())
