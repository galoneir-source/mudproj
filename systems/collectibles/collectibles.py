"""
systems/collectibles/collectibles.py

Lógica pura del sistema de coleccionables / tesoros ocultos.
Sin dependencias de Evennia.

db.tesoros_encontrados en Character: list[str] — IDs de tesoros hallados.

Cada sala con db.zona puede albergar un tesoro. El jugador usa el comando
'buscar' en la sala para encontrarlo. Algunos tesoros exigen haber derrotado
un guardián concreto (comprobado vía db.bestiary).
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
#  Catálogo de tesoros
# --------------------------------------------------------------------------- #
#  Cada entrada:
#   zona         — zona_id de la sala donde está oculto
#   nombre       — nombre del objeto encontrado
#   descripcion  — sabor literario al hallarlo
#   pista        — texto vago que orienta al jugador
#   nivel_min    — nivel mínimo para encontrarlo
#   requiere_kill— proto_key de NPC que debe haber muerto al menos 1 vez
#                  (verificado en bestiary del jugador). None = sin requisito.
#   recompensa   — dict con "monedas"

TESOROS: dict[str, dict] = {
    # ── Ciudad ──────────────────────────────────────────────────────────
    "moneda_antigua": {
        "nombre":       "Moneda Antigua del Reino",
        "descripcion":  "Una moneda de oro con la efigie de un rey olvidado. "
                        "Vale su peso en nostalgia.",
        "pista":        "Algo brilla entre los adoquines de la plaza central.",
        "zona":         "plaza_ciudad",
        "nivel_min":    1,
        "requiere_kill": None,
        "recompensa":   {"monedas": 60},
    },
    "pergamino_taberna": {
        "nombre":       "Pergamino Secreto del Mesonero",
        "descripcion":  "Una receta cifrada escondida detrás de un barril. "
                        "El mesonero la perdió hace años.",
        "pista":        "Los viejos establos siempre guardan secretos entre la paja.",
        "zona":         "taberna",
        "nivel_min":    1,
        "requiere_kill": None,
        "recompensa":   {"monedas": 80},
    },
    "bolsa_perdida": {
        "nombre":       "Bolsa del Comerciante Perdido",
        "descripcion":  "Una bolsa de cuero vieja con unas pocas monedas de plata "
                        "y un billete de deuda sin cobrar.",
        "pista":        "Dicen que un mercader distráido dejó algo valioso bajo su puesto.",
        "zona":         "mercado",
        "nivel_min":    2,
        "requiere_kill": None,
        "recompensa":   {"monedas": 100},
    },

    # ── Bosque ──────────────────────────────────────────────────────────
    "nido_ardilla": {
        "nombre":       "Nido de Ardilla con Monedas",
        "descripcion":  "Una ardilla muy lista había acumulado monedas relucientes "
                        "en su nido entre las raíces de un roble.",
        "pista":        "Las ardillas del bosque norte roban todo lo que brilla.",
        "zona":         "bosque_norte",
        "nivel_min":    2,
        "requiere_kill": None,
        "recompensa":   {"monedas": 90},
    },
    "piedra_druida": {
        "nombre":       "Piedra Druida Marcada",
        "descripcion":  "Una piedra de cuarzo con runas antiguas grabadas. "
                        "Parece que guiaba rituales olvidados.",
        "pista":        "Los druidas escondían sus reliquias donde el sol forma un claro.",
        "zona":         "claro_bosque",
        "nivel_min":    3,
        "requiere_kill": None,
        "recompensa":   {"monedas": 115},
    },

    # ── Calabozo ────────────────────────────────────────────────────────
    "cadena_rota": {
        "nombre":       "Cadena de Plata Rota",
        "descripcion":  "Un antiguo prisionero dejó esta cadena de plata "
                        "enterrada bajo las losetas húmedas.",
        "pista":        "Los prisioneros más ingeniosos siempre guardaban algo para el escape.",
        "zona":         "calabozo_celda",
        "nivel_min":    3,
        "requiere_kill": None,
        "recompensa":   {"monedas": 130},
    },

    # ── Pantano del Troll ───────────────────────────────────────────────
    "fetiche_fangoso": {
        "nombre":       "Fetiche Fangoso del Pantano",
        "descripcion":  "Una figura de barro y hueso usada en rituales tribales. "
                        "Tiene cierto valor entre coleccionistas de lo macabro.",
        "pista":        "Las criaturas del pantano ocultan sus fetiches bajo el fango más espeso.",
        "zona":         "pantano_cenagoso",
        "nivel_min":    3,
        "requiere_kill": None,
        "recompensa":   {"monedas": 140},
    },
    "corona_lodo": {
        "nombre":       "Corona de Lodo del Troll",
        "descripcion":  "La corona que el Troll creía que le hacía rey. "
                        "Hecha de ramas y huesos, tiene un valor sentimental absurdo.",
        "pista":        "El Troll guardaba algo especial en su guarida. Solo quien lo venza puede reclamarlo.",
        "zona":         "guarida_troll",
        "nivel_min":    5,
        "requiere_kill": "TROLL",
        "recompensa":   {"monedas": 210},
    },

    # ── Catacumbas ──────────────────────────────────────────────────────
    "urna_cineraria": {
        "nombre":       "Urna Cineraria con Monedas",
        "descripcion":  "Una urna sellada que, al abrirla, contenía cenizas "
                        "y, curiosamente, varias monedas de oro.",
        "pista":        "Los ricos solían enterrar sus riquezas con sus muertos.",
        "zona":         "sala_tumbas",
        "nivel_min":    4,
        "requiere_kill": None,
        "recompensa":   {"monedas": 165},
    },

    # ── Ruinas del Templo ────────────────────────────────────────────────
    "sello_baron": {
        "nombre":       "Sello del Barón Caído",
        "descripcion":  "El sello de cera lacrada del Barón, con su escudo de armas. "
                        "Un coleccionista en la ciudad pagaría bien por él.",
        "pista":        "El Barón escondió su sello personal en la cripta para que nadie "
                        "pudiera usurpar su linaje. Solo quien derrote al guardián puede tomarlo.",
        "zona":         "cripta_baron",
        "nivel_min":    6,
        "requiere_kill": "CABALLERO_OSCURO",
        "recompensa":   {"monedas": 270},
    },

    # ── Minas de Hierro Viejo ────────────────────────────────────────────
    "cristal_vena": {
        "nombre":       "Cristal de la Vena Perdida",
        "descripcion":  "Un cristal de cuarzo rosa puro, del tamaño de un puño. "
                        "Los mineros jamás llegaron a esta veta.",
        "pista":        "Las galerías principales esconden vetas que ningún minero ha explotado.",
        "zona":         "galeria_principal",
        "nivel_min":    4,
        "requiere_kill": None,
        "recompensa":   {"monedas": 185},
    },

    # ── Torre del Mago Caído ─────────────────────────────────────────────
    "grimorio_perdido": {
        "nombre":       "Grimorio Perdido del Archimago",
        "descripcion":  "Un tomo lleno de anotaciones personales del Archimago. "
                        "Incomprensible para los no iniciados, pero valioso.",
        "pista":        "El Archimago escondía sus notas más privadas en la biblioteca, "
                        "lejos de sus aprendices.",
        "zona":         "biblioteca_archimago",
        "nivel_min":    7,
        "requiere_kill": None,
        "recompensa":   {"monedas": 330},
    },
    "mascara_ritual": {
        "nombre":       "Máscara del Ritual Arcano",
        "descripcion":  "Una máscara de plata usada en rituales de invocación. "
                        "Aún zumba levemente con energía arcana residual.",
        "pista":        "La cámara del ritual guarda más secretos de los que revela.",
        "zona":         "camara_ritual",
        "nivel_min":    8,
        "requiere_kill": None,
        "recompensa":   {"monedas": 390},
    },

    # ── Ciudadela Oscura ─────────────────────────────────────────────────
    "trono_miniatura": {
        "nombre":       "Trono en Miniatura de Obsidiana",
        "descripcion":  "Una réplica perfecta del Trono Oscuro, tallada en obsidiana. "
                        "Un trofeo digno del más valiente.",
        "pista":        "El Salón del Trono esconde una réplica que el Señor Oscuro "
                        "usaba para sus rituales de poder.",
        "zona":         "salon_trono",
        "nivel_min":    9,
        "requiere_kill": None,
        "recompensa":   {"monedas": 450},
    },
    "ceniza_liche": {
        "nombre":       "Ceniza del Liche Inmortal",
        "descripcion":  "Las cenizas del Liche, contenidas en un vial de cristal negro. "
                        "Prueba incontestable de la hazaña más grande del reino.",
        "pista":        "Quien venza al Liche Inmortal encontrará algo en su altar "
                        "que ningún otro puede reclamar.",
        "zona":         "altar_liche",
        "nivel_min":    10,
        "requiere_kill": "LICHE_INMORTAL",
        "recompensa":   {"monedas": 500},
    },
}

# Índice inverso: zona_id → tesoro_id (calculado una vez)
ZONA_A_TESORO: dict[str, str] = {m["zona"]: tid for tid, m in TESOROS.items()}

_TOTAL = len(TESOROS)


# --------------------------------------------------------------------------- #
#  Lógica pura
# --------------------------------------------------------------------------- #

def tesoro_de_zona(zona_id: str | None) -> str | None:
    """Devuelve el tesoro_id de una zona, o None si no hay tesoro en ella."""
    return ZONA_A_TESORO.get(zona_id) if zona_id else None


def ya_encontrado(tesoro_id: str, encontrados: list) -> bool:
    """True si el tesoro ya está en la lista del jugador."""
    return tesoro_id in encontrados


def puede_buscar(
    tesoro_id: str,
    nivel: int,
    bestiary: dict,
    encontrados: list,
) -> tuple[bool, str]:
    """
    Comprueba si el jugador puede reclamar el tesoro de la sala.
    Devuelve (ok, mensaje_de_error).
    """
    t = TESOROS.get(tesoro_id)
    if not t:
        return False, "Tesoro desconocido."
    if ya_encontrado(tesoro_id, encontrados):
        return False, f"Ya encontraste |w{t['nombre']}|n aquí en el pasado."
    if nivel < t["nivel_min"]:
        return False, (
            f"Necesitas nivel |w{t['nivel_min']}|n para hallar este tesoro "
            f"(eres nivel {nivel})."
        )
    kill_req = t.get("requiere_kill")
    if kill_req and not bestiary.get(kill_req, {}).get("kills", 0):
        npc_nombre = kill_req.replace("_", " ").title()
        return False, (
            f"Debes haber derrotado a |w{npc_nombre}|n al menos una vez "
            f"para poder reclamar este tesoro."
        )
    return True, ""


def total_tesoros() -> int:
    return _TOTAL


def tesoros_encontrados_count(encontrados: list) -> int:
    """Número de tesoros únicos encontrados."""
    return len(set(encontrados))


def coleccion_completa(encontrados: list) -> bool:
    return set(TESOROS.keys()).issubset(set(encontrados))


def _barra(actual: int, total: int, ancho: int = 14) -> str:
    if total == 0:
        return "|x" + "░" * ancho + "|n"
    llenos = min(ancho, int(actual / total * ancho))
    return "|Y" + "█" * llenos + "|x" + "░" * (ancho - llenos) + "|n"


def formatear_coleccion(encontrados: list) -> str:
    """Muestra el progreso de coleccionables agrupado por área."""
    encontrados_set = set(encontrados)
    total = _TOTAL
    hallados = len(encontrados_set & set(TESOROS.keys()))

    sep = "|w" + "─" * 54 + "|n"
    barra = _barra(hallados, total)
    lineas = [
        f"\n{sep}",
        f"  |cColección de Tesoros Ocultos|n  —  "
        f"|w{hallados}/{total}|n hallados  {barra}",
        sep,
    ]

    # Agrupar por zona, preservando el orden de TESOROS
    zona_actual = None
    for tid, t in TESOROS.items():
        zona = t["zona"]
        if zona != zona_actual:
            zona_actual = zona
            lineas.append(f"\n  |y[{zona.replace('_', ' ').title()}]|n")
        if tid in encontrados_set:
            lineas.append(f"    |Y✔|n |w{t['nombre']}|n")
        else:
            req = ""
            if t.get("requiere_kill"):
                req = f" |x(requiere derrotar {t['requiere_kill'].replace('_',' ').title()})|n"
            lineas.append(f"    |x✗ {t['nombre']}{req}|n")

    pct = int(hallados / total * 100) if total else 0
    lineas.append(f"\n  Completado: |w{pct}%|n")
    lineas.append(f"  Usa |wbuscar|n en las salas del mundo para hallarlos.")
    lineas.append(f"{sep}\n")
    return "\n".join(lineas)


def formatear_pistas(encontrados: list) -> str:
    """Lista los tesoros pendientes con sus pistas."""
    pendientes = [(tid, t) for tid, t in TESOROS.items() if tid not in encontrados]
    if not pendientes:
        return "\n|g¡Has encontrado todos los tesoros del mundo!|n\n"
    sep = "|w" + "─" * 54 + "|n"
    lineas = [f"\n{sep}", f"  |cPistas — Tesoros Pendientes ({len(pendientes)})|n", sep]
    for tid, t in pendientes:
        req = ""
        if t.get("requiere_kill"):
            req = f"\n    |x  Requisito: derrotar {t['requiere_kill'].replace('_',' ').title()}|n"
        lineas.append(f"\n  |x✗|n |w?|n  {t['pista']}{req}")
    lineas.append(f"\n{sep}\n")
    return "\n".join(lineas)
