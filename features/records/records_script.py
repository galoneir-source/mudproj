"""
features/records/records_script.py

RecordsScript: script persistente que cachea el top-5 global por categoría.
Se actualiza cada 5 minutos y al arrancar el servidor.
"""
import time

from evennia import DefaultScript
from evennia.scripts.models import ScriptDB

from systems.records.records import CATEGORIAS, CAT_IDS, TOP_N, extraer_stat


class RecordsScript(DefaultScript):
    """
    Mantiene una caché del top-5 global para cada categoría de récords.
    Actualiza cada 5 minutos; la primera actualización ocurre en at_start().
    """

    def at_script_creation(self):
        self.key = "records_global"
        self.persistent = True
        self.interval = 300   # 5 minutos entre actualizaciones
        self.db.cache = {}    # {cat_id: [(nombre, valor), ...]}
        self.db.ultimo_actualizado = 0.0

    def at_start(self):
        self.actualizar()

    def at_repeat(self):
        self.actualizar()

    # ------------------------------------------------------------------ #
    #  API pública
    # ------------------------------------------------------------------ #

    def get_top(self, cat_id: str, n: int = TOP_N) -> list:
        """Devuelve los n primeros de una categoría. Lista de (nombre, valor)."""
        cache = dict(self.db.cache or {})
        return list(cache.get(cat_id, []))[:n]

    # ------------------------------------------------------------------ #
    #  Actualización
    # ------------------------------------------------------------------ #

    def actualizar(self):
        chars = _obtener_chars_jugadores()
        nueva_cache = {}
        for cat_id in CAT_IDS:
            entradas = []
            for char in chars:
                try:
                    db_dict = _leer_db_dict(char)
                    valor = extraer_stat(cat_id, db_dict)
                    entradas.append((char.key, valor))
                except Exception:
                    pass
            entradas.sort(key=lambda x: x[1], reverse=True)
            nueva_cache[cat_id] = entradas[:TOP_N]

        self.db.cache = nueva_cache
        self.db.ultimo_actualizado = time.time()


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _obtener_chars_jugadores():
    """Devuelve todos los personajes con cuenta de jugador asociada."""
    from evennia.objects.models import ObjectDB
    chars = ObjectDB.objects.filter(
        db_typeclass_path__icontains="characters.Character"
    )
    return [c for c in chars if bool(getattr(c, "account", None))]


def _leer_db_dict(char) -> dict:
    """Lee los atributos relevantes de un personaje como dict plano."""
    return {
        "kills_totales":     getattr(char.db, "kills_totales", 0),
        "quests":            dict(getattr(char.db, "quests", {}) or {}),
        "jefes_derrotados":  list(getattr(char.db, "jefes_derrotados", []) or []),
        "duelos_ganados":    getattr(char.db, "duelos_ganados", 0),
        "objetos_crafteados":getattr(char.db, "objetos_crafteados", 0),
    }


# --------------------------------------------------------------------------- #
#  Acceso global
# --------------------------------------------------------------------------- #

def obtener_records_script():
    """Devuelve el RecordsScript activo, creándolo si no existe."""
    qs = ScriptDB.objects.filter(db_key="records_global")
    if qs.exists():
        return qs.first()
    from evennia import create_script
    return create_script(RecordsScript, key="records_global", persistent=True)
