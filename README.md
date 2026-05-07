# mudproj

MUD de rol en español construido sobre [Evennia](https://www.evennia.com/). Combate por turnos, economía de tienda, equipamiento con slots, IA de NPCs y sistema de patrullas.

## Características

| Sistema | Descripción |
|---|---|
| **Combate** | Turnos por iniciativa, habilidades, horda/1v1, handler por sala |
| **Equipamiento** | Slots arma / armadura / accesorio con bonuses a stats |
| **Tienda** | NPCs vendedores con stock finito o ilimitado, compra/venta |
| **NPCs** | Temperamentos (neutral, agresivo, cobarde, guardián), diálogo por palabra clave, patrullas |
| **Puertas** | Puertas con llave, secretas, con estado persistente |
| **Respawn** | Reaparición de NPCs con loot configurable |
| **Percepción** | Sistema de detección de objetos y personajes ocultos |

## Estructura

```
mygame/
├── features/          # Sistemas jugables (combat, equipment, shop, doors, respawn)
├── systems/           # Motor de reglas (combat engine, perception)
├── typeclasses/       # Character, NPC, Object, Equipo, Room, Exit
├── commands/          # CmdSets globales y comandos generales
├── world/             # Prototipos, entradas de ayuda, scripts de construcción
├── tests/             # Suite de integración (150 tests)
└── server/conf/       # Configuración de Evennia
```

## Instalación

Requiere Python 3.11+ y Evennia 4.x.

```bash
git clone https://github.com/galoneir-source/mudproj
cd mudproj

python -m venv venv
source venv/bin/activate
pip install evennia

evennia migrate
evennia start          # superuser solicitado en el primer arranque
```

Conéctate con cualquier cliente MUD en `localhost:4000` o con el webclient en `http://localhost:4001`.

## Tests

```bash
evennia test --settings settings.py .
```

## Comandos principales

| Comando | Alias | Descripción |
|---|---|---|
| `tienda [npc]` | `shop` | Ver catálogo del comerciante |
| `comprar <item> [de <npc>]` | `buy` | Comprar un artículo |
| `vender <item> [a <npc>]` | `sell` | Vender un objeto |
| `equipar <objeto>` | `equip` | Equipar del inventario |
| `desequipar <slot\|objeto>` | `unequip` | Desequipar |
| `equipo` | `gear` | Ver equipamiento actual |
| `atacar <objetivo>` | `attack` | Iniciar combate |
| `habilidad <nombre>` | `skill` | Usar habilidad de combate |

## Convenciones

- Todo el código y mensajes en **español**.
- Moneda universal: `db.monedas` (int) en el personaje.
- Stats de personaje: `fuerza`, `defensa`, `velocidad`, `hp`, `hp_max`.
- Los NPCs con `db.tienda` son comerciantes; los que tienen `db.patrol_rooms` patrullan.
