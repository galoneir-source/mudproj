"""
features/equipment/commands.py

Comandos de equipamiento:
  equipar   — equipar un objeto del inventario
  desequipar — desequipar un slot o un objeto concreto
  equipo    — ver qué llevas equipado
"""
from collections.abc import Mapping
from evennia import Command, CmdSet


SLOTS = ("arma", "armadura", "accesorio")


def _get_equipamiento(char) -> dict:
    """Devuelve el dict de equipamiento del personaje, inicializándolo si falta."""
    eq = getattr(char.db, "equipamiento", None)
    # _SaverDict de Evennia es MutableMapping, no subclase de dict
    if not isinstance(eq, Mapping):
        eq = {s: None for s in SLOTS}
        char.db.equipamiento = eq
    # Asegura que existen todos los slots; persiste si se añadió alguno
    added = False
    for s in SLOTS:
        if s not in eq:
            eq[s] = None
            added = True
    if added:
        char.db.equipamiento = eq
    return eq


def _aplicar_bonuses(char, bonuses: dict, signo: int = 1):
    """Suma (signo=+1) o resta (signo=-1) los bonuses de un item a los stats del personaje."""
    for stat, valor in bonuses.items():
        actual = getattr(char.db, stat, None)
        if actual is not None:
            nuevo = actual + signo * valor
            setattr(char.db, stat, nuevo)
            if stat == "hp_max":
                hp = getattr(char.db, "hp", 0) or 0
                if signo == 1:
                    char.db.hp = hp + valor
                else:
                    char.db.hp = min(hp, nuevo)


# --------------------------------------------------------------------------- #
#  equipar
# --------------------------------------------------------------------------- #

class CmdEquipar(Command):
    """
    Equipar un objeto del inventario.

    Uso:
      equipar <objeto>

    Si ya tienes algo equipado en ese slot, se intercambia automáticamente.

    Ejemplo:
      equipar espada de hierro
      equipar armadura de cuero
    """
    key = "equipar"
    aliases = ["equip", "ponerse"]
    locks = "cmd:all()"
    help_category = "Equipamiento"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("¿Qué quieres equipar? Uso: |wequipar <objeto>|n")
            return

        # Buscar en inventario (contenido del personaje que no sea un exit)
        item = caller.search(
            self.args.strip(),
            location=caller,
            nofound_string=f"No tienes '{self.args.strip()}' en tu inventario.",
        )
        if not item:
            return

        # Verificar que es Equipo
        from typeclasses.objects import Equipo
        if not isinstance(item, Equipo):
            caller.msg(f"{item.key} no es un objeto equipable.")
            return

        slot = item.db.slot or "accesorio"
        eq = _get_equipamiento(caller)

        # Reequipar el mismo objeto que ya está puesto: el item nunca
        # cambia de location al equiparse (sigue en el inventario), así que
        # `equipar <objeto ya equipado>` lo encuentra con normalidad. Sin
        # este corte, el bloque de abajo no lo trata como una sustitución
        # (item == actual) y aplica sus bonuses una vez más sobre los que
        # ya están activos, acumulándolos sin límite con cada repetición.
        actual = eq.get(slot)
        if actual == item:
            caller.msg(f"Ya tienes |w{item.key}|n equipado.")
            return

        # Desequipar el item actual en ese slot si lo hay
        if actual and actual != item:
            bonuses_previos = actual.db.bonuses or {}
            _aplicar_bonuses(caller, bonuses_previos, signo=-1)
            actual.location = caller  # vuelve al inventario
            caller.msg(f"Desequipas |w{actual.key}|n y lo metes en tu mochila.")

        # Equipar el nuevo item
        bonuses = item.db.bonuses or {}
        _aplicar_bonuses(caller, bonuses, signo=1)
        eq[slot] = item
        caller.db.equipamiento = eq
        # Mover el item al "slot" (lo dejamos en el inventario del personaje
        # pero marcado como equipado; no cambia location en Evennia)

        if bonuses:
            bonus_txt = ", ".join(f"{k}+{v}" for k, v in bonuses.items())
            caller.msg(f"Equipas |w{item.key}|n en slot |c{slot}|n. ({bonus_txt})")
        else:
            caller.msg(f"Equipas |w{item.key}|n en slot |c{slot}|n.")

        caller.location.msg_contents(
            f"{caller.key} equipa {item.key}.",
            exclude=caller,
        )


# --------------------------------------------------------------------------- #
#  desequipar
# --------------------------------------------------------------------------- #

class CmdDesequipar(Command):
    """
    Desequipar un objeto equipado.

    Uso:
      desequipar <slot>
      desequipar <nombre del objeto>

    Slots válidos: arma, armadura, accesorio

    Ejemplo:
      desequipar arma
      desequipar espada de hierro
    """
    key = "desequipar"
    aliases = ["unequip", "quitarse"]
    locks = "cmd:all()"
    help_category = "Equipamiento"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("¿Qué quieres desequipar? Uso: |wdesequipar <slot o nombre>|n")
            return

        arg = self.args.strip().lower()
        eq = _get_equipamiento(caller)

        # Intentar por slot directo
        if arg in SLOTS:
            item = eq.get(arg)
            if not item:
                caller.msg(f"No tienes nada equipado en el slot |c{arg}|n.")
                return
            self._desequipar_item(caller, item, arg, eq)
            return

        # Intentar por nombre del objeto: coincidencia exacta primero, y si
        # hay varias parciales, avisar en vez de desequipar la primera que
        # encuentre (mismo patrón ya corregido en banco/tienda/grupo).
        equipados = [(slot, item) for slot, item in eq.items() if item]
        exactos = [(slot, item) for slot, item in equipados if item.key.lower() == arg]
        if len(exactos) == 1:
            slot, item = exactos[0]
            self._desequipar_item(caller, item, slot, eq)
            return

        parciales = [(slot, item) for slot, item in equipados if arg in item.key.lower()]
        if len(parciales) > 1:
            nombres = ", ".join(item.key for _slot, item in parciales)
            caller.msg(f"Nombre ambiguo: {nombres}. Sé más específico.")
            return
        if len(parciales) == 1:
            slot, item = parciales[0]
            self._desequipar_item(caller, item, slot, eq)
            return

        caller.msg(f"No tienes equipado ningún objeto llamado '{self.args.strip()}'.")

    def _desequipar_item(self, caller, item, slot, eq):
        bonuses = item.db.bonuses or {}
        _aplicar_bonuses(caller, bonuses, signo=-1)
        eq[slot] = None
        caller.db.equipamiento = eq
        caller.msg(f"Desequipas |w{item.key}|n del slot |c{slot}|n.")
        caller.location.msg_contents(
            f"{caller.key} desequipa {item.key}.",
            exclude=caller,
        )


# --------------------------------------------------------------------------- #
#  equipo (ver equipamiento actual)
# --------------------------------------------------------------------------- #

class CmdEquipo(Command):
    """
    Ver qué tienes equipado actualmente.

    Uso:
      equipo
    """
    key = "equipo"
    aliases = ["equipment", "gear"]
    locks = "cmd:all()"
    help_category = "Equipamiento"

    def func(self):
        caller = self.caller
        eq = _get_equipamiento(caller)

        lineas = [f"\n|w{'─'*36}|n", f"  |cEquipamiento de {caller.key}|n", f"|w{'─'*36}|n"]

        for slot in SLOTS:
            item = eq.get(slot)
            if item:
                bonuses = item.db.bonuses or {}
                if bonuses:
                    bonus_txt = "  (" + ", ".join(f"{k}+{v}" for k, v in bonuses.items()) + ")"
                else:
                    bonus_txt = ""
                lineas.append(f"  |c{slot:10}|n |w{item.key}|n{bonus_txt}")
            else:
                lineas.append(f"  |c{slot:10}|n |x(vacío)|n")

        lineas.append(f"|w{'─'*36}|n\n")
        caller.msg("\n".join(lineas))


# --------------------------------------------------------------------------- #
#  CmdSet de equipamiento
# --------------------------------------------------------------------------- #

class EquipmentCmdSet(CmdSet):
    key = "EquipmentCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdEquipar())
        self.add(CmdDesequipar())
        self.add(CmdEquipo())
