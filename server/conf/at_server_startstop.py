"""
Server startstop hooks

This module contains functions called by Evennia at various
points during its startup, reload and shutdown sequence. It
allows for customizing the server operation as desired.

This module must contain at least these global functions:

at_server_init()
at_server_start()
at_server_stop()
at_server_reload_start()
at_server_reload_stop()
at_server_cold_start()
at_server_cold_stop()

"""


def at_server_init():
    """
    This is called first as the server is starting up, regardless of how.
    """
    pass


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    from evennia.utils import logger

    try:
        from features.time.clock_script import obtener_reloj
        obtener_reloj()
    except Exception:
        logger.log_trace("at_server_start: fallo al arrancar el reloj mundial.")
    try:
        from features.weather.weather_script import obtener_clima_script
        obtener_clima_script()
    except Exception:
        logger.log_trace("at_server_start: fallo al arrancar el script de clima.")
    try:
        from features.events.event_script import obtener_evento_script
        obtener_evento_script()
    except Exception:
        logger.log_trace("at_server_start: fallo al arrancar el script de eventos.")
    try:
        from features.records.records_script import obtener_records_script
        obtener_records_script()
    except Exception:
        logger.log_trace("at_server_start: fallo al arrancar el script de récords.")
    try:
        from features.market.market_script import obtener_mercado_script
        obtener_mercado_script()
    except Exception:
        logger.log_trace("at_server_start: fallo al arrancar el script de mercado.")
    try:
        from features.contracts.contract_script import obtener_tablón_script
        obtener_tablón_script()
    except Exception:
        logger.log_trace("at_server_start: fallo al arrancar el tablón de contratos.")
    try:
        from features.world_bosses.world_boss_script import obtener_world_boss_script
        obtener_world_boss_script()
    except Exception:
        logger.log_trace("at_server_start: fallo al arrancar el script de jefes de mundo.")
    try:
        from features.housing.housing_script import obtener_gestor_script
        obtener_gestor_script()
    except Exception:
        logger.log_trace("at_server_start: fallo al arrancar el gestor de viviendas.")
    try:
        from features.bounty.bounty_script import obtener_recompensas_script
        obtener_recompensas_script()
    except Exception:
        logger.log_trace("at_server_start: fallo al arrancar el script de recompensas.")
    try:
        from features.daily.daily_script import obtener_desafios_script
        obtener_desafios_script()
    except Exception:
        logger.log_trace("at_server_start: fallo al arrancar el script de desafíos diarios.")

    _limpiar_actividad_huerfana()


def _limpiar_actividad_huerfana():
    """
    CombatHandler, TorneoScript y ExpedicionScript son persistent=False:
    Evennia para su timer incondicionalmente en cada arranque (reload,
    cold start o tras una caída) sin borrar la fila de la base de datos
    (ScriptDB.objects.update_scripts_after_server_start() solo hace
    script._stop_task(), nunca script.delete()). El resultado es un
    script "zombie" que sigue existiendo y sigue siendo devuelto como
    "el combate/torneo/expedición activo" por el código que lo busca,
    pero cuyo temporizador (turno_timeout, TIMEOUT_COMBATE, etc.) ya no
    puede volver a dispararse — así que si ninguno de los participantes
    vuelve a actuar, la actividad queda congelada para siempre y
    db.en_combate en los jugadores implicados queda en True de forma
    permanente (solo se limpia normalmente desde dentro del propio
    handler). Se resuelve cada uno con su propio método de cancelación
    ya existente, igual que si hubiera terminado por timeout.
    """
    from evennia.scripts.models import ScriptDB

    try:
        for handler in ScriptDB.objects.filter(db_key="combat_handler"):
            handler._terminar_combate()
    except Exception:
        logger.log_trace("at_server_start: fallo al limpiar combates huérfanos tras el reinicio.")
    try:
        for torneo in ScriptDB.objects.filter(db_key="torneo_arena"):
            torneo._cancelar("El servidor se reinició durante el torneo.")
    except Exception:
        logger.log_trace("at_server_start: fallo al limpiar torneos huérfanos tras el reinicio.")
    try:
        for exped in ScriptDB.objects.filter(db_key="expedicion_script"):
            exped._limpiar(exito=False)
    except Exception:
        logger.log_trace("at_server_start: fallo al limpiar expediciones huérfanas tras el reinicio.")


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    pass


def at_server_reload_start():
    """
    This is called only when server starts back up after a reload.
    """
    pass


def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    pass


def at_server_cold_start():
    """
    This is called only when the server starts "cold", i.e. after a
    shutdown or a reset.
    """
    try:
        from evennia.objects.models import ObjectDB
        from evennia.utils import logger
        salas_temp = [
            sala for sala in ObjectDB.objects.filter(
                db_typeclass_path__contains="rooms.Room"
            )
            if getattr(sala.db, "es_mazmorra", False)
        ]
        for sala in salas_temp:
            try:
                sala.delete()
            except Exception:
                pass
        if salas_temp:
            logger.log_info(f"Cold start: eliminadas {len(salas_temp)} salas de mazmorra huérfanas.")
    except Exception:
        from evennia.utils import logger
        logger.log_trace("at_server_cold_start: fallo al limpiar salas de mazmorra huérfanas.")


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    pass
