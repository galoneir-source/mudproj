"""
systems/achievements/achievements.py

Lógica pura del sistema de logros y títulos. Sin dependencias de Evennia.

Catálogo de 38 logros distribuidos en 11 categorías. Cada logro puede otorgar
un título que el jugador puede activar en su perfil.

datos (dict que reciben las funciones de verificación):
  nivel                  int   — nivel actual del personaje
  quests_entregadas      int   — misiones con estado "entregada"
  habilidades            list  — IDs de habilidades desbloqueadas
  reputacion             dict  — {faccion_id: puntos}
  kills_totales          int   — NPCs derrotados en total
  jefes_derrotados       list  — prototype_key de jefes eliminados
  objetos_crafteados     int   — objetos elaborados en total
  encantamiento_max      int   — nivel más alto alcanzado en cualquier encantamiento
  banco_usado            bool  — ha depositado alguna vez en el banco
  mascota_nivel_max      int   — nivel más alto alcanzado por cualquier mascota (1-3)
  gremios_fundados       int   — número de gremios fundados
  es_lider_gremio        bool  — actualmente es Líder de un gremio
  miembros_gremio        int   — número de miembros en el gremio actual
  gremio_banco_depositado int  — total de monedas depositadas en banco gremial (acumulado)
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

    # ── Gremio ───────────────────────────────────────────────────────────────
    "gremio_fundado": {
        "nombre":      "Fundador",
        "descripcion": "Funda tu propio gremio.",
        "titulo":      None,
        "categoria":   "gremio",
    },
    "gremio_cinco_miembros": {
        "nombre":      "Líder Unificador",
        "descripcion": "Lidera un gremio con al menos 5 miembros.",
        "titulo":      None,
        "categoria":   "gremio",
    },
    "gremio_pleno": {
        "nombre":      "Comandante",
        "descripcion": f"Lidera un gremio con el máximo de miembros (20).",
        "titulo":      "el Comandante",
        "categoria":   "gremio",
    },
    "gremio_tesorero": {
        "nombre":      "Tesorero",
        "descripcion": "Deposita un total de 500 monedas en el banco del gremio.",
        "titulo":      None,
        "categoria":   "gremio",
    },
    "gremio_mecenas": {
        "nombre":      "Mecenas",
        "descripcion": "Deposita un total de 2000 monedas en el banco del gremio.",
        "titulo":      "el Mecenas",
        "categoria":   "gremio",
    },

    # ── Mascotas ─────────────────────────────────────────────────────────────
    "mascota_nivel_2": {
        "nombre":      "Primer Compañero",
        "descripcion": "Lleva tu mascota al nivel 2 (Mayor).",
        "titulo":      None,
        "categoria":   "mascotas",
    },
    "mascota_nivel_3": {
        "nombre":      "Domador",
        "descripcion": "Lleva tu mascota al nivel 3 (Élite).",
        "titulo":      "el Domador",
        "categoria":   "mascotas",
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

    # ── Jefes de Mundo ────────────────────────────────────────────────────────
    "titan_derrotado": {
        "nombre":      "Cazador de Titanes",
        "descripcion": "Participa en la derrota del Titán del Pantano.",
        "titulo":      None,
        "categoria":   "jefe_mundo",
    },
    "guardian_derrotado": {
        "nombre":      "Forjado en Lava",
        "descripcion": "Participa en la derrota del Guardián de la Forja.",
        "titulo":      None,
        "categoria":   "jefe_mundo",
    },
    "dragon_derrotado": {
        "nombre":      "Cazadragones",
        "descripcion": "Participa en la derrota del Dragón de Ceniza.",
        "titulo":      "Cazadragones",
        "categoria":   "jefe_mundo",
    },
    "todos_jefes_mundo": {
        "nombre":      "Azote del Mundo",
        "descripcion": "Participa en la derrota de los tres jefes de mundo.",
        "titulo":      "el Azote",
        "categoria":   "jefe_mundo",
    },

    # ── Mazmorra ──────────────────────────────────────────────────────────────
    "cripta_completada": {
        "nombre":      "Conquistador de la Cripta",
        "descripcion": "Completa la Cripta de Ceniza.",
        "titulo":      None,
        "categoria":   "mazmorra",
    },
    "forja_completada": {
        "nombre":      "Templado en Fuego",
        "descripcion": "Completa la Forja Maldita.",
        "titulo":      None,
        "categoria":   "mazmorra",
    },
    "abismo_completado": {
        "nombre":      "Conquistador del Abismo",
        "descripcion": "Completa el Abismo Sin Fondo.",
        "titulo":      "el Conquistador",
        "categoria":   "mazmorra",
    },
    "todas_mazmorras": {
        "nombre":      "Explorador de lo Profundo",
        "descripcion": "Completa las tres mazmorras al menos una vez.",
        "titulo":      None,
        "categoria":   "mazmorra",
    },
    "mazmorra_legendario": {
        "nombre":      "Leyenda Viva",
        "descripcion": "Completa cualquier mazmorra en dificultad legendario.",
        "titulo":      "el Legendario",
        "categoria":   "mazmorra",
    },

    # ── Arena ─────────────────────────────────────────────────────────────────
    "campeon_arena": {
        "nombre":      "Campeón de la Arena",
        "descripcion": "Gana un torneo de la Arena.",
        "titulo":      "el Campeón de la Arena",
        "categoria":   "arena",
    },
    "maestro_arena": {
        "nombre":      "Imbatible",
        "descripcion": "Gana 3 torneos de la Arena.",
        "titulo":      "el Imbatible",
        "categoria":   "arena",
    },

    # ── Bestiario ─────────────────────────────────────────────────────────────
    "primera_presa": {
        "nombre":      "Primera Presa",
        "descripcion": "Registra tu primera criatura en el bestiario.",
        "titulo":      None,
        "categoria":   "bestiario",
    },
    "cazador_experimentado": {
        "nombre":      "Cazador Experimentado",
        "descripcion": "Registra 10 criaturas distintas en el bestiario.",
        "titulo":      None,
        "categoria":   "bestiario",
    },
    "enciclopedista": {
        "nombre":      "Enciclopedista",
        "descripcion": "Completa el bestiario derrotando todas las criaturas del catálogo.",
        "titulo":      "el Enciclopedista",
        "categoria":   "bestiario",
    },

    # ── Vivienda ───────────────────────────────────────────────────────────────
    "primera_vivienda": {
        "nombre":      "Propietario",
        "descripcion": "Compra tu primera vivienda.",
        "titulo":      None,
        "categoria":   "vivienda",
    },
    "hogar_decorado": {
        "nombre":      "Toque Personal",
        "descripcion": "Decora tu vivienda con una descripción propia.",
        "titulo":      "el Anfitrión",
        "categoria":   "vivienda",
    },

    # ── Monturas ──────────────────────────────────────────────────────────────
    "primer_jinete": {
        "nombre":      "Primer Jinete",
        "descripcion": "Adquiere tu primera montura.",
        "titulo":      None,
        "categoria":   "monturas",
    },
    "ecuyer": {
        "nombre":      "Escudero",
        "descripcion": "Posee 3 monturas distintas en tu cuadra.",
        "titulo":      None,
        "categoria":   "monturas",
    },
    "amo_grifo": {
        "nombre":      "Amo del Grifo",
        "descripcion": "Desbloquea el legendario Grifo Real.",
        "titulo":      "el Jinete",
        "categoria":   "monturas",
    },

    # ── Cartografía ───────────────────────────────────────────────────────────
    "primer_viaje": {
        "nombre":      "Primer Viaje",
        "descripcion": "Visita tu primera sala del mundo.",
        "titulo":      None,
        "categoria":   "cartografia",
    },
    "explorador": {
        "nombre":      "Explorador",
        "descripcion": "Explora 10 salas distintas del mundo.",
        "titulo":      None,
        "categoria":   "cartografia",
    },
    "cartografo": {
        "nombre":      "Cartógrafo",
        "descripcion": "Explora las 29 salas del mundo.",
        "titulo":      "el Cartógrafo",
        "categoria":   "cartografia",
    },

    # ── Runas ─────────────────────────────────────────────────────────────────
    "primera_runa": {
        "nombre":      "Grabador de Runas",
        "descripcion": "Graba tu primera runa en algún equipo.",
        "titulo":      None,
        "categoria":   "runas",
    },
    "runas_completas": {
        "nombre":      "Tríada Rúnica",
        "descripcion": "Graba runas en los tres slots de equipamiento a la vez.",
        "titulo":      "el Tallador",
        "categoria":   "runas",
    },
    "runa_arcana": {
        "nombre":      "Maestro Rúnico",
        "descripcion": "Graba la poderosa Runa Arcana (requiere nivel 9).",
        "titulo":      "el Maestro Rúnico",
        "categoria":   "runas",
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

    gremios_fundados     = datos.get("gremios_fundados", 0)
    es_lider             = datos.get("es_lider_gremio", False)
    miembros_gremio      = datos.get("miembros_gremio", 0)
    banco_gremio         = datos.get("gremio_banco_depositado", 0)
    if logro_id == "gremio_fundado":        return gremios_fundados >= 1
    if logro_id == "gremio_cinco_miembros": return es_lider and miembros_gremio >= 5
    if logro_id == "gremio_pleno":          return es_lider and miembros_gremio >= 20
    if logro_id == "gremio_tesorero":       return banco_gremio >= 500
    if logro_id == "gremio_mecenas":        return banco_gremio >= 2000

    nivel_mascota = datos.get("mascota_nivel_max", 1)
    if logro_id == "mascota_nivel_2": return nivel_mascota >= 2
    if logro_id == "mascota_nivel_3": return nivel_mascota >= 3

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

    jefes_mundo = datos.get("jefes_mundo_derrotados", {})
    if logro_id == "titan_derrotado":
        return bool(jefes_mundo.get("TITAN_PANTANO", 0))
    if logro_id == "guardian_derrotado":
        return bool(jefes_mundo.get("GUARDIAN_FORJA", 0))
    if logro_id == "dragon_derrotado":
        return bool(jefes_mundo.get("DRAGON_CENIZA", 0))
    if logro_id == "todos_jefes_mundo":
        return all(jefes_mundo.get(k, 0) for k in ("TITAN_PANTANO", "GUARDIAN_FORJA", "DRAGON_CENIZA"))

    mazmorras = datos.get("mazmorras_completadas", {})
    if logro_id == "cripta_completada":
        return bool(mazmorras.get("cripta_ceniza", 0))
    if logro_id == "forja_completada":
        return bool(mazmorras.get("forja_maldita", 0))
    if logro_id == "abismo_completado":
        return bool(mazmorras.get("abismo_sin_fondo", 0))
    if logro_id == "todas_mazmorras":
        return all(mazmorras.get(k, 0) for k in ("cripta_ceniza", "forja_maldita", "abismo_sin_fondo"))
    if logro_id == "mazmorra_legendario":
        return bool(datos.get("mazmorra_legendario", False))

    torneos = datos.get("torneos_ganados", 0)
    if logro_id == "campeon_arena":  return torneos >= 1
    if logro_id == "maestro_arena":  return torneos >= 3

    runas = datos.get("runas_equipadas", {})
    runas_activas = sum(1 for v in runas.values() if v)
    if logro_id == "primera_runa":
        return runas_activas >= 1
    if logro_id == "runas_completas":
        return runas_activas >= 3
    if logro_id == "runa_arcana":
        return "RUNA_ARCANA" in runas.values()

    if logro_id == "primera_vivienda": return bool(datos.get("vivienda_comprada", False))
    if logro_id == "hogar_decorado":   return bool(datos.get("vivienda_decorada", False))

    monturas_count = datos.get("monturas_poseidas", 0)
    if logro_id == "primer_jinete": return monturas_count >= 1
    if logro_id == "ecuyer":        return monturas_count >= 3
    if logro_id == "amo_grifo":     return bool(datos.get("tiene_grifo_real", False))

    salas_exploradas = datos.get("salas_exploradas", 0)
    if logro_id == "primer_viaje":  return salas_exploradas >= 1
    if logro_id == "explorador":    return salas_exploradas >= 10
    if logro_id == "cartografo":    return salas_exploradas >= 29

    criaturas = datos.get("criaturas_registradas", 0)
    if logro_id == "primera_presa":          return criaturas >= 1
    if logro_id == "cazador_experimentado":  return criaturas >= 10
    if logro_id == "enciclopedista":         return bool(datos.get("bestiary_completo", False))

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
