"""
systems/mounts/mounts.py

Lógica pura del sistema de monturas. Sin dependencias de Evennia.

db.monturas       en Character: list[str]  — IDs de monturas poseídas
db.montura_activa en Character: str | None — ID de la montura actualmente invocada
"""
from __future__ import annotations

# Umbral de reputación para monturas con requisito de facción
_REP_HONRADO = 3000

# --------------------------------------------------------------------------- #
#  Catálogo de monturas
# --------------------------------------------------------------------------- #
#  bonus: dict {stat: valor} — se aplica pasivamente mientras está montado

#  Agrupadas por "tipo" (orden ascendente de coste dentro de cada grupo):
#  formatear_catalogo() imprime una cabecera de sección cada vez que el tipo
#  cambia respecto a la entrada anterior, así que el orden de declaración
#  aquí debe mantener juntas las entradas del mismo tipo o la cabecera se
#  repite cada vez que el tipo "vuelve" a aparecer más adelante.
MONTURAS: dict[str, dict] = {
    "poni_viejo": {
        "nombre":      "Poni Viejo",
        "descripcion": "Pequeño y resistente. Ideal para aventureros que empiezan.",
        "tipo":        "caballo",
        "coste":       200,
        "nivel_min":   1,
        "faccion":     None,
        "rep_min":     0,
        "requisito_jefe": None,
        "bonus":       {"defensa": 1},
        "raro":        False,
    },
    "corcel_guerra": {
        "nombre":      "Corcel de Guerra",
        "descripcion": "Entrenado para el combate. Robusto y fiel en la batalla.",
        "tipo":        "caballo",
        "coste":       600,
        "nivel_min":   4,
        "faccion":     None,
        "rep_min":     0,
        "requisito_jefe": None,
        "bonus":       {"defensa": 2, "fuerza": 1},
        "raro":        False,
    },
    "corcel_oscuro": {
        "nombre":      "Corcel Oscuro",
        "descripcion": "Nacido entre las sombras de la Ciudadela. Emana un poder inquietante.",
        "tipo":        "caballo",
        "coste":       2000,
        "nivel_min":   8,
        "faccion":     None,
        "rep_min":     0,
        "requisito_jefe": None,
        "bonus":       {"fuerza": 3, "inteligencia": 1},
        "raro":        True,
    },
    "lobo_cazador": {
        "nombre":      "Lobo Cazador",
        "descripcion": "Ágil y silencioso. Favorito de los exploradores del norte.",
        "tipo":        "bestia",
        "coste":       900,
        "nivel_min":   5,
        "faccion":     None,
        "rep_min":     0,
        "requisito_jefe": None,
        "bonus":       {"destreza": 3},
        "raro":        False,
    },
    "hipogrifo": {
        "nombre":      "Hipogrifo",
        "descripcion": "Mitad águila, mitad caballo. Símbolo de honor entre los ciudadanos.",
        "tipo":        "bestia",
        "coste":       1500,
        "nivel_min":   6,
        "faccion":     "ciudadanos",
        "rep_min":     _REP_HONRADO,
        "requisito_jefe": None,
        "bonus":       {"destreza": 2, "defensa": 2},
        "raro":        True,
    },
    "grifo_real": {
        "nombre":      "Grifo Real",
        "descripcion": "La montura más codiciada del reino. Solo los más poderosos la doman.",
        "tipo":        "bestia",
        "coste":       3000,
        "nivel_min":   10,
        "faccion":     None,
        "rep_min":     0,
        "requisito_jefe": None,
        "bonus":       {"defensa": 4, "destreza": 2},
        "raro":        True,
    },
    "dragon_ceniza": {
        "nombre":      "Dragón de Ceniza",
        "descripcion": "El espíritu domado del Dragón de Ceniza. Solo quien lo ha vencido puede montarlo.",
        "tipo":        "dragon",
        "coste":       0,
        "nivel_min":   1,
        "faccion":     None,
        "rep_min":     0,
        "requisito_jefe": "DRAGON_CENIZA",
        "bonus":       {"inteligencia": 3, "defensa": 2},
        "raro":        True,
    },
}

_TOTAL_MONTURAS = len(MONTURAS)

# Mapeo de nombres de stat → abreviatura para mostrar
_ALIAS_STAT = {
    "fuerza":       "FUE",
    "destreza":     "DES",
    "constitucion": "CON",
    "inteligencia": "INT",
    "defensa":      "DEF",
}


# --------------------------------------------------------------------------- #
#  Lógica pura
# --------------------------------------------------------------------------- #

def puede_comprar(
    montura_id: str,
    monedas: int,
    nivel: int,
    reputacion: dict,
    monturas_poseidas: list,
    jefes_mundo_derrotados: dict,
) -> tuple[bool, str]:
    """
    Comprueba si el personaje puede comprar una montura.
    Devuelve (ok, mensaje_de_error).
    """
    m = MONTURAS.get(montura_id)
    if not m:
        return False, "Montura desconocida."
    if montura_id in monturas_poseidas:
        return False, f"Ya posees el |w{m['nombre']}|n."
    if nivel < m["nivel_min"]:
        return False, f"Necesitas nivel |w{m['nivel_min']}|n (eres nivel {nivel})."
    if m["faccion"] and reputacion.get(m["faccion"], 0) < m["rep_min"]:
        return False, (
            f"Necesitas reputación |wHonrado|n con |w{m['faccion'].capitalize()}|n "
            f"para esta montura."
        )
    jefe_req = m.get("requisito_jefe")
    if jefe_req and not jefes_mundo_derrotados.get(jefe_req):
        return False, (
            f"Debes derrotar al jefe de mundo |w{jefe_req.replace('_', ' ').title()}|n "
            f"antes de poder reclamar esta montura."
        )
    if m["coste"] > monedas:
        return False, f"No tienes suficientes monedas (necesitas |w{m['coste']}|n, tienes {monedas})."
    return True, ""


def puede_invocar(montura_id: str, monturas_poseidas: list) -> tuple[bool, str]:
    """Comprueba si el personaje puede invocar (montar) una montura."""
    if montura_id not in MONTURAS:
        return False, "Montura desconocida."
    if montura_id not in monturas_poseidas:
        return False, f"No posees esa montura. Usa |wmontura lista|n para ver las disponibles."
    return True, ""


def puede_desmontar(montura_activa: str | None) -> tuple[bool, str]:
    """Comprueba si el personaje puede desmontar."""
    if not montura_activa:
        return False, "No estás montado en ninguna montura."
    return True, ""


def bonus_montura(montura_id: str | None) -> dict:
    """
    Devuelve el dict de bonuses {stat: valor} de la montura activa.
    Devuelve {} si no hay montura o la ID es inválida.
    """
    if not montura_id:
        return {}
    m = MONTURAS.get(montura_id)
    if not m:
        return {}
    return dict(m["bonus"])


def monturas_poseidas_count(monturas: list) -> int:
    """Número de monturas únicas poseídas."""
    return len(set(monturas))


def _bonus_texto(bonus: dict) -> str:
    partes = []
    for stat, val in bonus.items():
        abr = _ALIAS_STAT.get(stat, stat[:3].upper())
        partes.append(f"+{val} {abr}")
    return ", ".join(partes) if partes else "sin bonus"


def formatear_estado(montura_activa: str | None, monturas_poseidas: list) -> str:
    sep = "|w" + "─" * 52 + "|n"
    lineas = [f"\n{sep}", "  |cMonturas|n", sep]

    if montura_activa and montura_activa in MONTURAS:
        m = MONTURAS[montura_activa]
        lineas.append(
            f"  Montado en: |Y{m['nombre']}|n  "
            f"(|g{_bonus_texto(m['bonus'])}|n)"
        )
    else:
        lineas.append("  No estás montado.")

    if monturas_poseidas:
        lineas.append(f"\n  Monturas poseídas ({len(set(monturas_poseidas))}/{_TOTAL_MONTURAS}):")
        for mid in sorted(set(monturas_poseidas)):
            m = MONTURAS.get(mid)
            if not m:
                continue
            activa_tag = " |Y[ACTIVA]|n" if mid == montura_activa else ""
            lineas.append(
                f"    |w{m['nombre']}|n — {_bonus_texto(m['bonus'])}{activa_tag}"
            )
    else:
        lineas.append("\n  No posees ninguna montura aún.")

    lineas.append(f"\n  Usa |wmontura lista|n para ver todas las disponibles.")
    lineas.append(f"{sep}\n")
    return "\n".join(lineas)


def formatear_catalogo(
    monturas_poseidas: list,
    nivel: int,
    reputacion: dict,
    monedas: int,
    jefes_mundo_derrotados: dict,
) -> str:
    sep = "|w" + "─" * 52 + "|n"
    poseidas = set(monturas_poseidas)
    lineas = [f"\n{sep}", "  |cCatálogo de Monturas|n", sep]

    tipo_actual = None
    for mid, m in MONTURAS.items():
        if m["tipo"] != tipo_actual:
            tipo_actual = m["tipo"]
            lineas.append(f"\n  |y[{tipo_actual.capitalize()}]|n")

        if mid in poseidas:
            lineas.append(
                f"    |g✔|n |w{m['nombre']}|n — {_bonus_texto(m['bonus'])}  |g[Poseída]|n"
            )
            continue

        # Comprobar requisitos
        ok, motivo = puede_comprar(
            mid, monedas, nivel, reputacion, list(poseidas), jefes_mundo_derrotados
        )
        coste_txt = f"|w{m['coste']} monedas|n" if m["coste"] > 0 else "|cGratis|n"
        req_txt = ""
        if m["nivel_min"] > 1:
            req_txt += f"  Nv.{m['nivel_min']}"
        if m["faccion"]:
            req_txt += f"  Honrado con {m['faccion'].capitalize()}"
        if m.get("requisito_jefe"):
            req_txt += f"  Derrotar {m['requisito_jefe'].replace('_',' ').title()}"

        if ok:
            lineas.append(
                f"    |x✗|n |w{m['nombre']}|n — {_bonus_texto(m['bonus'])}  "
                f"{coste_txt}{req_txt}"
            )
        else:
            lineas.append(
                f"    |r✗|n |x{m['nombre']}|n — {_bonus_texto(m['bonus'])}  "
                f"|x{coste_txt}{req_txt}  ({motivo})|n"
            )

    lineas.append(f"\n  Usa |wmontura comprar <nombre>|n para adquirir una.")
    lineas.append(f"  Usa |wmontura invocar <nombre>|n para montarla.")
    lineas.append(f"{sep}\n")
    return "\n".join(lineas)
