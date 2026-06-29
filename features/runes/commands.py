"""
features/runes/commands.py

Comandos del sistema de runas:
  runas                      — lista de runas disponibles
  runas info <ID>            — detalle de una runa
  runas estado               — tus runas actualmente grabadas
  runas grabar <ID> en <slot> — graba una runa en un slot de equipo
  runas borrar <slot>        — elimina la runa de un slot (materiales perdidos)
"""
from evennia import Command, CmdSet

from systems.runes.runes import (
    RUNAS, SLOTS_VALIDOS,
    buscar_runa, puede_grabar, slot_compatible, tiene_materiales,
    formatear_lista, formatear_runa, formatear_runas_equipadas,
)


def _get_runas(char) -> dict:
    runas = getattr(char.db, "runas_equipadas", None)
    if not runas or not isinstance(runas, dict):
        runas = {s: None for s in SLOTS_VALIDOS}
        char.db.runas_equipadas = runas
    return runas


def _get_equipamiento(char) -> dict:
    eq = getattr(char.db, "equipamiento", None) or {}
    return eq


def _inventario_sin_equipo(char) -> dict:
    """Devuelve {nombre_lower: cantidad} del inventario excluyendo items equipados."""
    eq = _get_equipamiento(char)
    equipped_ids = {item.id for item in eq.values() if item}
    inv: dict = {}
    for obj in char.contents:
        if obj.id in equipped_ids:
            continue
        k = obj.key.lower()
        inv[k] = inv.get(k, 0) + 1
    return inv


def _consumir_materiales(char, runa_id: str):
    """Elimina los objetos del inventario necesarios para la runa."""
    runa = RUNAS[runa_id]
    eq = _get_equipamiento(char)
    equipped_ids = {item.id for item in eq.values() if item}
    for mat, cantidad in runa["materiales"].items():
        consumidos = 0
        for obj in list(char.contents):
            if consumidos >= cantidad:
                break
            if obj.id in equipped_ids:
                continue
            if obj.key.lower() == mat.lower():
                obj.delete()
                consumidos += 1


class CmdRunas(Command):
    """
    Consulta y gestiona las runas grabadas en tu equipamiento.

    Uso:
      runas                         — lista todas las runas disponibles
      runas info <ID>               — detalles de una runa específica
      runas estado                  — runas actualmente grabadas en tu equipo
      runas grabar <ID> en <slot>   — graba una runa (consume materiales y monedas)
      runas borrar <slot>           — elimina la runa del slot (materiales perdidos)

    Slots válidos: arma, armadura, accesorio

    Ejemplo:
      runas info RUNA_VIGOR
      runas grabar RUNA_VIGOR en armadura
      runas borrar arma
    """
    key = "runas"
    aliases = ["runa"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args:
            caller.msg(formatear_lista())
            return

        partes = args.split(None, 1)
        subcmd = partes[0].lower()
        resto = partes[1].strip() if len(partes) > 1 else ""

        if subcmd == "estado":
            runas = _get_runas(caller)
            caller.msg(formatear_runas_equipadas(runas))

        elif subcmd == "info":
            if not resto:
                caller.msg("Uso: |wrunas info <ID>|n  Ejemplo: |wrunas info RUNA_VIGOR|n")
                return
            rid = buscar_runa(resto)
            if not rid:
                caller.msg(f"|rNo se encontró ninguna runa con ese nombre.|n")
                return
            caller.msg(formatear_runa(rid))

        elif subcmd == "grabar":
            # Formato: grabar <ID> en <slot>
            if " en " not in resto.lower():
                caller.msg("Uso: |wrunas grabar <ID> en <slot>|n")
                return
            partes_g = resto.lower().split(" en ", 1)
            nombre_runa = partes_g[0].strip()
            slot = partes_g[1].strip()

            if slot not in SLOTS_VALIDOS:
                caller.msg(
                    f"|rSlot inválido.|n Slots válidos: {', '.join(SLOTS_VALIDOS)}"
                )
                return

            rid = buscar_runa(nombre_runa)
            if not rid:
                caller.msg(
                    f"|rNo existe ninguna runa con ese nombre.|n "
                    f"Usa |wrunas|n para ver la lista."
                )
                return

            # Comprobar nivel
            nivel = int(getattr(caller.db, "nivel", 1) or 1)
            ok, msg_nv = puede_grabar(nivel, rid)
            if not ok:
                caller.msg(f"|r{msg_nv}|n")
                return

            # Comprobar slot compatible
            if not slot_compatible(rid, slot):
                runa_slot = RUNAS[rid]["slot"]
                caller.msg(
                    f"|r{RUNAS[rid]['nombre']}|n solo puede grabarse en el slot "
                    f"|c{runa_slot}|n."
                )
                return

            # Comprobar equipamiento en ese slot
            eq = _get_equipamiento(caller)
            item_equipado = eq.get(slot)
            if not item_equipado:
                caller.msg(
                    f"|rNo tienes ningún objeto equipado en el slot {slot}.|n "
                    f"Equipa un objeto primero."
                )
                return

            # Comprobar que el slot no tiene ya una runa
            runas = _get_runas(caller)
            if runas.get(slot):
                runa_actual = RUNAS.get(runas[slot], {}).get("nombre", runas[slot])
                caller.msg(
                    f"El slot |c{slot}|n ya tiene grabada la |w{runa_actual}|n. "
                    f"Usa |wrunas borrar {slot}|n primero."
                )
                return

            # Comprobar monedas
            coste = RUNAS[rid]["coste_monedas"]
            monedas = int(getattr(caller.db, "monedas", 0) or 0)
            if monedas < coste:
                caller.msg(
                    f"Necesitas |w{coste} monedas|n para grabar la {RUNAS[rid]['nombre']}. "
                    f"Tienes {monedas}."
                )
                return

            # Comprobar materiales
            inv = _inventario_sin_equipo(caller)
            ok_mat, faltantes = tiene_materiales(inv, rid)
            if not ok_mat:
                falta_txt = ", ".join(faltantes)
                caller.msg(
                    f"Te faltan materiales para grabar {RUNAS[rid]['nombre']}:\n"
                    f"  {falta_txt}"
                )
                return

            # Ejecutar grabado
            _consumir_materiales(caller, rid)
            caller.db.monedas = monedas - coste
            runas[slot] = rid
            caller.db.runas_equipadas = runas

            caller.msg(
                f"\n|Y✦ ¡Runa grabada!|n\n"
                f"  |w{RUNAS[rid]['nombre']}|n → slot |c{slot}|n "
                f"({item_equipado.key})\n"
                f"  Efecto: {RUNAS[rid]['descripcion']}\n"
                f"  Materiales consumidos. Monedas gastadas: {coste}\n"
            )

            # Comprobar logros
            try:
                from features.achievements.commands import comprobar_y_notificar
                comprobar_y_notificar(caller)
            except Exception:
                pass

        elif subcmd == "borrar":
            slot = resto.strip().lower()
            if slot not in SLOTS_VALIDOS:
                caller.msg(
                    f"|rSlot inválido.|n Slots válidos: {', '.join(SLOTS_VALIDOS)}"
                )
                return
            runas = _get_runas(caller)
            runa_id_actual = runas.get(slot)
            if not runa_id_actual:
                caller.msg(f"No tienes ninguna runa grabada en el slot |c{slot}|n.")
                return
            nombre = RUNAS.get(runa_id_actual, {}).get("nombre", runa_id_actual)
            runas[slot] = None
            caller.db.runas_equipadas = runas
            caller.msg(
                f"|yRuna eliminada:|n {nombre} borrada del slot |c{slot}|n. "
                f"Los materiales no se devuelven."
            )

        else:
            # Tratar el argumento como búsqueda de info directa
            rid = buscar_runa(args)
            if rid:
                caller.msg(formatear_runa(rid))
            else:
                caller.msg(
                    f"Subcomando desconocido. Usa:\n"
                    f"  |wrunas|n, |wrunas info <ID>|n, |wrunas estado|n,\n"
                    f"  |wrunas grabar <ID> en <slot>|n, |wrunas borrar <slot>|n"
                )


class RunasCmdSet(CmdSet):
    key = "RunasCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdRunas())
