"""
tests/test_general_commands.py

Tests de integración para los alias en español (coger/soltar/decir) de los
comandos base de Evennia (get/drop/say) añadidos en commands/general_commands.py.

Regresión: world/help_entries.py siempre documentó "coger", "soltar" y
"decir" como comandos reales (temas "inventario", "loot", "comandos"), pero
nunca se había registrado ningún comando con esas keys/aliases — sólo
existían los originales de Evennia en inglés (get/drop/say), inalcanzables
para cualquier jugador que siguiera la ayuda del juego al pie de la letra.

Ejecutar con:
  evennia test --settings settings.py tests.test_general_commands
"""
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from commands.default_cmdsets import CharacterCmdSet


class TestAliasesEspanol(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)
        self.obj = create_object(
            "typeclasses.objects.Object", key="piedra", location=self.room1
        )

    def test_coger_recoge_el_objeto(self):
        self.char1.execute_cmd("coger piedra")
        self.assertEqual(self.obj.location, self.char1)

    def test_soltar_deja_el_objeto(self):
        self.char1.execute_cmd("coger piedra")
        self.char1.execute_cmd("soltar piedra")
        self.assertEqual(self.obj.location, self.room1)

    def test_decir_habla_en_la_sala(self):
        capturado = []
        self.char2.msg = lambda text=None, **kw: capturado.append(text)
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.char1.execute_cmd("decir hola a todos")
        mensajes = [
            t[0] if isinstance(t, tuple) else t for t in capturado if t
        ]
        self.assertTrue(any("hola a todos" in str(m) for m in mensajes))


class TestSinColisionEnCharacterCmdSet(EvenniaTest):
    """
    coger/soltar/decir comparten alias ("get"/"drop"/"say") con los
    comandos por defecto de Evennia — comprobar que no reintroducen el
    mismo bug de colisión de key/alias ya corregido antes en
    CharacterCmdSet (be21b80, c69392f), donde compartir una sola alias
    borraba el comando anterior por completo en vez de solo la palabra
    en conflicto.
    """

    def test_los_tres_alias_estan_presentes_y_reemplazan_al_original(self):
        cmdset = CharacterCmdSet()
        cmdset.at_cmdset_creation()
        claves = {cmd.key for cmd in cmdset.commands}

        self.assertIn("coger", claves)
        self.assertIn("soltar", claves)
        self.assertIn("decir", claves)
        # Los comandos originales de Evennia quedan reemplazados por los
        # alias en español (comparten key/alias, así que no coexisten).
        self.assertNotIn("get", claves)
        self.assertNotIn("drop", claves)
        self.assertNotIn("say", claves)
