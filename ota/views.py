import json

from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from accounts.authentication import get_tenant_client_id, require_jwt

from .models import OTA


def _load_body(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return None
    return body if isinstance(body, dict) else None


def _serialize(ota):
    return {
        "id": ota.id,
        "name": ota.name,
        "code": ota.code,
        "created_at": ota.created_at.strftime("%Y-%m-%d %H:%M"),
    }


@require_jwt("admin")
@require_GET
def list_otas(request):
    requested_client_id = request.GET.get("client_id", "").strip() or None
    client_id = get_tenant_client_id(request, requested_client_id)
    if client_id is None:
        return JsonResponse({"error": "You are not authorized to access this client"}, status=403)
    otas = OTA.objects.filter(client_id=client_id)
    return JsonResponse({"success": True, "otas": [_serialize(ota) for ota in otas]})


@require_jwt("admin")
@require_POST
def create_ota(request):
    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)

    requested_client_id = str(body.get("client_id", "")).strip() or None
    client_id = get_tenant_client_id(request, requested_client_id)
    if client_id is None:
        return JsonResponse({"error": "You are not authorized to access this client"}, status=403)

    name = str(body.get("name", "")).strip()
    code = str(body.get("code", "")).strip().upper()
    if not name or not code:
        return JsonResponse({"error": "OTA name and code are required"}, status=400)
    if len(name) > 100:
        return JsonResponse({"error": "OTA name is too long"}, status=400)
    if len(code) > 50:
        return JsonResponse({"error": "OTA code is too long"}, status=400)
    if OTA.objects.filter(client_id=client_id, name__iexact=name).exists():
        return JsonResponse({"error": "An OTA with this name already exists"}, status=409)
    if OTA.objects.filter(client_id=client_id, code__iexact=code).exists():
        return JsonResponse({"error": "An OTA with this code already exists"}, status=409)

    try:
        ota = OTA.objects.create(client_id=client_id, name=name, code=code)
    except IntegrityError:
        return JsonResponse({"error": "An OTA with this name or code already exists"}, status=409)
    return JsonResponse({"success": True, "ota": _serialize(ota)}, status=201)
