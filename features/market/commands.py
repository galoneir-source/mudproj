"""
features/market/commands.py

Comandos del mercado global de jugadores.
"""
from evennia import Command, CmdSet


class CmdMercado(Command):
    """
    Mercado global para comprar y vender objetos entre jugadores.

    Uso:
      mercado                          - ver todos los anuncios
      mercado mis ventas               - ver tus propios anuncios
      mercado vender <objeto> <precio> - poner objeto a la venta
      mercado comprar <#>              - comprar el anuncio número #
      mercado retirar <#>              - retirar tu anuncio número #

    El mercado cobra una comisión del 5% sobre el precio de venta.
    El objeto queda reservado hasta que se venda o lo retires.

    Ejemplos:
      mercado
      mercado vender espada del cazador 500
      mercado comprar 3
      mercado retirar 7
      mercado mis ventas
    """
    key = "mercado"
    aliases = ["market"]
    locks = "cmd:all()"
    help_category = "Economía"

    def func(self):
        from features.market.market_script import obtener_mercado_script
        from systems.market.market import (
            COMISION_PCT, formatear_listing, validar_precio,
        )
        caller = self.caller
        script = obtener_mercado_script()
        args = self.args.strip()

        if not args:
            self._listar(caller, script, formatear_listing)
            return

        args_lower = args.lower()

        if args_lower in ("mis ventas", "mis_ventas", "mio", "mios"):
            self._mis_ventas(caller, script, formatear_listing)
            return

        if args_lower.startswith("comprar "):
            lid = args[len("comprar "):].strip()
            self._comprar(caller, script, lid)
            return

        if args_lower.startswith("retirar "):
            lid = args[len("retirar "):].strip()
            self._retirar(caller, script, lid)
            return

        if args_lower.startswith("vender "):
            resto = args[len("vender "):].strip()
            self._vender(caller, script, resto, validar_precio, COMISION_PCT)
            return

        caller.msg(
            "Uso: |wmercado|n · |wmercado vender <objeto> <precio>|n · "
            "|wmercado comprar <#>|n · |wmercado retirar <#>|n · "
            "|wmercado mis ventas|n"
        )

    # ------------------------------------------------------------------ #
    #  Subcomandos
    # ------------------------------------------------------------------ #

    def _listar(self, caller, script, formatear_listing):
        listings = script.obtener_listings()
        if not listings:
            caller.msg("\n|w── Mercado Global ──|n\n  No hay objetos a la venta.\n")
            return
        lineas = [
            "\n|w── Mercado Global ──|n",
            f"  {'#':>4}  {'Objeto':<32} {'Precio':>10}   Vendedor",
            "  " + "─" * 58,
        ]
        for lid, entry in sorted(listings.items(), key=lambda x: int(x[0])):
            lineas.append(
                formatear_listing(lid, entry["vendedor_nombre"],
                                  entry["item_nombre"], entry["precio"])
            )
        lineas.append(
            "\nUsa |wmercado comprar <#>|n para comprar. "
            "|wmercado vender <objeto> <precio>|n para vender.\n"
        )
        caller.msg("\n".join(lineas))

    def _mis_ventas(self, caller, script, formatear_listing):
        listings = script.obtener_listings(vendedor_dbref=caller.dbref)
        if not listings:
            caller.msg("\n|w── Tus anuncios ──|n\n  No tienes objetos en venta.\n")
            return
        lineas = ["\n|w── Tus anuncios ──|n"]
        for lid, entry in sorted(listings.items(), key=lambda x: int(x[0])):
            lineas.append(
                formatear_listing(lid, entry["vendedor_nombre"],
                                  entry["item_nombre"], entry["precio"])
            )
        lineas.append("\nUsa |wmercado retirar <#>|n para cancelar un anuncio.\n")
        caller.msg("\n".join(lineas))

    def _comprar(self, caller, script, lid):
        ok, msg = script.comprar(lid, caller)
        if ok:
            caller.msg(f"|g[Mercado]|n Has comprado |w{msg}|n.")
        else:
            caller.msg(f"|r[Mercado]|n {msg}")

    def _retirar(self, caller, script, lid):
        ok, msg = script.retirar(lid, caller)
        if ok:
            caller.msg(f"|g[Mercado]|n Has retirado |w{msg}|n de la venta.")
        else:
            caller.msg(f"|r[Mercado]|n {msg}")

    def _vender(self, caller, script, resto, validar_precio, comision_pct):
        from features.equipment.commands import _get_equipamiento
        from systems.market.market import calcular_comision, calcular_ganancia

        parts = resto.rsplit(None, 1)
        if len(parts) < 2:
            caller.msg("Uso: |wmercado vender <nombre del objeto> <precio>|n")
            return

        item_nombre, precio_str = parts
        ok, err = validar_precio(precio_str)
        if not ok:
            caller.msg(f"|r[Mercado]|n {err}")
            return
        precio = int(precio_str)

        # Buscar item en inventario, excluyendo equipados
        eq = _get_equipamiento(caller)
        equipped_ids = {item.id for item in eq.values() if item}
        nombre_lower = item_nombre.lower()

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
                f"|r[Mercado]|n No tienes '{item_nombre}' en el inventario "
                "(o está equipado)."
            )
            return

        comision = calcular_comision(precio)
        ganancia = calcular_ganancia(precio)
        ok, resultado = script.publicar(caller, item, precio)
        if ok:
            caller.msg(
                f"|g[Mercado]|n Has puesto |w{item.key}|n a la venta por "
                f"|y{precio}|n monedas. Recibirás |y{ganancia}|n tras la "
                f"comisión del {comision_pct}% ({comision} m).\n"
                f"ID del anuncio: |w#{resultado}|n"
            )
        else:
            caller.msg(f"|r[Mercado]|n {resultado}")


# --------------------------------------------------------------------------- #
#  CmdSet
# --------------------------------------------------------------------------- #

class MarketCmdSet(CmdSet):
    key = "MarketCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdMercado())
