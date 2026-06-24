"""
features/subclasses/commands.py

Comando del sistema de subclases de personaje:
  subclase  — ver tu subclase actual o elegir una (requiere clase + nivel 5)
"""
from evennia import Command, CmdSet

from systems.subclasses.subclasses import (
    SUBCLASES, NIVEL_MIN_SUBCLASE,
    subclase_valida, subclases_de_clase, puede_elegir_subclase,
)
from systems.combat.engine import STAT_DEFAULTS


class CmdSubclase(Command):
    """
    Ver tu subclase de personaje o elegir una.

    Uso:
      subclase                     — muestra tu subclase actual y las disponibles
      subclase <nombre>            — elige una subclase (requiere nivel 5 y clase)

    Subclases por clase:
      guerrero   → paladín, berserker
      explorador → asesino, cazador
      mago       → hechicero, nigromante

    ¡Solo puedes elegir subclase una vez y a partir del nivel 5!
    """
    key = "subclase"
    aliases = ["especializar", "especialización", "especializacion", "subclass"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = self.args.strip().lower()
        clase = getattr(caller.db, "clase", None)
        subclase_actual = getattr(caller.db, "subclase", None)

        if not args:
            self._mostrar_subclases(caller, clase, subclase_actual)
            return

        nivel = getattr(caller.db, "nivel", 1) or 1
        puede, err = puede_elegir_subclase(nivel, clase, subclase_actual, args)
        if not puede:
            caller.msg(f"|r{err}|n")
            return

        self._aplicar_subclase(caller, args)

    def _mostrar_subclases(self, caller, clase, subclase_actual):
        nivel = getattr(caller.db, "nivel", 1) or 1
        lineas = [
            f"\n|w{'='*50}|n",
            f"  |cSubclases de Personaje|n",
            f"|w{'='*50}|n",
        ]

        if subclase_actual:
            info = SUBCLASES[subclase_actual]
            color = info.get("color", "|n")
            lineas.append(
                f"\n  Tu subclase: {color}{info['nombre']}|n\n"
            )
        elif clase:
            if nivel >= NIVEL_MIN_SUBCLASE:
                lineas.append(
                    f"\n  |yAún no tienes subclase.|n  "
                    f"Usa |wsubclase <nombre>|n para especializarte.\n"
                )
            else:
                lineas.append(
                    f"\n  |xSubclase disponible a partir del nivel {NIVEL_MIN_SUBCLASE} "
                    f"(tienes {nivel}).|n\n"
                )
        else:
            lineas.append(
                "\n  |rNecesitas una clase antes de elegir subclase.|n  "
                "Usa |wclase|n para ver las disponibles.\n"
            )

        if clase:
            subs = subclases_de_clase(clase)
        else:
            subs = SUBCLASES

        for sid, info in subs.items():
            color = info.get("color", "|n")
            bonuses = info["stat_bonus"]
            partes = []
            for stat, val in bonuses.items():
                if stat == "hp_max":
                    partes.append(f"+{val} HP máx.")
                elif stat == "hp":
                    pass
                else:
                    partes.append(f"+{val} {stat.capitalize()[:3]}")
            bonus_txt = ", ".join(partes)
            activo = " |g◄ ACTUAL|n" if sid == subclase_actual else ""
            hab_txt = ", ".join(
                info["habilidades"][i].replace("_", " ").capitalize()
                for i in range(len(info["habilidades"]))
            )
            lineas += [
                f"  {color}[{info['nombre'].upper()}]|n{activo}",
                f"    {info['descripcion']}",
                f"    Bonuses: |w{bonus_txt}|n",
                f"    Habilidades: |w{hab_txt}|n",
                "",
            ]

        if clase and not subclase_actual and nivel >= NIVEL_MIN_SUBCLASE:
            subs_disp = list(subclases_de_clase(clase).keys())
            lineas.append(
                "  Uso: " + "  ".join(f"|wsubclase {s}|n" for s in subs_disp)
            )
        lineas.append(f"|w{'='*50}|n\n")
        caller.msg("\n".join(lineas))

    def _aplicar_subclase(self, caller, subclase_id):
        info = SUBCLASES[subclase_id]
        bonuses = info["stat_bonus"]

        for stat, valor in bonuses.items():
            actual = getattr(caller.db, stat, None)
            if actual is None:
                actual = STAT_DEFAULTS.get(stat, 0)
            setattr(caller.db, stat, actual + valor)

        caller.db.subclase = subclase_id

        color = info.get("color", "|n")
        bonus_lines = []
        for stat, val in bonuses.items():
            if stat == "hp":
                continue
            label = "HP máx." if stat == "hp_max" else stat.capitalize()
            bonus_lines.append(f"  |g+{val} {label}|n")

        caller.msg(
            f"\n|Y¡Has elegido la subclase {color}{info['nombre']}|Y!|n\n"
            f"  {info['descripcion']}\n"
            f"\n  Bonificaciones aplicadas:\n"
            + "\n".join(bonus_lines)
            + f"\n\n  Nuevas habilidades desbloqueadas para aprender:\n"
            + "\n".join(
                f"  |w{h.replace('_', ' ').capitalize()}|n  "
                f"(usa |whabilidades {subclase_id}|n para ver detalles)"
                for h in info["habilidades"]
            )
            + "\n"
        )
        caller.location.msg_contents(
            f"{caller.key} ha elegido su especialización como {info['nombre']}.",
            exclude=caller,
        )


class SubclassCmdSet(CmdSet):
    key = "SubclassCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdSubclase())
