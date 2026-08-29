"""
features/combat/commands.py

Comandos de combate para jugadores:
  atacar, habilidad, huir, pasar, stats, habilidades
"""
from evennia import Command, CmdSet
from systems.combat.engine import STAT_DEFAULTS, xp_para_siguiente_nivel
from systems.utils import barra as _barra


# --------------------------------------------------------------------------- #
#  Utilidades
# --------------------------------------------------------------------------- #

def _get_combat_handler(location):
    """Devuelve el CombatHandler activo en la sala, o None."""
    if not location:
        return None
    for script in location.scripts.all():
        if script.key == "combat_handler" and getattr(script.db, "activo", False):
            return script
    return None


def _añadir_partido_a_lista(personaje, sala, participantes: list):
    """Añade los miembros del grupo de personaje que estén en sala a participantes."""
    try:
        from features.party.commands import esta_en_partido, get_miembros
    except ImportError:
        return
    if not esta_en_partido(personaje):
        return
    for miembro in get_miembros(personaje):
        if miembro != personaje and miembro.location == sala and miembro not in participantes:
            participantes.append(miembro)
            sala.msg_contents(f"|y{miembro.key} se une al combate con su grupo!|n")


def _iniciar_combate(atacante, defensor):
    """Crea un CombatHandler en la sala e inicia el combate."""
    from features.combat.handler import CombatHandler
    sala = atacante.location
    handler = _get_combat_handler(sala)
    if handler:
        if not handler.agregar_participante(atacante):
            # Combate en curso es un duelo PvP privado: no se le puede
            # arrastrar a un tercero ajeno (ver agregar_participante()).
            atacante.msg("Hay un duelo privado en curso; no puedes unirte a ese combate ahora mismo.")
            return handler
        handler.agregar_participante(defensor)
        _añadir_partido_a_lista(atacante, sala, handler.db.participantes)
        sala.msg_contents(f"{atacante.key} se une al combate contra {defensor.key}!")
        return handler

    participantes = [atacante, defensor]
    _añadir_partido_a_lista(atacante, sala, participantes)
    _añadir_partido_a_lista(defensor, sala, participantes)

    handler = sala.scripts.add(CombatHandler)
    handler.iniciar(participantes)
    return handler


# --------------------------------------------------------------------------- #
#  Comando: atacar
# --------------------------------------------------------------------------- #

class CmdAtacar(Command):
    """
    Atacar a un objetivo en combate por turnos.

    Uso:
      atacar <objetivo>

    Inicia o continúa un combate. Si no hay combate activo,
    lo empieza. Si ya hay combate, registra tu acción de ataque.

    Ejemplo:
      atacar goblin
      atacar bandido
    """
    key = "atacar"
    aliases = ["attack", "golpear"]
    locks = "cmd:all()"
    help_category = "Combate"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("¿A quién quieres atacar? Uso: |watacar <objetivo>|n")
            return

        objetivo = caller.search(self.args.strip(), location=caller.location)
        if not objetivo:
            return

        if objetivo == caller:
            caller.msg("No puedes atacarte a ti mismo.")
            return

        handler = _get_combat_handler(caller.location)
        if handler:
            handler.registrar_accion(caller, "atacar", objetivo=objetivo)
        else:
            # Iniciar combate
            _iniciar_combate(caller, objetivo)


# --------------------------------------------------------------------------- #
#  Comando: habilidad
# --------------------------------------------------------------------------- #

class CmdHabilidad(Command):
    """
    Usar una habilidad especial en combate.

    Uso:
      habilidad <nombre_habilidad> [<objetivo>]

    Ejemplo:
      habilidad "golpe fuerte" goblin
      habilidad corte bandido

    Habilidades disponibles: golpe fuerte, golpe rapido, embestida, corte
    """
    key = "habilidad"
    aliases = ["skill"]
    locks = "cmd:all()"
    help_category = "Combate"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args:
            caller.msg("Uso: |whabilidad <nombre> <objetivo>|n  —  usa |whabilidades|n para ver tu árbol.")
            return

        # Parsear "nombre objetivo" o '"nombre con espacios" objetivo'
        partes = args.split()
        if len(partes) < 2:
            caller.msg("Uso: |whabilidad <nombre> <objetivo>|n")
            return

        # Último token = objetivo, el resto = nombre habilidad
        nombre_hab = " ".join(partes[:-1]).strip('"\'')
        nombre_obj = partes[-1]

        # Verificar que el personaje conoce la habilidad
        # Prioridad: db.habilidades_desbloqueadas (nuevo) > db.habilidades (legacy NPCs)
        nombre_norm = nombre_hab.lower().replace(" ", "_")
        desbloqueadas = set(getattr(caller.db, "habilidades_desbloqueadas", []) or [])
        habilidades_legacy = [h.lower() for h in (getattr(caller.db, "habilidades", []) or [])]

        if nombre_norm not in desbloqueadas and nombre_hab.lower() not in habilidades_legacy:
            caller.msg(
                f"No conoces la habilidad '|w{nombre_hab}|n'. "
                f"Usa |whabilidades|n para ver tu árbol de habilidades."
            )
            return

        objetivo = caller.search(nombre_obj, location=caller.location)
        if not objetivo:
            return

        handler = _get_combat_handler(caller.location)
        if not handler:
            caller.msg("No estás en combate. Usa |watacar <objetivo>|n primero.")
            return

        handler.registrar_accion(caller, "habilidad", objetivo=objetivo, habilidad=nombre_hab)


# --------------------------------------------------------------------------- #
#  Comando: huir
# --------------------------------------------------------------------------- #

class CmdHuir(Command):
    """
    Intentar huir del combate (50% de probabilidad).

    Uso:
      huir
    """
    key = "huir"
    aliases = ["flee", "escapar"]
    locks = "cmd:all()"
    help_category = "Combate"

    def func(self):
        caller = self.caller
        handler = _get_combat_handler(caller.location)
        if not handler:
            caller.msg("No estás en combate.")
            return
        handler.registrar_accion(caller, "huir")


# --------------------------------------------------------------------------- #
#  Comando: pasar (turno)
# --------------------------------------------------------------------------- #

class CmdPasarTurno(Command):
    """
    Pasar tu turno en combate sin hacer nada.

    Uso:
      pasar
    """
    key = "pasar"
    aliases = ["pass", "esperar"]
    locks = "cmd:all()"
    help_category = "Combate"

    def func(self):
        caller = self.caller
        handler = _get_combat_handler(caller.location)
        if not handler:
            caller.msg("No estás en combate.")
            return
        handler.registrar_accion(caller, "pasar")


# --------------------------------------------------------------------------- #
#  Comando: stats
# --------------------------------------------------------------------------- #

class CmdStats(Command):
    """
    Ver tus estadísticas de combate.

    Uso:
      stats
      stats <personaje>   (solo Builder/Admin puede ver stats ajenos)
    """
    key = "stats"
    aliases = ["estadisticas", "estado", "st"]
    locks = "cmd:all()"
    help_category = "Combate"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if args and (caller.check_permstring("Builder") or caller.check_permstring("Admin")):
            objetivo = caller.search(args)
            if not objetivo:
                return
        else:
            objetivo = caller

        def _s(k):
            val = getattr(objetivo.db, k, None)
            return val if val is not None else STAT_DEFAULTS.get(k, "?")

        hp = _s("hp")
        hp_max = _s("hp_max")
        nivel = _s("nivel")
        xp = _s("experiencia")
        xp_sig = xp_para_siguiente_nivel(nivel)
        desbloqueadas = set(getattr(objetivo.db, "habilidades_desbloqueadas", []) or [])
        if desbloqueadas:
            from systems.skills.trees import HABILIDADES as _H
            habilidades = [_H.get(h, {}).get("nombre", h) for h in sorted(desbloqueadas)]
        else:
            habilidades = getattr(objetivo.db, "habilidades", []) or []

        barra_hp = _barra(hp, hp_max, 20)
        barra_xp = _barra(xp, xp_sig, 20)

        caller.msg(
            f"\n|w{'='*40}|n\n"
            f"  |cPersonaje:|n {objetivo.key}\n"
            f"  |cNivel:|n    {nivel}  |c  XP:|n {xp}/{xp_sig}\n"
            f"  {barra_xp}\n"
            f"\n"
            f"  |rHP:|n {hp}/{hp_max}\n"
            f"  {barra_hp}\n"
            f"\n"
            f"  |wFuerza:|n      {_s('fuerza'):>3}   |wDestreza:|n    {_s('destreza'):>3}\n"
            f"  |wConstitución:|n {_s('constitucion'):>3}   |wInteligencia:|n {_s('inteligencia'):>3}\n"
            f"  |wDefensa:|n     {_s('defensa'):>3}\n"
            f"\n"
            f"  |cHabilidades:|n {', '.join(habilidades) or 'ninguna'}\n"
            f"|w{'='*40}|n\n"
        )




# --------------------------------------------------------------------------- #
#  CmdSet de combate
# --------------------------------------------------------------------------- #

class CombatCmdSet(CmdSet):
    key = "CombatCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdAtacar())
        self.add(CmdHabilidad())
        self.add(CmdHuir())
        self.add(CmdPasarTurno())
        self.add(CmdStats())
