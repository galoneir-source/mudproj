"""
tests/test_encantamiento.py

Tests de integración para el sistema de encantamiento (v0.16.0).
Cubre: comando encantar, validación de ingredientes, actualización de stats,
ítems equipados y límites de nivel.

Ejecutar con:
  cd /opt/evennia/mudproj && venv/bin/evennia test mygame.tests.test_encantamiento
"""
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from features.enchantment.commands import CmdEncantar
from typeclasses.objects import Equipo, Object


def _make_cmd(CmdClass, caller, args=""):
    cmd = CmdClass()
    cmd.caller = caller
    cmd.args = args
    cmd.cmdstring = cmd.key
    cmd.session = None
    cmd.obj = caller
    cmd.raw_string = cmd.key + (" " + args if args else "")
    cmd.switches = []
    cmd.lhs = args
    cmd.rhs = ""
    return cmd


def _item(nombre, location):
    return create_object(Object, key=nombre, location=location)


def _equipo(nombre, slot, bonuses, location):
    obj = create_object(Equipo, key=nombre, location=location)
    obj.db.slot = slot
    obj.db.bonuses = bonuses
    return obj


class EncantamientoTestBase(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.sala = self.room1
        self.jugador = self.char1
        self.jugador.move_to(self.sala, quiet=True)
        self.jugador.db.fuerza = 10
        self.jugador.db.destreza = 10
        self.jugador.db.inteligencia = 10
        self.jugador.db.defensa = 5
        self.jugador.db.hp = 80
        self.jugador.db.hp_max = 80
        self.jugador.db.constitucion = 10
        self.jugador.db.equipamiento = {"arma": None, "armadura": None, "accesorio": None}
        self.msgs = []
        self.jugador.msg = lambda text=None, **kw: self.msgs.append(str(text))
        self.sala.msg_contents = lambda m, **kw: None

    def _todos_msgs(self):
        return "\n".join(self.msgs)

    def _encantar(self, args=""):
        _make_cmd(CmdEncantar, self.jugador, args).func()


# --------------------------------------------------------------------------- #
#  Validación básica
# --------------------------------------------------------------------------- #

class TestEncantarValidacion(EncantamientoTestBase):

    def test_encantar_objeto_no_equipo_da_error(self):
        _item("piedra", self.jugador)
        self._encantar("piedra")
        self.assertIn("no es un objeto equipable", self._todos_msgs())

    def test_encantar_objeto_inexistente_da_error(self):
        self._encantar("espada mágica")
        self.assertFalse(any("completado" in m for m in self.msgs))

    def test_encantar_sin_ingredientes_da_error(self):
        _equipo("espada de hierro", "arma", {"fuerza": 3, "destreza": 1}, self.jugador)
        self._encantar("espada de hierro")
        self.assertIn("materiales", self._todos_msgs())

    def test_encantar_item_ya_max_da_error(self):
        espada = _equipo("espada de hierro +3", "arma", {"fuerza": 9, "destreza": 1}, self.jugador)
        espada.db.encantamiento = 3
        self._encantar("espada de hierro +3")
        self.assertIn("máximo", self._todos_msgs())

    def test_encantar_sin_stats_positivos_da_error(self):
        baston = _equipo("báculo roto", "arma", {"defensa": -1}, self.jugador)
        _item("mineral de hierro", self.jugador)
        _item("mineral de hierro", self.jugador)
        self._encantar("báculo roto")
        self.assertIn("no tiene estadísticas", self._todos_msgs())


# --------------------------------------------------------------------------- #
#  Encantamiento de arma
# --------------------------------------------------------------------------- #

class TestEncantarArma(EncantamientoTestBase):

    def setUp(self):
        super().setUp()
        self.espada = _equipo(
            "espada de hierro", "arma", {"fuerza": 3, "destreza": 1}, self.jugador
        )

    def _ingredientes_nivel1(self):
        _item("mineral de hierro", self.jugador)
        _item("mineral de hierro", self.jugador)

    def test_encantar_arma_nivel1_ok(self):
        self._ingredientes_nivel1()
        self._encantar("espada de hierro")
        self.assertIn("completado", self._todos_msgs().lower())

    def test_encantar_arma_nivel1_renueva_key(self):
        self._ingredientes_nivel1()
        self._encantar("espada de hierro")
        self.assertIn("+1", self.espada.key)

    def test_encantar_arma_nivel1_actualiza_encantamiento(self):
        self._ingredientes_nivel1()
        self._encantar("espada de hierro")
        self.assertEqual(self.espada.db.encantamiento, 1)

    def test_encantar_arma_nivel1_actualiza_bonuses(self):
        self._ingredientes_nivel1()
        bonuses_antes = dict(self.espada.db.bonuses)
        self._encantar("espada de hierro")
        self.assertEqual(self.espada.db.bonuses["fuerza"], bonuses_antes["fuerza"] + 2)

    def test_encantar_arma_nivel1_consume_ingredientes(self):
        self._ingredientes_nivel1()
        self._encantar("espada de hierro")
        minerales = [o for o in self.jugador.contents if o.key == "mineral de hierro"]
        self.assertEqual(len(minerales), 0)

    def test_encantar_arma_nivel1_ingrediente_parcial_falla(self):
        _item("mineral de hierro", self.jugador)
        self._encantar("espada de hierro")
        self.assertNotIn("+1", self.espada.key)

    def test_encantar_arma_dos_veces_nivel2(self):
        self._ingredientes_nivel1()
        self._encantar("espada de hierro")
        # Ingredientes para nivel 2
        _item("mineral de hierro", self.jugador)
        _item("mineral de hierro", self.jugador)
        _item("núcleo de piedra", self.jugador)
        self._encantar("espada de hierro +1")
        self.assertEqual(self.espada.db.encantamiento, 2)
        self.assertIn("+2", self.espada.key)

    def test_encantar_arma_nivel2_bonuses_acumulados(self):
        self._ingredientes_nivel1()
        self._encantar("espada de hierro")
        _item("mineral de hierro", self.jugador)
        _item("mineral de hierro", self.jugador)
        _item("núcleo de piedra", self.jugador)
        self._encantar("espada de hierro +1")
        self.assertEqual(self.espada.db.bonuses["fuerza"], 3 + 2 + 2)

    def test_encantar_arma_hasta_max(self):
        for nivel in range(1, 4):
            ingredientes = {
                1: [("mineral de hierro", 2)],
                2: [("mineral de hierro", 2), ("núcleo de piedra", 1)],
                3: [("núcleo de piedra", 1), ("núcleo arcano", 1)],
            }[nivel]
            for ingr, cant in ingredientes:
                for _ in range(cant):
                    _item(ingr, self.jugador)
            self._encantar(self.espada.key)
        self.assertEqual(self.espada.db.encantamiento, 3)

    def test_encantar_arma_mas_alla_max_bloqueado(self):
        self.espada.db.encantamiento = 3
        _item("mineral de hierro", self.jugador)
        _item("mineral de hierro", self.jugador)
        nivel_antes = self.espada.db.encantamiento
        self._encantar(self.espada.key)
        self.assertEqual(self.espada.db.encantamiento, nivel_antes)


# --------------------------------------------------------------------------- #
#  Encantamiento de armadura
# --------------------------------------------------------------------------- #

class TestEncantarArmadura(EncantamientoTestBase):

    def setUp(self):
        super().setUp()
        self.armadura = _equipo(
            "armadura de cuero", "armadura", {"defensa": 4, "hp_max": 10}, self.jugador
        )

    def test_encantar_armadura_nivel1_ok(self):
        _item("escama de lagarto", self.jugador)
        _item("escama de lagarto", self.jugador)
        self._encantar("armadura de cuero")
        self.assertEqual(self.armadura.db.encantamiento, 1)

    def test_encantar_armadura_suma_defensa_y_hp(self):
        _item("escama de lagarto", self.jugador)
        _item("escama de lagarto", self.jugador)
        def_antes = self.armadura.db.bonuses["defensa"]
        hp_antes = self.armadura.db.bonuses["hp_max"]
        self._encantar("armadura de cuero")
        self.assertEqual(self.armadura.db.bonuses["defensa"], def_antes + 2)
        self.assertEqual(self.armadura.db.bonuses["hp_max"], hp_antes + 5)

    def test_encantar_armadura_renueva_key(self):
        _item("escama de lagarto", self.jugador)
        _item("escama de lagarto", self.jugador)
        self._encantar("armadura de cuero")
        self.assertIn("+1", self.armadura.key)


# --------------------------------------------------------------------------- #
#  Encantamiento de accesorio
# --------------------------------------------------------------------------- #

class TestEncantarAccesorio(EncantamientoTestBase):

    def setUp(self):
        super().setUp()
        self.anillo = _equipo(
            "anillo de destreza", "accesorio",
            {"destreza": 3, "inteligencia": 1}, self.jugador
        )

    def test_encantar_accesorio_nivel1_ok(self):
        _item("gema en bruto", self.jugador)
        self._encantar("anillo de destreza")
        self.assertEqual(self.anillo.db.encantamiento, 1)

    def test_encantar_accesorio_sube_todos_stats(self):
        _item("gema en bruto", self.jugador)
        dex_antes = self.anillo.db.bonuses["destreza"]
        int_antes = self.anillo.db.bonuses["inteligencia"]
        self._encantar("anillo de destreza")
        self.assertEqual(self.anillo.db.bonuses["destreza"], dex_antes + 1)
        self.assertEqual(self.anillo.db.bonuses["inteligencia"], int_antes + 1)


# --------------------------------------------------------------------------- #
#  Ítem equipado recibe bonus inmediatamente
# --------------------------------------------------------------------------- #

class TestEncantarEquipado(EncantamientoTestBase):

    def test_encantar_arma_equipada_aplica_stat_al_jugador(self):
        espada = _equipo("espada de hierro", "arma", {"fuerza": 3}, self.jugador)
        self.jugador.db.equipamiento = {"arma": espada, "armadura": None, "accesorio": None}
        self.jugador.db.fuerza = 13  # base 10 + 3 de la espada equipada

        _item("mineral de hierro", self.jugador)
        _item("mineral de hierro", self.jugador)
        fuerza_antes = self.jugador.db.fuerza
        self._encantar("espada de hierro")
        self.assertEqual(self.jugador.db.fuerza, fuerza_antes + 2)

    def test_encantar_arma_no_equipada_no_modifica_stat(self):
        espada = _equipo("espada de hierro", "arma", {"fuerza": 3}, self.jugador)
        # No la ponemos en equipamiento
        fuerza_antes = self.jugador.db.fuerza
        _item("mineral de hierro", self.jugador)
        _item("mineral de hierro", self.jugador)
        self._encantar("espada de hierro")
        self.assertEqual(self.jugador.db.fuerza, fuerza_antes)

    def test_encantar_armadura_equipada_aplica_hp(self):
        armadura = _equipo("cota de malla", "armadura", {"defensa": 8, "hp_max": 20}, self.jugador)
        self.jugador.db.equipamiento = {"arma": None, "armadura": armadura, "accesorio": None}
        hp_antes = self.jugador.db.hp
        hp_max_antes = self.jugador.db.hp_max
        _item("escama de lagarto", self.jugador)
        _item("escama de lagarto", self.jugador)
        self._encantar("cota de malla")
        self.assertEqual(self.jugador.db.hp_max, hp_max_antes + 5)
        self.assertEqual(self.jugador.db.hp, hp_antes + 5)


# --------------------------------------------------------------------------- #
#  Listado de ítems encantables (sin args)
# --------------------------------------------------------------------------- #

class TestEncantarListado(EncantamientoTestBase):

    def test_listado_sin_equipo_da_mensaje(self):
        self._encantar("")
        self.assertIn("ningún", self._todos_msgs())

    def test_listado_con_equipo_muestra_item(self):
        _equipo("espada de hierro", "arma", {"fuerza": 3}, self.jugador)
        self._encantar("")
        self.assertIn("espada de hierro", self._todos_msgs())

    def test_listado_muestra_nivel_actual(self):
        espada = _equipo("espada +1", "arma", {"fuerza": 5}, self.jugador)
        espada.db.encantamiento = 1
        self._encantar("")
        texto = self._todos_msgs()
        self.assertIn("+1", texto)

    def test_listado_item_max_muestra_max(self):
        espada = _equipo("espada de hierro +3", "arma", {"fuerza": 9}, self.jugador)
        espada.db.encantamiento = 3
        self._encantar("")
        self.assertIn("máx", self._todos_msgs())

    def test_listado_muestra_coste(self):
        _equipo("espada de hierro", "arma", {"fuerza": 3}, self.jugador)
        self._encantar("")
        self.assertIn("mineral de hierro", self._todos_msgs())
