# Changelog

Todos los cambios notables de este proyecto se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/).

## [Sin publicar]

## [0.1.0] — 2026-05-07

### Añadido
- Sistema de combate por turnos con handler por sala, orden de iniciativa y rondas.
- Habilidades de combate configurables por NPC y personaje.
- Sistema de equipamiento con slots `arma`, `armadura` y `accesorio`; bonuses aplicados a stats al equipar/desequipar.
- Sistema de tienda: NPCs con catálogo (`db.tienda`), stock finito o ilimitado, comandos `tienda`, `comprar` y `vender`.
- Typeclass `NPC` con temperamentos (`neutral`, `agresivo`, `cobarde`, `guardián`), diálogo por palabra clave y patrullas por sala.
- Sistema de puertas con llave, puertas secretas y estado persistente.
- Sistema de respawn de NPCs con loot configurable.
- Sistema de percepción: detección de objetos y personajes ocultos.
- Prototipos de objetos y NPCs en `world/prototypes.py`.
- Script de construcción del mundo en `world/build_expansion.py`.
- Entradas de ayuda en español en `world/help_entries.py`.
- API REST básica en `web/api/` para consultas externas.
- Suite de 150 tests de integración con `EvenniaTest`.

### Corregido
- `_get_equipamiento` usaba `isinstance(eq, dict)` que fallaba con `_SaverDict` de Evennia (es `MutableMapping`, no subclase de `dict`); corregido a `isinstance(eq, Mapping)`.
- `_buscar_comerciante` ignoraba NPCs con tienda vacía `[]` por ser falsy; corregido a comparación `is not None`.
- Parser de `comprar` dividía incorrectamente nombres de artículo con `" de "` (ej. `"pocion de vida"`); corregido con búsqueda silenciosa para verificar si el sufijo es un NPC real.
- Parser de `vender` tenía el mismo problema con `" a "` en nombres de artículo; corregido con la misma técnica.
