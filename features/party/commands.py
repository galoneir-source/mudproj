"""
features/party/commands.py

Sistema de grupos (party):
  invitar   — invitar a un jugador al grupo
  unirse    — aceptar una invitación pendiente
  declinar  — rechazar una invitación pendiente
  partido   — ver el estado del grupo
  abandonar — salir del grupo
  expulsar  — expulsar a un miembro (solo el líder)
"""
from evennia import Command, CmdSet
from systems.party.engine import xp_por_miembro, puede_invitar_validar, MAX_MIEMBROS  # noqa: F401


# --------------------------------------------------------------------------- #
#  Helpers de acceso a datos (usados también desde combat)
# --------------------------------------------------------------------------- #

def esta_en_partido(personaje) -> bool:
    return getattr(personaje.db, "lider_partido", None) is not None


def es_lider(personaje) -> bool:
    lider = getattr(personaje.db, "lider_partido", None)
    return lider is not None and lider.dbref == personaje.dbref


def get_lider(personaje):
    return getattr(personaje.db, "lider_partido", None)


def get_miembros(personaje) -> list:
    """Devuelve todos los miembros del grupo, o lista vacía si no está en ninguno."""
    lider = get_lider(personaje)
    if not lider:
        return []
    return list(getattr(lider.db, "miembros_partido", []) or [])


# --------------------------------------------------------------------------- #
#  Operaciones internas
# --------------------------------------------------------------------------- #

def _crear_partido(lider):
    """Inicializa un grupo con lider como único miembro."""
    lider.db.lider_partido = lider
    lider.db.miembros_partido = [lider]


def _añadir_miembro(lider, nuevo):
    """Añade nuevo al grupo de lider."""
    miembros = list(getattr(lider.db, "miembros_partido", []) or [])
    if nuevo not in miembros:
        miembros.append(nuevo)
        lider.db.miembros_partido = miembros
    nuevo.db.lider_partido = lider
    nuevo.db.invitacion_partido = None


def _quitar_miembro(miembro) -> list:
    """
    Elimina miembro del grupo.
    - Si quedan ≤1 miembros, el grupo se disuelve.
    - Si el líder sale y quedan ≥2, transfiere el liderazgo.
    Devuelve la lista de miembros restantes (vacía si grupo disuelto).
    """
    lider = get_lider(miembro)
    if not lider:
        return []

    era_lider = (miembro == lider)
    miembros = list(getattr(lider.db, "miembros_partido", []) or [])
    if miembro in miembros:
        miembros.remove(miembro)

    miembro.db.lider_partido = None

    if len(miembros) <= 1:
        # Disolver: limpiar el miembro restante (si lo hay)
        for m in miembros:
            m.db.lider_partido = None
        lider.db.miembros_partido = []
        if not era_lider:
            lider.db.lider_partido = None
        return []

    if era_lider:
        nuevo_lider = miembros[0]
        nuevo_lider.db.miembros_partido = miembros
        nuevo_lider.db.lider_partido = nuevo_lider
        for m in miembros[1:]:
            m.db.lider_partido = nuevo_lider
        lider.db.miembros_partido = []
    else:
        lider.db.miembros_partido = miembros

    return miembros


def _disolver_partido(lider):
    """Disuelve completamente el grupo."""
    miembros = list(getattr(lider.db, "miembros_partido", []) or [])
    for m in miembros:
        m.db.lider_partido = None
    lider.db.miembros_partido = []
    lider.db.lider_partido = None


# --------------------------------------------------------------------------- #
#  Comandos
# --------------------------------------------------------------------------- #

class CmdInvitar(Command):
    """
    Invitar a otro jugador a tu grupo.

    Uso:
      invitar <jugador>

    Si no tienes grupo, se crea uno automáticamente y pasas a ser el líder.
    Solo el líder puede invitar. Máximo 4 miembros por grupo.
    """
    key = "invitar"
    aliases = ["invite"]
    locks = "cmd:all()"
    help_category = "Grupo"

    def func(self):
        caller = self.caller
        if not self.args.strip():
            caller.msg("¿A quién quieres invitar? Uso: |winvitar <jugador>|n")
            return

        objetivo = caller.search(self.args.strip(), location=caller.location)
        if not objetivo:
            return

        if not getattr(objetivo, "account", None):
            caller.msg("Solo puedes invitar a otros jugadores.")
            return

        if objetivo == caller:
            caller.msg("No puedes invitarte a ti mismo.")
            return

        ok, motivo = puede_invitar_validar(
            invitante_en_partido=esta_en_partido(caller),
            invitante_es_lider=es_lider(caller),
            objetivo_en_partido=esta_en_partido(objetivo),
            misma_sala=(caller.location == objetivo.location),
        )
        if not ok:
            caller.msg(f"|r{motivo}|n")
            return

        miembros_actuales = get_miembros(caller) if esta_en_partido(caller) else [caller]
        if len(miembros_actuales) >= MAX_MIEMBROS:
            caller.msg(f"|rEl grupo ya está lleno ({MAX_MIEMBROS} miembros máximo).|n")
            return

        if not esta_en_partido(caller):
            _crear_partido(caller)

        objetivo.db.invitacion_partido = caller
        caller.msg(f"|gHas invitado a {objetivo.key} al grupo.|n")
        objetivo.msg(
            f"\n|y{caller.key} te invita a unirte a su grupo.|n\n"
            f"  Usa |wunirse|n para aceptar o |wdeclinar|n para rechazar.\n"
        )


class CmdUnirse(Command):
    """
    Aceptar una invitación de grupo pendiente.

    Uso:
      unirse
    """
    key = "unirse"
    aliases = ["join"]
    locks = "cmd:all()"
    help_category = "Grupo"

    def func(self):
        caller = self.caller
        invitante = getattr(caller.db, "invitacion_partido", None)
        if not invitante:
            caller.msg("No tienes ninguna invitación de grupo pendiente.")
            return

        caller.db.invitacion_partido = None

        if not getattr(invitante, "has_account", False):
            caller.msg("El jugador que te invitó ya no está disponible.")
            return

        lider = get_lider(invitante)
        if not lider:
            caller.msg("El grupo ya no existe.")
            return

        miembros = get_miembros(invitante)
        if len(miembros) >= MAX_MIEMBROS:
            caller.msg(f"|rEl grupo ya está lleno ({MAX_MIEMBROS} miembros).|n")
            invitante.msg(f"|r{caller.key} quiso unirse pero el grupo está lleno.|n")
            return

        _añadir_miembro(lider, caller)

        nombres = ", ".join(m.key for m in get_miembros(caller))
        for m in get_miembros(caller):
            if m == caller:
                m.msg(f"|g¡Te has unido al grupo de {lider.key}!|n  Miembros: {nombres}")
            else:
                m.msg(f"|g{caller.key} se ha unido al grupo.|n  Miembros: {nombres}")


class CmdDeclinar(Command):
    """
    Rechazar una invitación de grupo pendiente.

    Uso:
      declinar
    """
    key = "declinar"
    aliases = ["decline"]
    locks = "cmd:all()"
    help_category = "Grupo"

    def func(self):
        caller = self.caller
        invitante = getattr(caller.db, "invitacion_partido", None)
        if not invitante:
            caller.msg("No tienes ninguna invitación de grupo pendiente.")
            return

        caller.db.invitacion_partido = None
        caller.msg(f"|yHas rechazado la invitación de {invitante.key}.|n")
        try:
            invitante.msg(f"|y{caller.key} ha rechazado tu invitación de grupo.|n")
        except Exception:
            pass


class CmdPartido(Command):
    """
    Ver el estado de tu grupo.

    Uso:
      partido
      grupo
    """
    key = "partido"
    aliases = ["grupo", "party", "group"]
    locks = "cmd:all()"
    help_category = "Grupo"

    def func(self):
        caller = self.caller
        if not esta_en_partido(caller):
            caller.msg("No perteneces a ningún grupo.")
            return

        lider = get_lider(caller)
        miembros = get_miembros(caller)

        lineas = [
            f"\n|w{'='*36}|n",
            f"  |cGrupo de {lider.key}|n  ({len(miembros)}/{MAX_MIEMBROS} miembros)",
            f"|w{'='*36}|n",
        ]
        for m in miembros:
            hp = getattr(m.db, "hp", "?")
            hp_max = getattr(m.db, "hp_max", "?")
            nivel = getattr(m.db, "nivel", "?")
            lider_tag = " |Y[Líder]|n" if m == lider else ""
            if m.location and caller.location and m.location == caller.location:
                sala_tag = " |g[aquí]|n"
            elif m.location:
                sala_tag = f" |y[{m.location.key}]|n"
            else:
                sala_tag = " |r[desconectado]|n"
            lineas.append(
                f"  {m.key}{lider_tag}  Nv.{nivel}  HP: {hp}/{hp_max}{sala_tag}"
            )
        lineas.append(f"|w{'='*36}|n\n")
        caller.msg("\n".join(lineas))


class CmdAbandonar(Command):
    """
    Abandonar tu grupo.

    Uso:
      abandonar

    Si eres el líder, el liderazgo pasa al siguiente miembro.
    Si solo quedáis dos, el grupo se disuelve.
    """
    key = "abandonar"
    aliases = ["leave"]
    locks = "cmd:all()"
    help_category = "Grupo"

    def func(self):
        caller = self.caller
        if not esta_en_partido(caller):
            caller.msg("No perteneces a ningún grupo.")
            return

        if getattr(caller.db, "en_combate", False):
            caller.msg("|rNo puedes abandonar el grupo mientras estás en combate.|n")
            return

        miembros_antes = get_miembros(caller)
        era_lider = es_lider(caller)
        restantes = _quitar_miembro(caller)

        caller.msg("|yHas abandonado el grupo.|n")

        if not restantes:
            for m in miembros_antes:
                if m != caller:
                    m.msg(f"|y{caller.key} ha abandonado el grupo. El grupo se ha disuelto.|n")
        else:
            nuevo_lider = restantes[0] if era_lider else None
            for m in restantes:
                if nuevo_lider and m == nuevo_lider:
                    m.msg(
                        f"|y{caller.key} ha abandonado el grupo. "
                        f"Ahora eres el nuevo líder.|n"
                    )
                else:
                    extra = f" Nuevo líder: {nuevo_lider.key}." if nuevo_lider else ""
                    m.msg(f"|y{caller.key} ha abandonado el grupo.|n{extra}")


class CmdExpulsar(Command):
    """
    Expulsar a un miembro del grupo (solo el líder).

    Uso:
      expulsar <jugador>
    """
    key = "expulsar"
    aliases = ["kick"]
    locks = "cmd:all()"
    help_category = "Grupo"

    def func(self):
        caller = self.caller
        if not esta_en_partido(caller):
            caller.msg("No perteneces a ningún grupo.")
            return

        if not es_lider(caller):
            caller.msg("|rSolo el líder puede expulsar miembros.|n")
            return

        if not self.args.strip():
            caller.msg("¿A quién quieres expulsar? Uso: |wexpulsar <jugador>|n")
            return

        nombre = self.args.strip().lower()
        candidatos = [m for m in get_miembros(caller) if m != caller]

        exactos = [m for m in candidatos if m.key.lower() == nombre]
        if len(exactos) == 1:
            objetivo = exactos[0]
        else:
            parciales = [m for m in candidatos if nombre in m.key.lower()]
            if len(parciales) > 1:
                nombres = ", ".join(m.key for m in parciales)
                caller.msg(f"Nombre ambiguo: {nombres}. Sé más específico.")
                return
            objetivo = parciales[0] if parciales else None

        if not objetivo:
            caller.msg(f"No hay ningún miembro llamado '{self.args.strip()}' en el grupo.")
            return

        if getattr(objetivo.db, "en_combate", False):
            caller.msg("|rNo puedes expulsar a alguien que está en combate.|n")
            return

        _quitar_miembro(objetivo)
        objetivo.msg(f"|rHas sido expulsado del grupo por {caller.key}.|n")
        for m in get_miembros(caller):
            m.msg(f"|y{objetivo.key} ha sido expulsado del grupo.|n")
        caller.msg(f"|yHas expulsado a {objetivo.key} del grupo.|n")


# --------------------------------------------------------------------------- #
#  CmdSet
# --------------------------------------------------------------------------- #

class PartyCmdSet(CmdSet):
    key = "PartyCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdInvitar())
        self.add(CmdUnirse())
        self.add(CmdDeclinar())
        self.add(CmdPartido())
        self.add(CmdAbandonar())
        self.add(CmdExpulsar())
