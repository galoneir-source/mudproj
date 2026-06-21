"""
features/events/commands.py

Comandos del sistema de eventos mundiales.

CmdEvento  — muestra el evento activo (si lo hay) con tiempo restante.
"""
from evennia import Command, CmdSet


class CmdEvento(Command):
    """
    Muestra el evento mundial activo y el tiempo restante.

    Uso:
      evento
      eventos

    Si hay un evento activo, muestra su nombre, descripción, efectos
    y el tiempo que queda. Si no hay ningún evento activo, lo indica.

    Ejemplo:
      evento
    """
    key = "evento"
    aliases = ["eventos", "event", "events"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        from features.events.event_script import (
            obtener_evento_activo, tiempo_restante_evento,
        )
        from systems.events.events import EVENTOS

        ev_id = obtener_evento_activo()

        if not ev_id or ev_id not in EVENTOS:
            self.caller.msg(
                "\n|x── Eventos Mundiales ──────────────────────|n\n"
                "  No hay ningún evento activo en este momento.\n"
                "  Los eventos surgen de vez en cuando de forma inesperada.\n"
                "|x────────────────────────────────────────────|n\n"
            )
            return

        ev = EVENTOS[ev_id]
        restante = tiempo_restante_evento()
        minutos = restante // 60
        segundos = restante % 60
        color = ev.get("color", "|w")

        # Construir línea de efectos
        efectos = ev.get("efectos", {})
        lineas_efecto = []
        if "xp_factor" in efectos:
            facs = efectos.get("facciones_afectadas", ["todos"])
            lineas_efecto.append(
                f"  XP ×{efectos['xp_factor']} contra: {', '.join(facs)}"
            )
        if "descuento_tienda" in efectos:
            pct = int(efectos["descuento_tienda"] * 100)
            lineas_efecto.append(f"  Descuento en tiendas: -{pct}%")
        if "bonus_inteligencia" in efectos:
            lineas_efecto.append(
                f"  +{efectos['bonus_inteligencia']} Inteligencia en combate"
            )

        lineas = [
            f"\n{color}{'─'*46}|n",
            f"  {color}EVENTO ACTIVO: {ev['nombre']}|n",
            f"  {ev['descripcion']}",
        ]
        lineas.extend(lineas_efecto)
        lineas += [
            f"  Tiempo restante: |y{minutos}:{segundos:02d}|n",
            f"{color}{'─'*46}|n\n",
        ]
        self.caller.msg("\n".join(lineas))


class EventCmdSet(CmdSet):
    key = "EventCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdEvento())
