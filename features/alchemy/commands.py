"""
features/alchemy/commands.py

Comandos del sistema de alquimia avanzada:
  alquimia [lista]            — ver recetas disponibles según tu rango
  alquimia info <receta>      — detalles de una receta
  alquimia elaborar <receta>  — crear una poción consumiendo ingredientes
"""
from evennia import Command, CmdSet

from systems.alchemy.alchemy import (
    RECETAS, RANGOS,
    rango_desde_pociones, recetas_disponibles, puede_elaborar,
    buscar_receta, formatear_recetas, formatear_info_receta,
)


class CmdAlquimia(Command):
    """
    Elaborar pociones alquímicas avanzadas.

    Uso:
      alquimia [lista]           — ver todas las recetas de tu rango
      alquimia info <receta>     — detalles e ingredientes de una receta
      alquimia elaborar <receta> — crear la poción (consume ingredientes)

    Los ingredientes son materiales de herboristería. Necesitas la profesión
    de herboristería para obtenerlos con el comando |wrecolectar|n.

    Rangos de alquimia:
      |wAprendiz|n  — disponible desde el inicio
      |cArtesano|n  — 5 pociones elaboradas
      |YMaestro|n   — 15 pociones elaboradas

    Ejemplo:
      alquimia lista
      alquimia info antidoto_reforzado
      alquimia elaborar balsamoregenerador
    """
    key = "alquimia"
    aliases = ["alchemy", "alq"]
    locks = "cmd:all()"
    help_category = "Jugador"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        rango = _obtener_rango(caller)

        if not args or args.lower() == "lista":
            caller.msg(formatear_recetas(rango))
            return

        partes = args.split(None, 1)
        subcmd = partes[0].lower()
        rest = partes[1].strip() if len(partes) > 1 else ""

        if subcmd in ("info", "detalle", "ver"):
            self._info(rest, rango)
        elif subcmd in ("elaborar", "hacer", "crear", "brew"):
            self._elaborar(rest, rango)
        else:
            # Tratar el argumento como nombre de receta directo
            rid = buscar_receta(args)
            if rid:
                caller.msg(formatear_info_receta(rid))
            else:
                caller.msg(
                    "Uso: |walquimia [lista|info <receta>|elaborar <receta>]|n"
                )

    def _info(self, rest, rango):
        caller = self.caller
        if not rest:
            caller.msg("Uso: |walquimia info <nombre de receta>|n")
            return
        rid = buscar_receta(rest)
        if not rid:
            caller.msg(
                f"|rReceta '|w{rest}|r' no encontrada.|n  "
                f"Usa |walquimia lista|n para ver las disponibles."
            )
            return
        caller.msg(formatear_info_receta(rid))

    def _elaborar(self, rest, rango):
        caller = self.caller
        if not rest:
            caller.msg("Uso: |walquimia elaborar <nombre de receta>|n")
            return

        rid = buscar_receta(rest)
        if not rid:
            caller.msg(
                f"|rReceta '|w{rest}|r' no encontrada.|n  "
                f"Usa |walquimia lista|n para ver las disponibles."
            )
            return

        # Construir inventario (mismo patrón que crafteo)
        eq = _get_equipamiento(caller)
        equipped_ids = {item.id for item in eq.values() if item}

        inventario: dict[str, int] = {}
        for obj in caller.contents:
            if obj.id in equipped_ids:
                continue
            inventario[obj.key.lower()] = inventario.get(obj.key.lower(), 0) + 1

        ok, msg = puede_elaborar(rid, rango, inventario)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return

        receta = RECETAS[rid]

        # Consumir ingredientes
        for ingr_nombre, cantidad_req in receta["ingredientes"].items():
            consumidos = 0
            for obj in list(caller.contents):
                if consumidos >= cantidad_req:
                    break
                if obj.id in equipped_ids:
                    continue
                if obj.key.lower() == ingr_nombre.lower():
                    obj.delete()
                    consumidos += 1

        # Crear la poción (Consumible directo, no desde prototipo)
        from typeclasses.objects import Consumible
        from evennia.utils.create import create_object
        res = receta["resultado"]
        pocion = create_object(
            Consumible,
            key=res["key"],
            location=caller,
            nohome=True,
        )
        pocion.db.desc      = res["desc"]
        pocion.db.efecto    = res["efecto"]
        pocion.db.potencia  = res["potencia"]
        pocion.db.stat_buff = res["stat_buff"]
        pocion.db.duracion  = res["duracion"]
        pocion.db.usos      = 1
        pocion.db.valor     = res["valor"]
        pocion.db.es_alquimia = True

        # Actualizar contador y rango
        pociones = (getattr(caller.db, "pociones_elaboradas", 0) or 0) + 1
        caller.db.pociones_elaboradas = pociones
        nuevo_rango = rango_desde_pociones(pociones)
        rango_anterior = rango
        caller.db.rango_alquimia = nuevo_rango

        caller.msg(
            f"|g¡Has elaborado|n |w{res['key']}|n|g!|n  "
            f"(Pociones elaboradas: |w{pociones}|n)"
        )
        if nuevo_rango != rango_anterior:
            caller.msg(
                f"\n|Y¡RANGO DE ALQUIMIA MEJORADO!|n  "
                f"Ahora eres |Y{nuevo_rango.capitalize()}|n. "
                f"Nuevas recetas disponibles.\n"
            )

        try:
            from features.achievements.commands import comprobar_y_notificar
            comprobar_y_notificar(caller)
        except Exception:
            pass
        try:
            from features.daily.daily_script import notificar_progreso
            notificar_progreso(caller, "alquimia")
        except Exception:
            pass


def _obtener_rango(caller) -> str:
    pociones = getattr(caller.db, "pociones_elaboradas", 0) or 0
    rango_guardado = getattr(caller.db, "rango_alquimia", None)
    # Recalcular siempre por consistencia
    return rango_desde_pociones(pociones)


def _get_equipamiento(caller) -> dict:
    eq = getattr(caller.db, "equipamiento", {}) or {}
    from evennia import search_object
    resultado = {}
    for slot, ref in eq.items():
        if ref is None:
            resultado[slot] = None
        elif isinstance(ref, str) and ref.startswith("#"):
            objs = search_object(ref)
            resultado[slot] = objs[0] if objs else None
        else:
            resultado[slot] = ref
    return resultado


class AlchemyCmdSet(CmdSet):
    key = "AlchemyCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdAlquimia())
