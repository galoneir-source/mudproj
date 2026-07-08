# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comandos esenciales

El directorio de trabajo es `/opt/evennia/mudproj/mygame/`. Todos los comandos de Evennia se ejecutan desde `/opt/evennia/mudproj/`.

```bash
# Servidor
evennia start          # arrancar (pide superuser la primera vez)
evennia reload         # recargar sin perder conexiones
evennia stop

# Tests puros (sin Django, ejecutar desde mygame/)
pytest tests/test_arena_system.py          # un archivo concreto
pytest tests/ -k "system"                 # todos los *_system.py (lógica pura)

# Tests de integración (requieren Django setup, ejecutar desde mudproj/)
evennia test --settings settings.py tests.test_combat_states   # un archivo
evennia test --settings settings.py .                          # suite completa
```

Los archivos `tests/test_*_system.py` son **tests puros** (pytest directo, sin Evennia). Los archivos `tests/test_*.py` sin sufijo `_system` son **tests de integración** que heredan de `EvenniaTest` y requieren `evennia test`.

## Arquitectura

### Separación systems / features / typeclasses

La convención más importante del proyecto:

- **`systems/`** — lógica de negocio pura, sin importaciones de Evennia. Funciones y constantes que se pueden testear con pytest directamente.
- **`features/`** — integración con Evennia: `Command`, `CmdSet`, `DefaultScript`. Importa de `systems/` para la lógica y de Evennia para el framework.
- **`typeclasses/`** — `Character`, `NPC`, `Room`, `Object`, etc. Sólo inicialización de atributos `db.*` y hooks de ciclo de vida.

Un sistema nuevo sigue siempre este patrón: `systems/<nombre>/<nombre>.py` (lógica pura + tests puros) → `features/<nombre>/commands.py` + `features/<nombre>/<nombre>_script.py` (integración Evennia).

### Registro de comandos

Todos los `CmdSet` se importan y añaden en `commands/default_cmdsets.py → CharacterCmdSet.at_cmdset_creation()`. Al añadir un nuevo sistema hay que registrarlo ahí.

### Scripts globales persistentes

Los scripts que gestiona el servidor (clima, reloj, mercado, contratos, jefes de mundo, etc.) se arrancan en `server/conf/at_server_startstop.py → at_server_start()`. El patrón es `obtener_<nombre>_script()`: si el script ya existe lo devuelve; si no, lo crea.

### Atributos del personaje (`Character.at_object_creation`)

Cada sistema nuevo que necesite estado en el personaje añade su inicialización en `typeclasses/characters.py → at_object_creation`. Convenio: `db.<nombre_sistema>` en minúsculas con guión bajo.

### Sistema de logros

`features/achievements/commands.py` centraliza dos piezas clave:

- `_extraer_datos(caller)` — construye el dict de estado que se pasa a la lógica pura. Cada nuevo stat de logro debe añadirse aquí.
- `comprobar_y_notificar(caller)` — se llama desde cualquier handler tras un evento (kill, quest, crafteo, etc.). También llama `verificar_subida_rango()`.

Las categorías de logros se declaran en `_ORDEN_CATS` y `_NOMBRES_CATS` en ese mismo módulo.

### Mundo

- `server/conf/at_initial_setup.py` — construcción del mundo base (9 salas, NPCs civiles, items iniciales). Se ejecuta una sola vez.
- `world/build_expansion.py` — salas adicionales, idempotente (seguro de relanzar).
- `world/prototypes.py` — todos los prototipos de NPCs e ítems del mundo.

Las salas tienen `db.zona` (string id) para el sistema de spawn. Los NPCs tienen `db.npc_prototipo` para respawn y `db.faccion` para reputación.

## Convenciones clave

- Todo el código, mensajes y comentarios en **español**.
- Stats de personaje en `db.*`: `fuerza`, `destreza`, `constitucion`, `inteligencia`, `defensa`, `hp`, `hp_max`, `nivel`, `experiencia`.
- `db.monedas` es la moneda universal (int).
- `db.habilidades_desbloqueadas` (lista de IDs con underscore) en jugadores; `db.habilidades` (legacy con espacios) en NPCs.
- Colores Evennia: `|r` rojo, `|g` verde, `|y` amarillo, `|w` blanco, `|c` cian, `|Y` amarillo brillante, `|x` gris oscuro, `|n` reset.
- `_SaverDict` de Evennia no es subclase de `dict` — usar `isinstance(x, MutableMapping)` o convertir con `dict(...)` antes de operar.
- Los tests puros deben importar solo de `systems/`; si necesitan objetos Evennia, son tests de integración.
