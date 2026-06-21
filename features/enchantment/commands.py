"""
features/enchantment/commands.py

Comandos del sistema de encantamiento:
  encantar [objeto]  — encanta un ítem subiendo su nivel (+1 → +2 → +3)
                       Sin argumento muestra los ítems mejorables y sus costes.
"""
import re
from collections.abc import Mapping

from evennia import Command, CmdSet

from systems.enchantment.enchantment import (
    MAX_ENCANTAMIENTO,
    delta_encantamiento,
    coste_encantamiento,
    puede_encantar,
    verificar_ingredientes_encantamiento,
    texto_coste,
)


def _base_key(key: str) -> str:
    """Elimina el sufijo ' +N' del nombre de un ítem encantado."""
    return re.sub(r"\s*\+\d+$", "", key)


def _inventario_conteo(caller) -> dict[str, int]:
    """Devuelve {nombre_lower: cantidad} de todos los objetos en el inventario."""
    conteo: dict[str, int] = {}
    for obj in caller.contents:
        nombre = obj.key.lower()
        conteo[nombre] = conteo.get(nombre, 0) + 1
    return conteo


def _aplicar_delta(caller, delta: dict, signo: int = 1):
    """Aplica o revierte un delta de stats al personaje."""
    for stat, valor in delta.items():
        actual = getattr(caller.db, stat, None)
        if actual is not None:
            nuevo = actual + signo * valor
            setattr(caller.db, stat, nuevo)
            if stat == "hp_max" and signo == 1:
                caller.db.hp = (getattr(caller.db, "hp", 0) or 0) + valor


def _esta_equipado(caller, item) -> bool:
    """True si el ítem está actualmente en un slot de equipamiento."""
    eq = getattr(caller.db, "equipamiento", None)
    if not isinstance(eq, Mapping):
        return False
    return any(v is not None and v.id == item.id for v in eq.values())


class CmdEncantar(Command):
    """
    Encanta un objeto de tu inventario, mejorando sus estadísticas.

    Uso:
      encantar            — lista los ítems que puedes encantar y sus costes
      encantar <objeto>   — encanta el ítem indicado (consume materiales)

    Cada ítem puede encantarse hasta +3. Los materiales requeridos aumentan
    con cada nivel. Los ítems equipados reciben el bonus inmediatamente.

    Niveles y costes:
      Arma     +1: mineral de hierro ×2
               +2: mineral de hierro ×2 + núcleo de piedra ×1
               +3: núcleo de piedra ×1 + núcleo arcano ×1
      Armadura +1: escama de lagarto ×2
               +2: escama de lagarto ×2 + fragmento de alma ×1
               +3: fragmento de alma ×1 + cenizas arcanas ×2
      Accesorio+1: gema en bruto ×1
               +2: gema en bruto ×1 + cristal sagrado ×1
               +3: cristal sagrado ×1 + núcleo arcano ×1

    Ejemplo:
      encantar espada de hierro
      encantar manto arcano
    """
    key = "encantar"
    aliases = ["enchant", "encantamiento"]
    locks = "cmd:all()"
    help_category = "Encantamiento"

    def func(self):
        caller = self.caller

        if not self.args:
            self._mostrar_encantables(caller)
            return

        from typeclasses.objects import Equipo

        item = caller.search(
            self.args.strip(),
            location=caller,
            nofound_string=f"No tienes '{self.args.strip()}' en tu inventario.",
        )
        if not item:
            return

        if not isinstance(item, Equipo):
            caller.msg(f"|w{item.key}|n no es un objeto equipable.")
            return

        slot = item.db.slot or "accesorio"
        nivel_actual = item.db.encantamiento or 0

        ok, motivo = puede_encantar(nivel_actual)
        if not ok:
            caller.msg(motivo)
            return

        nivel_nuevo = nivel_actual + 1
        bonuses_actuales = dict(item.db.bonuses or {})
        delta = delta_encantamiento(slot, bonuses_actuales)

        if not delta:
            caller.msg(
                f"|w{item.key}|n no tiene estadísticas mejorables con el encantamiento."
            )
            return

        inventario = _inventario_conteo(caller)
        ingredientes_ok, faltantes = verificar_ingredientes_encantamiento(
            slot, nivel_nuevo, inventario
        )

        if not ingredientes_ok:
            lineas = [f"Necesitas más materiales para encantar |w{item.key}|n a +{nivel_nuevo}:"]
            for ingr, cant in faltantes.items():
                lineas.append(f"  |r{ingr}|n: te faltan {cant}")
            caller.msg("\n".join(lineas))
            return

        # Consumir ingredientes
        coste = coste_encantamiento(slot, nivel_nuevo)
        for ingr_key, cant in coste.items():
            restante = cant
            for obj in list(caller.contents):
                if restante <= 0:
                    break
                if obj.key.lower() == ingr_key.lower():
                    obj.delete()
                    restante -= 1

        # Actualizar bonuses del ítem
        for stat, val in delta.items():
            bonuses_actuales[stat] = bonuses_actuales.get(stat, 0) + val
        item.db.bonuses = bonuses_actuales
        item.db.encantamiento = nivel_nuevo

        # Renombrar ítem
        item.key = f"{_base_key(item.key)} +{nivel_nuevo}"

        # Si está equipado, aplicar el delta al personaje inmediatamente
        if _esta_equipado(caller, item):
            _aplicar_delta(caller, delta, signo=1)
            equipado_txt = " |g(bonus aplicado)|n"
        else:
            equipado_txt = ""

        delta_txt = ", ".join(f"|w{k}|n +{v}" for k, v in delta.items())
        caller.msg(
            f"|g¡Encantamiento completado!|n |w{item.key}|n  "
            f"({delta_txt}){equipado_txt}"
        )
        caller.location.msg_contents(
            f"Una luz plateada envuelve brevemente las manos de {caller.key}.",
            exclude=caller,
        )

        enc_max = getattr(caller.db, "encantamiento_max", 0) or 0
        if nivel_nuevo > enc_max:
            caller.db.encantamiento_max = nivel_nuevo
        from features.achievements.commands import comprobar_y_notificar
        comprobar_y_notificar(caller)

    def _mostrar_encantables(self, caller):
        from typeclasses.objects import Equipo

        items_equipo = [
            obj for obj in caller.contents if isinstance(obj, Equipo)
        ]

        if not items_equipo:
            caller.msg("No tienes ningún objeto equipable en el inventario.")
            return

        sep = "|w" + "─" * 52 + "|n"
        lineas = [f"\n{sep}", "  |cEncantamiento — objetos mejorables|n", sep]

        for item in items_equipo:
            slot = item.db.slot or "accesorio"
            nivel = item.db.encantamiento or 0
            if nivel >= MAX_ENCANTAMIENTO:
                estado = f"|y+{nivel} (máx)|n"
                coste_txt = "—"
            else:
                estado = f"+{nivel}→|g+{nivel+1}|n"
                coste_txt = texto_coste(slot, nivel + 1)
            lineas.append(
                f"  |w{item.key:<28}|n [{slot:<9} {estado}]  {coste_txt}"
            )

        lineas.append(f"{sep}")
        lineas.append("  Usa: |wencantar <objeto>|n")
        lineas.append(f"{sep}\n")
        caller.msg("\n".join(lineas))


class EnchantCmdSet(CmdSet):
    key = "EnchantCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdEncantar())
