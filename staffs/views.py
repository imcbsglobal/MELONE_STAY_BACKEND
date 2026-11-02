import json

from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from accounts.authentication import (
    get_tenant_client_id,
    password_matches_and_upgrade,
    require_jwt,
)
from accounts.models import AdminAccount

from .models import Staff


def _serialize(staff):
    return {
        "id": staff.id,
        "client_id": staff.client_id,
        "name": staff.name,
        "department": staff.department,
        "designation": staff.designation,
        "phone": staff.phone,
        "username": staff.username,
        "status": staff.status,
        "created_at": staff.created_at.strftime("%Y-%m-%d %H:%M"),
    }


def _load_body(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return None
    return body if isinstance(body, dict) else None


@require_jwt("admin")
@require_GET
def list_staffs(request):
    requested_client_id = request.GET.get("client_id", "").strip() or None
    client_id = get_tenant_client_id(request, requested_client_id)
    if client_id is None:
        return JsonResponse({"error": "You are not authorized to access this client"}, status=403)
    staffs = Staff.objects.filter(client_id=client_id).order_by("-created_at")
    return JsonResponse({"success": True, "staffs": [_serialize(staff) for staff in staffs]})


@require_jwt("admin")
@require_POST
def create_staff(request):
    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)

    requested_client_id = str(body.get("client_id", "")).strip()
    client_id = get_tenant_client_id(request, requested_client_id)
    if client_id is None:
        return JsonResponse({"error": "You are not authorized to access this client"}, status=403)
    name = str(body.get("name", "")).strip()
    department = str(body.get("department", "")).strip()
    designation = str(body.get("designation", "")).strip()
    phone = str(body.get("phone", "")).strip()
    username = str(body.get("username", "")).strip()
    password = body.get("password", "")
    status = str(body.get("status", "Active")).strip()

    if not all([name, department, designation, phone, username]) or not isinstance(password, str) or not password:
        return JsonResponse({"error": "All required fields must be filled"}, status=400)
    if any(char.isspace() for char in username):
        return JsonResponse({"error": "Username cannot contain spaces"}, status=400)
    if status not in ("Active", "Inactive"):
        status = "Active"
    if Staff.objects.filter(client_id=client_id, username=username).exists():
        return JsonResponse({"error": "A staff member with this username already exists"}, status=409)

    staff = Staff.objects.create(
        client_id=client_id,
        name=name,
        department=department,
        designation=designation,
        phone=phone,
        username=username,
        password=make_password(password),
        status=status,
    )
    return JsonResponse({"success": True, "staff": _serialize(staff)}, status=201)


@require_jwt("admin")
@require_POST
def delete_staff(request):
    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)
    staff_id = body.get("id")
    if not staff_id:
        return JsonResponse({"error": "Staff id is required"}, status=400)

    requested_client_id = str(body.get("client_id", "")).strip() or None
    client_id = get_tenant_client_id(request, requested_client_id)
    username = request.jwt_claims["sub"]
    password = body.get("password", "")
    if client_id is None:
        return JsonResponse({"error": "You are not authorized to access this client"}, status=403)
    if not password:
        return JsonResponse({"error": "Admin password is required"}, status=400)

    try:
        staff = Staff.objects.get(id=staff_id, client_id=client_id)
    except (Staff.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"error": "Staff not found"}, status=404)
    try:
        admin = AdminAccount.objects.get(client_id=client_id, username=username)
    except AdminAccount.DoesNotExist:
        return JsonResponse({"error": "Admin account not found"}, status=404)
    if not password_matches_and_upgrade(admin, password):
        return JsonResponse({"error": "Invalid admin password"}, status=403)

    staff.delete()
    return JsonResponse({"success": True})


@require_jwt("admin")
@require_POST
def edit_staff(request):
    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)
    staff_id = body.get("id")
    if not staff_id:
        return JsonResponse({"error": "Staff id is required"}, status=400)

    client_id = request.jwt_claims["client_id"]
    try:
        staff = Staff.objects.get(id=staff_id, client_id=client_id)
    except (Staff.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"error": "Staff not found"}, status=404)

    name = str(body.get("name", "")).strip()
    department = str(body.get("department", "")).strip()
    designation = str(body.get("designation", "")).strip()
    phone = str(body.get("phone", "")).strip()
    username = str(body.get("username", "")).strip()
    password = body.get("password", "")
    status = str(body.get("status", "")).strip()
    if not all([name, department, designation, phone, username]):
        return JsonResponse({"error": "All required fields must be filled"}, status=400)
    if any(char.isspace() for char in username):
        return JsonResponse({"error": "Username cannot contain spaces"}, status=400)
    if Staff.objects.filter(client_id=client_id, username=username).exclude(id=staff.id).exists():
        return JsonResponse({"error": "A staff member with this username already exists"}, status=409)
    if status not in ("Active", "Inactive"):
        status = "Active"

    staff.name = name
    staff.department = department
    staff.designation = designation
    staff.phone = phone
    staff.username = username
    if password:
        staff.password = make_password(password)
    staff.status = status
    staff.save()
    return JsonResponse({"success": True, "staff": _serialize(staff)})
