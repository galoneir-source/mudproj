"""
tests/test_equipment.py

Tests de integración para features/equipment/commands.py.
Ejecutar con:
  cd /opt/evennia/mudproj && venv/bin/evennia test mygame.tests.test_equipment
"""
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from features.equipment.commands import (
    _get_equipamiento,
    _aplicar_bonuses,
    CmdEquipar,
    CmdDesequipar,
    CmdEquipo,
    SLOTS,
)


def _make_cmd(CmdClass, caller, args=""):
    """Instancia un comando listo para llamar a func() en tests."""
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


# --------------------------------------------------------------------------- #
#  _get_equipamiento
# --------------------------------------------------------------------------- #

class TestGetEquipamiento(EvenniaTest):

    def test_crea_slots_vacios_si_no_existe(self):
        char = create_object("typeclasses.characters.Character", key="test_eq_1")
        char.db.equipamiento = None
        eq = _get_equipamiento(char)
        self.assertEqual(set(eq.keys()), set(SLOTS))
        for v in eq.values():
            self.assertIsNone(v)

    def test_no_sobreescribe_slots_existentes(self):
        char = create_object("typeclasses.characters.Character", key="test_eq_2")
        espada = create_object("typeclasses.objects.Equipo", key="espada_guard")
        espada.db.slot = "arma"
        espada.db.bonuses = {"fuerza": 2}
        char.db.equipamiento = {"arma": espada, "armadura": None, "accesorio": None}
        eq = _get_equipamiento(char)
        self.assertEqual(eq["arma"], espada)

    def test_añade_slots_faltantes_sin_borrar_existentes(self):
        char = create_object("typeclasses.characters.Character", key="test_eq_3")
        char.db.equipamiento = {"arma": None}
        eq = _get_equipamiento(char)
        for s in SLOTS:
            self.assertIn(s, eq)


# --------------------------------------------------------------------------- #
#  _aplicar_bonuses
# --------------------------------------------------------------------------- #

class TestAplicarBonuses(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char = create_object("typeclasses.characters.Character", key="test_bonus")
        self.char.db.fuerza = 10
        self.char.db.defensa = 5
        self.char.db.hp = 50
        self.char.db.hp_max = 50

    def test_suma_bonuses(self):
        _aplicar_bonuses(self.char, {"fuerza": 3, "defensa": 2}, signo=1)
        self.assertEqual(self.char.db.fuerza, 13)
        self.assertEqual(self.char.db.defensa, 7)

    def test_resta_bonuses(self):
        _aplicar_bonuses(self.char, {"fuerza": 3, "defensa": 2}, signo=-1)
        self.assertEqual(self.char.db.fuerza, 7)
        self.assertEqual(self.char.db.defensa, 3)

    def test_bonus_hp_max_tambien_sube_hp(self):
        _aplicar_bonuses(self.char, {"hp_max": 20}, signo=1)
        self.assertEqual(self.char.db.hp_max, 70)
        self.assertEqual(self.char.db.hp, 70)

    def test_reducir_hp_max_recorta_hp_al_nuevo_maximo(self):
        self.char.db.hp = 70
        self.char.db.hp_max = 70
        _aplicar_bonuses(self.char, {"hp_max": 20}, signo=-1)
        self.assertEqual(self.char.db.hp_max, 50)
        self.assertEqual(self.char.db.hp, 50)

    def test_stat_inexistente_no_falla(self):
        _aplicar_bonuses(self.char, {"mana": 10}, signo=1)
        # stat sin inicializar (None) se ignora silenciosamente

    def test_dict_vacio_no_modifica(self):
        _aplicar_bonuses(self.char, {}, signo=1)
        self.assertEqual(self.char.db.fuerza, 10)


# --------------------------------------------------------------------------- #
#  CmdEquipar
# --------------------------------------------------------------------------- #

class TestCmdEquipar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char = self.char1
        self.char.location = self.room1
        self.char.db.fuerza = 10
        self.char.db.defensa = 5
        self.char.db.hp = 50
        self.char.db.hp_max = 50
        self.char.db.equipamiento = {s: None for s in SLOTS}
        self.msgs = []
        self.char.msg = lambda text=None, **kw: self.msgs.append(text)

    def _crear_espada(self, key="espada de prueba", bonus_fuerza=3):
        item = create_object("typeclasses.objects.Equipo", key=key, location=self.char)
        item.db.slot = "arma"
        item.db.bonuses = {"fuerza": bonus_fuerza}
        return item

    def test_sin_args_muestra_uso(self):
        cmd = _make_cmd(CmdEquipar, self.char, args="")
        cmd.func()
        self.assertTrue(any("equipar" in m.lower() for m in self.msgs))

    def test_objeto_no_equipable_da_error(self):
        create_object("typeclasses.objects.Object", key="piedra", location=self.char)
        cmd = _make_cmd(CmdEquipar, self.char, args="piedra")
        cmd.func()
        self.assertTrue(any("equipable" in m.lower() for m in self.msgs))

    def test_equipar_aplica_bonuses_al_personaje(self):
        self._crear_espada()
        cmd = _make_cmd(CmdEquipar, self.char, args="espada de prueba")
        cmd.func()
        self.assertEqual(self.char.db.fuerza, 13)

    def test_equipar_registra_item_en_slot(self):
        espada = self._crear_espada()
        cmd = _make_cmd(CmdEquipar, self.char, args="espada de prueba")
        cmd.func()
        eq = _get_equipamiento(self.char)
        self.assertEqual(eq["arma"], espada)

    def test_equipar_reemplaza_slot_ocupado_y_revierte_bonus_anterior(self):
        self._crear_espada(key="espada vieja", bonus_fuerza=3)
        hacha = create_object("typeclasses.objects.Equipo", key="hacha nueva", location=self.char)
        hacha.db.slot = "arma"
        hacha.db.bonuses = {"fuerza": 5}

        cmd = _make_cmd(CmdEquipar, self.char, args="espada vieja")
        cmd.func()
        self.assertEqual(self.char.db.fuerza, 13)

        cmd2 = _make_cmd(CmdEquipar, self.char, args="hacha nueva")
        cmd2.func()
        # base 10 + hacha 5 (bonus espada ya revertido)
        self.assertEqual(self.char.db.fuerza, 15)
        eq = _get_equipamiento(self.char)
        self.assertEqual(eq["arma"], hacha)


# --------------------------------------------------------------------------- #
#  CmdDesequipar
# --------------------------------------------------------------------------- #

class TestCmdDesequipar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char = self.char1
        self.char.location = self.room1
        self.char.db.fuerza = 13
        self.char.db.defensa = 5
        self.char.db.hp = 50
        self.char.db.hp_max = 50
        self.msgs = []
        self.char.msg = lambda text=None, **kw: self.msgs.append(text)

        self.espada = create_object(
            "typeclasses.objects.Equipo", key="espada equipada", location=self.char
        )
        self.espada.db.slot = "arma"
        self.espada.db.bonuses = {"fuerza": 3}
        self.char.db.equipamiento = {"arma": self.espada, "armadura": None, "accesorio": None}

    def test_sin_args_muestra_uso(self):
        cmd = _make_cmd(CmdDesequipar, self.char, args="")
        cmd.func()
        self.assertTrue(any("desequipar" in m.lower() for m in self.msgs))

    def test_desequipar_por_slot_revierte_bonus(self):
        cmd = _make_cmd(CmdDesequipar, self.char, args="arma")
        cmd.func()
        self.assertEqual(self.char.db.fuerza, 10)
        self.assertIsNone(_get_equipamiento(self.char)["arma"])

    def test_desequipar_por_nombre_revierte_bonus(self):
        cmd = _make_cmd(CmdDesequipar, self.char, args="espada equipada")
        cmd.func()
        self.assertEqual(self.char.db.fuerza, 10)

    def test_slot_vacio_da_error(self):
        cmd = _make_cmd(CmdDesequipar, self.char, args="armadura")
        cmd.func()
        self.assertTrue(any("nada equipado" in m.lower() for m in self.msgs))

    def test_nombre_no_encontrado_da_error(self):
        cmd = _make_cmd(CmdDesequipar, self.char, args="objeto invisible")
        cmd.func()
        self.assertTrue(any("no tienes equipado" in m.lower() for m in self.msgs))


# --------------------------------------------------------------------------- #
#  CmdEquipo
# --------------------------------------------------------------------------- #

class TestCmdEquipo(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char = self.char1
        self.char.location = self.room1
        self.msgs = []
        self.char.msg = lambda text=None, **kw: self.msgs.append(text)

    def test_muestra_todos_los_slots(self):
        self.char.db.equipamiento = {s: None for s in SLOTS}
        cmd = _make_cmd(CmdEquipo, self.char)
        cmd.func()
        output = "\n".join(self.msgs)
        for slot in SLOTS:
            self.assertIn(slot, output)

    def test_muestra_nombre_del_item_equipado(self):
        espada = create_object("typeclasses.objects.Equipo", key="espada_show", location=self.char)
        espada.db.slot = "arma"
        espada.db.bonuses = {"fuerza": 2}
        self.char.db.equipamiento = {"arma": espada, "armadura": None, "accesorio": None}
        cmd = _make_cmd(CmdEquipo, self.char)
        cmd.func()
        self.assertIn("espada_show", "\n".join(self.msgs))

    def test_slots_vacios_muestran_vacio(self):
        self.char.db.equipamiento = {s: None for s in SLOTS}
        cmd = _make_cmd(CmdEquipo, self.char)
        cmd.func()
        self.assertIn("vacío", "\n".join(self.msgs))
