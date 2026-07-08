"""
features/gambling/commands.py

Comandos del sistema de apuestas (solo en la Taberna):
  apostar                       — muestra las reglas de todos los juegos
  apostar moneda <cara|cruz> <apuesta>
  apostar dados <apuesta>
  apostar cartas <apuesta>
  apostar ruleta <1-6> <apuesta>
"""
from evennia import Command, CmdSet

from systems.gambling.gambling import (
    MIN_APUESTA, MAX_APUESTA,
    puede_apostar,
    validar_eleccion_moneda,
    validar_numero_ruleta,
    jugar_moneda,
    jugar_dados,
    jugar_cartas,
    jugar_ruleta,
    formatear_reglas,
)

_ZONA_REQUERIDA = "taberna"


def _en_taberna(caller) -> bool:
    sala = caller.location
    return sala and getattr(sala.db, "zona", None) == _ZONA_REQUERIDA


def _aplicar_resultado(caller, resultado: dict):
    """Actualiza monedas y estadísticas del jugador tras una partida."""
    ganancia = resultado["ganancia_neta"]
    caller.db.monedas = max(0, (getattr(caller.db, "monedas", 0) or 0) + ganancia)
    caller.db.apuestas_jugadas = (getattr(caller.db, "apuestas_jugadas", 0) or 0) + 1

    if resultado["gano"]:
        caller.db.apuestas_ganadas = (getattr(caller.db, "apuestas_ganadas", 0) or 0) + 1
        mayor = getattr(caller.db, "mayor_ganancia", 0) or 0
        if ganancia > mayor:
            caller.db.mayor_ganancia = ganancia
        try:
            from features.daily.daily_script import notificar_progreso
            notificar_progreso(caller, "apostar_ganar")
        except Exception:
            pass

    signo = f"|g+{ganancia}|n" if ganancia > 0 else f"|r{ganancia}|n"
    saldo = getattr(caller.db, "monedas", 0) or 0
    caller.msg(
        f"\n  {resultado['descripcion']}\n"
        f"  Monedas: {signo}  (saldo: |w{saldo}|n)\n"
    )
    from features.achievements.commands import comprobar_y_notificar
    comprobar_y_notificar(caller)


class CmdApostar(Command):
    """
    Juega en la Taberna apostando monedas.

    Uso (solo en la Taberna):
      apostar                          — muestra las reglas
      apostar moneda <cara|cruz> <N>   — cara o cruz
      apostar dados <N>                — tus 2 dados vs la casa
      apostar cartas <N>               — tu carta vs la carta de la casa
      apostar ruleta <1-6> <N>         — elige un número de la ruleta

    <N> es la cantidad de monedas apostadas (mín 10, máx 1000).

    Ejemplo:
      apostar moneda cara 50
      apostar ruleta 4 200
    """
    key = "apostar"
    aliases = ["jugar", "gamble", "casino", "apuesta"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller

        if not self.args.strip():
            caller.msg(formatear_reglas())
            return

        if not _en_taberna(caller):
            caller.msg(
                "Los juegos de azar solo están disponibles en la |wTaberna El Jabalí Borracho|n."
            )
            return

        partes = self.args.strip().split()
        juego = partes[0].lower()

        if juego == "moneda":
            self._moneda(caller, partes[1:])
        elif juego == "dados":
            self._dados(caller, partes[1:])
        elif juego == "cartas":
            self._cartas(caller, partes[1:])
        elif juego == "ruleta":
            self._ruleta(caller, partes[1:])
        else:
            caller.msg(
                f"Juego '|w{juego}|n' desconocido. "
                f"Opciones: |wmoneda|n, |wdados|n, |wcartas|n, |wruleta|n."
            )

    # ------------------------------------------------------------------ #

    def _parse_apuesta(self, caller, partes: list, pos: int) -> int | None:
        """Extrae y valida la apuesta de la posición `pos` de la lista de partes."""
        if pos >= len(partes):
            caller.msg("Indica la cantidad a apostar. Ej: |wapostar dados 100|n")
            return None
        try:
            apuesta = int(partes[pos])
        except ValueError:
            caller.msg(f"Cantidad inválida: '|w{partes[pos]}|n'. Debe ser un número entero.")
            return None
        monedas = int(getattr(caller.db, "monedas", 0) or 0)
        ok, msg = puede_apostar(monedas, apuesta)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return None
        return apuesta

    def _moneda(self, caller, partes: list):
        if not partes:
            caller.msg("Uso: |wapostar moneda <cara|cruz> <apuesta>|n")
            return
        eleccion = partes[0].lower()
        ok, msg = validar_eleccion_moneda(eleccion)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return
        apuesta = self._parse_apuesta(caller, partes, 1)
        if apuesta is None:
            return
        caller.msg(f"Apuestas |w{apuesta}|n monedas a |w{eleccion}|n…")
        _aplicar_resultado(caller, jugar_moneda(apuesta, eleccion))

    def _dados(self, caller, partes: list):
        apuesta = self._parse_apuesta(caller, partes, 0)
        if apuesta is None:
            return
        caller.msg(f"Apuestas |w{apuesta}|n monedas. Lanzas los dados…")
        _aplicar_resultado(caller, jugar_dados(apuesta))

    def _cartas(self, caller, partes: list):
        apuesta = self._parse_apuesta(caller, partes, 0)
        if apuesta is None:
            return
        caller.msg(f"Apuestas |w{apuesta}|n monedas. Sacas una carta…")
        _aplicar_resultado(caller, jugar_cartas(apuesta))

    def _ruleta(self, caller, partes: list):
        if not partes:
            caller.msg("Uso: |wapostar ruleta <1-6> <apuesta>|n")
            return
        try:
            numero = int(partes[0])
        except ValueError:
            caller.msg(f"Número inválido: '|w{partes[0]}|n'. Elige un entero entre 1 y 6.")
            return
        ok, msg = validar_numero_ruleta(numero)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return
        apuesta = self._parse_apuesta(caller, partes, 1)
        if apuesta is None:
            return
        caller.msg(f"Apuestas |w{apuesta}|n monedas al número |w{numero}|n. La ruleta gira…")
        _aplicar_resultado(caller, jugar_ruleta(apuesta, numero))


class GamblingCmdSet(CmdSet):
    key = "GamblingCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdApostar())
