"""
tests/test_reputation.py

Tests de integración para el sistema de reputación.
Usan EvenniaTest (Django + BD de prueba).

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test --settings settings.py tests.test_reputation
"""
from collections.abc import MutableMapping
from unittest.mock import patch, MagicMock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from features.reputation.commands import CmdReputacion
from features.shop.commands import CmdComprar, CmdTienda, CmdVender
from systems.reputation.engine import modificar_rep


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _set_rep(char, faccion_id: str, puntos: int):
    rep = dict(getattr(char.db, "reputacion", {}) or {})
    rep[faccion_id] = puntos
    char.db.reputacion = rep


def _run_cmd(caller, cmdclass, args="", **kwargs):
    cmd = cmdclass(**kwargs)
    cmd.caller = caller
    cmd.args = args
    cmd.cmdstring = cmdclass.key
    cmd.session = MagicMock()
    cmd.func()


# --------------------------------------------------------------------------- #
#  Personaje: inicialización
# --------------------------------------------------------------------------- #

class TestCharacterReputacion(EvenniaTest):
    def test_personaje_nuevo_tiene_reputacion_vacia(self):
        self.assertIsNotNone(self.char1.db.reputacion)
        self.assertIsInstance(self.char1.db.reputacion, MutableMapping)
        self.assertEqual(len(self.char1.db.reputacion), 0)


# --------------------------------------------------------------------------- #
#  Comando: reputación
# --------------------------------------------------------------------------- #

class TestCmdReputacion(EvenniaTest):
    def test_muestra_todas_las_facciones(self):
        msgs = []
        self.char1.msg = lambda text, **kw: msgs.append(text)
        _run_cmd(self.char1, CmdReputacion)
        output = "\n".join(msgs)
        self.assertIn("Ciudadanos", output)
        self.assertIn("Horda Salvaje", output)
        self.assertIn("Legión Oscura", output)
        self.assertIn("Sombras del Pantano", output)
        self.assertIn("Gremio de Aventureros", output)

    def test_muestra_neutral_por_defecto(self):
        msgs = []
        self.char1.msg = lambda text, **kw: msgs.append(text)
        _run_cmd(self.char1, CmdReputacion)
        output = "\n".join(msgs)
        self.assertIn("Neutral", output)

    def test_muestra_amistoso_tras_ganar_rep(self):
        _set_rep(self.char1, "ciudadanos", 1500)
        msgs = []
        self.char1.msg = lambda text, **kw: msgs.append(text)
        _run_cmd(self.char1, CmdReputacion)
        output = "\n".join(msgs)
        self.assertIn("Amistoso", output)

    def test_muestra_enemigo_con_rep_muy_negativa(self):
        _set_rep(self.char1, "horda_salvaje", -5000)
        msgs = []
        self.char1.msg = lambda text, **kw: msgs.append(text)
        _run_cmd(self.char1, CmdReputacion)
        output = "\n".join(msgs)
        self.assertIn("Enemigo", output)


# --------------------------------------------------------------------------- #
#  Tienda: descuento / recargo por reputación
# --------------------------------------------------------------------------- #

class TestShopReputacion(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.comerciante = create_object("typeclasses.npc.NPC", key="Tendero Test")
        self.comerciante.move_to(self.room1, quiet=True)
        self.comerciante.db.faccion = "ciudadanos"
        self.comerciante.db.tienda = [
            {"key": "espada", "precio": 100, "cantidad": -1, "valor": 100},
        ]
        self.char1.db.monedas = 200

    def test_precio_normal_con_rep_neutral(self):
        msgs = []
        self.char1.msg = lambda text, **kw: msgs.append(text)
        _run_cmd(self.char1, CmdComprar, args="espada")
        output = "\n".join(msgs)
        # Con rep neutral (0 pts) → factor 1.0 → precio 100
        self.assertIn("100 monedas", output)
        self.assertEqual(self.char1.db.monedas, 100)

    def test_precio_reducido_con_rep_amistosa(self):
        _set_rep(self.char1, "ciudadanos", 1500)  # Amistoso → 5% descuento
        self.char1.db.monedas = 200
        msgs = []
        self.char1.msg = lambda text, **kw: msgs.append(text)
        _run_cmd(self.char1, CmdComprar, args="espada")
        # 100 * 0.95 = 95
        self.assertEqual(self.char1.db.monedas, 200 - 95)

    def test_precio_aumentado_con_rep_hostil(self):
        _set_rep(self.char1, "ciudadanos", -2000)  # Hostil → 20% recargo
        self.char1.db.monedas = 200
        msgs = []
        self.char1.msg = lambda text, **kw: msgs.append(text)
        _run_cmd(self.char1, CmdComprar, args="espada")
        # 100 * 1.20 = 120
        self.assertEqual(self.char1.db.monedas, 200 - 120)

    def test_enemigo_rechazado_no_puede_comprar(self):
        _set_rep(self.char1, "ciudadanos", -5000)  # Enemigo
        monedas_antes = self.char1.db.monedas
        msgs = []
        self.char1.msg = lambda text, **kw: msgs.append(text)
        _run_cmd(self.char1, CmdComprar, args="espada")
        output = "\n".join(msgs)
        self.assertIn("niega", output)
        self.assertEqual(self.char1.db.monedas, monedas_antes)

    def test_tienda_muestra_recargo_hostil(self):
        _set_rep(self.char1, "ciudadanos", -2000)  # Hostil
        msgs = []
        self.char1.msg = lambda text, **kw: msgs.append(text)
        _run_cmd(self.char1, CmdTienda)
        output = "\n".join(msgs)
        self.assertIn("Recargo", output)

    def test_tienda_muestra_descuento_amistoso(self):
        _set_rep(self.char1, "ciudadanos", 1500)  # Amistoso
        msgs = []
        self.char1.msg = lambda text, **kw: msgs.append(text)
        _run_cmd(self.char1, CmdTienda)
        output = "\n".join(msgs)
        self.assertIn("Descuento", output)

    def test_tienda_enemigo_rechazado(self):
        _set_rep(self.char1, "ciudadanos", -5000)  # Enemigo
        msgs = []
        self.char1.msg = lambda text, **kw: msgs.append(text)
        _run_cmd(self.char1, CmdTienda)
        output = "\n".join(msgs)
        self.assertIn("niega", output)

    def test_enemigo_rechazado_no_puede_vender(self):
        """
        Regresión: CmdVender no comprobaba la reputación en absoluto, a
        diferencia de CmdComprar/CmdTienda (que rechazan con "se niega a
        hacer negocios contigo" si descuento_tienda() devuelve None). Un
        jugador con rango Enemigo (rep < -3000) con la facción del
        comerciante podía venderle objetos con total normalidad, aunque ese
        mismo comerciante se negara a venderle nada.
        """
        item = create_object(
            "typeclasses.objects.Object", key="daga vieja", location=self.char1
        )
        item.db.valor = 20
        _set_rep(self.char1, "ciudadanos", -5000)  # Enemigo
        monedas_antes = self.char1.db.monedas
        msgs = []
        self.char1.msg = lambda text, **kw: msgs.append(text)
        _run_cmd(self.char1, CmdVender, args="daga vieja")
        output = "\n".join(msgs)
        self.assertIn("niega", output)
        self.assertEqual(self.char1.db.monedas, monedas_antes)

    def test_npc_sin_faccion_precio_base_siempre(self):
        self.comerciante.db.faccion = None
        _set_rep(self.char1, "ciudadanos", 15000)  # Exaltado → pero faccion=None
        msgs = []
        self.char1.msg = lambda text, **kw: msgs.append(text)
        _run_cmd(self.char1, CmdComprar, args="espada")
        # Sin faccion → precio base 100
        self.assertEqual(self.char1.db.monedas, 100)


# --------------------------------------------------------------------------- #
#  NPC: aggro por reputación enemiga
# --------------------------------------------------------------------------- #

class TestNPCAggroReputacion(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.npc = create_object("typeclasses.npc.NPC", key="Guardia Test")
        self.npc.move_to(self.room1, quiet=True)
        self.npc.db.temperamento = "neutral"
        self.npc.db.faccion = "ciudadanos"

    def test_npc_neutral_no_agrede_con_rep_neutral(self):
        # Rep neutral → no agresión
        with patch.object(self.npc, "_agredir") as mock_agredir:
            self.npc._reaccionar_a_presencia(self.char1)
            mock_agredir.assert_not_called()

    def test_npc_neutral_agrede_con_rep_enemiga(self):
        _set_rep(self.char1, "ciudadanos", -5000)  # Enemigo
        with patch.object(self.npc, "_agredir") as mock_agredir:
            self.npc._reaccionar_a_presencia(self.char1)
            mock_agredir.assert_called_once_with(self.char1)

    def test_npc_cobarde_no_agrede_aunque_rep_enemiga(self):
        self.npc.db.temperamento = "cobarde"
        _set_rep(self.char1, "ciudadanos", -5000)
        with patch.object(self.npc, "_agredir") as mock_agredir:
            self.npc._reaccionar_a_presencia(self.char1)
            mock_agredir.assert_not_called()

    def test_npc_sin_faccion_no_agrede_por_rep(self):
        self.npc.db.faccion = None
        _set_rep(self.char1, "ciudadanos", -5000)
        with patch.object(self.npc, "_agredir") as mock_agredir:
            self.npc._reaccionar_a_presencia(self.char1)
            mock_agredir.assert_not_called()

    def test_npc_agresivo_agrede_siempre_independiente_de_rep(self):
        self.npc.db.temperamento = "agresivo"
        self.npc.db.faccion = None  # sin faccion → no rep check
        with patch.object(self.npc, "_agredir") as mock_agredir:
            self.npc._reaccionar_a_presencia(self.char1)
            mock_agredir.assert_called_once_with(self.char1)
