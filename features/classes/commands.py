"""
features/classes/commands.py

Comando del sistema de clases de personaje:
  clase  — ver tu clase actual o elegir una (solo nivel 1, solo una vez)
"""
from evennia import Command, CmdSet

from systems.classes.classes import CLASES, clase_valida
from systems.combat.engine import STAT_DEFAULTS


class CmdClase(Command):
    """
    Ver tu clase de personaje o elegir una.

    Uso:
      clase                    — muestra tu clase actual y las disponibles
      clase <nombre>           — elige una clase (solo a nivel 1, solo una vez)

    Clases disponibles:
      guerrero    — +3 FUE, +2 CON, +1 DEF, +20 HP máx.
      explorador  — +4 DES, +1 CON
      mago        — +5 INT

    Cada clase restringe el árbol de habilidades a su rama.
    ¡Solo puedes elegir clase una vez y a nivel 1!
    """
    key = "clase"
    aliases = ["class", "vocacion", "vocación"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = self.args.strip().lower()
        clase_actual = getattr(caller.db, "clase", None)

        if not args:
            self._mostrar_clases(caller, clase_actual)
            return

        if clase_actual:
            nombre = CLASES[clase_actual]["nombre"]
            caller.msg(
                f"|rYa tienes la clase |w{nombre}|r asignada.|n "
                f"No es posible cambiarla."
            )
            return

        nivel = getattr(caller.db, "nivel", 1) or 1
        if nivel > 1:
            caller.msg("|rSolo puedes elegir clase cuando eres nivel 1.|n")
            return

        if not clase_valida(args):
            nombres = ", ".join(CLASES.keys())
            caller.msg(
                f"|rClase '|w{args}|r' no existe.|n  Elige entre: {nombres}"
            )
            return

        self._aplicar_clase(caller, args)

    def _mostrar_clases(self, caller, clase_actual):
        lineas = [
            f"\n|w{'='*48}|n",
            f"  |cClases de Personaje|n",
            f"|w{'='*48}|n",
        ]

        if clase_actual:
            info = CLASES[clase_actual]
            color = info.get("color", "|n")
            lineas.append(
                f"\n  Tu clase: {color}{info['nombre']}|n"
                f"  |x(rama: {info['rama'].capitalize()})|n\n"
            )
        else:
            nivel = getattr(caller.db, "nivel", 1) or 1
            if nivel > 1:
                lineas.append(
                    "\n  |rNo tienes clase y ya no puedes elegir "
                    "(requiere nivel 1).|n\n"
                )
            else:
                lineas.append(
                    "\n  |yAún no has elegido clase.|n  "
                    "Usa |wclase <nombre>|n para elegir.\n"
                )

        for cid, info in CLASES.items():
            color = info.get("color", "|n")
            bonuses = info["stat_bonus"]
            partes = []
            for stat, val in bonuses.items():
                if stat == "hp_max":
                    partes.append(f"+{val} HP máx.")
                elif stat == "hp":
                    pass  # hp_max ya lo muestra
                else:
                    partes.append(f"+{val} {stat.capitalize()[:3]}")
            bonus_txt = ", ".join(partes)
            activo = " |g◄ ACTUAL|n" if cid == clase_actual else ""
            lineas += [
                f"  {color}[{info['nombre'].upper()}]|n{activo}",
                f"    {info['descripcion']}",
                f"    Bonuses: |w{bonus_txt}|n   "
                f"|xRama restringida: {info['rama'].capitalize()}|n",
                "",
            ]

        if not clase_actual:
            lineas.append(
                "  Uso: |wclase guerrero|n  |wclase explorador|n  |wclase mago|n"
            )
        lineas.append(f"|w{'='*48}|n\n")
        caller.msg("\n".join(lineas))

    def _aplicar_clase(self, caller, clase_id):
        info = CLASES[clase_id]
        bonuses = info["stat_bonus"]

        for stat, valor in bonuses.items():
            actual = getattr(caller.db, stat, None)
            if actual is None:
                actual = STAT_DEFAULTS.get(stat, 0)
            setattr(caller.db, stat, actual + valor)

        caller.db.clase = clase_id

        color = info.get("color", "|n")
        bonus_lines = []
        for stat, val in bonuses.items():
            if stat == "hp":
                continue
            label = "HP máx." if stat == "hp_max" else stat.capitalize()
            bonus_lines.append(f"  |g+{val} {label}|n")

        caller.msg(
            f"\n|Y¡Has elegido la clase {color}{info['nombre']}|Y!|n\n"
            f"  {info['descripcion']}\n"
            f"\n  Bonificaciones aplicadas:\n"
            + "\n".join(bonus_lines)
            + f"\n\n  Tu árbol de habilidades está ahora restringido "
            f"a la rama |w{info['rama'].capitalize()}|n.\n"
            f"  Usa |whabilidades|n para ver las habilidades disponibles.\n"
        )
        caller.location.msg_contents(
            f"{caller.key} ha elegido su camino como {info['nombre']}.",
            exclude=caller,
        )

        from features.achievements.commands import comprobar_y_notificar
        comprobar_y_notificar(caller)


class ClassCmdSet(CmdSet):
    key = "ClassCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdClase())
