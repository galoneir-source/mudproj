"""
features/expeditions/commands.py

Comandos del sistema de expediciones grupales:
  expedicion [lista]         — ver expediciones disponibles
  expedicion info <tipo>     — detalles de una expedición
  expedicion iniciar <tipo>  — iniciar expedición como líder de grupo
  expedicion estado          — progreso de la expedición actual
  expedicion abandonar       — salir de la expedición en curso
"""
from evennia import Command, CmdSet

from systems.expeditions.expeditions import (
    EXPEDICIONES, puede_iniciar, formatear_catalogo, formatear_info,
    formatear_progreso, total_oleadas,
)


def _obtener_script_expedicion(jugador):
    """Devuelve el ExpedicionScript activo en la sala del jugador, o None."""
    sala = jugador.location
    if not sala:
        return None
    script_id = getattr(sala.db, "expedicion_script_id", None)
    if not script_id:
        return None
    from evennia import search_script
    resultados = search_script(f"#{script_id}")
    if resultados:
        return resultados[0]
    # Fallback: buscar por id directamente
    try:
        from evennia.scripts.models import ScriptDB
        return ScriptDB.objects.get(id=script_id)
    except Exception:
        return None


class CmdExpedicion(Command):
    """
    Gestionar expediciones grupales.

    Uso:
      expedicion [lista]         — ver todas las expediciones disponibles
      expedicion info <tipo>     — ver detalles de una expedición
      expedicion iniciar <tipo>  — iniciar expedición (debes ser líder)
      expedicion estado          — ver progreso de la expedición en curso
      expedicion abandonar       — salir de la expedición

    Solo el líder del grupo puede iniciar una expedición. Todos los miembros
    del grupo son teletransportados automáticamente a la zona de combate.

    Ejemplo:
      expedicion lista
      expedicion info catacumbas_perdidas
      expedicion iniciar bosque_profundo
    """
    key = "expedicion"
    aliases = ["expedicion", "expediciones", "expedition"]
    locks = "cmd:all()"
    help_category = "Jugador"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args or args.lower() == "lista":
            caller.msg(formatear_catalogo())
            return

        partes = args.split(None, 1)
        subcmd = partes[0].lower()
        rest = partes[1].strip() if len(partes) > 1 else ""

        if subcmd == "info":
            self._info(rest)
        elif subcmd == "iniciar":
            self._iniciar(rest)
        elif subcmd == "estado":
            self._estado()
        elif subcmd == "abandonar":
            self._abandonar()
        else:
            # Intentar tratar el argumento como tipo directamente
            tipo_id = self._resolver_tipo(args)
            if tipo_id:
                caller.msg(formatear_info(tipo_id))
            else:
                caller.msg(
                    "Uso: |wexpedicion [lista|info <tipo>|iniciar <tipo>|estado|abandonar]|n"
                )

    def _resolver_tipo(self, texto):
        texto = texto.lower().strip()
        if texto in EXPEDICIONES:
            return texto
        # Búsqueda parcial por nombre
        for tid, exp in EXPEDICIONES.items():
            if texto in exp["nombre"].lower() or texto in tid:
                return tid
        return None

    def _info(self, rest):
        if not rest:
            self.caller.msg("Uso: |wexpedicion info <tipo>|n")
            return
        tipo_id = self._resolver_tipo(rest)
        if not tipo_id:
            self.caller.msg(
                f"|rExpedición '|w{rest}|r' no encontrada.|n  "
                f"Usa |wexpedicion lista|n para ver las disponibles."
            )
            return
        self.caller.msg(formatear_info(tipo_id))

    def _iniciar(self, rest):
        caller = self.caller
        if not rest:
            caller.msg("Uso: |wexpedicion iniciar <tipo>|n")
            return

        tipo_id = self._resolver_tipo(rest)
        if not tipo_id:
            caller.msg(
                f"|rExpedición '|w{rest}|r' no encontrada.|n  "
                f"Usa |wexpedicion lista|n para ver las disponibles."
            )
            return

        # Verificar que es líder de grupo. db.lider_partido guarda el objeto
        # Character del líder (no un dbref), así que se compara por
        # identidad de objeto, no como string.
        lider = getattr(caller.db, "lider_partido", None)
        if lider and lider != caller:
            caller.msg("|rSolo el líder del grupo puede iniciar una expedición.|n")
            return

        # Recopilar miembros del grupo (incluyendo al líder). db.miembros_partido
        # ya contiene objetos Character reales (solo se puebla en el líder).
        miembros = list(getattr(caller.db, "miembros_partido", []) or [])
        if not miembros:
            miembros = [caller]

        niveles = [getattr(m.db, "nivel", 1) or 1 for m in miembros]
        ok, msg = puede_iniciar(tipo_id, len(miembros), niveles)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return

        # Verificar que ningún miembro esté ya en expedición
        for m in miembros:
            if getattr(m.location.db if m.location else None, "es_expedicion", False):
                caller.msg(f"|r{m.key} ya está en una expedición activa.|n")
                return

        # Crear el script
        from evennia.utils.create import create_script
        from features.expeditions.expedition_script import ExpedicionScript
        script = create_script(
            ExpedicionScript,
            key="expedicion_script",
            persistent=False,
            autostart=False,
        )
        script.db.tipo_id = tipo_id
        script.iniciar(caller, miembros)
        script.start()

    def _estado(self):
        caller = self.caller
        sala = caller.location
        if not sala or not getattr(sala.db, "es_expedicion", False):
            caller.msg("|rNo estás en ninguna expedición activa.|n")
            return
        script = _obtener_script_expedicion(caller)
        if not script:
            caller.msg("|rNo se encontró el script de expedición.|n")
            return
        tipo_id = script.db.tipo_id
        oleada = script.db.oleada_actual or 0
        caller.msg(formatear_progreso(tipo_id, oleada))

    def _abandonar(self):
        caller = self.caller
        sala = caller.location
        if not sala or not getattr(sala.db, "es_expedicion", False):
            caller.msg("|rNo estás en ninguna expedición activa.|n")
            return
        script = _obtener_script_expedicion(caller)
        if not script:
            caller.msg("|rNo se encontró el script de expedición.|n")
            return
        script.abandonar(caller)


class ExpeditionCmdSet(CmdSet):
    key = "ExpeditionCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdExpedicion())
