import json
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.test import TestCase
import jwt

from .authentication import issue_access_token
from .models import AdminAccount


class AccountJwtApiTests(TestCase):
    def make_admin(self, password="legacy-password"):
        return AdminAccount.objects.create(
            client_id="hotel-a",
            customer_name="Hotel A",
            license_key="license",
            package="Standard",
            username="admin-a",
            password=password,
        )

    def post_json(self, path, payload):
        return self.client.post(path, data=json.dumps(payload), content_type="application/json")

    def test_admin_login_issues_tenant_scoped_jwt_and_upgrades_legacy_password(self):
        admin = self.make_admin()
        with patch("accounts.views._live_client_status", return_value="Active"):
            response = self.post_json("/api/admin-login/", {
                "client_id": "hotel-a",
                "username": "admin-a",
                "password": "legacy-password",
            })
        self.assertEqual(response.status_code, 200)
        token = response.json()["token"]
        claims = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
            audience="melonestay-api",
            issuer="melonestay",
        )
        self.assertEqual(claims["role"], "admin")
        self.assertEqual(claims["client_id"], "hotel-a")
        admin.refresh_from_db()
        self.assertTrue(check_password("legacy-password", admin.password))

    def test_superuser_only_api_rejects_admin_token(self):
        token = issue_access_token(
            subject="admin-a",
            role="admin",
            client_id="hotel-a",
        )
        self.client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        response = self.client.get("/api/list-admins/")
        self.assertEqual(response.status_code, 403)

    def test_protected_api_rejects_missing_and_invalid_token(self):
        missing = self.client.get("/api/list-admins/")
        self.client.defaults["HTTP_AUTHORIZATION"] = "Bearer invalid"
        invalid = self.client.get("/api/list-admins/")
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(invalid.status_code, 401)

    def test_superuser_login_issues_superuser_jwt(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "username": "root",
            "password": "root-password",
            "status": "active",
            "project_name": "Melone Stay",
        }
        with patch("accounts.views.requests.get", return_value=response):
            result = self.post_json("/api/superuser-login/", {
                "username": "root",
                "password": "root-password",
            })
        self.assertEqual(result.status_code, 200)
        claims = jwt.decode(
            result.json()["token"],
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
            audience="melonestay-api",
            issuer="melonestay",
        )
        self.assertEqual(claims["role"], "superuser")

    def test_admin_credentials_are_not_returned_by_superuser_listing(self):
        self.make_admin()
        token = issue_access_token(subject="root", role="superuser")
        self.client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        with patch("accounts.views._fetch_project_data", return_value=None):
            response = self.client.get("/api/list-admins/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("password", response.json()["admins"][0])

    def test_superuser_can_create_admin_with_hashed_password(self):
        token = issue_access_token(subject="root", role="superuser")
        self.client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        response = self.post_json("/api/create-admin/", {
            "client_id": "hotel-b",
            "customer_name": "Hotel B",
            "license_key": "license-b",
            "package": "Standard",
            "username": "admin-b",
            "password": "new-password",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(check_password("new-password", AdminAccount.objects.get(username="admin-b").password))
