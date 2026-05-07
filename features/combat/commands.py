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


def _iniciar_combate(atacante, defensor):
    """Crea un CombatHandler en la sala e inicia el combate."""
    from features.combat.handler import CombatHandler
    sala = atacante.location
    handler = _get_combat_handler(sala)
    if handler:
        # Ya hay combate: unirse si no están dentro
        handler.agregar_participante(atacante)
        handler.agregar_participante(defensor)
        sala.msg_contents(
            f"{atacante.key} se une al combate contra {defensor.key}!"
        )
        return handler

    handler = sala.scripts.add(CombatHandler)
    handler.iniciar([atacante, defensor])
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
    aliases = ["skill", "usar"]
    locks = "cmd:all()"
    help_category = "Combate"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args:
            habilidades = getattr(caller.db, "habilidades", []) or []
            if habilidades:
                caller.msg(f"Tus habilidades: {', '.join(habilidades)}")
            else:
                caller.msg("No tienes habilidades especiales aún.")
            return

        # Parsear "nombre objetivo" o '"nombre con espacios" objetivo'
        partes = args.split()
        if len(partes) < 2:
            caller.msg("Uso: |whabilidad <nombre> <objetivo>|n")
            return

        # Último token = objetivo, el resto = nombre habilidad
        nombre_hab = " ".join(partes[:-1]).strip('"\'')
        nombre_obj = partes[-1]

        habilidades = getattr(caller.db, "habilidades", []) or []
        if nombre_hab.lower() not in [h.lower() for h in habilidades]:
            caller.msg(
                f"No conoces la habilidad '{nombre_hab}'. "
                f"Tus habilidades: {', '.join(habilidades) or 'ninguna'}"
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
#  Comando: habilidades (listar las propias)
# --------------------------------------------------------------------------- #

class CmdListarHabilidades(Command):
    """
    Ver tus habilidades de combate disponibles.

    Uso:
      habilidades
    """
    key = "habilidades"
    aliases = ["skills"]
    locks = "cmd:all()"
    help_category = "Combate"

    def func(self):
        caller = self.caller
        habilidades = getattr(caller.db, "habilidades", []) or []
        if not habilidades:
            caller.msg("Aún no tienes habilidades especiales de combate.")
            return
        desc = {
            "golpe fuerte": "Ataque potente. x1.5 daño, sin bonificación de velocidad.",
            "golpe rapido": "Ataque rápido. Menor daño, más difícil de esquivar.",
            "embestida": "+5 daño base. Puede romper la postura del enemigo.",
            "corte": "Herida cortante. x1.3 daño.",
            "veneno": "Envenenar al objetivo. +1d4 daño extra.",
        }
        lineas = [f"\n|cHabilidades de {caller.key}:|n"]
        for h in habilidades:
            d = desc.get(h.lower(), "Sin descripción.")
            lineas.append(f"  |w{h}|n — {d}")
        caller.msg("\n".join(lineas) + "\n")


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
        self.add(CmdListarHabilidades())
