import json

from django.contrib.auth.hashers import check_password, make_password
from django.test import TestCase

from accounts.authentication import issue_access_token
from accounts.models import AdminAccount
from .models import Staff


class StaffApiTests(TestCase):
    def setUp(self):
        self.admin = AdminAccount.objects.create(
            client_id="hotel-a",
            customer_name="Hotel A",
            license_key="license",
            package="Standard",
            username="admin-a",
            password=make_password("secret"),
        )
        token = issue_access_token(
            subject=self.admin.username,
            role="admin",
            client_id=self.admin.client_id,
        )
        self.client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    def post_json(self, path, payload):
        return self.client.post(path, data=json.dumps(payload), content_type="application/json")

    def test_staff_api_requires_jwt(self):
        self.client.defaults.pop("HTTP_AUTHORIZATION")
        response = self.client.get("/api/staffs/list/?client_id=hotel-a")
        self.assertEqual(response.status_code, 401)

    def test_staff_create_uses_token_tenant_and_does_not_return_password(self):
        response = self.post_json("/api/staffs/create/", {
            "client_id": "hotel-a",
            "name": "Alex",
            "department": "Front Office",
            "designation": "Receptionist",
            "phone": "123456",
            "username": "alex",
            "password": "staff-secret",
        })
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.json()["staff"])
        staff = Staff.objects.get()
        self.assertTrue(check_password("staff-secret", staff.password))

    def test_staff_cannot_be_created_for_another_tenant(self):
        response = self.post_json("/api/staffs/create/", {
            "client_id": "hotel-b",
            "name": "Alex",
            "department": "Front Office",
            "designation": "Receptionist",
            "phone": "123456",
            "username": "alex",
            "password": "staff-secret",
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Staff.objects.count(), 0)
