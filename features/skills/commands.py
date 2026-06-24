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


def _get_clase(caller) -> str | None:
    return getattr(caller.db, "clase", None)


def _get_subclase(caller) -> str | None:
    return getattr(caller.db, "subclase", None)


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
        clase = _get_clase(caller)
        subclase = _get_subclase(caller)
        gastados = puntos_gastados(desbloqueadas)
        puntos = puntos_disponibles(nivel, gastados)

        from systems.subclasses.subclasses import SUBCLASES, NIVEL_MIN_SUBCLASE

        if args in RAMAS:
            self._mostrar_rama(caller, args, desbloqueadas, nivel, puntos, clase, subclase)
            return

        if args in SUBCLASES:
            self._mostrar_rama_subclase(caller, args, desbloqueadas, nivel, puntos, subclase)
            return

        if args:
            hid, info = buscar_habilidad(args)
            if not info:
                caller.msg(f"No se encontró la habilidad '|w{args}|n'.")
                return
            self._mostrar_detalle(caller, hid, info, desbloqueadas, nivel, puntos, clase, subclase)
            return

        from systems.classes.classes import CLASES
        cabecera = []
        if clase and clase in CLASES:
            info_clase = CLASES[clase]
            color_clase = info_clase.get("color", "|n")
            cab = f"  Clase: {color_clase}{info_clase['nombre']}|n"
            if subclase and subclase in SUBCLASES:
                info_sub = SUBCLASES[subclase]
                color_sub = info_sub.get("color", "|n")
                cab += f"  →  {color_sub}{info_sub['nombre']}|n"
            cabecera.append(cab)

        lineas = [
            f"\n|w{'='*48}|n",
            f"  |cÁrbol de Habilidades — {caller.key}|n",
            f"  Nivel: {nivel}   |gPuntos disponibles: {puntos}|n",
        ]
        lineas += cabecera
        lineas.append(f"|w{'='*48}|n")

        for rama in RAMAS:
            lineas.append(f"\n  |Y[{rama.upper()}]|n")
            for hid, info in habilidades_por_rama(rama):
                estado = self._estado(hid, desbloqueadas, nivel, clase, subclase)
                tipo_tag = "|y(P)|n" if info["tipo"] == "pasiva" else "   "
                lineas.append(
                    f"    {tipo_tag} {estado} |w{info['nombre']}|n "
                    f"(nv.{info['nivel_req']}, {info['coste']}pt) — {info['descripcion']}"
                )

        # Sección de subclase
        if subclase and subclase in SUBCLASES:
            info_sub = SUBCLASES[subclase]
            color_sub = info_sub.get("color", "|n")
            lineas.append(f"\n  |Y[SUBCLASE: {color_sub}{info_sub['nombre'].upper()}|Y]|n")
            for hid, info in habilidades_por_rama(subclase):
                estado = self._estado(hid, desbloqueadas, nivel, clase, subclase)
                tipo_tag = "|y(P)|n" if info["tipo"] == "pasiva" else "   "
                lineas.append(
                    f"    {tipo_tag} {estado} |w{info['nombre']}|n "
                    f"(nv.{info['nivel_req']}, {info['coste']}pt) — {info['descripcion']}"
                )
        elif clase and not subclase:
            if nivel >= NIVEL_MIN_SUBCLASE:
                lineas.append(f"\n  |Y[SUBCLASE]|n  Usa |wsubclase|n para especializarte.")
            else:
                lineas.append(
                    f"\n  |Y[SUBCLASE]|n  "
                    f"|xDisponible a nivel {NIVEL_MIN_SUBCLASE}.|n"
                )

        leyenda_clase = "  |m[C]|n=clase" if clase else ""
        leyenda_sub = "  |x[S]|n=subclase" if clase else ""
        lineas += [
            f"\n|w{'='*48}|n",
            f"  |y(P)|n=pasiva  |g[✓]|n=aprendida  |w[ ]|n=disponible"
            f"  |r[✗]|n=bloqueada{leyenda_clase}{leyenda_sub}",
            f"  Usa |waprender <habilidad>|n para desbloquear.",
            f"|w{'='*48}|n\n",
        ]
        caller.msg("\n".join(lineas))

    def _estado(self, hid, desbloqueadas, nivel, clase=None, subclase=None) -> str:
        if hid in desbloqueadas:
            return "|g[✓]|n"
        info = HABILIDADES[hid]
        rama = info.get("rama", "")
        from systems.subclasses.subclasses import SUBCLASES
        if rama in SUBCLASES:
            if not subclase or rama != subclase:
                return "|x[S]|n"
        elif clase:
            from systems.classes.classes import puede_aprender_clase
            puede_clase, _ = puede_aprender_clase(hid, clase)
            if not puede_clase:
                return "|m[C]|n"
        if nivel < info["nivel_req"]:
            return "|r[✗]|n"
        for req in info["requisitos"]:
            if req not in desbloqueadas:
                return "|r[✗]|n"
        return "|w[ ]|n"

    def _mostrar_rama(self, caller, rama, desbloqueadas, nivel, puntos, clase=None, subclase=None):
        lineas = [f"\n  |Y[{rama.upper()}]|n  —  Puntos disponibles: |g{puntos}|n\n"]
        for hid, info in habilidades_por_rama(rama):
            estado = self._estado(hid, desbloqueadas, nivel, clase, subclase)
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

    def _mostrar_rama_subclase(self, caller, rama_sub, desbloqueadas, nivel, puntos, subclase=None):
        from systems.subclasses.subclasses import SUBCLASES
        info_sub = SUBCLASES.get(rama_sub, {})
        color = info_sub.get("color", "|n")
        nombre_sub = info_sub.get("nombre", rama_sub.capitalize())
        lineas = [
            f"\n  |Y[SUBCLASE: {color}{nombre_sub.upper()}|Y]|n  "
            f"—  Puntos disponibles: |g{puntos}|n\n"
        ]
        for hid, info in habilidades_por_rama(rama_sub):
            estado = self._estado(hid, desbloqueadas, nivel, None, subclase)
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

    def _mostrar_detalle(self, caller, hid, info, desbloqueadas, nivel, puntos, clase=None, subclase=None):
        estado = self._estado(hid, desbloqueadas, nivel, clase, subclase)
        puede, err = puede_aprender(hid, desbloqueadas, nivel, clase=clase, subclase=subclase)
        reqs = ", ".join(
            HABILIDADES.get(r, {}).get("nombre", r) for r in info["requisitos"]
        ) or "Ninguno"
        from systems.subclasses.subclasses import SUBCLASES
        rama = info.get("rama", "")
        rama_display = SUBCLASES[rama]["nombre"] if rama in SUBCLASES else rama.capitalize()
        lineas = [
            f"\n|w{'='*42}|n",
            f"  {estado} |Y{info['nombre']}|n  ({rama_display})",
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
        clase = _get_clase(caller)
        subclase = _get_subclase(caller)

        exito, nuevas, err = aprender(hid, desbloqueadas, nivel, clase=clase, subclase=subclase)
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

        from features.achievements.commands import comprobar_y_notificar
        comprobar_y_notificar(caller)


class SkillCmdSet(CmdSet):
    key = "SkillCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdHabilidades())
        self.add(CmdAprender())
