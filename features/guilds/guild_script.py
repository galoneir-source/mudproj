"""
features/guilds/guild_script.py

GuildScript: script persistente que almacena el estado de un gremio.
Un script por gremio, key = "guild_<nombre_normalizado>".
"""
import time

from evennia import DefaultScript
from evennia.scripts.models import ScriptDB

from systems.guilds.guilds import RANGO_LIDER, RANGO_MIEMBRO, normalizar_nombre


class GuildScript(DefaultScript):
    """
    Contenedor persistente de un gremio de jugadores.
    No tiene intervalo de tick: solo almacena estado.
    """

    def at_script_creation(self):
        self.persistent = True
        self.db.nombre    = ""    # nombre de display
        self.db.descripcion = ""
        self.db.miembros  = {}    # {dbref_str: rango_str}
        self.db.banco     = 0     # monedas en el banco del gremio
        self.db.fundado   = 0.0   # Unix timestamp de creación

    # ------------------------------------------------------------------ #
    #  Consultas
    # ------------------------------------------------------------------ #

    def get_rango(self, char) -> str:
        """Devuelve el rango del personaje en el gremio, o None si no es miembro."""
        return dict(self.db.miembros or {}).get(char.dbref)

    def es_miembro(self, char) -> bool:
        return self.get_rango(char) is not None

    def contar_miembros(self) -> int:
        return len(dict(self.db.miembros or {}))

    def get_lider_dbref(self) -> str:
        """Devuelve el dbref del Líder actual, o None."""
        for dbref, rango in dict(self.db.miembros or {}).items():
            if rango == RANGO_LIDER:
                return dbref
        return None

    # ------------------------------------------------------------------ #
    #  Modificaciones de roster
    # ------------------------------------------------------------------ #

    def añadir_miembro(self, char, rango: str = RANGO_MIEMBRO):
        miembros = dict(self.db.miembros or {})
        miembros[char.dbref] = rango
        self.db.miembros = miembros
        char.db.gremio = self.db.nombre

    def eliminar_miembro(self, char):
        miembros = dict(self.db.miembros or {})
        miembros.pop(char.dbref, None)
        self.db.miembros = miembros
        char.db.gremio = None

    def cambiar_rango(self, char, nuevo_rango: str):
        miembros = dict(self.db.miembros or {})
        if char.dbref in miembros:
            miembros[char.dbref] = nuevo_rango
            self.db.miembros = miembros

    # ------------------------------------------------------------------ #
    #  Banco
    # ------------------------------------------------------------------ #

    def depositar(self, char, cantidad: int) -> bool:
        monedas = getattr(char.db, "monedas", 0) or 0
        if monedas < cantidad:
            return False
        char.db.monedas = monedas - cantidad
        self.db.banco = (self.db.banco or 0) + cantidad
        return True

    def retirar(self, char, cantidad: int) -> bool:
        banco = self.db.banco or 0
        if banco < cantidad:
            return False
        monedas = getattr(char.db, "monedas", 0) or 0
        self.db.banco = banco - cantidad
        char.db.monedas = monedas + cantidad
        return True

    # ------------------------------------------------------------------ #
    #  Notificaciones y disolución
    # ------------------------------------------------------------------ #

    def notificar_miembros(self, mensaje: str, excluir=None):
        """Envía un mensaje a todos los miembros actualmente conectados."""
        from evennia import search_object
        for dbref in list(dict(self.db.miembros or {}).keys()):
            if excluir and dbref == excluir.dbref:
                continue
            results = search_object(dbref, use_dbref=True)
            if results and results[0].sessions.count() > 0:
                results[0].msg(mensaje)

    def disolver(self, devolver_banco_a=None):
        """
        Disuelve el gremio: limpia db.gremio de todos los miembros y borra el script.
        Si se indica devolver_banco_a, las monedas del banco van a ese personaje.
        """
        from evennia import search_object
        for dbref in list(dict(self.db.miembros or {}).keys()):
            results = search_object(dbref, use_dbref=True)
            if results:
                results[0].db.gremio = None
        if devolver_banco_a and self.db.banco:
            monedas = getattr(devolver_banco_a.db, "monedas", 0) or 0
            devolver_banco_a.db.monedas = monedas + (self.db.banco or 0)
        self.db.miembros = {}
        self.delete()


# --------------------------------------------------------------------------- #
#  Helpers de búsqueda
# --------------------------------------------------------------------------- #

def obtener_gremio_por_nombre(nombre: str):
    """Devuelve el GuildScript del gremio con ese nombre, o None."""
    clave = f"guild_{normalizar_nombre(nombre)}"
    qs = ScriptDB.objects.filter(db_key=clave)
    return qs.first() if qs.exists() else None


def obtener_gremio_de(char):
    """Devuelve el GuildScript al que pertenece el personaje, o None."""
    nombre = getattr(char.db, "gremio", None)
    if not nombre:
        return None
    return obtener_gremio_por_nombre(nombre)
