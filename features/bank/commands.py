"""
features/bank/commands.py

Comandos del banco: banco, depositar, retirar.
Requieren la presencia de un NPC con db.es_banquero=True en la sala.
"""
from evennia import Command, CmdSet

from systems.bank.bank import puede_depositar, limpiar_banco


def _buscar_banquero(caller):
    """Devuelve el primer NPC banquero en la sala, o None."""
    sala = caller.location
    if not sala:
        return None
    for obj in sala.contents:
        if getattr(obj.db, "es_banquero", False):
            return obj
    return None


def _banco_limpio(caller) -> list:
    """Devuelve db.banco limpia de referencias muertas, actualizando el atributo."""
    banco = list(getattr(caller.db, "banco", []) or [])
    banco = limpiar_banco(banco)
    caller.db.banco = banco
    return banco


class CmdBanco(Command):
    """
    Ver los objetos guardados en tu banco.

    Uso:
      banco

    Muestra todos los objetos que has depositado en el banco.
    Debes estar cerca de un banquero para acceder.

    Ejemplo:
      banco
    """
    key = "banco"
    aliases = ["bóveda", "boveda"]
    locks = "cmd:all()"
    help_category = "Banco"

    def func(self):
        caller = self.caller
        banquero = _buscar_banquero(caller)
        if not banquero:
            caller.msg("Necesitas estar cerca de un banquero para acceder al banco.")
            return

        banco = _banco_limpio(caller)

        lineas = [
            f"\n|w{'─'*46}|n",
            f"  |cBanco — {banquero.key}|n",
            f"|w{'─'*46}|n",
        ]
        if not banco:
            lineas.append("  |x(No tienes objetos guardados en el banco.)|n")
        else:
            for i, item in enumerate(banco, 1):
                tipo = type(item).__name__
                lineas.append(f"  {i:>2}. |w{item.key}|n  |x({tipo})|n")

        lineas += [
            f"|w{'─'*46}|n",
            f"  |wdepositar <objeto>|n  — guardar en el banco",
            f"  |wretirar <objeto>|n    — sacar del banco\n",
        ]
        caller.msg("\n".join(lineas))


class CmdDepositar(Command):
    """
    Depositar un objeto en el banco.

    Uso:
      depositar <objeto>

    El objeto se guarda en el banco y desaparece de tu inventario
    hasta que lo retires. No puedes depositar objetos equipados.

    Ejemplo:
      depositar espada de hierro
      depositar poción de vida
    """
    key = "depositar"
    aliases = ["deposit"]
    locks = "cmd:all()"
    help_category = "Banco"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args:
            caller.msg("¿Qué quieres depositar? Uso: |wdepositar <objeto>|n")
            return

        banquero = _buscar_banquero(caller)
        if not banquero:
            caller.msg("Necesitas estar cerca de un banquero para usar el banco.")
            return

        item = caller.search(
            args,
            location=caller,
            nofound_string=f"No tienes '{args}' en tu inventario.",
        )
        if not item:
            return

        from features.equipment.commands import _get_equipamiento
        eq = _get_equipamiento(caller)
        puede, razon = puede_depositar(item, eq)
        if not puede:
            caller.msg(razon)
            return

        banco = _banco_limpio(caller)
        item.location = None
        item.db.banco_propietario = caller.id
        banco.append(item)
        caller.db.banco = banco

        caller.msg(
            f"Depositas |w{item.key}|n en el banco de {banquero.key}. "
            f"(|y{len(banco)}|n objeto(s) guardado(s))"
        )
        caller.location.msg_contents(
            f"{caller.key} deposita algo en el banco.",
            exclude=caller,
        )

        if not getattr(caller.db, "banco_usado", False):
            caller.db.banco_usado = True
        from features.achievements.commands import comprobar_y_notificar
        comprobar_y_notificar(caller)


class CmdRetirar(Command):
    """
    Retirar un objeto del banco.

    Uso:
      retirar <objeto>

    El objeto vuelve a tu inventario desde el banco.
    Debes estar cerca de un banquero para acceder.

    Ejemplo:
      retirar espada de hierro
      retirar poción de vida
    """
    key = "retirar"
    aliases = ["withdraw"]
    locks = "cmd:all()"
    help_category = "Banco"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args:
            caller.msg("¿Qué quieres retirar? Uso: |wretirar <objeto>|n")
            return

        banquero = _buscar_banquero(caller)
        if not banquero:
            caller.msg("Necesitas estar cerca de un banquero para usar el banco.")
            return

        banco = _banco_limpio(caller)

        if not banco:
            caller.msg("Tu banco está vacío.")
            return

        args_lower = args.lower()
        item = next(
            (it for it in banco if args_lower in it.key.lower()),
            None,
        )
        if not item:
            caller.msg(
                f"No tienes '{args}' en el banco. "
                f"Usa |wbanco|n para ver tus objetos guardados."
            )
            return

        banco.remove(item)
        caller.db.banco = banco
        item.db.banco_propietario = None
        item.location = caller

        caller.msg(
            f"Retiras |w{item.key}|n del banco de {banquero.key}. "
            f"(|y{len(banco)}|n objeto(s) restante(s))"
        )
        caller.location.msg_contents(
            f"{caller.key} retira algo del banco.",
            exclude=caller,
        )


class BankCmdSet(CmdSet):
    key = "BankCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdBanco())
        self.add(CmdDepositar())
        self.add(CmdRetirar())
