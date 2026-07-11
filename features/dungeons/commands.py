"""
features/dungeons/commands.py

Comandos del sistema de mazmorras instanciadas.

  mazmorra / mazmorras / maz
    <sin args>         → lista de mazmorras
    info <id>          → información detallada
    entrar <id> [dif]  → entra a la mazmorra desde el vestíbulo
    estado             → muestra el estado de la instancia activa
    salir              → abandona sin recompensa

  avanzar              → avanza a la siguiente sala (o completa)
"""

from evennia import Command, CmdSet
from evennia import search_object

from systems.dungeons.dungeons import (
    MAZMORRAS,
    DIFICULTADES,
    buscar_mazmorra,
    puede_entrar_grupo,
    formatear_lista,
    formatear_info,
    NOMBRES_DIFICULTAD,
    SALA_PORTAL,
)


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _instancia_del_jugador(char):
    """Devuelve el MazmorraScript activo en el que está el jugador, o None."""
    sala = char.location
    if not sala:
        return None
    script_id = getattr(sala.db, "mazmorra_script_id", None)
    if not script_id:
        return None
    from evennia import ScriptDB
    try:
        return ScriptDB.objects.get(id=script_id)
    except Exception:
        return None


def _buscar_vestibulo():
    """Devuelve la sala 'Vestíbulo del Portal' o None."""
    resultados = search_object(SALA_PORTAL, typeclass="typeclasses.rooms.Room")
    return resultados[0] if resultados else None


# --------------------------------------------------------------------------- #
#  Comando principal: mazmorra
# --------------------------------------------------------------------------- #

class CmdMazmorra(Command):
    """
    Gestiona las mazmorras instanciadas.

    Uso:
      mazmorra                    - Lista todas las mazmorras
      mazmorra info <nombre>      - Información detallada de una mazmorra
      mazmorra entrar <nombre> [dificultad]
                                  - Entra a la mazmorra (solo desde el vestíbulo)
      mazmorra estado             - Estado de tu instancia activa
      mazmorra salir              - Abandona la mazmorra sin recompensa

    Dificultades: normal (por defecto), dificil, legendario
    """

    key = "mazmorra"
    aliases = ["mazmorras", "maz"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args.strip().split(None, 1)
        sub = args[0].lower() if args else ""
        resto = args[1].strip() if len(args) > 1 else ""

        if not sub or sub in ("lista", "ver"):
            caller.msg(formatear_lista())
            return

        if sub == "info":
            if not resto:
                caller.msg("|rUso: mazmorra info <nombre>|n")
                return
            mid, _ = buscar_mazmorra(resto)
            if not mid:
                caller.msg(f"|rNo se encontró ninguna mazmorra con ese nombre.|n")
                return
            caller.msg(formatear_info(mid))
            return

        if sub == "estado":
            instancia = _instancia_del_jugador(caller)
            if not instancia:
                caller.msg("|xNo estás en ninguna mazmorra activa.|n")
                return
            mid = instancia.db.mazmorra_id
            dif = instancia.db.dificultad or "normal"
            idx = instancia.db.sala_actual or 0
            datos = MAZMORRAS.get(mid, {})
            total = len(datos.get("salas", []))
            nombre_maz = datos.get("nombre", mid)
            dif_txt = NOMBRES_DIFICULTAD.get(dif, dif)
            caller.msg(
                f"|wMazmorra:|n {nombre_maz}  |wDificultad:|n {dif_txt}\n"
                f"|wSala actual:|n {idx + 1}/{total} — {datos.get('salas', [{}])[idx].get('nombre', '?')}"
            )
            return

        if sub == "salir":
            instancia = _instancia_del_jugador(caller)
            if not instancia:
                caller.msg("|xNo estás en ninguna mazmorra activa.|n")
                return
            instancia.salir(caller)
            return

        if sub == "entrar":
            partes = resto.split(None, 1)
            nombre_maz = partes[0] if partes else ""
            dificultad = partes[1].lower().strip() if len(partes) > 1 else "normal"

            if not nombre_maz:
                caller.msg("|rUso: mazmorra entrar <nombre> [dificultad]|n")
                return

            if dificultad not in DIFICULTADES:
                caller.msg(
                    f"|rDificultad '{dificultad}' no válida. "
                    f"Elige: normal, dificil, legendario.|n"
                )
                return

            mid, _ = buscar_mazmorra(nombre_maz)
            if not mid:
                caller.msg(
                    f"|rNo se encontró la mazmorra '{nombre_maz}'.\n"
                    f"Usa |wmazmorra|n para ver la lista.|n"
                )
                return

            # Verificar que el jugador está en el vestíbulo
            vestibulo = _buscar_vestibulo()
            if not vestibulo:
                caller.msg("|rError: no se encontró el Vestíbulo del Portal.|n")
                return
            if caller.location != vestibulo:
                caller.msg(
                    f"|rDebes estar en el |wVestíbulo del Portal|r para entrar a una mazmorra.|n"
                )
                return

            # Solo el líder del grupo puede iniciar la mazmorra.
            # db.lider_partido guarda el objeto Character del líder (no un
            # dbref), así que se compara por identidad de objeto.
            lider = getattr(caller.db, "lider_partido", None)
            if lider and lider != caller:
                caller.msg("|rSolo el líder del grupo puede entrar a una mazmorra.|n")
                return

            # Recopilar miembros del grupo (incluyendo al líder). db.miembros_partido
            # ya contiene objetos Character reales (solo se puebla en el líder).
            miembros = list(getattr(caller.db, "miembros_partido", []) or [])
            if not miembros:
                miembros = [caller]

            # Verificar que ningún miembro esté ya en una instancia
            for m in miembros:
                if _instancia_del_jugador(m):
                    caller.msg(
                        f"|r{m.key} ya está dentro de una mazmorra. "
                        f"Usa |wmazmorra salir|r primero.|n"
                    )
                    return

            # Verificar tamaño de grupo y nivel mínimo de todos los miembros
            niveles = [getattr(m.db, "nivel", 1) or 1 for m in miembros]
            ok, motivo = puede_entrar_grupo(mid, len(miembros), niveles)
            if not ok:
                caller.msg(f"|r{motivo}|n")
                return

            # Crear instancia
            self._crear_instancia(miembros, mid, dificultad, vestibulo)
            return

        caller.msg(
            "|rSubcomando desconocido. Usa: |wmazmorra|r, "
            "|wmazmorra info <nombre>|r, |wmazmorra entrar <nombre>|r, "
            "|wmazmorra estado|r, |wmazmorra salir|r.|n"
        )

    def _crear_instancia(self, jugadores, mid, dificultad, vestibulo):
        from evennia import create_script
        lider = jugadores[0]
        try:
            script = create_script(
                "features.dungeons.dungeon_script.MazmorraScript",
                key=f"mazmorra_{mid}_{lider.id}",
                obj=None,
                persistent=True,
                autostart=True,
            )
            script.iniciar(mid, dificultad, jugadores, vestibulo)
        except Exception as err:
            lider.msg(f"|rError al iniciar la mazmorra: {err}|n")
            from evennia.utils import logger
            logger.log_err(f"CmdMazmorra: error creando instancia: {err}")


# --------------------------------------------------------------------------- #
#  Comando: avanzar
# --------------------------------------------------------------------------- #

class CmdAvanzar(Command):
    """
    Avanza a la siguiente sala de la mazmorra.
    Solo funciona cuando todos los enemigos de la sala actual han sido derrotados.

    Uso:
      avanzar
    """

    key = "avanzar"
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        instancia = _instancia_del_jugador(caller)
        if not instancia:
            caller.msg("|xNo estás en ninguna mazmorra activa.|n")
            return
        instancia.avanzar(caller)


# --------------------------------------------------------------------------- #
#  CmdSet
# --------------------------------------------------------------------------- #

class DungeonCmdSet(CmdSet):
    key = "DungeonCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdMazmorra)
        self.add(CmdAvanzar)
