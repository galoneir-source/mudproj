"""
features/skills/commands.py

Comandos del árbol de habilidades:
  habilidades  — ver el árbol completo con estado de cada habilidad
  aprender     — desbloquear una habilidad del árbol
"""
from evennia import Command, CmdSet

from systems.skills.trees import HABILIDADES, RAMAS, HABILIDADES_INICIALES
from systems.skills.engine import (
    puntos_disponibles,
    puntos_gastados,
    puede_aprender,
    aprender,
    buscar_habilidad,
    habilidades_por_rama,
)


def _get_desbloqueadas(caller) -> set:
    v = getattr(caller.db, "habilidades_desbloqueadas", None)
    if v is None:
        return set(HABILIDADES_INICIALES)
    return set(v)


def _get_nivel(caller) -> int:
    return getattr(caller.db, "nivel", 1) or 1


class CmdHabilidades(Command):
    """
    Ver el árbol de habilidades y puntos disponibles.

    Uso:
      habilidades                — árbol completo
      habilidades <rama>         — solo una rama (guerrero, explorador, mago)
      habilidades <habilidad>    — detalle de una habilidad concreta

    Ejemplo:
      habilidades
      habilidades guerrero
      habilidades golpe maestro
    """
    key = "habilidades"
    aliases = ["skills"]
    locks = "cmd:all()"
    help_category = "Habilidades"

    def func(self):
        caller = self.caller
        args = self.args.strip().lower()
        desbloqueadas = _get_desbloqueadas(caller)
        nivel = _get_nivel(caller)
        gastados = puntos_gastados(desbloqueadas)
        puntos = puntos_disponibles(nivel, gastados)

        if args in RAMAS:
            self._mostrar_rama(caller, args, desbloqueadas, nivel, puntos)
            return

        if args:
            hid, info = buscar_habilidad(args)
            if not info:
                caller.msg(f"No se encontró la habilidad '|w{args}|n'.")
                return
            self._mostrar_detalle(caller, hid, info, desbloqueadas, nivel, puntos)
            return

        lineas = [
            f"\n|w{'='*48}|n",
            f"  |cÁrbol de Habilidades — {caller.key}|n",
            f"  Nivel: {nivel}   |gPuntos disponibles: {puntos}|n",
            f"|w{'='*48}|n",
        ]
        for rama in RAMAS:
            lineas.append(f"\n  |Y[{rama.upper()}]|n")
            for hid, info in habilidades_por_rama(rama):
                estado = self._estado(hid, desbloqueadas, nivel)
                tipo_tag = "|y(P)|n" if info["tipo"] == "pasiva" else "   "
                lineas.append(
                    f"    {tipo_tag} {estado} |w{info['nombre']}|n "
                    f"(nv.{info['nivel_req']}, {info['coste']}pt) — {info['descripcion']}"
                )
        lineas += [
            f"\n|w{'='*48}|n",
            f"  |y(P)|n=pasiva  |g[✓]|n=aprendida  |w[ ]|n=disponible  |r[✗]|n=bloqueada",
            f"  Usa |waprender <habilidad>|n para desbloquear.",
            f"|w{'='*48}|n\n",
        ]
        caller.msg("\n".join(lineas))

    def _estado(self, hid, desbloqueadas, nivel) -> str:
        if hid in desbloqueadas:
            return "|g[✓]|n"
        info = HABILIDADES[hid]
        if nivel < info["nivel_req"]:
            return "|r[✗]|n"
        for req in info["requisitos"]:
            if req not in desbloqueadas:
                return "|r[✗]|n"
        return "|w[ ]|n"

    def _mostrar_rama(self, caller, rama, desbloqueadas, nivel, puntos):
        lineas = [f"\n  |Y[{rama.upper()}]|n  —  Puntos disponibles: |g{puntos}|n\n"]
        for hid, info in habilidades_por_rama(rama):
            estado = self._estado(hid, desbloqueadas, nivel)
            tipo_tag = "|y(Pasiva)|n" if info["tipo"] == "pasiva" else "|c(Activa)|n"
            reqs = ", ".join(
                HABILIDADES.get(r, {}).get("nombre", r) for r in info["requisitos"]
            ) or "—"
            lineas += [
                f"  {estado} |w{info['nombre']}|n  {tipo_tag}",
                f"       Nv.{info['nivel_req']}  Coste: {info['coste']}pt  Req: {reqs}",
                f"       {info['descripcion']}",
                "",
            ]
        caller.msg("\n".join(lineas))

    def _mostrar_detalle(self, caller, hid, info, desbloqueadas, nivel, puntos):
        estado = self._estado(hid, desbloqueadas, nivel)
        puede, err = puede_aprender(hid, desbloqueadas, nivel)
        reqs = ", ".join(
            HABILIDADES.get(r, {}).get("nombre", r) for r in info["requisitos"]
        ) or "Ninguno"
        lineas = [
            f"\n|w{'='*42}|n",
            f"  {estado} |Y{info['nombre']}|n  ({info['rama'].capitalize()})",
            f"  Nivel requerido : {info['nivel_req']}",
            f"  Coste           : {info['coste']} punto(s)",
            f"  Tipo            : {info['tipo'].capitalize()}",
            f"  Requisitos      : {reqs}",
            f"  Descripción     : {info['descripcion']}",
        ]
        if hid not in desbloqueadas:
            if puede:
                lineas.append(f"\n  |g¡Puedes aprenderla!|n  Puntos: {puntos}")
                lineas.append(f"  Usa: |waprender {info['nombre'].lower()}|n")
            else:
                lineas.append(f"\n  |rNo disponible:|n {err}")
        lineas.append(f"|w{'='*42}|n\n")
        caller.msg("\n".join(lineas))


class CmdAprender(Command):
    """
    Aprender una habilidad del árbol de progresión.

    Uso:
      aprender <habilidad>

    Ejemplo:
      aprender embestida
      aprender escudo de fe
      aprender dardo magico

    Ganas 1 punto de habilidad por nivel (a partir del nivel 2).
    Las habilidades iniciales (golpe fuerte, golpe rápido) son gratuitas.
    Usa |whabilidades|n para ver el árbol completo.
    """
    key = "aprender"
    aliases = ["learn"]
    locks = "cmd:all()"
    help_category = "Habilidades"

    def func(self):
        caller = self.caller
        args = self.args.strip()
        if not args:
            caller.msg("¿Qué habilidad quieres aprender? Uso: |waprender <habilidad>|n")
            return

        hid, info = buscar_habilidad(args)
        if not info:
            caller.msg(
                f"No se encontró la habilidad '|w{args}|n'. "
                f"Usa |whabilidades|n para ver las disponibles."
            )
            return

        desbloqueadas = _get_desbloqueadas(caller)
        nivel = _get_nivel(caller)

        exito, nuevas, err = aprender(hid, desbloqueadas, nivel)
        if not exito:
            caller.msg(f"|rNo puedes aprender {info['nombre']}:|n {err}")
            return

        caller.db.habilidades_desbloqueadas = list(nuevas)

        efecto_pasivo = info.get("efecto_pasivo", {})
        for stat, bonus in efecto_pasivo.items():
            from systems.combat.engine import STAT_DEFAULTS
            actual = getattr(caller.db, stat, None)
            if actual is None:
                actual = STAT_DEFAULTS.get(stat, 0)
            setattr(caller.db, stat, actual + bonus)
            caller.msg(f"  |g+{bonus} {stat.capitalize()}|n (efecto pasivo)")

        tipo_tag = "pasiva" if info["tipo"] == "pasiva" else "activa"
        caller.msg(
            f"\n|g¡Has aprendido {info['nombre']}!|n ({tipo_tag})\n"
            f"  {info['descripcion']}\n"
        )
        if info["tipo"] == "activa":
            nombre_display = info["nombre"].lower()
            caller.msg(f"  Úsala en combate: |whabilidad {nombre_display} <objetivo>|n\n")


class SkillCmdSet(CmdSet):
    key = "SkillCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdHabilidades())
        self.add(CmdAprender())
