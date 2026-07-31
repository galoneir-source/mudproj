"""
features/fast_travel/commands.py

Comando de viaje rápido:
  viajar            — lista los destinos ya explorados disponibles
  viajar <destino>  — viaja a un destino ya explorado (coste + cooldown)
"""
import time

from evennia import Command, CmdSet, search_object

from systems.fast_travel.fast_travel import (
    COSTE_VIAJE,
    destinos_disponibles,
    buscar_destino,
    puede_pagar,
    cooldown_restante,
    formatear_destinos,
)
from systems.cartography.cartography import ZONAS_INFO


class CmdViajar(Command):
    """
    Viaja rápidamente a una sala que ya hayas explorado.

    Uso:
      viajar             — lista tus destinos disponibles
      viajar <destino>   — viaja al destino indicado (por nombre de sala)

    Solo puedes viajar a zonas que ya hayas explorado (ver |wmapa|n).
    Cuesta monedas y tiene un pequeño tiempo de espera entre viajes.
    No puedes viajar mientras estás en combate.
    """
    key = "viajar"
    aliases = ["fast travel", "viaje rapido", "viaje rápido"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        from features.cartography.commands import _zonas_a_dbref

        exploradas = list(getattr(caller.db, "salas_exploradas", []) or [])
        zonas_a_dbref = _zonas_a_dbref()
        destinos = destinos_disponibles(exploradas, zonas_a_dbref, ZONAS_INFO)

        args = self.args.strip()
        if not args:
            caller.msg(formatear_destinos(destinos))
            return

        if getattr(caller.db, "en_combate", False):
            caller.msg("|rNo puedes viajar mientras estás en combate.|n")
            return

        destino = buscar_destino(args, destinos)
        if not destino:
            caller.msg(
                f"|rNo tienes un destino explorado que coincida con '{args}'.|n "
                "Usa |wviajar|n sin argumentos para ver tus destinos disponibles."
            )
            return

        zona_id, nombre_sala, area, dbref = destino

        ahora = time.time()
        ultimo_viaje = caller.ndb.ultimo_viaje_rapido or 0
        restante = cooldown_restante(ultimo_viaje, ahora)
        if restante > 0:
            caller.msg(f"Debes esperar |w{restante}s|n antes de volver a viajar.")
            return

        monedas = getattr(caller.db, "monedas", 0) or 0
        ok, msg = puede_pagar(monedas, COSTE_VIAJE)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return

        resultados = search_object(dbref, use_dbref=True)
        sala = resultados[0] if resultados else None
        if not sala:
            caller.msg("|rEse destino ya no existe.|n")
            return

        if caller.location == sala:
            caller.msg("Ya estás ahí.")
            return

        caller.db.monedas = monedas - COSTE_VIAJE
        caller.ndb.ultimo_viaje_rapido = ahora
        caller.move_to(sala, quiet=False, move_type="teleport")
        caller.msg(
            f"|gViajas rápidamente a {nombre_sala}.|n "
            f"(Monedas restantes: |y{caller.db.monedas}|n)"
        )


class FastTravelCmdSet(CmdSet):
    key = "FastTravelCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdViajar())
