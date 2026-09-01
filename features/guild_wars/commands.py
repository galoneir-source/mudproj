"""
features/guild_wars/commands.py

Comando de guerras entre gremios. Solo el Líder de un gremio puede
declarar, aceptar, rechazar o rendirse en una guerra.
"""
from evennia import Command, CmdSet

from systems.guilds.guilds import RANGO_LIDER


class CmdGuerra(Command):
    """
    Guerra entre gremios: mientras dura, las bajas de PvP entre ambos
    gremios se cuentan en un marcador y gana el que más tenga al cierre.
    El PvP en sí ya es libre en todo momento ('atacar <jugador>'); esto
    solo lleva la cuenta y anuncia el resultado.

    Uso:
      guerra                    - ver el estado de la guerra de tu gremio
      guerra declarar <gremio>  - declarar la guerra a otro gremio (solo Líder)
      guerra aceptar            - aceptar un reto de guerra recibido (solo Líder)
      guerra rechazar           - rechazar un reto de guerra recibido (solo Líder)
      guerra rendirse           - rendirse en la guerra activa (solo Líder)

    Dura 1 hora. El reto de guerra caduca a los 5 minutos si no se acepta.
    """
    key = "guerra"
    aliases = ["guildwar"]
    locks = "cmd:all()"
    help_category = "Gremios"

    def func(self):
        from features.guild_wars.guild_war_script import obtener_guerra_script
        from features.guilds.guild_script import obtener_gremio_de

        caller = self.caller
        gremio = obtener_gremio_de(caller)
        if not gremio:
            caller.msg("No perteneces a ningún gremio.")
            return

        script = obtener_guerra_script()
        args = self.args.strip()

        if not args:
            self._estado(caller, script, gremio)
            return

        args_lower = args.lower()

        if args_lower.startswith("declarar "):
            self._declarar(caller, script, gremio, args[len("declarar "):].strip())
            return
        if args_lower == "aceptar":
            self._aceptar(caller, script, gremio)
            return
        if args_lower == "rechazar":
            self._rechazar(caller, script, gremio)
            return
        if args_lower == "rendirse":
            self._rendirse(caller, script, gremio)
            return

        caller.msg(
            "Uso: |wguerra|n · |wguerra declarar <gremio>|n · |wguerra aceptar|n · "
            "|wguerra rechazar|n · |wguerra rendirse|n"
        )

    # ------------------------------------------------------------------ #
    #  Subcomandos
    # ------------------------------------------------------------------ #

    def _estado(self, caller, script, gremio):
        import time
        from systems.guild_wars.guild_wars import formatear_estado

        _, entry = script.guerra_de(gremio.db.nombre)
        if entry:
            caller.msg(formatear_estado(entry, time.time()))
            return

        retos = dict(script.db.retos or {})
        reto = retos.get(gremio.db.nombre)
        if reto:
            caller.msg(
                f"|y{reto['gremio_retador']}|n te ha declarado la guerra. "
                "Usa |wguerra aceptar|n o |wguerra rechazar|n."
            )
            return

        # `retos` está indexado por el gremio RETADO, así que el bucle
        # anterior nunca encuentra el reto propio cuando este gremio es
        # quien lo lanzó (retador) -- sin esto, el líder que acababa de
        # declarar la guerra veía "no tiene retos pendientes" al consultar
        # su propio estado, como si el reto nunca se hubiera enviado.
        for objetivo, reto_saliente in retos.items():
            if reto_saliente.get("gremio_retador") == gremio.db.nombre:
                caller.msg(
                    f"Has retado a |y{objetivo}|n. Esperando respuesta."
                )
                return

        caller.msg("Tu gremio no está en guerra ni tiene retos pendientes.")

    def _requiere_lider(self, caller, gremio) -> bool:
        if gremio.get_rango(caller) != RANGO_LIDER:
            caller.msg("Solo el Líder de tu gremio puede hacer eso.")
            return False
        return True

    def _declarar(self, caller, script, gremio, nombre_rival):
        if not self._requiere_lider(caller, gremio):
            return
        if not nombre_rival:
            caller.msg("Uso: |wguerra declarar <gremio>|n")
            return

        from features.guilds.guild_script import obtener_gremio_por_nombre
        rival = obtener_gremio_por_nombre(nombre_rival)
        if not rival:
            caller.msg(f"No existe ningún gremio llamado '|w{nombre_rival}|n'.")
            return

        ok, msg = script.declarar(gremio.db.nombre, rival.db.nombre)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return
        caller.msg(f"|gHas declarado la guerra a |w{rival.db.nombre}|n.|n")
        rival.notificar_miembros(
            f"|r⚔ |w{gremio.db.nombre}|n os ha declarado la guerra!|n "
            "Usa |wguerra aceptar|n o |wguerra rechazar|n."
        )

    def _aceptar(self, caller, script, gremio):
        if not self._requiere_lider(caller, gremio):
            return
        ok, msg = script.aceptar(gremio.db.nombre)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return
        caller.msg("|gHas aceptado la guerra.|n")

    def _rechazar(self, caller, script, gremio):
        if not self._requiere_lider(caller, gremio):
            return
        ok, msg = script.rechazar(gremio.db.nombre)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return
        caller.msg("|gHas rechazado el reto de guerra.|n")

    def _rendirse(self, caller, script, gremio):
        if not self._requiere_lider(caller, gremio):
            return
        ok, msg = script.rendirse(gremio.db.nombre)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return
        caller.msg("|yTu gremio se ha rendido.|n")


class GuildWarCmdSet(CmdSet):
    key = "GuildWarCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdGuerra())
