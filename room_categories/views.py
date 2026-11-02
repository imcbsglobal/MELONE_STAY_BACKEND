import json

from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from accounts.authentication import get_tenant_client_id, require_jwt

from .models import RoomCategory


def _load_body(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return None
    return body if isinstance(body, dict) else None


def _serialize(category):
    return {
        "id": category.id,
        "client_id": category.client_id,
        "name": category.name,
        "room_count": category.rooms.count(),
        "created_at": category.created_at.strftime("%Y-%m-%d %H:%M"),
    }


@require_jwt("admin")
@require_GET
def list_categories(request):
    requested_client_id = request.GET.get("client_id", "").strip() or None
    client_id = get_tenant_client_id(request, requested_client_id)
    if client_id is None:
        return JsonResponse({"error": "You are not authorized to access this client"}, status=403)
    categories = RoomCategory.objects.filter(client_id=client_id).prefetch_related("rooms")
    return JsonResponse({
        "success": True,
        "categories": [_serialize(category) for category in categories],
    })


@require_jwt("admin")
@require_POST
def create_category(request):
    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)
    requested_client_id = str(body.get("client_id", "")).strip() or None
    client_id = get_tenant_client_id(request, requested_client_id)
    if client_id is None:
        return JsonResponse({"error": "You are not authorized to access this client"}, status=403)
    name = str(body.get("name", "")).strip()
    if not name:
        return JsonResponse({"error": "name is required"}, status=400)
    if len(name) > 100:
        return JsonResponse({"error": "Category name is too long"}, status=400)
    if RoomCategory.objects.filter(client_id=client_id, name__iexact=name).exists():
        return JsonResponse({"error": "A room category with this name already exists"}, status=409)
    try:
        category = RoomCategory.objects.create(client_id=client_id, name=name)
    except IntegrityError:
        return JsonResponse({"error": "A room category with this name already exists"}, status=409)
    return JsonResponse({"success": True, "category": _serialize(category)}, status=201)


@require_jwt("admin")
@require_POST
def edit_category(request):
    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)
    requested_client_id = str(body.get("client_id", "")).strip() or None
    client_id = get_tenant_client_id(request, requested_client_id)
    if client_id is None:
        return JsonResponse({"error": "You are not authorized to access this client"}, status=403)
    name = str(body.get("name", "")).strip()
    if not name or len(name) > 100:
        return JsonResponse({"error": "A valid category name is required"}, status=400)
    try:
        category = RoomCategory.objects.get(id=body.get("id"), client_id=client_id)
    except (RoomCategory.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"error": "Room category not found"}, status=404)
    if RoomCategory.objects.filter(client_id=client_id, name__iexact=name).exclude(id=category.id).exists():
        return JsonResponse({"error": "A room category with this name already exists"}, status=409)
    category.name = name
    category.save(update_fields=["name"])
    return JsonResponse({"success": True, "category": _serialize(category)})


@require_jwt("admin")
@require_POST
def delete_category(request):
    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)
    requested_client_id = str(body.get("client_id", "")).strip() or None
    client_id = get_tenant_client_id(request, requested_client_id)
    if client_id is None:
        return JsonResponse({"error": "You are not authorized to access this client"}, status=403)
    try:
        category = RoomCategory.objects.get(id=body.get("id"), client_id=client_id)
    except (RoomCategory.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"error": "Room category not found"}, status=404)
    if category.rooms.exists():
        return JsonResponse({"error": "This category is assigned to one or more rooms"}, status=409)
    category.delete()
    return JsonResponse({"success": True})
