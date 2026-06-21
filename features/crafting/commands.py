"""
features/crafting/commands.py

Comandos de crafteo: recetas y craftear.
"""
from evennia import Command, CmdSet


# --------------------------------------------------------------------------- #
#  Comando: recetas
# --------------------------------------------------------------------------- #

class CmdRecetas(Command):
    """
    Consultar las recetas de crafteo disponibles.

    Uso:
      recetas
      recetas <nombre>

    Sin argumento muestra la lista completa de recetas.
    Con nombre muestra los ingredientes y el resultado de esa receta.

    Ejemplos:
      recetas
      recetas poción de vida
      recetas elixir
    """
    key = "recetas"
    aliases = ["recipes"]
    locks = "cmd:all()"
    help_category = "Crafteo"

    def func(self):
        from systems.crafting.recipes import RECETAS, buscar_receta
        caller = self.caller

        if self.args.strip():
            nombre, receta = buscar_receta(self.args.strip())
            if not receta:
                caller.msg(
                    f"No existe receta para '|w{self.args.strip()}|n'. "
                    f"Usa |wrecetas|n para ver la lista completa."
                )
                return
            ingrs = ", ".join(
                f"|w{k}|n x{v}" for k, v in receta["ingredientes"].items()
            )
            cant = receta.get("cantidad", 1)
            resultado_txt = f"|y{nombre}|n" + (f" x{cant}" if cant > 1 else "")
            tipo_txt = " |g[equipo]|n" if receta.get("tipo") == "equipo" else ""
            calidad_txt = (
                "\n  |xCalidad      : Normal/Fino/Magistral (según objetos crafteados)|n"
                if receta.get("tipo") == "equipo" else ""
            )
            caller.msg(
                f"\n|c{nombre}|n{tipo_txt}\n"
                f"  Ingredientes : {ingrs}\n"
                f"  Resultado    : {resultado_txt}"
                f"{calidad_txt}\n"
                f"  |x{receta['desc_receta']}|n\n"
            )
        else:
            lineas = ["\n|w── Recetas de crafteo ──|n"]
            for nombre, receta in RECETAS.items():
                ingrs = ", ".join(
                    f"{k} x{v}" for k, v in receta["ingredientes"].items()
                )
                cant = receta.get("cantidad", 1)
                result_txt = f"|y{nombre}|n" + (f" x{cant}" if cant > 1 else "")
                tipo_tag = " |g[equipo]|n" if receta.get("tipo") == "equipo" else ""
                lineas.append(f"  {result_txt}{tipo_tag}  |x←|n  {ingrs}")
            lineas.append(
                "\nUsa |wrecetas <nombre>|n para ver detalles. "
                "Usa |wcraftear <nombre>|n para elaborar.\n"
            )
            caller.msg("\n".join(lineas))


# --------------------------------------------------------------------------- #
#  Comando: craftear
# --------------------------------------------------------------------------- #

class CmdCraftear(Command):
    """
    Elaborar un objeto usando ingredientes de tu inventario.

    Uso:
      craftear <receta>

    Consume los ingredientes necesarios y añade el resultado a tu inventario.
    Usa el comando |wrecetas|n para ver qué puedes fabricar.

    Ejemplos:
      craftear poción de vida
      craftear antídoto
      craftear elixir de restauración
    """
    key = "craftear"
    aliases = ["craft", "fabricar", "elaborar"]
    locks = "cmd:all()"
    help_category = "Crafteo"

    def func(self):
        from systems.crafting.recipes import buscar_receta, verificar_ingredientes
        from features.equipment.commands import _get_equipamiento
        caller = self.caller

        if not self.args.strip():
            caller.msg(
                "¿Qué quieres craftear? Uso: |wcraftear <receta>|n\n"
                "Usa |wrecetas|n para ver la lista."
            )
            return

        nombre_receta, receta = buscar_receta(self.args.strip())
        if not receta:
            caller.msg(
                f"No existe receta para '|w{self.args.strip()}|n'. "
                f"Usa |wrecetas|n para ver la lista."
            )
            return

        # Excluir items equipados del inventario disponible
        eq = _get_equipamiento(caller)
        equipped_ids = {item.id for item in eq.values() if item}

        inventario: dict[str, int] = {}
        for obj in caller.contents:
            if obj.id in equipped_ids:
                continue
            key_lower = obj.key.lower()
            inventario[key_lower] = inventario.get(key_lower, 0) + 1

        ok, faltantes = verificar_ingredientes(inventario, receta)
        if not ok:
            falta_txt = ", ".join(
                f"|w{k}|n x{v}" for k, v in faltantes.items()
            )
            caller.msg(f"Te faltan ingredientes: {falta_txt}")
            return

        # Consumir ingredientes del inventario (saltando equipados)
        for nombre_ingr, cantidad_req in receta["ingredientes"].items():
            consumidos = 0
            for obj in list(caller.contents):
                if consumidos >= cantidad_req:
                    break
                if obj.id in equipped_ids:
                    continue
                if obj.key.lower() == nombre_ingr.lower():
                    obj.delete()
                    consumidos += 1

        # Calidad para recetas de equipo (calculada antes de incrementar contador)
        es_equipo = receta.get("tipo") == "equipo"
        calidad_nombre = None
        bonus_stat = 0
        if es_equipo:
            from systems.crafting.equipment import (
                calcular_calidad, aplicar_bonuses_calidad, nombre_con_calidad,
            )
            nivel_crafteo = int(getattr(caller.db, "objetos_crafteados", 0) or 0)
            calidad_nombre, bonus_stat = calcular_calidad(nivel_crafteo)

        # Crear resultado(s) desde prototipo
        from evennia.prototypes import spawner
        from evennia.utils import logger

        prototype_key = receta["resultado_prototipo"]
        cantidad = receta.get("cantidad", 1)
        creados = []
        for _ in range(cantidad):
            try:
                obj = spawner.spawn(prototype_key)[0]
                obj.location = caller
                if es_equipo:
                    bonuses_base = dict(obj.db.bonuses or {})
                    obj.db.bonuses = aplicar_bonuses_calidad(bonuses_base, bonus_stat)
                    obj.key = nombre_con_calidad(obj.key, calidad_nombre)
                    obj.db.calidad = calidad_nombre
                creados.append(obj.key)
            except Exception as err:
                logger.log_err(f"craftear: error spawning '{prototype_key}': {err}")

        if creados:
            nombres = ", ".join(f"|y{n}|n" for n in creados)
            caller.msg(f"|g¡Crafteo exitoso!|n Has elaborado: {nombres}")
            if calidad_nombre and calidad_nombre != "Normal":
                caller.msg(
                    f"|y¡Calidad {calidad_nombre}!|n Tu experiencia como artesano "
                    f"ha mejorado el objeto."
                )
            caller.location.msg_contents(
                f"{caller.key} elabora algo con sus materiales.",
                exclude=caller,
            )
            caller.db.objetos_crafteados = (
                getattr(caller.db, "objetos_crafteados", 0) or 0
            ) + len(creados)
            from features.achievements.commands import comprobar_y_notificar
            comprobar_y_notificar(caller)
        else:
            caller.msg("|rError al crear el objeto. Contacta a un administrador.|n")


# --------------------------------------------------------------------------- #
#  CmdSet
# --------------------------------------------------------------------------- #

class CraftingCmdSet(CmdSet):
    key = "CraftingCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdRecetas())
        self.add(CmdCraftear())
