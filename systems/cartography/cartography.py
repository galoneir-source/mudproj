"""
systems/cartography/cartography.py

Lógica pura del sistema de cartografía. Sin dependencias de Evennia.

Se registra cada sala visitada por su dbref. Solo cuentan las salas con
db.zona asignado que no sean instanciadas (mazmorras, viviendas).

db.salas_exploradas en Character: list[str]  — lista de dbrefs únicos.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
#  Catálogo de zonas — define el orden y la agrupación para el mapa
# --------------------------------------------------------------------------- #
#  Cada entrada: (zona_id, nombre_sala, area_display)

ZONAS_INFO: list[tuple[str, str, str]] = [
    # Ciudad
    ("plaza_ciudad",         "Plaza de la Ciudad",        "Ciudad"),
    ("taberna",              "Taberna El Jabalí Borracho","Ciudad"),
    ("mercado",              "Mercado de la Ciudad",       "Ciudad"),
    # Bosque
    ("bosque_norte",         "Bosque del Norte",           "Bosque"),
    ("claro_bosque",         "Claro del Bosque",           "Bosque"),
    # Calabozo
    ("calabozo_entrada",     "Entrada al Calabozo",        "Calabozo"),
    ("calabozo_pasillo",     "Pasillo del Calabozo",       "Calabozo"),
    ("calabozo_celda",       "Celda Abandonada",           "Calabozo"),
    # Pantano
    ("senda_fangosa",        "Senda Fangosa",              "Pantano del Troll"),
    ("pantano_cenagoso",     "Pantano Cenagoso",           "Pantano del Troll"),
    ("guarida_troll",        "Guarida del Troll",          "Pantano del Troll"),
    # Catacumbas
    ("sala_tumbas",          "Sala de las Tumbas",         "Catacumbas"),
    ("camara_nigromante",    "Cámara del Nigromante",      "Catacumbas"),
    # Ruinas del Templo
    ("camino_templo",        "Camino al Templo",           "Ruinas del Templo"),
    ("ruinas_templo",        "Ruinas del Templo",          "Ruinas del Templo"),
    ("cripta_baron",         "Cripta del Barón",           "Ruinas del Templo"),
    # Minas
    ("boca_mina",            "Boca de la Mina",            "Minas de Hierro Viejo"),
    ("galeria_principal",    "Galería Principal",          "Minas de Hierro Viejo"),
    ("caverna_coloso",       "Caverna del Coloso",         "Minas de Hierro Viejo"),
    # Torre
    ("base_torre",           "Base de la Torre",           "Torre del Mago Caído"),
    ("biblioteca_archimago", "Biblioteca del Archimago",   "Torre del Mago Caído"),
    ("camara_ritual",        "Cámara del Ritual",          "Torre del Mago Caído"),
    # Ciudadela
    ("portal_ciudadela",     "Portal de la Ciudadela",     "Ciudadela Oscura"),
    ("salon_trono",          "Salón del Trono",            "Ciudadela Oscura"),
    ("altar_liche",          "Altar del Liche",            "Ciudadela Oscura"),
    # Zonas especiales
    ("orilla_rio",           "Orilla del Río",             "Zonas Especiales"),
    ("vestibulo_portal",     "Vestíbulo del Portal",       "Zonas Especiales"),
    ("arena_ciudad",         "Arena de la Ciudad",         "Zonas Especiales"),
    ("barrio_residencial",   "Barrio Residencial",         "Zonas Especiales"),
]

# Conjunto de IDs válidos para validación rápida
ZONAS_VALIDAS: frozenset[str] = frozenset(z[0] for z in ZONAS_INFO)

# Total de salas explorables conocidas en el catálogo
TOTAL_SALAS = len(ZONAS_INFO)


# --------------------------------------------------------------------------- #
#  Lógica pura
# --------------------------------------------------------------------------- #

def registrar_sala(exploradas: list, dbref: str) -> tuple[list, bool]:
    """
    Registra una sala en la lista de exploradas.
    Devuelve (lista_actualizada, es_nueva).
    es_nueva=True solo si el dbref no estaba ya registrado.
    No modifica la lista original.
    """
    if dbref in exploradas:
        return list(exploradas), False
    return list(exploradas) + [dbref], True


def total_exploradas(exploradas: list) -> int:
    """Número de salas únicas exploradas."""
    return len(set(exploradas))


def es_zona_explorable(zona_id: str | None) -> bool:
    """True si la zona está en el catálogo y por tanto debe registrarse."""
    return zona_id in ZONAS_VALIDAS


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

def _barra(actual: int, total: int, ancho: int = 16) -> str:
    if total == 0:
        return "░" * ancho
    llenos = min(ancho, int(actual / total * ancho))
    return "|g" + "█" * llenos + "|x" + "░" * (ancho - llenos) + "|n"


def formatear_mapa(
    exploradas_set: set,
    zonas_a_dbref: dict,
) -> str:
    """
    Construye el texto del mapa.

    exploradas_set  — set de dbrefs explorados por el jugador
    zonas_a_dbref   — {zona_id: dbref_de_la_sala} para todas las salas del mundo
                      (obtenido desde Evennia en la feature)
    """
    total_mundo = len(zonas_a_dbref)
    exploradas_count = sum(
        1 for zona_id, dbref in zonas_a_dbref.items()
        if dbref in exploradas_set
    )

    sep = "|w" + "─" * 56 + "|n"
    barra = _barra(exploradas_count, total_mundo)
    lineas = [
        f"\n{sep}",
        f"  |cMapa del Mundo|n  —  "
        f"|w{exploradas_count}/{total_mundo}|n salas exploradas  {barra}",
        sep,
    ]

    area_actual = None
    for zona_id, nombre_sala, area in ZONAS_INFO:
        if zona_id not in zonas_a_dbref:
            continue   # zona no construida aún en este servidor
        if area != area_actual:
            area_actual = area
            lineas.append(f"\n  |y[{area}]|n")
        dbref = zonas_a_dbref[zona_id]
        if dbref in exploradas_set:
            lineas.append(f"    |g✔|n |w{nombre_sala}|n")
        else:
            lineas.append(f"    |x✗ {nombre_sala}|n")

    porcentaje = int(exploradas_count / total_mundo * 100) if total_mundo else 0
    lineas.append(f"\n  Progreso global: |w{porcentaje}%|n completado.")
    lineas.append(f"  Cada sala se registra sola al entrar en ella.")
    lineas.append(f"{sep}\n")
    return "\n".join(lineas)
