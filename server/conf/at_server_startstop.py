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
    try:
        from features.time.clock_script import obtener_reloj
        obtener_reloj()
    except Exception:
        pass
    try:
        from features.weather.weather_script import obtener_clima_script
        obtener_clima_script()
    except Exception:
        pass
    try:
        from features.events.event_script import obtener_evento_script
        obtener_evento_script()
    except Exception:
        pass
    try:
        from features.records.records_script import obtener_records_script
        obtener_records_script()
    except Exception:
        pass
    try:
        from features.market.market_script import obtener_mercado_script
        obtener_mercado_script()
    except Exception:
        pass
    try:
        from features.contracts.contract_script import obtener_tablón_script
        obtener_tablón_script()
    except Exception:
        pass


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
        from evennia import search_object
        from evennia.utils import logger
        salas_temp = search_object(
            typeclass="typeclasses.rooms.Room", attribute_name="es_mazmorra", attribute_value=True
        )
        for sala in salas_temp:
            try:
                sala.delete()
            except Exception:
                pass
        if salas_temp:
            logger.log_info(f"Cold start: eliminadas {len(salas_temp)} salas de mazmorra huérfanas.")
    except Exception:
        pass


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    pass
