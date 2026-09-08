"""
tests/test_npc.py

Tests de integración para hooks de typeclasses/npc.py que Evennia invoca
directamente (no a través de un Command custom del proyecto).

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_npc
"""
from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from typeclasses.npc import NPC


class TestNPCAtMsgReceive(EvenniaTest):
    """
    Regresión: NPC.at_msg_receive() declaraba su primer parámetro como
    "msg" y sin valor por defecto. DefaultObject.msg() (evennia/objects/
    objects.py) siempre invoca este hook por keyword -- at_msg_receive(
    text=text, from_obj=from_obj, **kwargs) -- nunca posicional, así que
    el nombre "msg" nunca recibía el valor: cualquier .msg() real a un NPC
    (p. ej. el "decir" de un jugador en la misma sala, que Evennia reparte
    a todos los objetos de la sala vía msg_contents() -> .msg()) lanzaba
    TypeError: at_msg_receive() missing 1 required positional argument:
    'msg', y _reaccionar_a_dialogo() nunca llegaba a ejecutarse. Ningún
    test anterior llamaba a .msg() sobre un NPC con la firma real de
    Evennia (los tests de test_cadenas.py solo comprueban el dict
    db.dialogo, sin pasar por este hook), así que pasó desapercibido hasta
    verse en los logs del servidor real tras un despliegue (2026-09-08).
    """

    def setUp(self):
        super().setUp()
        self.npc = create.create_object(NPC, key="Guardia", location=self.room1)
        self.npc.db.dialogo = {"hola": "Bienvenido, viajero."}

    def test_msg_con_firma_real_de_evennia_no_crashea(self):
        # Firma real: siempre por keyword, como hace DefaultObject.msg().
        self.npc.at_msg_receive(text='Char dice, "hola"', from_obj=self.char1)

    def test_dialogo_responde_a_palabra_clave_via_msg_real(self):
        with patch.object(self.npc, "execute_cmd") as mock_execute:
            self.npc.at_msg_receive(text='Char dice, "hola"', from_obj=self.char1)
        mock_execute.assert_called_once_with("say Bienvenido, viajero.")

    def test_no_reacciona_a_mensajes_sin_from_obj(self):
        # from_obj=None (p. ej. mensajes de sistema) no debe intentar
        # acceder a from_obj.has_account ni lanzar excepción.
        self.npc.at_msg_receive(text="algo", from_obj=None)
