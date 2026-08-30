"""
features/housing/housing_script.py

GestorViviendasScript: script persistente global que administra todas las
viviendas de jugadores.

  db.viviendas  dict  {propietario_dbref: sala_dbref}

El script crea y destruye salas de vivienda dinámicamente. Cada sala tiene:
  db.es_vivienda        True
  db.propietario_dbref  str   dbref del dueño
  db.invitados          list  dbrefs con acceso
  db.desc_personalizada str | None
"""
from evennia import DefaultScript
from evennia.scripts.models import ScriptDB
from evennia.utils.logger import log_err


def obtener_gestor_script():
    """Devuelve el GestorViviendasScript global, creándolo si no existe."""
    scripts = ScriptDB.objects.filter(db_key="gestor_viviendas")
    for s in scripts:
        return s
    import evennia
    return evennia.create_script(
        GestorViviendasScript, key="gestor_viviendas", persistent=True, autostart=True
    )


def _buscar_barrio() -> object | None:
    """Devuelve la sala 'Barrio Residencial' o None."""
    import evennia
    results = evennia.search_object("Barrio Residencial")
    for r in results:
        if r.is_typeclass("typeclasses.rooms.Room", exact=False):
            return r
    return None


def _resolver_objeto(dbref: str) -> object | None:
    if not dbref:
        return None
    try:
        import evennia
        results = evennia.search_object(dbref, use_dbref=True)
        return results[0] if results else None
    except Exception:
        return None


class GestorViviendasScript(DefaultScript):

    def at_script_creation(self):
        self.key        = "gestor_viviendas"
        self.desc       = "Gestor global de viviendas de jugadores"
        self.persistent = True
        self.interval   = 0       # sin tick periódico
        self.db.viviendas = {}    # {propietario_dbref: sala_dbref}

    # ------------------------------------------------------------------ #
    #  Consultas
    # ------------------------------------------------------------------ #

    def tiene_vivienda(self, jugador) -> bool:
        return jugador.dbref in dict(self.db.viviendas or {})

    def obtener_sala(self, jugador) -> object | None:
        viviendas = dict(self.db.viviendas or {})
        sala_dbref = viviendas.get(jugador.dbref)
        return _resolver_objeto(sala_dbref) if sala_dbref else None

    # ------------------------------------------------------------------ #
    #  Compra
    # ------------------------------------------------------------------ #

    def comprar(self, jugador) -> tuple[bool, str]:
        from systems.housing.housing import puede_comprar, PRECIO_VIVIENDA

        ok, msg = puede_comprar(
            int(getattr(jugador.db, "monedas", 0) or 0),
            self.tiene_vivienda(jugador),
        )
        if not ok:
            return False, msg

        barrio = _buscar_barrio()
        if not barrio:
            return False, "|rError: no se encontró el Barrio Residencial. Avisa a un admin.|n"

        import evennia

        sala = evennia.create_object(
            "typeclasses.rooms.Room",
            key=f"Casa de {jugador.key}",
            nohome=True,
        )
        sala.db.desc = (
            "Una habitación acogedora de paredes de piedra clara. "
            "El suelo de madera cruje suavemente bajo los pies. "
            "Es tuya. Puedes decorarla con el comando |wdecorar <texto>|n."
        )
        sala.db.es_vivienda        = True
        sala.db.propietario_dbref  = jugador.dbref
        sala.db.invitados          = []
        sala.db.desc_personalizada = None
        sala.db.zona               = "barrio_residencial"

        # Salida fija de vuelta al Barrio Residencial
        evennia.create_object(
            "typeclasses.exits.Exit",
            key="salir",
            aliases=["s", "sur", "salida"],
            location=sala,
            destination=barrio,
        )

        jugador.db.monedas     = (getattr(jugador.db, "monedas", 0) or 0) - PRECIO_VIVIENDA
        jugador.db.vivienda_dbref = sala.dbref

        viviendas = dict(self.db.viviendas or {})
        viviendas[jugador.dbref] = sala.dbref
        self.db.viviendas = viviendas

        return True, sala

    # ------------------------------------------------------------------ #
    #  Abandono
    # ------------------------------------------------------------------ #

    def abandonar(self, jugador) -> tuple[bool, str]:
        sala = self.obtener_sala(jugador)
        if not sala:
            return False, "No tienes vivienda."

        # El PvP es libre en cualquier sala (no hay "zona segura" en el
        # motor de combate), así que puede haber un combate activo dentro
        # de la vivienda -- p. ej. el propietario y un invitado peleando.
        # CombatHandler es un script hijo de la sala: si se borrase la
        # sala sin terminar el combate primero, el script se borraría en
        # cascada junto con ella sin pasar nunca por
        # _terminar_combate(), y los participantes se quedarían con
        # db.en_combate=True para siempre. A diferencia de un servidor
        # caído (donde _limpiar_actividad_huerfana() encuentra el script
        # "zombie" al reiniciar y lo limpia), aquí el script desaparece
        # del todo junto con la sala, así que ni un reinicio del
        # servidor podría arreglarlo después.
        for script in sala.scripts.all():
            if script.key == "combat_handler" and getattr(script.db, "activo", False):
                try:
                    script._terminar_combate()
                except Exception as err:
                    log_err(f"abandonar vivienda: error terminando combate: {err}")

        barrio = _buscar_barrio()
        destino_objetos = barrio if barrio else jugador.location

        # Mover todos los objetos de la sala al jugador (o al barrio si no está disponible)
        for obj in list(sala.contents):
            if obj.is_typeclass("typeclasses.exits.Exit", exact=False):
                continue
            try:
                obj.move_to(destino_objetos, quiet=True)
            except Exception as err:
                log_err(f"abandonar vivienda: error moviendo objeto {obj}: {err}")

        # Limpiar estado del jugador
        jugador.db.vivienda_dbref = None

        viviendas = dict(self.db.viviendas or {})
        viviendas.pop(jugador.dbref, None)
        self.db.viviendas = viviendas

        try:
            sala.delete()
        except Exception as err:
            log_err(f"abandonar vivienda: error borrando sala {sala}: {err}")

        return True, "Has abandonado tu vivienda. Los objetos que había se han trasladado al Barrio Residencial."

    # ------------------------------------------------------------------ #
    #  Acceso
    # ------------------------------------------------------------------ #

    def dar_acceso(self, jugador, objetivo) -> tuple[bool, str]:
        from systems.housing.housing import puede_invitar

        sala = self.obtener_sala(jugador)
        if not sala:
            return False, "No tienes vivienda."
        if objetivo.dbref == jugador.dbref:
            return False, "Ya eres el propietario."

        invitados = list(sala.db.invitados or [])
        ok, msg = puede_invitar(invitados, objetivo.dbref)
        if not ok:
            return False, msg

        invitados.append(objetivo.dbref)
        sala.db.invitados = invitados
        return True, f"|w{objetivo.key}|n ahora tiene acceso a tu vivienda."

    def quitar_acceso(self, jugador, objetivo) -> tuple[bool, str]:
        from systems.housing.housing import puede_quitar_acceso

        sala = self.obtener_sala(jugador)
        if not sala:
            return False, "No tienes vivienda."

        invitados = list(sala.db.invitados or [])
        ok, msg = puede_quitar_acceso(invitados, objetivo.dbref)
        if not ok:
            return False, msg

        invitados.remove(objetivo.dbref)
        sala.db.invitados = invitados
        return True, f"|w{objetivo.key}|n ya no tiene acceso a tu vivienda."

    # ------------------------------------------------------------------ #
    #  Decoración
    # ------------------------------------------------------------------ #

    def decorar(self, jugador, texto: str) -> tuple[bool, str]:
        from systems.housing.housing import validar_descripcion

        sala = self.obtener_sala(jugador)
        if not sala:
            return False, "No tienes vivienda."
        if jugador.location != sala:
            return False, "Debes estar en tu vivienda para decorarla."

        ok, resultado = validar_descripcion(texto)
        if not ok:
            return False, resultado

        sala.db.desc_personalizada = resultado
        sala.db.desc = resultado
        jugador.db.vivienda_decorada = True

        return True, "Has decorado tu vivienda."

    # ------------------------------------------------------------------ #
    #  Acceso de visita
    # ------------------------------------------------------------------ #

    def puede_visitar(self, visitante, propietario) -> tuple[bool, str]:
        """Comprueba si visitante puede ir a la vivienda de propietario."""
        sala = self.obtener_sala(propietario)
        if not sala:
            return False, f"|w{propietario.key}|n no tiene vivienda."

        from systems.housing.housing import puede_entrar
        invitados = list(sala.db.invitados or [])
        if not puede_entrar(sala.db.propietario_dbref, invitados, visitante.dbref):
            return False, "No tienes acceso a esa vivienda."

        return True, sala
