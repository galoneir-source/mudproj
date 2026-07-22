"""
Regression tests for room/API classification of characters vs regular objects.
"""
import json
from types import SimpleNamespace

from django.test import RequestFactory
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from web.api.views import api_room_detail


class TestRoomObjectClassification(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.room = create_object("typeclasses.rooms.Room", key="Sala Clasificacion")
        self.char1.move_to(self.room, quiet=True)
        self.item = create_object("typeclasses.objects.Object", key="piedra suelta")
        self.item.move_to(self.room, quiet=True)
        self.npc = create_object("typeclasses.npc.NPC", key="Goblin vigilante")
        self.npc.move_to(self.room, quiet=True)

    def test_room_appearance_lists_regular_objects_as_objects(self):
        text = self.room.return_appearance(self.char1)

        self.assertIn("|cPersonajes|n:", text)
        self.assertIn("Goblin vigilante", text)
        self.assertIn("|cObjetos|n:", text)
        self.assertIn("piedra suelta", text)

        personajes_section = text.split("|cObjetos|n:", 1)[0]
        self.assertNotIn("piedra suelta", personajes_section)

    def test_api_room_detail_separates_npcs_from_regular_objects(self):
        """
        request.user ES la cuenta directamente en Evennia (AUTH_USER_MODEL =
        "accounts.AccountDB") — no tiene ningún atributo "db_object". El
        mock debe imitar eso, no la interfaz incorrecta que _require_builder()
        asumía antes del fix (ver web/api/views.py).
        """
        request = RequestFactory().get(f"/api/rooms/{self.room.id}/")
        request.user = SimpleNamespace(
            is_authenticated=True,
            check_permstring=lambda perm: perm == "Builder",
        )

        response = api_room_detail(request, self.room.id)
        data = json.loads(response.content.decode("utf-8"))

        character_names = {entry["name"] for entry in data["characters"]}
        object_names = {entry["name"] for entry in data["objects"]}

        self.assertIn("Goblin vigilante", character_names)
        self.assertNotIn("piedra suelta", character_names)
        self.assertIn("piedra suelta", object_names)
