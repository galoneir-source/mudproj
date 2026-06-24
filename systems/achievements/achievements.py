"""
systems/achievements/achievements.py

Lógica pura del sistema de logros y títulos. Sin dependencias de Evennia.

Catálogo de 20 logros distribuidos en 7 categorías. Cada logro puede otorgar
un título que el jugador puede activar en su perfil.

datos (dict que reciben las funciones de verificación):
  nivel             int   — nivel actual del personaje
  quests_entregadas int   — misiones con estado "entregada"
  habilidades       list  — IDs de habilidades desbloqueadas
  reputacion        dict  — {faccion_id: puntos}
  kills_totales     int   — NPCs derrotados en total
  jefes_derrotados  list  — prototype_key de jefes eliminados
  objetos_crafteados int  — objetos elaborados en total
  encantamiento_max int   — nivel más alto alcanzado en cualquier encantamiento
  banco_usado       bool  — ha depositado alguna vez en el banco
"""
from __future__ import annotations

# Prototype keys de los jefes del mundo
JEFES: frozenset[str] = frozenset({
    "GOBLIN_JEFE",
    "BANDIDO_CAPITAN",
    "TROLL",
    "CABALLERO_OSCURO",
    "GOLEM_PIEDRA",
    "ARCHIMAGO_VEXTHAR",
    "LICHE_INMORTAL",
})

# Habilidades iniciales que no cuentan como "aprendidas" para logros
_INICIALES: frozenset[str] = frozenset({"golpe_fuerte", "golpe_rapido"})

# Conjuntos de habilidades por rama
_RAMAS: dict[str, frozenset[str]] = {
    "guerrero":   frozenset({"golpe_fuerte", "embestida", "escudo_fe", "golpe_maestro"}),
    "explorador": frozenset({"golpe_rapido", "corte", "veneno", "ejecutar"}),
    "mago":       frozenset({"dardo_magico", "escudo_arcano", "bola_fuego", "drenar_vida"}),
}

# Conjuntos de habilidades por subclase
_HABS_SUBCLASE: dict[str, frozenset[str]] = {
    "paladin":    frozenset({"escudo_divino",       "golpe_sagrado"}),
    "berserker":  frozenset({"furia_berserker",     "golpe_demoledor"}),
    "asesino":    frozenset({"golpe_certero",       "golpe_letal"}),
    "cazador":    frozenset({"instinto_cazador",    "trampa_mortal"}),
    "hechicero":  frozenset({"concentracion_arcana","nova_arcana"}),
    "nigromante": frozenset({"escudo_sombrio",      "drenar_esencia"}),
}

# Umbrales de reputación (en puntos) para "al menos X rango"
_UMBRAL_AMISTOSO = 1000
_UMBRAL_HONRADO  = 3000


LOGROS: dict[str, dict] = {
    # ── Progresión ──────────────────────────────────────────────────────────
    "nivel_2": {
        "nombre":      "Primer Paso",
        "descripcion": "Alcanza el nivel 2.",
        "titulo":      "el Novato",
        "categoria":   "progresion",
    },
    "nivel_5": {
        "nombre":      "Veterano",
        "descripcion": "Alcanza el nivel 5.",
        "titulo":      "el Veterano",
        "categoria":   "progresion",
    },
    "nivel_10": {
        "nombre":      "Leyenda",
        "descripcion": "Alcanza el nivel máximo (10).",
        "titulo":      "la Leyenda",
        "categoria":   "progresion",
    },

    # ── Misiones ─────────────────────────────────────────────────────────────
    "primera_mision": {
        "nombre":      "Aventurero",
        "descripcion": "Entrega tu primera misión.",
        "titulo":      None,
        "categoria":   "misiones",
    },
    "cinco_misiones": {
        "nombre":      "Héroe",
        "descripcion": "Entrega 5 misiones.",
        "titulo":      "el Héroe",
        "categoria":   "misiones",
    },
    "diez_misiones": {
        "nombre":      "Campeón",
        "descripcion": "Entrega 10 misiones.",
        "titulo":      "el Campeón",
        "categoria":   "misiones",
    },

    # ── Combate ──────────────────────────────────────────────────────────────
    "diez_kills": {
        "nombre":      "Cazador",
        "descripcion": "Derrota 10 enemigos.",
        "titulo":      None,
        "categoria":   "combate",
    },
    "cincuenta_kills": {
        "nombre":      "Verdugo",
        "descripcion": "Derrota 50 enemigos.",
        "titulo":      "el Verdugo",
        "categoria":   "combate",
    },
    "tres_jefes": {
        "nombre":      "Azote de Jefes",
        "descripcion": "Derrota 3 jefes distintos.",
        "titulo":      "Azote de Jefes",
        "categoria":   "combate",
    },
    "todos_jefes": {
        "nombre":      "Terror del Mundo",
        "descripcion": f"Derrota los {len(JEFES)} jefes del mundo.",
        "titulo":      "el Terror",
        "categoria":   "combate",
    },

    # ── Habilidades ──────────────────────────────────────────────────────────
    "primera_habilidad": {
        "nombre":      "Aprendiz",
        "descripcion": "Aprende tu primera habilidad fuera de las iniciales.",
        "titulo":      None,
        "categoria":   "habilidades",
    },
    "seis_habilidades": {
        "nombre":      "Experto",
        "descripcion": "Aprende 6 habilidades.",
        "titulo":      None,
        "categoria":   "habilidades",
    },
    "rama_completa": {
        "nombre":      "Especialista",
        "descripcion": "Domina las 4 habilidades de una rama.",
        "titulo":      "el Especialista",
        "categoria":   "habilidades",
    },

    # ── Encantamiento ────────────────────────────────────────────────────────
    "primer_encantamiento": {
        "nombre":      "Forjador",
        "descripcion": "Encanta un objeto por primera vez.",
        "titulo":      None,
        "categoria":   "encantamiento",
    },
    "encantamiento_max": {
        "nombre":      "Maestro Forjador",
        "descripcion": "Alcanza el nivel +3 en un objeto encantado.",
        "titulo":      "el Forjador",
        "categoria":   "encantamiento",
    },

    # ── Reputación ───────────────────────────────────────────────────────────
    "honrado_ciudadanos": {
        "nombre":      "Ciudadano Honrado",
        "descripcion": "Alcanza el rango Honrado con los Ciudadanos.",
        "titulo":      None,
        "categoria":   "reputacion",
    },
    "diplomatico": {
        "nombre":      "Diplomático",
        "descripcion": "Alcanza el rango Amistoso con 3 facciones.",
        "titulo":      "el Diplomático",
        "categoria":   "reputacion",
    },

    # ── Crafteo ──────────────────────────────────────────────────────────────
    "primer_crafteo": {
        "nombre":      "Artesano",
        "descripcion": "Elabora tu primer objeto.",
        "titulo":      None,
        "categoria":   "crafteo",
    },
    "diez_crafteos": {
        "nombre":      "Maestro Artesano",
        "descripcion": "Elabora 10 objetos.",
        "titulo":      "el Artesano",
        "categoria":   "crafteo",
    },

    # ── Economía ─────────────────────────────────────────────────────────────
    "primer_deposito": {
        "nombre":      "Ahorrador",
        "descripcion": "Deposita un objeto en el banco por primera vez.",
        "titulo":      None,
        "categoria":   "economia",
    },

    # ── Subclase ─────────────────────────────────────────────────────────────
    "especializacion_elegida": {
        "nombre":      "Elegido",
        "descripcion": "Elige tu especialización.",
        "titulo":      None,
        "categoria":   "subclase",
    },
    "maestro_paladin": {
        "nombre":      "Escudo Sagrado",
        "descripcion": "Como Paladín, aprende las 2 habilidades de tu subclase.",
        "titulo":      "el Paladín",
        "categoria":   "subclase",
    },
    "maestro_berserker": {
        "nombre":      "Furia Sin Fin",
        "descripcion": "Como Berserker, aprende las 2 habilidades de tu subclase.",
        "titulo":      "el Berserker",
        "categoria":   "subclase",
    },
    "maestro_asesino": {
        "nombre":      "Golpe en las Sombras",
        "descripcion": "Como Asesino, aprende las 2 habilidades de tu subclase.",
        "titulo":      "la Sombra Oscura",
        "categoria":   "subclase",
    },
    "maestro_cazador": {
        "nombre":      "Depredador",
        "descripcion": "Como Cazador, aprende las 2 habilidades de tu subclase.",
        "titulo":      "el Depredador",
        "categoria":   "subclase",
    },
    "maestro_hechicero": {
        "nombre":      "Tormenta Arcana",
        "descripcion": "Como Hechicero, aprende las 2 habilidades de tu subclase.",
        "titulo":      "la Tormenta",
        "categoria":   "subclase",
    },
    "maestro_nigromante": {
        "nombre":      "Drenador de Almas",
        "descripcion": "Como Nigromante, aprende las 2 habilidades de tu subclase.",
        "titulo":      "el Nigromante",
        "categoria":   "subclase",
    },

    # ── Clase ─────────────────────────────────────────────────────────────────
    "vocacion_elegida": {
        "nombre":      "Llamado",
        "descripcion": "Elige tu vocación.",
        "titulo":      None,
        "categoria":   "clase",
    },
    "maestro_guerrero": {
        "nombre":      "Caballero de Hierro",
        "descripcion": "Como Guerrero, aprende las 4 habilidades de tu rama.",
        "titulo":      "el Caballero",
        "categoria":   "clase",
    },
    "maestro_explorador": {
        "nombre":      "Sombra Veloz",
        "descripcion": "Como Explorador, aprende las 4 habilidades de tu rama.",
        "titulo":      "la Sombra",
        "categoria":   "clase",
    },
    "maestro_mago": {
        "nombre":      "Archimago",
        "descripcion": "Como Mago, aprende las 4 habilidades de tu rama.",
        "titulo":      "el Archimago",
        "categoria":   "clase",
    },
}


def _cumple(logro_id: str, datos: dict) -> bool:
    """Comprueba si se cumplen las condiciones de un logro dado el estado del personaje."""
    nivel     = datos.get("nivel", 1)
    kills     = datos.get("kills_totales", 0)
    jefes     = set(datos.get("jefes_derrotados", []))
    entregadas = datos.get("quests_entregadas", 0)
    habs      = set(datos.get("habilidades", []))
    rep       = datos.get("reputacion", {})
    crafteados = datos.get("objetos_crafteados", 0)
    enc_max   = datos.get("encantamiento_max", 0)
    banco     = datos.get("banco_usado", False)

    if logro_id == "nivel_2":       return nivel >= 2
    if logro_id == "nivel_5":       return nivel >= 5
    if logro_id == "nivel_10":      return nivel >= 10

    if logro_id == "primera_mision":  return entregadas >= 1
    if logro_id == "cinco_misiones":  return entregadas >= 5
    if logro_id == "diez_misiones":   return entregadas >= 10

    if logro_id == "diez_kills":      return kills >= 10
    if logro_id == "cincuenta_kills": return kills >= 50
    if logro_id == "tres_jefes":      return len(jefes & JEFES) >= 3
    if logro_id == "todos_jefes":     return JEFES.issubset(jefes)

    if logro_id == "primera_habilidad": return bool(habs - _INICIALES)
    if logro_id == "seis_habilidades":  return len(habs) >= 6
    if logro_id == "rama_completa":
        return any(rama.issubset(habs) for rama in _RAMAS.values())

    if logro_id == "primer_encantamiento": return enc_max >= 1
    if logro_id == "encantamiento_max":    return enc_max >= 3

    if logro_id == "honrado_ciudadanos":
        return rep.get("ciudadanos", 0) >= _UMBRAL_HONRADO
    if logro_id == "diplomatico":
        amistosos = sum(1 for pts in rep.values() if pts >= _UMBRAL_AMISTOSO)
        return amistosos >= 3

    if logro_id == "primer_crafteo":  return crafteados >= 1
    if logro_id == "diez_crafteos":   return crafteados >= 10

    if logro_id == "primer_deposito": return bool(banco)

    subclase = datos.get("subclase") or ""
    if logro_id == "especializacion_elegida": return bool(subclase)
    if logro_id == "maestro_paladin":
        return subclase == "paladin" and _HABS_SUBCLASE["paladin"].issubset(habs)
    if logro_id == "maestro_berserker":
        return subclase == "berserker" and _HABS_SUBCLASE["berserker"].issubset(habs)
    if logro_id == "maestro_asesino":
        return subclase == "asesino" and _HABS_SUBCLASE["asesino"].issubset(habs)
    if logro_id == "maestro_cazador":
        return subclase == "cazador" and _HABS_SUBCLASE["cazador"].issubset(habs)
    if logro_id == "maestro_hechicero":
        return subclase == "hechicero" and _HABS_SUBCLASE["hechicero"].issubset(habs)
    if logro_id == "maestro_nigromante":
        return subclase == "nigromante" and _HABS_SUBCLASE["nigromante"].issubset(habs)

    clase = datos.get("clase") or ""
    if logro_id == "vocacion_elegida":  return bool(clase)
    if logro_id == "maestro_guerrero":
        return clase == "guerrero" and _RAMAS["guerrero"].issubset(habs)
    if logro_id == "maestro_explorador":
        return clase == "explorador" and _RAMAS["explorador"].issubset(habs)
    if logro_id == "maestro_mago":
        return clase == "mago" and _RAMAS["mago"].issubset(habs)

    return False


def verificar_todos(datos: dict) -> list[str]:
    """Devuelve la lista de IDs de todos los logros que se cumplen."""
    return [lid for lid in LOGROS if _cumple(lid, datos)]


def nuevos_logros(datos: dict, ya_desbloqueados: list[str]) -> list[str]:
    """Devuelve los logros que se cumplen ahora pero no estaban en ya_desbloqueados."""
    ya = set(ya_desbloqueados)
    return [lid for lid in LOGROS if lid not in ya and _cumple(lid, datos)]


def titulos_disponibles(logros_desbloqueados: list[str]) -> list[str]:
    """Devuelve la lista de títulos únicos desbloqueados (en orden de logro)."""
    vistos: list[str] = []
    for lid in logros_desbloqueados:
        t = LOGROS.get(lid, {}).get("titulo")
        if t and t not in vistos:
            vistos.append(t)
    return vistos
