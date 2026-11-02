import json

from django.test import TestCase

from accounts.authentication import issue_access_token
from .models import RoomCategory


class RoomCategoryApiTests(TestCase):
    def setUp(self):
        token = issue_access_token(
            subject="admin-a",
            role="admin",
            client_id="hotel-a",
        )
        self.client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    def post_json(self, path, payload):
        return self.client.post(path, data=json.dumps(payload), content_type="application/json")

    def test_categories_are_scoped_to_token_client(self):
        self.post_json(
            "/api/room-categories/create/",
            {"client_id": "hotel-a", "name": "Deluxe"},
        )
        response = self.client.get("/api/room-categories/list/?client_id=hotel-b")
        self.assertEqual(response.status_code, 403)
        scoped_response = self.client.get("/api/room-categories/list/")
        self.assertEqual(scoped_response.status_code, 200)
        self.assertEqual(len(scoped_response.json()["categories"]), 1)

    def test_duplicate_category_name_is_rejected_without_case_sensitivity(self):
        self.post_json(
            "/api/room-categories/create/",
            {"client_id": "hotel-a", "name": "Deluxe"},
        )
        response = self.post_json(
            "/api/room-categories/create/",
            {"client_id": "hotel-a", "name": "deluxe"},
        )
        self.assertEqual(response.status_code, 409)

    def test_room_category_endpoints_require_admin_jwt(self):
        self.client.defaults.pop("HTTP_AUTHORIZATION")
        response = self.client.get("/api/room-categories/list/?client_id=hotel-a")
        self.assertEqual(response.status_code, 401)

    def test_category_is_created_for_authenticated_tenant(self):
        response = self.post_json(
            "/api/room-categories/create/",
            {"name": "Suite"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(RoomCategory.objects.get().client_id, "hotel-a")
