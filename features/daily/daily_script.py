"""
features/daily/daily_script.py

Script global persistente del sistema de Desafíos Diarios y
función pública notificar_progreso() que los demás sistemas llaman
tras eventos relevantes (kill, recolección, apuesta, alquimia, expedición).
"""
from datetime import date, timedelta

from evennia import DefaultScript
from evennia.utils import logger

from systems.daily.daily import (
    generar_desafios_del_dia,
    actualizar_progreso,
    progreso_completado,
    bonus_racha_monedas,
    bonus_racha_xp,
)


def _hoy() -> str:
    return date.today().isoformat()


def _ayer() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


class DesafiosDiariosScript(DefaultScript):
    """Script persistente que existe para inicializar el sistema. El tick
    comprueba cambios de día y puede usarse para tareas globales."""

    def at_script_creation(self):
        self.key = "desafios_diarios_script"
        self.desc = "Desafíos diarios — gestor global"
        self.persistent = True
        self.interval = 3600
        self.db.fecha_actual = _hoy()

    def at_repeat(self):
        hoy = _hoy()
        if self.db.fecha_actual != hoy:
            self.db.fecha_actual = hoy
            logger.log_info(f"[Desafíos] Nuevo día detectado: {hoy}")


def obtener_desafios_script() -> DesafiosDiariosScript:
    """Devuelve el script global, creándolo si no existe."""
    from evennia import search_script
    scripts = search_script("desafios_diarios_script")
    if scripts:
        return scripts[0]
    from evennia import create_script
    return create_script(DesafiosDiariosScript)


def _reset_progreso_si_nuevo_dia(jugador, hoy: str):
    """Reinicia el progreso si la fecha almacenada no es de hoy."""
    fecha_guardada = getattr(jugador.db, "fecha_desafios", None)
    if fecha_guardada != hoy:
        jugador.db.fecha_desafios = hoy
        jugador.db.progreso_desafios = [0, 0, 0, 0, 0]
        jugador.db.desafios_completados_hoy = []


def _completar_todos(jugador, hoy: str):
    """Otorga el bonus de racha al completar los 5 desafíos del día."""
    # Actualizar racha
    ultimo = getattr(jugador.db, "ultimo_dia_desafios", None)
    racha_actual = int(getattr(jugador.db, "racha_desafios", 0) or 0)
    if ultimo == _ayer():
        racha_nueva = racha_actual + 1
    else:
        racha_nueva = 1
    jugador.db.racha_desafios = racha_nueva
    jugador.db.ultimo_dia_desafios = hoy

    bonus_m = bonus_racha_monedas(racha_nueva)
    bonus_x = bonus_racha_xp(racha_nueva)

    if bonus_m > 0:
        jugador.db.monedas = (getattr(jugador.db, "monedas", 0) or 0) + bonus_m
    if bonus_x > 0:
        jugador.db.experiencia = (getattr(jugador.db, "experiencia", 0) or 0) + bonus_x

    lineas = [
        "\n|Y╔══════════════════════════════════════╗|n",
        "|Y║   ¡5/5 DESAFÍOS COMPLETADOS HOY!    ║|n",
        "|Y╚══════════════════════════════════════╝|n",
        f"  Racha actual: |Y{racha_nueva}|n día{'s' if racha_nueva != 1 else ''}",
    ]
    if bonus_x > 0 or bonus_m > 0:
        lineas.append(
            f"  Bonus de racha: |g+{bonus_x} XP|n  |y+{bonus_m} monedas|n"
        )
    else:
        lineas.append("  (Mantén la racha mañana para obtener bonificaciones)")
    jugador.msg("\n".join(lineas) + "\n")

    # Logros
    try:
        from features.achievements.commands import comprobar_y_notificar
        comprobar_y_notificar(jugador)
    except Exception as _e:
        logger.log_err(f"[Desafíos] comprobar_y_notificar: {_e}")


def notificar_progreso(jugador, tipo: str, **datos):
    """
    Notifica al sistema de desafíos que el jugador ha realizado una acción.

    Llamar desde los handlers de cada sistema:
        notificar_progreso(caller, "kill_faccion", faccion="bandidos")
        notificar_progreso(caller, "recolectar", profesion="herboristeria")
        notificar_progreso(caller, "apostar_ganar")
        notificar_progreso(caller, "alquimia")
        notificar_progreso(caller, "expedicion")
    """
    try:
        if not getattr(jugador, "has_account", False):
            return

        hoy = _hoy()
        _reset_progreso_si_nuevo_dia(jugador, hoy)

        desafios = generar_desafios_del_dia(hoy)
        progreso = list(getattr(jugador.db, "progreso_desafios", []) or [])
        completados_idx = list(
            getattr(jugador.db, "desafios_completados_hoy", []) or []
        )

        nuevo_progreso, nuevos_completados, avanzados = actualizar_progreso(
            desafios, progreso, completados_idx, tipo, datos
        )

        if not avanzados:
            return

        jugador.db.progreso_desafios = nuevo_progreso

        for i in nuevos_completados:
            completados_idx.append(i)
            d = desafios[i]
            desc = d["desc"].format(objetivo=d["objetivo"])
            jugador.db.total_desafios_completados = (
                int(getattr(jugador.db, "total_desafios_completados", 0) or 0) + 1
            )
            jugador.db.experiencia = (
                getattr(jugador.db, "experiencia", 0) or 0
            ) + d["recompensa_xp"]
            jugador.db.monedas = (
                getattr(jugador.db, "monedas", 0) or 0
            ) + d["recompensa_monedas"]
            jugador.msg(
                f"\n|Y✦ ¡DESAFÍO COMPLETADO!|n  |w{desc}|n\n"
                f"   |g+{d['recompensa_xp']} XP|n  |y+{d['recompensa_monedas']} monedas|n\n"
            )

        jugador.db.desafios_completados_hoy = completados_idx

        # ¿Todos completados por primera vez hoy?
        total_previo = len(completados_idx) - len(nuevos_completados)
        if len(completados_idx) >= 5 and total_previo < 5:
            _completar_todos(jugador, hoy)

    except Exception as _e:
        logger.log_err(f"[Desafíos] notificar_progreso: {_e}")
