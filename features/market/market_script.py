"""
features/market/market_script.py

Script persistente del mercado global de jugadores.
"""
import time

from evennia import create_script, DefaultScript


def _buscar_por_dbref(dbref_str):
    import evennia
    results = evennia.search_object(dbref_str, use_dbref=True)
    return results[0] if results else None


class MarketScript(DefaultScript):

    def at_script_creation(self):
        self.key = "mercado_global"
        self.desc = "Mercado global de jugadores"
        self.persistent = True
        self.db.listings = {}
        self.db.next_id = 1

    # ------------------------------------------------------------------ #
    #  API pública
    # ------------------------------------------------------------------ #

    def publicar(self, vendedor, item, precio: int) -> tuple[bool, str]:
        """
        Pone un item a la venta. Devuelve (True, lid) o (False, msg_error).
        El item queda en limbo hasta que se venda o se retire.
        """
        from systems.market.market import MAX_LISTINGS_POR_JUGADOR
        listings = dict(self.db.listings or {})

        vendedor_dbref = vendedor.dbref
        conteo = sum(1 for v in listings.values() if v["vendedor_dbref"] == vendedor_dbref)
        if conteo >= MAX_LISTINGS_POR_JUGADOR:
            return False, (
                f"Ya tienes {MAX_LISTINGS_POR_JUGADOR} objetos en venta. "
                "Retira alguno primero."
            )

        lid = str(self.db.next_id or 1)
        self.db.next_id = int(self.db.next_id or 1) + 1

        item.location = None  # mover a limbo

        listings[lid] = {
            "vendedor_dbref": vendedor_dbref,
            "vendedor_nombre": vendedor.key,
            "item_dbref": item.dbref,
            "item_nombre": item.key,
            "precio": int(precio),
            "timestamp": time.time(),
        }
        self.db.listings = listings
        return True, lid

    def retirar(self, lid: str, solicitante) -> tuple[bool, str]:
        """
        Retira el anuncio lid. Solo el vendedor puede hacerlo.
        Devuelve (True, nombre_item) o (False, msg_error).
        """
        listings = dict(self.db.listings or {})
        if lid not in listings:
            return False, "No existe ese anuncio."

        entry = listings[lid]
        if entry["vendedor_dbref"] != solicitante.dbref:
            return False, "No eres el vendedor de ese objeto."

        item = _buscar_por_dbref(entry["item_dbref"])
        if item:
            item.location = solicitante

        del listings[lid]
        self.db.listings = listings
        return True, entry["item_nombre"]

    def comprar(self, lid: str, comprador) -> tuple[bool, str]:
        """
        Ejecuta la compra del anuncio lid.
        Devuelve (True, nombre_item) o (False, msg_error).
        El vendedor recibe el pago automáticamente, aunque esté offline.
        """
        from systems.market.market import calcular_comision, calcular_ganancia
        listings = dict(self.db.listings or {})

        if lid not in listings:
            return False, "No existe ese anuncio."

        entry = listings[lid]
        if entry["vendedor_dbref"] == comprador.dbref:
            return False, "No puedes comprar tu propio objeto."

        precio = entry["precio"]
        monedas = int(getattr(comprador.db, "monedas", 0) or 0)
        if monedas < precio:
            from systems.market.market import _fmt
            return False, f"Te faltan {_fmt(precio - monedas)} monedas."

        item = _buscar_por_dbref(entry["item_dbref"])
        if not item:
            del listings[lid]
            self.db.listings = listings
            return False, "El objeto ya no existe en el mercado."

        # Transferir dinero
        comprador.db.monedas = monedas - precio
        ganancia = calcular_ganancia(precio)
        comision = calcular_comision(precio)

        vendedor = _buscar_por_dbref(entry["vendedor_dbref"])
        if vendedor:
            vendedor.db.monedas = (int(getattr(vendedor.db, "monedas", 0) or 0)) + ganancia
            vendedor.msg(
                f"|g[Mercado]|n |y{comprador.key}|n ha comprado |w{item.key}|n "
                f"por |y{precio}|n monedas. Recibes |y{ganancia}|n "
                f"(comisión: {comision})."
            )

        item.location = comprador
        del listings[lid]
        self.db.listings = listings
        return True, entry["item_nombre"]

    def obtener_listings(self, vendedor_dbref=None) -> dict:
        listings = dict(self.db.listings or {})
        if vendedor_dbref:
            return {k: v for k, v in listings.items() if v["vendedor_dbref"] == vendedor_dbref}
        return listings

    def contar_listings_vendedor(self, vendedor_dbref: str) -> int:
        listings = dict(self.db.listings or {})
        return sum(1 for v in listings.values() if v["vendedor_dbref"] == vendedor_dbref)


# --------------------------------------------------------------------------- #
#  Obtención idempotente
# --------------------------------------------------------------------------- #

def obtener_mercado_script() -> MarketScript:
    from evennia.scripts.models import ScriptDB
    qs = ScriptDB.objects.filter(db_key="mercado_global")
    if qs.exists():
        return qs.first()
    return create_script(MarketScript, key="mercado_global", persistent=True)
