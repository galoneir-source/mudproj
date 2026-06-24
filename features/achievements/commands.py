"""
features/achievements/commands.py

Comandos del sistema de logros y títulos:
  logros [categoria]  — muestra todos los logros con estado de desbloqueo
  titulo <titulo>     — establece el título activo del personaje

También expone comprobar_y_notificar(), función utilitaria que comprueban
logros nuevos tras cualquier evento y notifica al jugador.
"""
from evennia import Command, CmdSet

from systems.achievements.achievements import (
    LOGROS,
    nuevos_logros,
    titulos_disponibles,
)

_ORDEN_CATS = [
    "progresion", "misiones", "combate", "habilidades",
    "encantamiento", "reputacion", "crafteo", "economia", "clase",
]
_NOMBRES_CATS = {
    "progresion":   "Progresión",
    "misiones":     "Misiones",
    "combate":      "Combate",
    "habilidades":  "Habilidades",
    "encantamiento":"Encantamiento",
    "reputacion":   "Reputación",
    "crafteo":      "Crafteo",
    "economia":     "Economía",
    "clase":        "Clase",
}


def _extraer_datos(caller) -> dict:
    """Construye el dict de estado del personaje para verificar logros."""
    quests = dict(getattr(caller.db, "quests", {}) or {})
    quests_entregadas = sum(
        1 for q in quests.values() if q.get("estado") == "entregada"
    )
    return {
        "nivel":             getattr(caller.db, "nivel", 1) or 1,
        "quests_entregadas": quests_entregadas,
        "habilidades":       list(getattr(caller.db, "habilidades_desbloqueadas", []) or []),
        "reputacion":        dict(getattr(caller.db, "reputacion", {}) or {}),
        "kills_totales":     getattr(caller.db, "kills_totales", 0) or 0,
        "jefes_derrotados":  list(getattr(caller.db, "jefes_derrotados", []) or []),
        "objetos_crafteados":getattr(caller.db, "objetos_crafteados", 0) or 0,
        "encantamiento_max": getattr(caller.db, "encantamiento_max", 0) or 0,
        "banco_usado":       bool(getattr(caller.db, "banco_usado", False)),
        "clase":             getattr(caller.db, "clase", None) or "",
    }


def comprobar_y_notificar(caller):
    """
    Comprueba si el jugador ha desbloqueado logros nuevos y se los notifica.
    Llama esta función después de cualquier evento que pueda cumplir condiciones
    (kill, nivel, quest entregada, crafteo, encantamiento, habilidad, banco).
    """
    ya = list(getattr(caller.db, "logros", []) or [])
    datos = _extraer_datos(caller)
    nuevos = nuevos_logros(datos, ya)
    if not nuevos:
        return
    caller.db.logros = ya + nuevos
    for lid in nuevos:
        logro = LOGROS[lid]
        lineas = [
            f"\n|Y✦ ¡LOGRO DESBLOQUEADO!|n  |w{logro['nombre']}|n",
            f"   {logro['descripcion']}",
        ]
        if logro.get("titulo"):
            lineas.append(
                f"   |cTítulo desbloqueado:|n |Y{logro['titulo']}|n"
                f"  (usa: |wtitulo {logro['titulo']}|n)"
            )
        caller.msg("\n".join(lineas) + "\n")


class CmdLogros(Command):
    """
    Ver tu registro de logros y títulos desbloqueados.

    Uso:
      logros                — muestra todos los logros
      logros <categoría>    — filtra por categoría

    Categorías disponibles:
      progresion, misiones, combate, habilidades,
      encantamiento, reputacion, crafteo, economia

    Ejemplo:
      logros combate
      logros habilidades
    """
    key = "logros"
    aliases = ["achievements", "logro"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        filtro = self.args.strip().lower() if self.args.strip() else None

        desbloqueados = set(getattr(caller.db, "logros", []) or [])
        titulo_activo = getattr(caller.db, "titulo_activo", None)

        sep = "|w" + "─" * 54 + "|n"
        lineas = [f"\n{sep}", "  |cRegistro de Logros|n"]
        if titulo_activo:
            lineas.append(f"  Título activo: |Y{titulo_activo}|n")
        lineas.append(sep)

        cats = [filtro] if filtro else _ORDEN_CATS
        total = desbloq = 0

        for cat in cats:
            en_cat = [(lid, l) for lid, l in LOGROS.items() if l["categoria"] == cat]
            if not en_cat:
                continue
            lineas.append(f"\n  |w{_NOMBRES_CATS.get(cat, cat.capitalize())}|n")
            for lid, logro in en_cat:
                total += 1
                if lid in desbloqueados:
                    desbloq += 1
                    titulo_tag = f"  |c[{logro['titulo']}]|n" if logro.get("titulo") else ""
                    lineas.append(
                        f"    |g✔|n |w{logro['nombre']}|n  —  {logro['descripcion']}{titulo_tag}"
                    )
                else:
                    lineas.append(
                        f"    |x✗ {logro['nombre']}  —  {logro['descripcion']}|n"
                    )

        lineas.append(f"\n{sep}")
        lineas.append(f"  Completados: |w{desbloq}/{total}|n")
        tits = titulos_disponibles(list(desbloqueados))
        if tits:
            lineas.append(f"  Títulos disponibles: {', '.join(f'|Y{t}|n' for t in tits)}")
        lineas.append(f"{sep}\n")
        caller.msg("\n".join(lineas))


class CmdTitulo(Command):
    """
    Establecer tu título activo de personaje.

    Uso:
      titulo <titulo>   — activa el título indicado
      titulo            — elimina el título activo

    El título aparece junto a tu nombre en el comando |wperfil|n.
    Solo puedes usar títulos que hayas desbloqueado mediante logros.

    Ejemplo:
      titulo el Héroe
      titulo la Leyenda
      titulo          (para quitarlo)
    """
    key = "titulo"
    aliases = ["title"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        arg = self.args.strip()

        if not arg:
            caller.db.titulo_activo = None
            caller.msg("Has eliminado tu título activo.")
            return

        desbloqueados = list(getattr(caller.db, "logros", []) or [])
        disponibles = titulos_disponibles(desbloqueados)

        match = next((t for t in disponibles if t.lower() == arg.lower()), None)
        if not match:
            if disponibles:
                caller.msg(
                    f"No tienes el título '|w{arg}|n'.\n"
                    f"Tus títulos: {', '.join(f'|Y{t}|n' for t in disponibles)}"
                )
            else:
                caller.msg(
                    "Aún no has desbloqueado ningún título. "
                    "Completa logros para obtenerlos (usa |wlogros|n)."
                )
            return

        caller.db.titulo_activo = match
        caller.msg(f"Título activo: |Y{match}|n  — Aparecerá en tu |wperfil|n.")


class AchievementCmdSet(CmdSet):
    key = "AchievementCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdLogros())
        self.add(CmdTitulo())
