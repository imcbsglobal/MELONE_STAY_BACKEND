import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings
from django.contrib.auth.hashers import make_password
import requests

from .authentication import issue_access_token, password_matches_and_upgrade, require_jwt
from .models import AdminAccount


def _fetch_project_data():
    try:
        api_response = requests.get(
            settings.PROJECT_API_URL,
            timeout=settings.PROJECT_API_TIMEOUT,
        )
        api_response.raise_for_status()
        return api_response.json().get("customers", [])
    except (requests.exceptions.RequestException, ValueError):
        return None


def _live_client_status(client_id):
    customers = _fetch_project_data()
    if customers is None:
        return None
    for customer in customers:
        if customer.get("client_id", "").strip() == client_id:
            return customer.get("status", "").strip()
    return ""


def _sync_admin_status(admin, live_status):
    if live_status and live_status != admin.status:
        admin.status = live_status
        admin.save(update_fields=["status"])
    return admin.status


@require_POST
def superuser_login(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid request body"}, status=400)
    if not isinstance(body, dict):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    username = str(body.get("username", "")).strip()
    password = body.get("password", "")

    if not username or not isinstance(password, str) or not password:
        return JsonResponse({"error": "Username and password are required"}, status=400)

    try:
        api_response = requests.get(
            settings.SUPERUSER_API_URL,
            timeout=settings.SUPERUSER_API_TIMEOUT,
        )
        api_response.raise_for_status()
    except requests.exceptions.RequestException:
        return JsonResponse(
            {"error": "Service unavailable. Please try again."},
            status=503,
        )

    try:
        api_data = api_response.json()
    except ValueError:
        return JsonResponse(
            {"error": "Service unavailable. Please try again."},
            status=503,
        )

    api_username = api_data.get("username", "")
    api_password = api_data.get("password", "")
    api_status = api_data.get("status", "")

    if api_status != "active":
        return JsonResponse(
            {"error": "Account is not active"},
            status=403,
        )

    if username == api_username and password == api_password:
        return JsonResponse({
            "success": True,
            "username": api_data.get("username", ""),
            "project_name": api_data.get("project_name", ""),
            "token": issue_access_token(
                subject=api_data.get("username", ""),
                role="superuser",
            ),
        })
    else:
        return JsonResponse(
            {"error": "Invalid credentials"},
            status=401,
        )


@require_POST
@require_jwt("superuser")
def fetch_client(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid request body"}, status=400)
    if not isinstance(body, dict):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    client_id = str(body.get("client_id", "")).strip()
    if not client_id:
        return JsonResponse({"error": "Gmail is required"}, status=400)

    try:
        api_response = requests.get(
            settings.PROJECT_API_URL,
            timeout=settings.PROJECT_API_TIMEOUT,
        )
        api_response.raise_for_status()
    except requests.exceptions.RequestException:
        return JsonResponse(
            {"error": "Failed to connect to project API. Please try again."},
            status=503,
        )

    try:
        api_data = api_response.json()
    except ValueError:
        return JsonResponse(
            {"error": "Invalid response from project API."},
            status=503,
        )

    if not api_data.get("success"):
        return JsonResponse(
            {"error": "Project API returned an error."},
            status=502,
        )

    customers = api_data.get("customers", [])
    matched = None
    for customer in customers:
        if customer.get("client_id", "").strip() == client_id:
            matched = customer
            break

    if not matched:
        return JsonResponse(
            {"error": f"No customer found with Gmail: {client_id}"},
            status=404,
        )

    license_validity = matched.get("license_validity", {})
    modules = matched.get("modules", [])
    module_name = modules[0].get("module_name", "") if modules else ""

    return JsonResponse({
        "success": True,
        "customer": {
            "client_id": matched.get("client_id", ""),
            "customer_name": matched.get("customer_name", ""),
            "license_key": matched.get("license_key", ""),
            "package": matched.get("package", ""),
            "module_name": module_name,
            "expiry_date": license_validity.get("expiry_date", ""),
            "status": matched.get("status", ""),
        },
    })


@require_POST
@require_jwt("superuser")
def create_admin(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid request body"}, status=400)
    if not isinstance(body, dict):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    client_id = str(body.get("client_id", "")).strip()
    customer_name = str(body.get("customer_name", "")).strip()
    license_key = str(body.get("license_key", "")).strip()
    package = str(body.get("package", "")).strip()
    module_name = str(body.get("module_name", "")).strip()
    expiry_date = str(body.get("expiry_date", "")).strip()
    status_val = str(body.get("status", "Active")).strip()
    username = str(body.get("username", "")).strip()
    password = body.get("password", "")

    if not all([client_id, customer_name, license_key, username]) or not isinstance(password, str) or not password:
        return JsonResponse({"error": "All required fields must be filled"}, status=400)

    if AdminAccount.objects.filter(username=username).exists():
        return JsonResponse({"error": "Username already exists"}, status=409)

    if AdminAccount.objects.filter(client_id=client_id).exists():
        return JsonResponse(
            {"error": "An admin already exists for this Gmail"},
            status=409,
        )

    admin = AdminAccount.objects.create(
        client_id=client_id,
        customer_name=customer_name,
        license_key=license_key,
        package=package,
        module_name=module_name,
        expiry_date=expiry_date,
        status=status_val,
        username=username,
        password=make_password(password),
    )

    return JsonResponse({
        "success": True,
        "admin": {
            "id": admin.id,
            "username": admin.username,
            "customer_name": admin.customer_name,
            "client_id": admin.client_id,
            "package": admin.package,
        },
    })


@require_POST
def admin_login(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid request body"}, status=400)
    if not isinstance(body, dict):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    client_id = str(body.get("client_id", "")).strip()
    username = str(body.get("username", "")).strip()
    password = body.get("password", "")

    if not client_id or not username or not isinstance(password, str) or not password:
        return JsonResponse(
            {"error": "Gmail, username and password are required"},
            status=400,
        )

    try:
        admin = AdminAccount.objects.get(username=username)
    except AdminAccount.DoesNotExist:
        return JsonResponse({"error": "Invalid credentials"}, status=401)

    if admin.client_id != client_id:
        return JsonResponse({"error": "Invalid credentials"}, status=401)

    if not password_matches_and_upgrade(admin, password):
        return JsonResponse({"error": "Invalid credentials"}, status=401)

    live_status = _live_client_status(client_id)
    current_status = _sync_admin_status(admin, live_status or admin.status)

    if current_status.lower() != "active":
        return JsonResponse(
            {"error": "Your account is inactive. Please contact the administrator."},
            status=403,
        )

    return JsonResponse({
        "success": True,
        "admin": {
            "id": admin.id,
            "username": admin.username,
            "client_id": admin.client_id,
            "customer_name": admin.customer_name,
            "package": admin.package,
            "module_name": admin.module_name,
            "expiry_date": admin.expiry_date,
        },
        "token": issue_access_token(
            subject=admin.username,
            role="admin",
            client_id=admin.client_id,
        ),
    })


@require_GET
@require_jwt("admin")
def check_member_status(request):
    client_id = request.jwt_claims["client_id"]
    username = request.jwt_claims["sub"]
    requested_client_id = request.GET.get("client_id", "").strip()
    requested_username = request.GET.get("username", "").strip()
    if requested_client_id and requested_client_id != client_id:
        return JsonResponse({"error": "You are not authorized to access this account"}, status=403)
    if requested_username and requested_username != username:
        return JsonResponse({"error": "You are not authorized to access this account"}, status=403)

    try:
        admin = AdminAccount.objects.get(client_id=client_id, username=username)
    except AdminAccount.DoesNotExist:
        return JsonResponse({"error": "Admin not found"}, status=404)

    live_status = _live_client_status(admin.client_id)
    current_status = _sync_admin_status(admin, live_status or admin.status)

    return JsonResponse({
        "active": current_status.lower() == "active",
        "status": current_status,
    })


@require_GET
@require_jwt("superuser")
def list_admins(request):
    admins = AdminAccount.objects.all().order_by("-created_at")

    customers = _fetch_project_data()
    status_by_client = {}
    if customers is not None:
        for customer in customers:
            status_by_client[customer.get("client_id", "").strip()] = customer.get("status", "").strip()

    data = []
    for a in admins:
        live_status = status_by_client.get(a.client_id)
        if live_status:
            _sync_admin_status(a, live_status)
            a.refresh_from_db()
        data.append({
            "id": a.id,
            "client_id": a.client_id,
            "customer_name": a.customer_name,
            "license_key": a.license_key,
            "package": a.package,
            "module_name": a.module_name,
            "expiry_date": a.expiry_date,
            "status": a.status,
            "username": a.username,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M"),
        })
    return JsonResponse({"success": True, "admins": data})


@require_POST
@require_jwt("superuser")
def delete_admin(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid request body"}, status=400)
    if not isinstance(body, dict):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    admin_id = body.get("id")
    password = body.get("password", "")

    if not admin_id:
        return JsonResponse({"error": "Admin ID is required"}, status=400)

    if not password:
        return JsonResponse({"error": "Superuser password is required"}, status=400)

    try:
        api_response = requests.get(
            settings.SUPERUSER_API_URL,
            timeout=settings.SUPERUSER_API_TIMEOUT,
        )
        api_response.raise_for_status()
        api_data = api_response.json()
    except (requests.exceptions.RequestException, ValueError):
        return JsonResponse(
            {"error": "Service unavailable. Please try again."},
            status=503,
        )

    if api_data.get("status") != "active" or api_data.get("password") != password:
        return JsonResponse({"error": "Invalid superuser password"}, status=401)

    try:
        admin = AdminAccount.objects.get(id=admin_id)
    except AdminAccount.DoesNotExist:
        return JsonResponse({"error": "Admin not found"}, status=404)

    admin.delete()
    return JsonResponse({"success": True})


@require_POST
@require_jwt("superuser")
def edit_admin(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid request body"}, status=400)
    if not isinstance(body, dict):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    admin_id = body.get("id")
    new_username = str(body.get("username", "")).strip()
    new_password = body.get("password", "")
    superuser_password = body.get("superuser_password", "")

    if not admin_id:
        return JsonResponse({"error": "Admin ID is required"}, status=400)

    if not new_username:
        return JsonResponse({"error": "Username is required"}, status=400)

    if not isinstance(new_password, str) or not isinstance(superuser_password, str) or not superuser_password:
        return JsonResponse({"error": "Superuser password is required"}, status=400)

    try:
        api_response = requests.get(
            settings.SUPERUSER_API_URL,
            timeout=settings.SUPERUSER_API_TIMEOUT,
        )
        api_response.raise_for_status()
        api_data = api_response.json()
    except (requests.exceptions.RequestException, ValueError):
        return JsonResponse(
            {"error": "Service unavailable. Please try again."},
            status=503,
        )

    if api_data.get("status") != "active" or api_data.get("password") != superuser_password:
        return JsonResponse({"error": "Invalid superuser password"}, status=401)

    try:
        admin = AdminAccount.objects.get(id=admin_id)
    except AdminAccount.DoesNotExist:
        return JsonResponse({"error": "Admin not found"}, status=404)

    if AdminAccount.objects.filter(username=new_username).exclude(id=admin_id).exists():
        return JsonResponse({"error": "Username already exists"}, status=409)

    admin.username = new_username
    update_fields = ["username"]
    if new_password:
        admin.password = make_password(new_password)
        update_fields.append("password")
    admin.save(update_fields=update_fields)

    return JsonResponse({"success": True})
