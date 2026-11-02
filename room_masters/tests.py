import json

from django.test import TestCase

from accounts.authentication import issue_access_token
from room_categories.models import RoomCategory
from .models import Room, RoomPrice


class RoomMasterApiTests(TestCase):
    def setUp(self):
        self.category = RoomCategory.objects.create(client_id="hotel-a", name="Deluxe")
        token = issue_access_token(
            subject="admin-a",
            role="admin",
            client_id="hotel-a",
        )
        self.client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    def payload(self, **overrides):
        values = {
            "client_id": "hotel-a",
            "code": "DLX-01",
            "name": "Deluxe King",
            "category_id": self.category.id,
            "air_conditioning": "AC",
            "floor": "First",
            "tax": "12.5",
            "prices": [{"name": "Standard", "amount": "1200.00"}],
        }
        values.update(overrides)
        return values

    def post_json(self, path, payload):
        return self.client.post(path, data=json.dumps(payload), content_type="application/json")

    def test_create_and_list_room_with_prices(self):
        response = self.post_json("/api/room-master/create/", self.payload())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["room"]["prices"][0]["name"], "Standard")
        rooms = self.client.get("/api/room-master/list/?client_id=hotel-a")
        self.assertEqual(rooms.status_code, 200)
        self.assertEqual(len(rooms.json()["rooms"]), 1)
        self.assertEqual(rooms.json()["rooms"][0]["category_name"], "Deluxe")

    def test_create_room_with_unnamed_prices(self):
        response = self.post_json(
            "/api/room-master/create/",
            self.payload(prices=[{"amount": "1200.00"}, {"amount": "1500.00"}]),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            [price["amount"] for price in response.json()["room"]["prices"]],
            ["1200.00", "1500.00"],
        )
        self.assertEqual([price["name"] for price in response.json()["room"]["prices"]], ["", ""])

    def test_category_dropdown_data_is_owned_by_same_client(self):
        response = self.post_json("/api/room-master/create/", self.payload(client_id="hotel-b"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Room.objects.count(), 0)

    def test_room_master_endpoints_require_admin_jwt(self):
        self.client.defaults.pop("HTTP_AUTHORIZATION")
        response = self.client.get("/api/room-master/list/?client_id=hotel-a")
        self.assertEqual(response.status_code, 401)

    def test_edit_replaces_room_prices(self):
        room = Room.objects.create(
            client_id="hotel-a",
            code="DLX-01",
            name="Deluxe King",
            category=self.category,
            air_conditioning="AC",
            floor="First",
            tax="12.50",
        )
        RoomPrice.objects.create(room=room, name="Old", amount="1000.00")
        payload = self.payload(id=room.id, prices=[
            {"name": "Weekday", "amount": "1100.00"},
            {"name": "Weekend", "amount": "1400.00"},
        ])
        response = self.post_json("/api/room-master/edit/", payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([price["name"] for price in response.json()["room"]["prices"]], ["Weekday", "Weekend"])

    def test_invalid_tax_and_empty_prices_are_rejected(self):
        invalid_tax = self.post_json("/api/room-master/create/", self.payload(tax="101"))
        no_prices = self.post_json("/api/room-master/create/", self.payload(prices=[]))
        self.assertEqual(invalid_tax.status_code, 400)
        self.assertEqual(no_prices.status_code, 400)

    def test_room_favorite_can_be_updated_and_is_included_in_list(self):
        room = Room.objects.create(
            client_id="hotel-a",
            code="DLX-01",
            name="Deluxe King",
            category=self.category,
            air_conditioning="AC",
            floor="First",
            tax="12.50",
        )
        response = self.post_json(
            "/api/room-master/favorite/",
            {"id": room.id, "client_id": "hotel-a", "is_favorite": True},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["room"]["is_favorite"])
        listing = self.client.get("/api/room-master/list/?client_id=hotel-a")
        self.assertTrue(listing.json()["rooms"][0]["is_favorite"])

    def test_room_favorite_requires_boolean_and_tenant_ownership(self):
        room = Room.objects.create(
            client_id="hotel-a",
            code="DLX-01",
            name="Deluxe King",
            category=self.category,
            air_conditioning="AC",
            floor="First",
            tax="12.50",
        )
        invalid = self.post_json(
            "/api/room-master/favorite/",
            {"id": room.id, "client_id": "hotel-a", "is_favorite": "true"},
        )
        denied = self.post_json(
            "/api/room-master/favorite/",
            {"id": room.id, "client_id": "hotel-b", "is_favorite": True},
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(denied.status_code, 403)
        room.refresh_from_db()
        self.assertFalse(room.is_favorite)
