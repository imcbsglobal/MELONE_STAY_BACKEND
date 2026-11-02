import json

from django.test import TestCase

from accounts.authentication import issue_access_token
from .models import OTA


class OtaApiTests(TestCase):
    def setUp(self):
        token = issue_access_token(
            subject="admin-a",
            role="admin",
            client_id="hotel-a",
        )
        self.client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    def post_json(self, path, payload):
        return self.client.post(path, data=json.dumps(payload), content_type="application/json")

    def test_create_and_list_otas(self):
        response = self.post_json(
            "/api/ota/create/",
            {"name": "Booking.com", "code": "booking"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["ota"]["code"], "BOOKING")

        listing = self.client.get("/api/ota/list/?client_id=hotel-a")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(
            [(ota["name"], ota["code"]) for ota in listing.json()["otas"]],
            [("Booking.com", "BOOKING")],
        )
        self.assertEqual(OTA.objects.get().client_id, "hotel-a")

    def test_duplicate_ota_name_and_code_are_rejected_case_insensitively(self):
        self.post_json("/api/ota/create/", {"name": "Booking.com", "code": "BOOKING"})
        duplicate_name = self.post_json(
            "/api/ota/create/",
            {"name": "booking.com", "code": "BOOKING-2"},
        )
        duplicate_code = self.post_json(
            "/api/ota/create/",
            {"name": "Another OTA", "code": "booking"},
        )
        self.assertEqual(duplicate_name.status_code, 409)
        self.assertEqual(duplicate_code.status_code, 409)

    def test_create_and_list_are_scoped_to_authenticated_tenant(self):
        denied_create = self.post_json(
            "/api/ota/create/",
            {"client_id": "hotel-b", "name": "Booking.com", "code": "BOOKING"},
        )
        denied_list = self.client.get("/api/ota/list/?client_id=hotel-b")
        self.assertEqual(denied_create.status_code, 403)
        self.assertEqual(denied_list.status_code, 403)
        self.assertEqual(OTA.objects.count(), 0)

    def test_required_fields_and_admin_authentication(self):
        missing_fields = self.post_json("/api/ota/create/", {"name": "Booking.com"})
        self.assertEqual(missing_fields.status_code, 400)

        self.client.defaults.pop("HTTP_AUTHORIZATION")
        unauthorized = self.client.get("/api/ota/list/?client_id=hotel-a")
        self.assertEqual(unauthorized.status_code, 401)
