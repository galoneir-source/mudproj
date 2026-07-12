"""
tests/test_crafteo_equipo.py

Tests de integración Evennia para el sistema de crafteo de equipo (v0.24.0).
Cubre: craftear equipo con distintas calidades, verificar bonuses y nombre,
       craftear sin ingredientes, recetas de consumibles no afectadas.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_crafteo_equipo
"""
from evennia.utils.test_resources import EvenniaTest

from features.crafting.commands import CmdCraftear, CmdRecetas


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


class _MsgCapture:
    def __init__(self, char):
        self.msgs = []
        char.msg = lambda text=None, **kw: self.msgs.append(str(text))

    def all(self):
        return "\n".join(self.msgs)


def _dar_ingrediente(char, nombre, cantidad=1):
    """Crea objetos simples con el nombre dado en el inventario del personaje."""
    from evennia import create_object
    for _ in range(cantidad):
        obj = create_object("typeclasses.objects.Object", key=nombre, location=char)
    return obj


def _ingredientes_daga_acero(char):
    _dar_ingrediente(char, "mineral de hierro", 2)
    _dar_ingrediente(char, "piel de serpiente", 1)


def _ingredientes_espada_cazador(char):
    _dar_ingrediente(char, "mineral de hierro", 3)
    _dar_ingrediente(char, "garra de troll", 1)


def _ingredientes_vara_arcana(char):
    _dar_ingrediente(char, "cenizas arcanas", 2)
    _dar_ingrediente(char, "fragmento arcano", 2)


def _ingredientes_hacha_tallada(char):
    _dar_ingrediente(char, "mineral de hierro", 2)
    _dar_ingrediente(char, "escama de lagarto", 2)


def _ingredientes_coraza_hierro(char):
    _dar_ingrediente(char, "mineral de hierro", 4)
    _dar_ingrediente(char, "piel de serpiente", 2)


# ---------------------------------------------------------------------------
# Crafteo de equipo — calidad Normal
# ---------------------------------------------------------------------------

class TestCraftearEquipoNormal(EvenniaTest):
    """Craftear con 0 objetos crafteados → calidad Normal."""

    def setUp(self):
        super().setUp()
        self.char1.db.objetos_crafteados = 0
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)
        _ingredientes_daga_acero(self.char1)

    def _craftear(self, receta="daga de acero"):
        cmd = _make_cmd(CmdCraftear, self.char1, receta)
        cmd.func()

    def test_crafteo_exitoso(self):
        self._craftear()
        self.assertIn("exitoso", self.cap.all().lower())

    def test_item_creado_en_inventario(self):
        self._craftear()
        nombres = [obj.key for obj in self.char1.contents]
        self.assertTrue(any("daga" in n.lower() for n in nombres))

    def test_nombre_sin_sufijo_calidad(self):
        self._craftear()
        daga = next((o for o in self.char1.contents if "daga" in o.key.lower()), None)
        self.assertIsNotNone(daga)
        self.assertNotIn("(", daga.key)

    def test_bonuses_sin_modificar(self):
        self._craftear()
        daga = next((o for o in self.char1.contents if "daga" in o.key.lower()), None)
        self.assertIsNotNone(daga)
        bonuses = dict(daga.db.bonuses or {})
        self.assertEqual(bonuses.get("fuerza"), 3)
        self.assertEqual(bonuses.get("destreza"), 2)

    def test_calidad_guardada_en_db(self):
        self._craftear()
        daga = next((o for o in self.char1.contents if "daga" in o.key.lower()), None)
        self.assertIsNotNone(daga)
        self.assertEqual(daga.db.calidad, "Normal")

    def test_contador_incrementado(self):
        self._craftear()
        self.assertEqual(self.char1.db.objetos_crafteados, 1)

    def test_no_muestra_mensaje_calidad_normal(self):
        self._craftear()
        texto = self.cap.all()
        self.assertNotIn("¡Calidad Normal!", texto)

    def test_ingredientes_consumidos(self):
        self._craftear()
        nombres = [obj.key.lower() for obj in self.char1.contents]
        self.assertNotIn("mineral de hierro", nombres)
        self.assertNotIn("piel de serpiente", nombres)


# ---------------------------------------------------------------------------
# Crafteo de equipo — calidad Fino
# ---------------------------------------------------------------------------

class TestCraftearEquipoFino(EvenniaTest):
    """Craftear con 15 objetos crafteados → calidad Fino."""

    def setUp(self):
        super().setUp()
        self.char1.db.objetos_crafteados = 15
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)
        _ingredientes_daga_acero(self.char1)

    def _craftear(self):
        cmd = _make_cmd(CmdCraftear, self.char1, "daga de acero")
        cmd.func()

    def test_crafteo_exitoso(self):
        self._craftear()
        self.assertIn("exitoso", self.cap.all().lower())

    def test_nombre_con_sufijo_fino(self):
        self._craftear()
        daga = next((o for o in self.char1.contents if "daga" in o.key.lower()), None)
        self.assertIsNotNone(daga)
        self.assertIn("(Fino)", daga.key)

    def test_bonuses_aumentados_en_uno(self):
        self._craftear()
        daga = next((o for o in self.char1.contents if "daga" in o.key.lower()), None)
        self.assertIsNotNone(daga)
        bonuses = dict(daga.db.bonuses or {})
        self.assertEqual(bonuses.get("fuerza"), 4)
        self.assertEqual(bonuses.get("destreza"), 3)

    def test_calidad_guardada_fino(self):
        self._craftear()
        daga = next((o for o in self.char1.contents if "daga" in o.key.lower()), None)
        self.assertEqual(daga.db.calidad, "Fino")

    def test_mensaje_calidad_fino(self):
        self._craftear()
        self.assertIn("Fino", self.cap.all())

    def test_contador_incrementado(self):
        self._craftear()
        self.assertEqual(self.char1.db.objetos_crafteados, 16)


# ---------------------------------------------------------------------------
# Crafteo de equipo — calidad Magistral
# ---------------------------------------------------------------------------

class TestCraftearEquipoMagistral(EvenniaTest):
    """Craftear con 30 objetos crafteados → calidad Magistral."""

    def setUp(self):
        super().setUp()
        self.char1.db.objetos_crafteados = 30
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)
        _ingredientes_espada_cazador(self.char1)

    def _craftear(self):
        cmd = _make_cmd(CmdCraftear, self.char1, "espada del cazador")
        cmd.func()

    def test_nombre_con_sufijo_magistral(self):
        self._craftear()
        espada = next((o for o in self.char1.contents if "espada" in o.key.lower()), None)
        self.assertIsNotNone(espada)
        self.assertIn("(Magistral)", espada.key)

    def test_bonuses_aumentados_en_dos(self):
        self._craftear()
        espada = next((o for o in self.char1.contents if "espada" in o.key.lower()), None)
        bonuses = dict(espada.db.bonuses or {})
        self.assertEqual(bonuses.get("fuerza"), 7)   # 5 base + 2
        self.assertEqual(bonuses.get("defensa"), 3)  # 1 base + 2

    def test_calidad_guardada_magistral(self):
        self._craftear()
        espada = next((o for o in self.char1.contents if "espada" in o.key.lower()), None)
        self.assertEqual(espada.db.calidad, "Magistral")

    def test_mensaje_calidad_magistral(self):
        self._craftear()
        self.assertIn("Magistral", self.cap.all())

    def test_contador_incrementado(self):
        self._craftear()
        self.assertEqual(self.char1.db.objetos_crafteados, 31)


# ---------------------------------------------------------------------------
# Crafteo de equipo — otros items
# ---------------------------------------------------------------------------

class TestCraftearEquipoVariados(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.objetos_crafteados = 20
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def _craftear(self, receta):
        cmd = _make_cmd(CmdCraftear, self.char1, receta)
        cmd.func()

    def test_craftear_vara_arcana(self):
        _ingredientes_vara_arcana(self.char1)
        self._craftear("vara arcana")
        vara = next((o for o in self.char1.contents if "vara" in o.key.lower()), None)
        self.assertIsNotNone(vara)
        bonuses = dict(vara.db.bonuses or {})
        self.assertEqual(bonuses.get("inteligencia"), 6)  # 5 + 1 (Fino)

    def test_craftear_hacha_tallada(self):
        _ingredientes_hacha_tallada(self.char1)
        self._craftear("hacha tallada")
        hacha = next((o for o in self.char1.contents if "hacha" in o.key.lower()), None)
        self.assertIsNotNone(hacha)
        bonuses = dict(hacha.db.bonuses or {})
        self.assertEqual(bonuses.get("fuerza"), 5)  # 4 + 1 (Fino)

    def test_craftear_coraza_hierro(self):
        _ingredientes_coraza_hierro(self.char1)
        self._craftear("coraza de hierro")
        coraza = next((o for o in self.char1.contents if "coraza" in o.key.lower()), None)
        self.assertIsNotNone(coraza)
        bonuses = dict(coraza.db.bonuses or {})
        self.assertEqual(bonuses.get("defensa"), 6)   # 5 + 1 (Fino)
        self.assertEqual(bonuses.get("constitucion"), 3)  # 2 + 1 (Fino)

    def test_slot_arma_preservado(self):
        _ingredientes_vara_arcana(self.char1)
        self._craftear("vara arcana")
        vara = next((o for o in self.char1.contents if "vara" in o.key.lower()), None)
        self.assertIsNotNone(vara)
        self.assertEqual(vara.db.slot, "arma")

    def test_slot_armadura_preservado(self):
        _ingredientes_coraza_hierro(self.char1)
        self._craftear("coraza de hierro")
        coraza = next((o for o in self.char1.contents if "coraza" in o.key.lower()), None)
        self.assertIsNotNone(coraza)
        self.assertEqual(coraza.db.slot, "armadura")


# ---------------------------------------------------------------------------
# Sin ingredientes suficientes
# ---------------------------------------------------------------------------

class TestCraftearEquipoSinIngredientes(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.objetos_crafteados = 0
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_sin_ingredientes_muestra_error(self):
        cmd = _make_cmd(CmdCraftear, self.char1, "daga de acero")
        cmd.func()
        self.assertIn("faltan", self.cap.all().lower())

    def test_sin_ingredientes_no_incrementa_contador(self):
        cmd = _make_cmd(CmdCraftear, self.char1, "daga de acero")
        cmd.func()
        self.assertEqual(self.char1.db.objetos_crafteados, 0)

    def test_ingredientes_parciales_fallan(self):
        _dar_ingrediente(self.char1, "mineral de hierro", 1)  # falta 1 más y piel
        cmd = _make_cmd(CmdCraftear, self.char1, "daga de acero")
        cmd.func()
        self.assertIn("faltan", self.cap.all().lower())

    def test_receta_invalida_muestra_error(self):
        cmd = _make_cmd(CmdCraftear, self.char1, "espada de cristal")
        cmd.func()
        self.assertIn("no existe", self.cap.all().lower())


# ---------------------------------------------------------------------------
# Consumibles no afectados por sistema de calidad
# ---------------------------------------------------------------------------

class TestConsumiblesNoAfectados(EvenniaTest):
    """Verificar que las recetas de consumibles no tienen tipo equipo."""

    def setUp(self):
        super().setUp()
        self.char1.db.objetos_crafteados = 30
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)
        _dar_ingrediente(self.char1, "piel de serpiente", 1)

    def test_pocion_vida_crafteable(self):
        cmd = _make_cmd(CmdCraftear, self.char1, "poción de vida")
        cmd.func()
        self.assertIn("exitoso", self.cap.all().lower())

    def test_pocion_vida_no_tiene_calidad(self):
        cmd = _make_cmd(CmdCraftear, self.char1, "poción de vida")
        cmd.func()
        pocion = next((o for o in self.char1.contents if "poción" in o.key.lower()), None)
        self.assertIsNotNone(pocion)
        # Las pociones no tienen db.calidad
        self.assertIsNone(getattr(pocion.db, "calidad", None))

    def test_pocion_vida_nombre_sin_sufijo_calidad(self):
        cmd = _make_cmd(CmdCraftear, self.char1, "poción de vida")
        cmd.func()
        pocion = next((o for o in self.char1.contents if "poción" in o.key.lower()), None)
        self.assertIsNotNone(pocion)
        self.assertNotIn("(Magistral)", pocion.key)
        self.assertNotIn("(Fino)", pocion.key)


# ---------------------------------------------------------------------------
# CmdRecetas: etiqueta [equipo] en listado
# ---------------------------------------------------------------------------

class TestCmdRecetasEquipo(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_listado_muestra_equipo(self):
        cmd = _make_cmd(CmdRecetas, self.char1, "")
        cmd.func()
        self.assertIn("equipo", self.cap.all().lower())

    def test_detalle_daga_acero_muestra_tipo_equipo(self):
        cmd = _make_cmd(CmdRecetas, self.char1, "daga de acero")
        cmd.func()
        self.assertIn("equipo", self.cap.all().lower())

    def test_detalle_daga_acero_muestra_calidad(self):
        cmd = _make_cmd(CmdRecetas, self.char1, "daga de acero")
        cmd.func()
        self.assertIn("calidad", self.cap.all().lower())

    def test_detalle_pocion_no_muestra_equipo(self):
        cmd = _make_cmd(CmdRecetas, self.char1, "poción de vida")
        cmd.func()
        # El detalle de una poción no debe mostrar "equipo" ni "calidad"
        texto = self.cap.all().lower()
        self.assertNotIn("[equipo]", texto)


if __name__ == "__main__":
    import unittest
    unittest.main()
