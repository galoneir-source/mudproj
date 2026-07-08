"""
features/bounty/bounty_script.py

Script global persistente que almacena las recompensas activas del servidor.

Patrón de acceso:
    from features.bounty.bounty_script import obtener_recompensas_script
    script = obtener_recompensas_script()
    bounties = list(script.db.bounties or [])
"""
from evennia import DefaultScript, search_script
from evennia.utils import logger


class RecompensasScript(DefaultScript):
    """Script singleton que persiste la lista de recompensas activas."""

    def at_script_creation(self):
        self.key = "recompensas_script"
        self.desc = "Gestor global de cazarrecompensas"
        self.persistent = True
        self.interval = 0
        self.db.bounties = []


def obtener_recompensas_script() -> RecompensasScript:
    """Devuelve el RecompensasScript global; lo crea si no existe."""
    resultados = search_script("recompensas_script")
    if resultados:
        return resultados[0]
    from evennia.utils.create import create_script
    script = create_script(RecompensasScript, key="recompensas_script", persistent=True)
    logger.log_info("RecompensasScript creado.")
    return script


def cobrar_recompensa_por_duelo(cazador, objetivo):
    """
    Llamado desde _fin_duelo del CombatHandler cuando el cazador gana.
    Cobra todas las recompensas sobre el objetivo y las ingresa al cazador.
    Actualiza stats y notifica a ambos jugadores.
    """
    from systems.bounty.bounty import cobrar_bounties, hay_recompensa

    script = obtener_recompensas_script()
    bounties = list(script.db.bounties or [])

    objetivo_dbref = objetivo.dbref
    if not hay_recompensa(objetivo_dbref, bounties):
        return

    nueva_lista, total = cobrar_bounties(bounties, objetivo_dbref)
    script.db.bounties = nueva_lista

    # Pagar al cazador
    cazador.db.monedas = (getattr(cazador.db, "monedas", 0) or 0) + total
    cazador.db.recompensas_cobradas = (getattr(cazador.db, "recompensas_cobradas", 0) or 0) + 1

    # Actualizar contador del objetivo
    objetivo.db.recompensas_recibidas = (getattr(objetivo.db, "recompensas_recibidas", 0) or 0) + 1

    cazador.msg(
        f"\n|Y¡Recompensa cobrada!|n  Has recibido |w{total} monedas|n "
        f"por derrotar a |w{objetivo.key}|n."
    )
    objetivo.msg(
        f"\n|rUna recompensa ha sido cobrada sobre ti.|n  "
        f"|w{cazador.key}|n cobró |r{total} monedas|n."
    )

    try:
        from features.achievements.commands import comprobar_y_notificar
        comprobar_y_notificar(cazador)
        comprobar_y_notificar(objetivo)
    except Exception:
        pass
