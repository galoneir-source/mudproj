"""
features/auctions/auction_script.py

Script global que gestiona la casa de subastas: publicar, pujar y cerrar
subastas expiradas automáticamente (tick cada 60s).
"""
import time

from evennia import DefaultScript

TICK_INTERVALO = 60


def _buscar_por_dbref(dbref_str):
    import evennia
    results = evennia.search_object(dbref_str, use_dbref=True)
    return results[0] if results else None


class AuctionScript(DefaultScript):

    def at_script_creation(self):
        self.key = "subastas_global"
        self.desc = "Casa de subastas global de jugadores"
        self.persistent = True
        self.interval = TICK_INTERVALO
        self.db.subastas = {}
        self.db.next_id = 1

    # ------------------------------------------------------------------ #
    #  Tick — cierre automático de subastas expiradas
    # ------------------------------------------------------------------ #

    def at_repeat(self):
        from systems.auctions.auctions import subasta_expirada
        subastas = dict(self.db.subastas or {})
        ahora = time.time()
        for aid, entry in list(subastas.items()):
            if subasta_expirada(entry["timestamp_inicio"], ahora):
                self._cerrar_subasta(aid, entry)

    def _cerrar_subasta(self, aid: str, entry: dict):
        from systems.auctions.auctions import calcular_comision, calcular_ganancia

        subastas = dict(self.db.subastas or {})
        item = _buscar_por_dbref(entry["item_dbref"])
        vendedor = _buscar_por_dbref(entry["vendedor_dbref"])

        if entry.get("mejor_pujador_dbref"):
            ganador = _buscar_por_dbref(entry["mejor_pujador_dbref"])
            precio = entry["precio_actual"]
            ganancia = calcular_ganancia(precio)
            comision = calcular_comision(precio)

            if item and ganador:
                item.location = ganador
                ganador.msg(
                    f"|g[Subastas]|n Has ganado la subasta de |w{entry['item_nombre']}|n "
                    f"por |y{precio}|n monedas."
                )
            if vendedor:
                vendedor.db.monedas = (
                    int(getattr(vendedor.db, "monedas", 0) or 0) + ganancia
                )
                vendedor.msg(
                    f"|g[Subastas]|n Tu subasta de |w{entry['item_nombre']}|n se cerró: "
                    f"vendido por |y{precio}|n monedas a |c{entry['mejor_pujador_nombre']}|n "
                    f"(recibes |y{ganancia}|n, comisión: {comision})."
                )
        else:
            # Nadie pujó: el objeto vuelve al vendedor.
            if item and vendedor:
                item.location = vendedor
            if vendedor:
                vendedor.msg(
                    f"|y[Subastas]|n Tu subasta de |w{entry['item_nombre']}|n cerró sin "
                    f"pujas. El objeto ha vuelto a tu inventario."
                )

        del subastas[aid]
        self.db.subastas = subastas

    # ------------------------------------------------------------------ #
    #  API pública
    # ------------------------------------------------------------------ #

    def publicar(self, vendedor, item, precio_inicial: int) -> tuple[bool, str]:
        """
        Pone un item a subasta. Devuelve (True, aid) o (False, msg_error).
        El item queda en limbo hasta que se cierre la subasta.
        """
        from systems.auctions.auctions import MAX_SUBASTAS_POR_JUGADOR
        subastas = dict(self.db.subastas or {})

        vendedor_dbref = vendedor.dbref
        conteo = sum(1 for v in subastas.values() if v["vendedor_dbref"] == vendedor_dbref)
        if conteo >= MAX_SUBASTAS_POR_JUGADOR:
            return False, (
                f"Ya tienes {MAX_SUBASTAS_POR_JUGADOR} subastas activas. "
                "Espera a que se cierren."
            )

        aid = str(self.db.next_id or 1)
        self.db.next_id = int(self.db.next_id or 1) + 1

        item.location = None  # limbo

        subastas[aid] = {
            "vendedor_dbref":       vendedor_dbref,
            "vendedor_nombre":      vendedor.key,
            "item_dbref":           item.dbref,
            "item_nombre":          item.key,
            "precio_inicial":       int(precio_inicial),
            "precio_actual":        int(precio_inicial),
            "mejor_pujador_dbref":  None,
            "mejor_pujador_nombre": None,
            "timestamp_inicio":     time.time(),
        }
        self.db.subastas = subastas
        return True, aid

    def pujar(self, aid: str, pujador, monto: int) -> tuple[bool, str]:
        """
        Puja por una subasta activa. Devuelve (True, "") o (False, msg_error).
        Retiene las monedas de la puja; reembolsa al pujador anterior si lo hay.
        """
        from systems.auctions.auctions import validar_puja, subasta_expirada
        subastas = dict(self.db.subastas or {})

        if aid not in subastas:
            return False, "No existe esa subasta."

        entry = subastas[aid]
        if subasta_expirada(entry["timestamp_inicio"], time.time()):
            return False, "Esta subasta ya ha finalizado."
        if entry["vendedor_dbref"] == pujador.dbref:
            return False, "No puedes pujar en tu propia subasta."

        monedas_pujador = int(getattr(pujador.db, "monedas", 0) or 0)
        ok, msg = validar_puja(monto, entry["precio_actual"], monedas_pujador)
        if not ok:
            return False, msg

        monto = int(monto)
        pujador.db.monedas = monedas_pujador - monto

        # Reembolsar al pujador anterior, si existía
        anterior_dbref = entry.get("mejor_pujador_dbref")
        if anterior_dbref:
            anterior = _buscar_por_dbref(anterior_dbref)
            if anterior:
                anterior.db.monedas = (
                    int(getattr(anterior.db, "monedas", 0) or 0) + entry["precio_actual"]
                )
                anterior.msg(
                    f"|y[Subastas]|n Te han superado la puja en |w{entry['item_nombre']}|n. "
                    f"Se te han reembolsado |y{entry['precio_actual']}|n monedas."
                )

        entry["precio_actual"] = monto
        entry["mejor_pujador_dbref"] = pujador.dbref
        entry["mejor_pujador_nombre"] = pujador.key
        subastas[aid] = entry
        self.db.subastas = subastas
        return True, ""

    def retirar(self, aid: str, solicitante) -> tuple[bool, str]:
        """
        Retira una subasta sin pujas. Solo el vendedor puede hacerlo, y
        solo si nadie ha pujado todavía (para no perjudicar al pujador).
        """
        subastas = dict(self.db.subastas or {})
        if aid not in subastas:
            return False, "No existe esa subasta."

        entry = subastas[aid]
        if entry["vendedor_dbref"] != solicitante.dbref:
            return False, "No eres el vendedor de esa subasta."
        if entry.get("mejor_pujador_dbref"):
            return False, "Ya tiene una puja; no se puede retirar."

        item = _buscar_por_dbref(entry["item_dbref"])
        if item:
            item.location = solicitante

        del subastas[aid]
        self.db.subastas = subastas
        return True, entry["item_nombre"]

    def obtener_subastas(self, vendedor_dbref=None) -> dict:
        subastas = dict(self.db.subastas or {})
        if vendedor_dbref:
            return {k: v for k, v in subastas.items() if v["vendedor_dbref"] == vendedor_dbref}
        return subastas


def obtener_subastas_script() -> AuctionScript:
    """Devuelve el script global de subastas, creándolo si no existe."""
    from evennia.scripts.models import ScriptDB
    from evennia.utils import create

    script = ScriptDB.objects.filter(db_key="subastas_global").first()
    if script:
        return script
    return create.create_script(AuctionScript, key="subastas_global", persistent=True)
