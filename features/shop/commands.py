"""
features/shop/commands.py

Sistema de tienda: tienda, comprar, vender.

Formato de db.tienda en NPCs (lista de dicts):
  [
    {
      "key": "cerveza oscura",
      "desc": "Una jarra de cerveza...",
      "precio": 3,
      "typeclass": "typeclasses.objects.Object",  # opcional
      "prototype_key": "ESPADA_HIERRO",            # opcional; usa spawn si está presente
      "cantidad": -1,                              # -1 = ilimitado; N > 0 = stock
      "valor": 3,                                  # valor del item (para reventa)
    },
  ]

Los jugadores tienen db.monedas (int) como moneda universal.
Los NPCs compran items al 50% de db.valor del objeto (mínimo 1 moneda).
"""
from evennia import Command, CmdSet


PRECIO_VENTA_DEFAULT = 2   # monedas para items sin db.valor


def _buscar_comerciante(caller, nombre=None):
    """
    Devuelve (comerciante, error_str).
    Si nombre dado, busca por nombre en la sala.
    Si no, busca el único NPC con db.tienda presente.
    """
    sala = caller.location
    if not sala:
        return None, "No estás en ningún lugar."

    if nombre:
        obj = caller.search(nombre, location=sala)
        if not obj:
            return None, None   # search ya emitió el mensaje de error
        if getattr(obj.db, "tienda", None) is None:
            return None, f"{obj.key} no es un comerciante."
        return obj, None

    comerciantes = [o for o in sala.contents if getattr(o.db, "tienda", None) is not None]
    if not comerciantes:
        return None, "No hay ningún comerciante aquí."
    if len(comerciantes) > 1:
        nombres = ", ".join(c.key for c in comerciantes)
        return None, f"Hay varios comerciantes: {nombres}. Especifica a quién con 'de <npc>' o 'a <npc>'."
    return comerciantes[0], None


class CmdTienda(Command):
    """
    Ver los artículos disponibles en la tienda de un comerciante.

    Uso:
      tienda
      tienda <npc>

    Muestra los artículos disponibles y sus precios de compra.
    Tus monedas actuales se muestran arriba.

    Ejemplo:
      tienda
      tienda Mira
      tienda mesonero
    """
    key = "tienda"
    aliases = ["shop", "catalogo"]
    locks = "cmd:all()"
    help_category = "Comercio"

    def func(self):
        caller = self.caller
        nombre = self.args.strip() or None
        comerciante, error = _buscar_comerciante(caller, nombre)
        if error:
            caller.msg(error)
            return
        if comerciante is None:
            return

        tienda = comerciante.db.tienda or []
        monedas = getattr(caller.db, "monedas", 0) or 0

        lineas = [
            f"\n|w{'─'*46}|n",
            f"  |cTienda de {comerciante.key}|n",
            f"  Tus monedas: |y{monedas}|n",
            f"|w{'─'*46}|n",
        ]

        if not tienda:
            lineas.append("  |x(Sin artículos disponibles)|n")
        else:
            for entrada in tienda:
                nombre_item = entrada.get("key", "objeto desconocido")
                precio = entrada.get("precio", 0)
                cantidad = entrada.get("cantidad", -1)
                desc = entrada.get("desc", "")
                stock_txt = "" if cantidad < 0 else f" |x[{cantidad} en stock]|n"
                desc_txt = f"\n    |x{desc[:60]}{'...' if len(desc) > 60 else ''}|n" if desc else ""
                lineas.append(
                    f"  |w{nombre_item:<24}|n |y{precio:>3} monedas|n{stock_txt}{desc_txt}"
                )

        lineas += [
            f"|w{'─'*46}|n",
            f"  |wcomprar <artículo> [de <npc>]|n — comprar",
            f"  |wvender <objeto> [a <npc>]|n   — vender\n",
        ]
        caller.msg("\n".join(lineas))


class CmdComprar(Command):
    """
    Comprar un artículo de un comerciante.

    Uso:
      comprar <artículo>
      comprar <artículo> de <npc>

    El artículo se añade a tu inventario y se descuentan las monedas.
    Usa |wtienda|n para ver qué hay disponible y los precios.

    Ejemplo:
      comprar cerveza oscura
      comprar espada de hierro de Mira
    """
    key = "comprar"
    aliases = ["buy", "adquirir"]
    locks = "cmd:all()"
    help_category = "Comercio"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args:
            caller.msg("¿Qué quieres comprar? Uso: |wcomprar <artículo> [de <npc>]|n")
            return

        # Separar "artículo de npc". Usamos rfind para manejar "espada de hierro de Mira".
        # Si el sufijo tras " de " no corresponde a ningún objeto en la sala,
        # tratamos el string completo como nombre del artículo (sin NPC explícito).
        nombre_npc = None
        nombre_item = args
        if " de " in args.lower():
            idx = args.lower().rfind(" de ")
            posible_npc = args[idx + 4:].strip()
            sala = caller.location
            if sala and caller.search(posible_npc, location=sala, quiet=True):
                nombre_item = args[:idx].strip()
                nombre_npc = posible_npc

        comerciante, error = _buscar_comerciante(caller, nombre_npc)
        if error:
            caller.msg(error)
            return
        if comerciante is None:
            return

        tienda = comerciante.db.tienda or []
        nombre_lower = nombre_item.lower()

        entrada = next(
            (e for e in tienda if nombre_lower in e.get("key", "").lower()),
            None,
        )
        if not entrada:
            caller.msg(f"{comerciante.key} no vende '{nombre_item}'. Usa |wtienda|n para ver el catálogo.")
            return

        precio = entrada.get("precio", 0)
        monedas = getattr(caller.db, "monedas", 0) or 0

        if monedas < precio:
            caller.msg(
                f"No tienes suficientes monedas. "
                f"Necesitas |y{precio}|n, tienes |y{monedas}|n."
            )
            return

        cantidad = entrada.get("cantidad", -1)
        if cantidad == 0:
            caller.msg(f"{comerciante.key} ya no tiene más '{entrada['key']}'.")
            return

        # Crear el item
        try:
            prototype_key = entrada.get("prototype_key")
            if prototype_key:
                from evennia.prototypes import spawner
                item = spawner.spawn(prototype_key)[0]
                item.location = caller
            else:
                import evennia as _evennia
                typeclass = entrada.get("typeclass", "typeclasses.objects.Object")
                item = _evennia.create_object(typeclass, key=entrada["key"], location=caller)
                if entrada.get("desc"):
                    item.db.desc = entrada["desc"]
                if entrada.get("valor") is not None:
                    item.db.valor = entrada["valor"]
        except Exception as err:
            from evennia.utils import logger
            logger.log_err(f"CmdComprar: error creando '{entrada.get('key')}': {err}")
            caller.msg("Hubo un problema al crear el artículo. Inténtalo de nuevo.")
            return

        # Cobrar y actualizar stock
        caller.db.monedas = monedas - precio
        if cantidad > 0:
            entrada["cantidad"] = cantidad - 1
            comerciante.db.tienda = list(tienda)  # asignación explícita → persiste en DB

        caller.msg(
            f"Compras |w{item.key}|n a {comerciante.key} por |y{precio} monedas|n. "
            f"(Monedas restantes: |y{caller.db.monedas}|n)"
        )
        caller.location.msg_contents(
            f"{caller.key} compra {item.key} a {comerciante.key}.",
            exclude=caller,
        )


class CmdVender(Command):
    """
    Vender un objeto a un comerciante.

    Uso:
      vender <objeto>
      vender <objeto> a <npc>

    Recibirás el 50% del valor del objeto en monedas (mínimo 1).
    No puedes vender objetos que tengas equipados.

    Ejemplo:
      vender garra de troll
      vender espada de hierro a Mira
    """
    key = "vender"
    aliases = ["sell", "enajenar"]
    locks = "cmd:all()"
    help_category = "Comercio"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args:
            caller.msg("¿Qué quieres vender? Uso: |wvender <objeto> [a <npc>]|n")
            return

        # Separar "objeto a npc". Verificamos que el sufijo sea un NPC real
        # para evitar falsos splits en nombres como "pocion a la venta".
        nombre_npc = None
        nombre_item = args
        if " a " in args.lower():
            idx = args.lower().rfind(" a ")
            posible_npc = args[idx + 3:].strip()
            sala = caller.location
            if sala and caller.search(posible_npc, location=sala, quiet=True):
                nombre_item = args[:idx].strip()
                nombre_npc = posible_npc

        comerciante, error = _buscar_comerciante(caller, nombre_npc)
        if error:
            caller.msg(error)
            return
        if comerciante is None:
            return

        # Verificar que el item no está equipado
        from features.equipment.commands import _get_equipamiento
        eq = _get_equipamiento(caller)
        equipado_ids = {it.id for it in eq.values() if it}

        item = caller.search(
            nombre_item,
            location=caller,
            nofound_string=f"No tienes '{nombre_item}' en tu inventario.",
        )
        if not item:
            return

        if item.id in equipado_ids:
            caller.msg(
                f"Tienes |w{item.key}|n equipado. "
                f"Usa |wdesequipar {item.key}|n antes de venderlo."
            )
            return

        valor = getattr(item.db, "valor", None) or PRECIO_VENTA_DEFAULT
        precio_venta = max(1, int(valor) // 2)

        caller.db.monedas = (getattr(caller.db, "monedas", 0) or 0) + precio_venta
        caller.location.msg_contents(
            f"{caller.key} vende {item.key} a {comerciante.key}.",
            exclude=caller,
        )
        caller.msg(
            f"Vendes |w{item.key}|n a {comerciante.key} por |y{precio_venta} monedas|n. "
            f"(Monedas totales: |y{caller.db.monedas}|n)"
        )
        item.delete()


class ShopCmdSet(CmdSet):
    key = "ShopCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdTienda())
        self.add(CmdComprar())
        self.add(CmdVender())
