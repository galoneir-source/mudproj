"""
features/records/commands.py

Comandos del libro de récords globales:
  records               — top-5 global en todas las categorías
  records personal      — estadísticas personales del jugador
  records <categoria>   — top-5 de una categoría concreta
"""
import time

from evennia import Command, CmdSet

from systems.records.records import (
    CATEGORIAS,
    CAT_IDS,
    extraer_stat,
    formatear_numero,
    formatear_posicion,
    tiempo_desde,
)


def _get_script():
    """Obtiene el RecordsScript sin crear uno si no existe."""
    from evennia.scripts.models import ScriptDB
    qs = ScriptDB.objects.filter(db_key="records_global")
    return qs.first() if qs.exists() else None


def _stats_personales(caller) -> dict:
    """Lee las stats relevantes del personaje llamador."""
    from features.records.records_script import _leer_db_dict, extraer_stat as _ext
    db_dict = _leer_db_dict(caller)
    return {cat_id: extraer_stat(cat_id, db_dict) for cat_id in CAT_IDS}


class CmdRecords(Command):
    """
    Ver el libro de récords global o tus estadísticas personales.

    Uso:
      records                — top-5 global en todas las categorías
      records personal       — tus estadísticas personales
      records kills          — top-5 en kills totales
      records misiones       — top-5 en misiones entregadas
      records jefes          — top-5 en jefes únicos derrotados
      records duelos         — top-5 en duelos ganados
      records crafteo        — top-5 en objetos crafteados

    El tablón global se actualiza automáticamente cada 5 minutos.
    """
    key = "records"
    aliases = ["récords", "ranking", "tablón", "records"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = self.args.strip().lower()

        # --- Vista personal ---
        if args in ("personal", "yo", "mis stats", "mis estadísticas"):
            self._mostrar_personal(caller)
            return

        # --- Vista de una categoría concreta ---
        if args in CAT_IDS:
            self._mostrar_categoria(caller, args)
            return

        # --- Vista global completa (sin args) ---
        if not args:
            self._mostrar_global(caller)
            return

        caller.msg(
            f"Categoría '|w{args}|n' no reconocida. "
            f"Usa: |wrecords [personal | {' | '.join(CAT_IDS)}]|n"
        )

    # ------------------------------------------------------------------ #

    def _mostrar_global(self, caller):
        script = _get_script()
        lineas = [
            f"\n|w{'=' * 54}|n",
            f"  |Y📖 LIBRO DE RÉCORDS GLOBAL|n",
            f"|w{'=' * 54}|n",
        ]

        for cat_id in CAT_IDS:
            cat = CATEGORIAS[cat_id]
            icono = cat["icono"]
            titulo = cat["titulo"]
            desc = cat["descripcion"]

            lineas.append(f"\n  {icono} |c{titulo}|n  |x({desc})|n")

            if script:
                top = script.get_top(cat_id)
            else:
                top = []

            if top:
                for i, (nombre, valor) in enumerate(top, 1):
                    lineas.append(formatear_posicion(i, nombre, valor))
            else:
                lineas.append("    |x(Sin datos aún)|n")

        # Pie de página
        if script:
            ts = getattr(script.db, "ultimo_actualizado", 0) or 0
            lineas.append(
                f"\n|w{'─' * 54}|n\n"
                f"  |xActualizado {tiempo_desde(ts, time.time())}  ·  "
                f"|wrecords personal|x para tus stats|n\n"
                f"|w{'=' * 54}|n\n"
            )
        else:
            lineas.append(f"\n|w{'=' * 54}|n\n")

        caller.msg("\n".join(lineas))

    def _mostrar_categoria(self, caller, cat_id: str):
        script = _get_script()
        cat = CATEGORIAS[cat_id]
        top = script.get_top(cat_id) if script else []

        lineas = [
            f"\n|w{'=' * 44}|n",
            f"  {cat['icono']} |c{cat['titulo']}|n  |x({cat['descripcion']})|n",
            f"|w{'─' * 44}|n",
        ]
        if top:
            for i, (nombre, valor) in enumerate(top, 1):
                lineas.append(formatear_posicion(i, nombre, valor))
        else:
            lineas.append("    |x(Sin datos aún)|n")
        lineas.append(f"|w{'=' * 44}|n\n")
        caller.msg("\n".join(lineas))

    def _mostrar_personal(self, caller):
        stats = _stats_personales(caller)
        nivel = getattr(caller.db, "nivel", 1) or 1
        gremio = getattr(caller.db, "gremio", None) or "|xSin gremio|n"
        titulo = getattr(caller.db, "titulo_activo", None) or "|xSin título|n"

        lineas = [
            f"\n|w{'=' * 48}|n",
            f"  |c📊 ESTADÍSTICAS DE {caller.key.upper()}|n",
            f"|w{'─' * 48}|n",
            f"  |xNivel:|n      {nivel:<6}  |xGremio:|n  {gremio}",
            f"  |xTítulo:|n     {titulo}",
            f"|w{'─' * 48}|n",
        ]

        for cat_id in CAT_IDS:
            cat = CATEGORIAS[cat_id]
            icono = cat["icono"]
            desc = cat["descripcion"].capitalize()
            valor = stats[cat_id]
            lineas.append(f"  {icono} {desc:<32} |w{formatear_numero(valor):>8}|n")

        lineas.append(f"|w{'=' * 48}|n\n")
        caller.msg("\n".join(lineas))


class RecordsCmdSet(CmdSet):
    key = "RecordsCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdRecords())
