"""
features/mounts/commands.py

Comandos del sistema de monturas:
  montura              — estado actual y monturas poseídas
  montura lista        — catálogo completo con requisitos y precios
  montura comprar <X>  — adquirir una montura nueva
  montura invocar <X>  — montar (debe poseerse)
  montura desmontar    — bajar de la montura actual
"""
from evennia import Command, CmdSet

from systems.mounts.mounts import (
    MONTURAS,
    puede_comprar,
    puede_invocar,
    puede_desmontar,
    formatear_estado,
    formatear_catalogo,
)


def _buscar_montura(nombre: str) -> list[str]:
    """Búsqueda parcial e insensible a mayúsculas en el catálogo."""
    nombre_low = nombre.lower()
    exactos = [mid for mid, m in MONTURAS.items() if m["nombre"].lower() == nombre_low]
    if exactos:
        return exactos
    return [mid for mid, m in MONTURAS.items() if nombre_low in m["nombre"].lower()]


class CmdMontura(Command):
    """
    Gestiona tus monturas.

    Uso:
      montura               — estado actual y monturas poseídas
      montura lista         — catálogo completo con requisitos y precios
      montura comprar <X>   — compra una montura por su nombre
      montura invocar <X>   — monta una montura que ya poseas
      montura desmontar     — desmonta tu montura actual

    Ejemplo:
      montura lista
      montura comprar Poni Viejo
      montura invocar Corcel de Guerra
      montura desmontar
    """
    key = "montura"
    aliases = ["mount", "montar", "monturas"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args:
            self._estado(caller)
            return

        subcmd, _, resto = args.partition(" ")
        subcmd = subcmd.lower()

        if subcmd == "lista":
            self._lista(caller)
        elif subcmd == "comprar":
            self._comprar(caller, resto.strip())
        elif subcmd in ("invocar", "llamar", "equipar"):
            self._invocar(caller, resto.strip())
        elif subcmd in ("desmontar", "bajar", "quitar"):
            self._desmontar(caller)
        else:
            # Interpretar todo el args como nombre de montura a invocar
            self._invocar(caller, args.strip())

    # ------------------------------------------------------------------ #

    def _estado(self, caller):
        monturas = list(getattr(caller.db, "monturas", []) or [])
        activa = getattr(caller.db, "montura_activa", None)
        caller.msg(formatear_estado(activa, monturas))

    def _lista(self, caller):
        monturas = list(getattr(caller.db, "monturas", []) or [])
        nivel = int(getattr(caller.db, "nivel", 1) or 1)
        rep = dict(getattr(caller.db, "reputacion", {}) or {})
        monedas = int(getattr(caller.db, "monedas", 0) or 0)
        jefes = dict(getattr(caller.db, "jefes_mundo_derrotados", {}) or {})
        caller.msg(formatear_catalogo(monturas, nivel, rep, monedas, jefes))

    def _comprar(self, caller, nombre: str):
        if not nombre:
            caller.msg("Indica el nombre de la montura: |wmontura comprar <nombre>|n")
            return

        resultados = _buscar_montura(nombre)
        if not resultados:
            caller.msg(f"No se encontró ninguna montura con ese nombre. Usa |wmontura lista|n.")
            return
        if len(resultados) > 1:
            nombres = ", ".join(f"|w{MONTURAS[mid]['nombre']}|n" for mid in resultados)
            caller.msg(f"Varias monturas coinciden: {nombres}. Sé más específico.")
            return

        montura_id = resultados[0]
        monturas = list(getattr(caller.db, "monturas", []) or [])
        nivel = int(getattr(caller.db, "nivel", 1) or 1)
        rep = dict(getattr(caller.db, "reputacion", {}) or {})
        monedas = int(getattr(caller.db, "monedas", 0) or 0)
        jefes = dict(getattr(caller.db, "jefes_mundo_derrotados", {}) or {})

        ok, msg = puede_comprar(montura_id, monedas, nivel, rep, monturas, jefes)
        if not ok:
            caller.msg(f"|rNo puedes comprar esa montura:|n {msg}")
            return

        m = MONTURAS[montura_id]
        caller.db.monturas = monturas + [montura_id]
        if m["coste"] > 0:
            caller.db.monedas = monedas - m["coste"]

        caller.msg(
            f"\n|g¡Montura adquirida!|n |w{m['nombre']}|n\n"
            f"  {m['descripcion']}\n"
            f"  Usa |wmontura invocar {m['nombre']}|n para montarla.\n"
        )
        from features.achievements.commands import comprobar_y_notificar
        comprobar_y_notificar(caller)

    def _invocar(self, caller, nombre: str):
        if not nombre:
            caller.msg("Indica el nombre de la montura: |wmontura invocar <nombre>|n")
            return

        resultados = _buscar_montura(nombre)
        if not resultados:
            caller.msg(f"No se encontró ninguna montura con ese nombre.")
            return
        if len(resultados) > 1:
            nombres = ", ".join(f"|w{MONTURAS[mid]['nombre']}|n" for mid in resultados)
            caller.msg(f"Varias monturas coinciden: {nombres}. Sé más específico.")
            return

        montura_id = resultados[0]
        monturas = list(getattr(caller.db, "monturas", []) or [])

        ok, msg = puede_invocar(montura_id, monturas)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return

        activa = getattr(caller.db, "montura_activa", None)
        m = MONTURAS[montura_id]

        if activa == montura_id:
            caller.msg(f"Ya estás montado en |w{m['nombre']}|n.")
            return

        caller.db.montura_activa = montura_id
        caller.msg(
            f"\n|gMontado en|n |w{m['nombre']}|n.\n"
            f"  {m['descripcion']}\n"
            f"  Bonus activo: |g{', '.join(f'+{v} {stat.upper()[:3]}' for stat, v in m['bonus'].items())}|n\n"
        )

    def _desmontar(self, caller):
        activa = getattr(caller.db, "montura_activa", None)
        ok, msg = puede_desmontar(activa)
        if not ok:
            caller.msg(msg)
            return
        m = MONTURAS.get(activa)
        caller.db.montura_activa = None
        nombre = m["nombre"] if m else activa
        caller.msg(f"Has desmontado de |w{nombre}|n.")


class MountCmdSet(CmdSet):
    key = "MountCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdMontura())
