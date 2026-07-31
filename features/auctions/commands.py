"""
features/auctions/commands.py

Comandos de la casa de subastas global.
"""
from evennia import Command, CmdSet


class CmdSubasta(Command):
    """
    Casa de subastas: puja al alza por objetos entre jugadores.

    Uso:
      subasta                          - ver todas las subastas activas
      subasta mis subastas             - ver tus propias subastas
      subasta publicar <objeto> <precio> - poner un objeto a subasta
      subasta pujar <#> <monto>        - pujar por una subasta
      subasta retirar <#>              - retirar tu subasta (solo si nadie pujó)

    Distinta del mercado (precio fijo): aquí se puja durante 30 minutos y
    se la lleva el mejor postor al cerrarse. La casa cobra una comisión
    del 5% al vendedor. Las monedas de una puja quedan retenidas; si te
    superan, se te reembolsan automáticamente.

    Ejemplos:
      subasta
      subasta publicar espada del cazador 500
      subasta pujar 3 550
      subasta retirar 7
      subasta mis subastas
    """
    key = "subasta"
    aliases = ["auction", "subastas"]
    locks = "cmd:all()"
    help_category = "Economía"

    def func(self):
        from features.auctions.auction_script import obtener_subastas_script
        from systems.auctions.auctions import formatear_subasta, validar_precio_inicial
        caller = self.caller
        script = obtener_subastas_script()
        args = self.args.strip()

        if not args:
            self._listar(caller, script, formatear_subasta)
            return

        args_lower = args.lower()

        if args_lower in ("mis subastas", "mis_subastas", "mio", "mios"):
            self._mis_subastas(caller, script, formatear_subasta)
            return

        if args_lower.startswith("pujar "):
            resto = args[len("pujar "):].strip()
            self._pujar(caller, script, resto)
            return

        if args_lower.startswith("retirar "):
            aid = args[len("retirar "):].strip()
            self._retirar(caller, script, aid)
            return

        if args_lower.startswith("publicar "):
            resto = args[len("publicar "):].strip()
            self._publicar(caller, script, resto, validar_precio_inicial)
            return

        caller.msg(
            "Uso: |wsubasta|n · |wsubasta publicar <objeto> <precio>|n · "
            "|wsubasta pujar <#> <monto>|n · |wsubasta retirar <#>|n · "
            "|wsubasta mis subastas|n"
        )

    # ------------------------------------------------------------------ #
    #  Subcomandos
    # ------------------------------------------------------------------ #

    def _listar(self, caller, script, formatear_subasta):
        import time
        subastas = script.obtener_subastas()
        if not subastas:
            caller.msg("\n|w── Casa de Subastas ──|n\n  No hay subastas activas.\n")
            return
        ahora = time.time()
        lineas = [
            "\n|w── Casa de Subastas ──|n",
            f"  {'#':>4}  {'Objeto':<28} {'Puja':>10}   {'Mejor postor':<16} {'Restante':>8}",
            "  " + "─" * 68,
        ]
        for aid, entry in sorted(subastas.items(), key=lambda x: int(x[0])):
            lineas.append(formatear_subasta(aid, entry, ahora))
        lineas.append(
            "\nUsa |wsubasta pujar <#> <monto>|n para pujar. "
            "|wsubasta publicar <objeto> <precio>|n para publicar.\n"
        )
        caller.msg("\n".join(lineas))

    def _mis_subastas(self, caller, script, formatear_subasta):
        import time
        subastas = script.obtener_subastas(vendedor_dbref=caller.dbref)
        if not subastas:
            caller.msg("\n|w── Tus subastas ──|n\n  No tienes subastas activas.\n")
            return
        ahora = time.time()
        lineas = ["\n|w── Tus subastas ──|n"]
        for aid, entry in sorted(subastas.items(), key=lambda x: int(x[0])):
            lineas.append(formatear_subasta(aid, entry, ahora))
        caller.msg("\n".join(lineas))

    def _publicar(self, caller, script, resto, validar_precio_inicial):
        from features.equipment.commands import _get_equipamiento

        partes = resto.rsplit(None, 1)
        if len(partes) != 2:
            caller.msg("Uso: |wsubasta publicar <objeto> <precio>|n")
            return
        nombre_obj, precio_str = partes

        ok, msg = validar_precio_inicial(precio_str)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return

        # Buscar item en inventario, excluyendo equipados (mismo criterio
        # que 'mercado vender' en features/market/commands.py)
        eq = _get_equipamiento(caller)
        equipped_ids = {item.id for item in eq.values() if item}
        nombre_lower = nombre_obj.strip().lower()

        item = next(
            (obj for obj in caller.contents
             if obj.id not in equipped_ids and obj.key.lower() == nombre_lower),
            None,
        )
        if not item:
            item = next(
                (obj for obj in caller.contents
                 if obj.id not in equipped_ids
                 and obj.key.lower().startswith(nombre_lower)),
                None,
            )
        if not item:
            caller.msg(
                f"No tienes '{nombre_obj.strip()}' en el inventario (o está equipado)."
            )
            return

        ok, resultado = script.publicar(caller, item, int(precio_str))
        if not ok:
            caller.msg(f"|r{resultado}|n")
            return
        caller.msg(
            f"|gHas puesto |w{item.key}|n a subasta (precio de salida: "
            f"|y{precio_str}|n monedas, ID |w#{resultado}|n).|n"
        )

    def _pujar(self, caller, script, resto):
        partes = resto.split()
        if len(partes) != 2:
            caller.msg("Uso: |wsubasta pujar <#> <monto>|n")
            return
        aid, monto = partes
        ok, msg = script.pujar(aid, caller, monto)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return
        caller.msg(f"|gHas pujado |y{monto}|n monedas por la subasta #{aid}.|n")

    def _retirar(self, caller, script, aid):
        ok, resultado = script.retirar(aid, caller)
        if not ok:
            caller.msg(f"|r{resultado}|n")
            return
        caller.msg(f"|gHas retirado |w{resultado}|n de la subasta.|n")


class AuctionCmdSet(CmdSet):
    key = "AuctionCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdSubasta())
