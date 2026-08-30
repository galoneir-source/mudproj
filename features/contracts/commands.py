"""
features/contracts/commands.py

Comandos del tablón de contratos (v0.27.0).
"""
from evennia import Command, CmdSet


class CmdTablon(Command):
    """
    Consulta y gestiona el tablón de contratos.

    Uso:
      tablón                  - ver los contratos disponibles
      tablón aceptar <#>      - aceptar el contrato número #
      tablón entregar         - completar tu contrato activo
      tablón cancelar         - abandonar tu contrato activo
      tablón estado           - ver progreso de tu contrato activo

    Los contratos se renuevan cada hora. Hay 5 disponibles simultáneamente.
    Solo puedes tener un contrato activo a la vez.

    Contratos de tipo 'matar': requieren eliminar N enemigos desde que
    aceptaste el contrato.
    Contratos de tipo 'entrega': requieren llevar N materiales al tablón.
    """
    key = "tablón"
    aliases = ["tablon", "contratos", "board", "contrato"]
    locks = "cmd:all()"
    help_category = "Misiones"

    def func(self):
        from features.contracts.contract_script import obtener_tablón_script
        caller = self.caller
        args = self.args.strip()
        args_lower = args.lower()

        script = obtener_tablón_script()

        if not args or args_lower in ("ver", "lista", "list"):
            self._mostrar_tablón(caller, script)
            return

        if args_lower in ("estado", "progreso", "mis contratos", "activo"):
            self._estado(caller)
            return

        if args_lower in ("cancelar", "abandonar"):
            self._cancelar(caller)
            return

        if args_lower in ("entregar", "completar", "terminar"):
            self._entregar(caller)
            return

        if args_lower.startswith("aceptar "):
            num_str = args[len("aceptar "):].strip()
            try:
                num = int(num_str)
            except ValueError:
                caller.msg("|rUso: tablón aceptar <número del contrato>|n")
                return
            self._aceptar(caller, script, num)
            return

        caller.msg(
            "Uso: |wtablón|n · |wtablón aceptar <#>|n · "
            "|wtablón entregar|n · |wtablón cancelar|n · |wtablón estado|n"
        )

    # ------------------------------------------------------------------ #
    #  Subcomandos
    # ------------------------------------------------------------------ #

    def _mostrar_tablón(self, caller, script):
        from systems.contracts.contracts import formatear_contrato
        contratos = script.obtener_contratos()
        activo = caller.db.contrato_activo

        lineas = ["\n|w── Tablón de Contratos ──|n"]
        for i, c in enumerate(contratos, 1):
            lineas.append(formatear_contrato(i, c))
        lineas.append("\n|w[Consejo]|n Usa |wtablón aceptar <#>|n para aceptar un contrato.")
        if activo:
            lineas.append(
                f"|y[Activo]|n Ya tienes un contrato: \"{activo['descripcion']}\". "
                "Usa |wtablón estado|n para ver el progreso."
            )
        lineas.append("")
        caller.msg("\n".join(lineas))

    def _aceptar(self, caller, script, num):
        activo = caller.db.contrato_activo
        if activo:
            caller.msg(
                f"|r[Tablón]|n Ya tienes un contrato activo: "
                f"\"{activo['descripcion']}\". "
                "Usa |wtablón cancelar|n para abandonarlo primero."
            )
            return

        contrato = script.obtener_contrato(num)
        if not contrato:
            caller.msg(f"|r[Tablón]|n No hay ningún contrato con ese número.")
            return

        nuevo = dict(contrato)
        if nuevo["tipo"] == "kill":
            nuevo["kills_al_aceptar"] = getattr(caller.db, "kills_totales", 0) or 0

        caller.db.contrato_activo = nuevo
        r = nuevo["recompensa"]
        caller.msg(
            f"|g[Tablón]|n Has aceptado el contrato:\n"
            f"  {nuevo['etiqueta']} |w{nuevo['descripcion']}|n\n"
            f"  Recompensa: |y{r['monedas']} monedas|n + |c{r['xp']} XP|n\n"
            "Usa |wtablón estado|n para ver el progreso."
        )

    def _estado(self, caller):
        from systems.contracts.contracts import (
            formatear_progreso, puede_completar_kill, puede_completar_entrega,
        )
        activo = caller.db.contrato_activo
        if not activo:
            caller.msg("|y[Tablón]|n No tienes ningún contrato activo. Usa |wtablón|n para ver los disponibles.")
            return

        tipo = activo["tipo"]
        r = activo["recompensa"]

        if tipo == "kill":
            kills = getattr(caller.db, "kills_totales", 0) or 0
            completado, hechas = puede_completar_kill(activo, kills)
            texto = formatear_progreso(activo, kills_totales=kills)
        else:
            disponible = self._contar_material(caller, activo["objetivo"])
            completado, _ = puede_completar_entrega(activo, disponible)
            texto = formatear_progreso(activo, disponible=disponible)

        estado_str = "|g¡LISTO para entregar!|n" if completado else "|y En progreso...|n"
        caller.msg(
            f"\n|w── Contrato Activo ──|n\n"
            f"  {texto}\n"
            f"  Recompensa: |y{r['monedas']}m|n + |c{r['xp']} XP|n\n"
            f"  Estado: {estado_str}\n"
        )

    def _cancelar(self, caller):
        activo = caller.db.contrato_activo
        if not activo:
            caller.msg("|y[Tablón]|n No tienes ningún contrato activo.")
            return
        desc = activo["descripcion"]
        caller.db.contrato_activo = None
        caller.msg(f"|y[Tablón]|n Has abandonado el contrato: \"{desc}\".")

    def _entregar(self, caller):
        from systems.contracts.contracts import (
            puede_completar_kill, puede_completar_entrega,
        )
        activo = caller.db.contrato_activo
        if not activo:
            caller.msg("|y[Tablón]|n No tienes ningún contrato activo.")
            return

        tipo = activo["tipo"]

        if tipo == "kill":
            kills = getattr(caller.db, "kills_totales", 0) or 0
            completado, hechas = puede_completar_kill(activo, kills)
            if not completado:
                faltan = activo["cantidad"] - hechas
                caller.msg(
                    f"|r[Tablón]|n Aún no has cumplido el contrato. "
                    f"Te faltan |w{faltan}|n kills más."
                )
                return
        else:
            objetivo = activo["objetivo"]
            disponible = self._contar_material(caller, objetivo)
            completado, _ = puede_completar_entrega(activo, disponible)
            if not completado:
                faltan = activo["cantidad"] - disponible
                caller.msg(
                    f"|r[Tablón]|n Necesitas |w{faltan}|n más de '{objetivo}'."
                )
                return
            # Consumir los materiales del inventario
            self._consumir_material(caller, objetivo, activo["cantidad"])

        self._dar_recompensa(caller, activo["recompensa"])
        caller.db.contrato_activo = None

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _contar_material(self, caller, nombre_objetivo: str) -> int:
        """Cuenta cuántos objetos con ese nombre hay en el inventario."""
        nombre_lower = nombre_objetivo.lower()
        return sum(
            1 for obj in caller.contents
            if obj.key.lower() == nombre_lower
        )

    def _consumir_material(self, caller, nombre_objetivo: str, cantidad: int):
        """Elimina hasta `cantidad` objetos con ese nombre del inventario."""
        nombre_lower = nombre_objetivo.lower()
        eliminados = 0
        for obj in list(caller.contents):
            if eliminados >= cantidad:
                break
            if obj.key.lower() == nombre_lower:
                obj.delete()
                eliminados += 1

    def _dar_recompensa(self, caller, recompensa: dict):
        from systems.combat.engine import procesar_subida_de_nivel
        from features.combat.handler import _get_stats_base, _set_stat

        monedas = recompensa.get("monedas", 0)
        xp_ganado = recompensa.get("xp", 0)

        monedas_actuales = getattr(caller.db, "monedas", 0) or 0
        caller.db.monedas = monedas_actuales + monedas

        xp_actual = getattr(caller.db, "experiencia", 0) or 0
        caller.db.experiencia = xp_actual + xp_ganado

        # Comprobar subida de nivel
        stats = _get_stats_base(caller)
        subio, nuevos_stats = procesar_subida_de_nivel(stats)
        if subio:
            for k, v in nuevos_stats.items():
                _set_stat(caller, k, v)
            caller.msg(
                f"\n|Y★ ¡SUBISTE AL NIVEL {nuevos_stats['nivel']}!|n\n"
                f"  HP: |w{nuevos_stats['hp_max']}|n  "
                f"FUE: |w{nuevos_stats['fuerza']}|n  "
                f"DEF: |w{nuevos_stats['defensa']}|n\n"
            )

        caller.msg(
            f"|g[Tablón]|n |w¡Contrato completado!|n\n"
            f"  Recompensa: |y+{monedas} monedas|n · |c+{xp_ganado} XP|n"
        )

        # Logros
        try:
            from features.achievements.commands import comprobar_y_notificar
            comprobar_y_notificar(caller)
        except Exception:
            pass


# --------------------------------------------------------------------------- #
#  CmdSet
# --------------------------------------------------------------------------- #

class ContractCmdSet(CmdSet):
    key = "ContractCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdTablon())
