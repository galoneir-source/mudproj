"""
tests/test_api_views.py

Tests de integración Evennia/Django para web/api/views.py (API REST del
juego). Cubre: /api/status/, /api/who/ (públicos), /api/rooms/ y
/api/rooms/<dbref>/ (requieren perm Builder/Admin).

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_api_views
"""
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from typeclasses.objects import Object
from typeclasses.rooms import Room


class TestApiPublicos(EvenniaTest):
    def test_status_no_requiere_autenticacion(self):
        resp = self.client.get("/api/status/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("server", resp.json())

    def test_who_no_requiere_autenticacion(self):
        # EvenniaTest.setUp() ya deja una sesión de prueba conectada y
        # puppeteando self.char1 (ver evennia/utils/test_resources.py).
        resp = self.client.get("/api/who/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["players"][0]["name"], self.char1.key)


class TestApiRoomsRequierePermiso(EvenniaTest):
    """
    Regresión: _require_builder() hacía `request.user.db_object` para
    llegar a la cuenta y comprobar su permiso — pero en Evennia,
    AUTH_USER_MODEL = "accounts.AccountDB", así que request.user YA ES la
    cuenta; AccountDB no tiene ningún atributo "db_object". La llamada
    lanzaba AttributeError, atrapada por un except Exception genérico que
    devolvía False siempre — /api/rooms/ y /api/rooms/<dbref>/ rechazaban
    a TODO el mundo con 403, incluso a un Developer/Builder/Admin legítimo,
    desde que se escribieron.
    """

    def test_anonimo_recibe_403(self):
        resp = self.client.get("/api/rooms/")
        self.assertEqual(resp.status_code, 403)

    def test_cuenta_sin_permiso_recibe_403(self):
        self.client.force_login(self.account2)
        resp = self.client.get("/api/rooms/")
        self.assertEqual(resp.status_code, 403)

    def test_cuenta_con_permiso_developer_puede_listar_salas(self):
        # self.account tiene permiso "Developer" por defecto en EvenniaTest,
        # jerárquicamente por encima de Builder/Admin.
        self.client.force_login(self.account)
        resp = self.client.get("/api/rooms/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("rooms", resp.json())


class TestApiRoomDetail(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.account)

    def test_detalle_de_sala_real(self):
        sala = create.create_object(Room, key="Sala de prueba API")
        sala.db.desc = "Una descripción de prueba."
        create.create_object(Object, key="cofre de prueba", location=sala)

        resp = self.client.get(f"/api/rooms/{sala.id}/")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["name"], "Sala de prueba API")
        self.assertEqual(len(data["objects"]), 1)

    def test_dbref_de_personaje_no_se_confunde_con_sala(self):
        """
        Regresión: api_room_detail() hacía ObjectDB.objects.get(id=...) sin
        comprobar el typeclass, a diferencia de api_rooms() (que sí filtra
        por rooms.Room) — pedir el dbref de un Character (o cualquier otro
        objeto) devolvía sus contenidos como si fueran el interior de una
        sala, en vez de un 404.
        """
        personaje = create.create_object(Character, key="Personaje de prueba API")

        resp = self.client.get(f"/api/rooms/{personaje.id}/")

        self.assertEqual(resp.status_code, 404)

    def test_dbref_inexistente_da_404(self):
        resp = self.client.get("/api/rooms/999999/")
        self.assertEqual(resp.status_code, 404)
