# Changelog

Todos los cambios notables de este proyecto se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/).

## [Sin publicar]

## [0.3.0] — 2026-05-11

### Añadido
- Sistema de crafteo: módulo puro `systems/crafting/recipes.py` con 4 recetas y funciones de validación sin dependencias de Evennia.
- Comando `craftear` (alias `fabricar`, `elaborar`) para elaborar objetos consumibles desde el inventario.
- Comando `recetas` (alias `recipes`) para listar y consultar recetas disponibles.
- Búsqueda de receta por nombre exacto, por prefijo y por contenido; detecta ambigüedad y pide más precisión.
- Los objetos equipados nunca se consumen accidentalmente al craftear.
- 4 recetas que dan uso al loot de las zonas de expansión:
  - `piel de serpiente` → poción de vida
  - `piel de serpiente` + `veneno de pantano` → antídoto x2
  - `garra de troll` + `piel de serpiente` → poción de vida mayor
  - `fragmento de alma` + `escama de lagarto x2` → elixir de restauración
- 35 tests nuevos: 19 unitarios puros + 16 de integración (suite total: 206 tests).

## [0.2.0] — 2026-05-11

### Añadido
- Sistema de consumibles: typeclass `Consumible` con efectos `curar_hp`, `curar_maximo` y `curar_veneno`.
- Comando `usar` (alias `beber`, `tomar`, `consumir`) para usar objetos consumibles del inventario.
- Los consumibles con usos finitos se eliminan automáticamente al agotarse.
- 4 prototipos nuevos: `POCION_VIDA` (+30 HP), `POCION_VIDA_MAYOR` (+60 HP), `ELIXIR_RESTAURACION` (HP al máximo), `ANTIDOTO` (cura envenenamiento).
- El mesonero vende poción de vida (15 m) y antídoto (20 m).
- La mercader vende poción de vida mayor (30 m) y elixir de restauración (75 m).
- El inventario muestra los consumibles como grupo propio con el efecto resumido.
- 21 tests de integración para el sistema de consumibles (suite total: 171 tests).

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
