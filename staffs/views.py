import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET

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
        "password": staff.password,
        "status": staff.status,
        "created_at": staff.created_at.strftime("%Y-%m-%d %H:%M"),
    }


def _load_body(request):
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return None


@require_GET
def list_staffs(request):
    client_id = request.GET.get("client_id", "").strip()
    if not client_id:
        return JsonResponse({"error": "client_id is required"}, status=400)

    staffs = Staff.objects.filter(client_id=client_id).order_by("-created_at")
    return JsonResponse({"success": True, "staffs": [_serialize(s) for s in staffs]})


@require_POST
def create_staff(request):
    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)

    client_id = body.get("client_id", "").strip()
    name = body.get("name", "").strip()
    department = body.get("department", "").strip()
    designation = body.get("designation", "").strip()
    phone = body.get("phone", "").strip()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    status = body.get("status", "Active").strip()

    if not all([client_id, name, department, designation, phone, username, password]):
        return JsonResponse({"error": "All required fields must be filled"}, status=400)

    if any(char.isspace() for char in username):
        return JsonResponse(
            {"error": "Username cannot contain spaces"},
            status=400,
        )

    if status not in ("Active", "Inactive"):
        status = "Active"

    if Staff.objects.filter(client_id=client_id, username=username).exists():
        return JsonResponse(
            {"error": "A staff member with this username already exists"},
            status=409,
        )

    staff = Staff.objects.create(
        client_id=client_id,
        name=name,
        department=department,
        designation=designation,
        phone=phone,
        username=username,
        password=password,
        status=status,
    )

    return JsonResponse({"success": True, "staff": _serialize(staff)})


@require_POST
def delete_staff(request):
    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)

    staff_id = body.get("id")
    if not staff_id:
        return JsonResponse({"error": "Staff id is required"}, status=400)

    client_id = body.get("client_id", "").strip()
    username = body.get("username", "").strip()
    password = body.get("password", "")

    if not client_id or not username or not password:
        return JsonResponse({"error": "Admin password is required"}, status=400)

    try:
        staff = Staff.objects.get(id=staff_id)
    except Staff.DoesNotExist:
        return JsonResponse({"error": "Staff not found"}, status=404)

    if staff.client_id != client_id:
        return JsonResponse({"error": "Staff not found"}, status=404)

    if not AdminAccount.objects.filter(
        client_id=client_id,
        username=username,
        password=password,
    ).exists():
        return JsonResponse({"error": "Invalid admin password"}, status=403)

    staff.delete()
    return JsonResponse({"success": True})


@require_POST
def edit_staff(request):
    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)

    staff_id = body.get("id")
    if not staff_id:
        return JsonResponse({"error": "Staff id is required"}, status=400)

    try:
        staff = Staff.objects.get(id=staff_id)
    except Staff.DoesNotExist:
        return JsonResponse({"error": "Staff not found"}, status=404)

    name = body.get("name", "").strip()
    department = body.get("department", "").strip()
    designation = body.get("designation", "").strip()
    phone = body.get("phone", "").strip()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    status = body.get("status", "").strip()

    if not all([name, department, designation, phone, username, password]):
        return JsonResponse({"error": "All required fields must be filled"}, status=400)

    if any(char.isspace() for char in username):
        return JsonResponse(
            {"error": "Username cannot contain spaces"},
            status=400,
        )

    if Staff.objects.filter(client_id=staff.client_id, username=username).exclude(id=staff.id).exists():
        return JsonResponse(
            {"error": "A staff member with this username already exists"},
            status=409,
        )

    if status not in ("Active", "Inactive"):
        status = "Active"

    staff.name = name
    staff.department = department
    staff.designation = designation
    staff.phone = phone
    staff.username = username
    staff.password = password
    staff.status = status
    staff.save()

    return JsonResponse({"success": True, "staff": _serialize(staff)})