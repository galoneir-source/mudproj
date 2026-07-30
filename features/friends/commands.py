"""
features/friends/commands.py

Comandos del sistema de lista de amigos:
  agregar amigo <jugador>   — agrega a un jugador a tu lista de amigos
  quitar amigo <jugador>    — lo quita de tu lista
  amigos                    — muestra tu lista de amigos y quién está en línea
"""
from evennia import Command, CmdSet
from evennia import search_object

from systems.friends.friends import (
    puede_agregar,
    agregar_amigo,
    quitar_amigo,
    formatear_lista_amigos,
)


def _buscar_jugador(nombre: str):
    """Busca un Character por nombre (en línea o no). Devuelve (char, error)."""
    resultados = search_object(nombre, typeclass="typeclasses.characters.Character")
    if not resultados:
        return None, f"|rNo se encontró ningún jugador con el nombre '{nombre}'.|n"
    if len(resultados) > 1:
        nombres = ", ".join(r.key for r in resultados)
        return None, f"|rNombre ambiguo: {nombres}. Sé más específico.|n"
    return resultados[0], ""


class CmdAgregarAmigo(Command):
    """
    Agrega a un jugador a tu lista de amigos.

    Uso:
      agregar amigo <jugador>

    No hace falta que la otra persona acepte: es una lista de contactos,
    no una amistad mutua. Cuando esa persona se conecte o desconecte, te
    avisamos si está en tu lista.
    """
    key = "agregar amigo"
    aliases = ["add friend"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        nombre = self.args.strip()
        if not nombre:
            caller.msg("Uso: agregar amigo <jugador>")
            return

        objetivo, error = _buscar_jugador(nombre)
        if error:
            caller.msg(error)
            return

        amigos = list(getattr(caller.db, "amigos", None) or [])
        ok, error = puede_agregar(amigos, objetivo.dbref, caller.dbref)
        if not ok:
            caller.msg(f"|r{error}|n")
            return

        caller.db.amigos = agregar_amigo(amigos, objetivo.dbref)
        caller.msg(f"|g{objetivo.key} fue agregado a tu lista de amigos.|n")


class CmdQuitarAmigo(Command):
    """
    Quita a un jugador de tu lista de amigos.

    Uso:
      quitar amigo <jugador>
    """
    key = "quitar amigo"
    aliases = ["remove friend"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        nombre = self.args.strip()
        if not nombre:
            caller.msg("Uso: quitar amigo <jugador>")
            return

        objetivo, error = _buscar_jugador(nombre)
        if error:
            caller.msg(error)
            return

        amigos = list(getattr(caller.db, "amigos", None) or [])
        if objetivo.dbref not in amigos:
            caller.msg(f"|r{objetivo.key} no está en tu lista de amigos.|n")
            return

        caller.db.amigos = quitar_amigo(amigos, objetivo.dbref)
        caller.msg(f"|y{objetivo.key} fue quitado de tu lista de amigos.|n")


class CmdAmigos(Command):
    """
    Muestra tu lista de amigos y quién está en línea ahora mismo.

    Uso:
      amigos
    """
    key = "amigos"
    aliases = ["friends", "lista amigos"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        amigos = list(getattr(caller.db, "amigos", None) or [])
        entradas = []
        for dbref in amigos:
            resultados = search_object(dbref, use_dbref=True)
            if not resultados:
                continue
            personaje = resultados[0]
            en_linea = personaje.sessions.count() > 0
            entradas.append((personaje.key, en_linea))
        caller.msg(formatear_lista_amigos(entradas))


class FriendsCmdSet(CmdSet):
    key = "FriendsCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdAgregarAmigo())
        self.add(CmdQuitarAmigo())
        self.add(CmdAmigos())
