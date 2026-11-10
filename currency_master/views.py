import json

from django.db import IntegrityError
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods

from accounts.authentication import get_tenant_client_id, require_jwt

from .models import Currency


def _load_body(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return None
    return body if isinstance(body, dict) else None


def _serialize(rec):
    return {
        "id": rec.id,
        "client_id": rec.client_id,
        "code": rec.code,
        "name": rec.name,
        "status": rec.status,
    }


@require_jwt("admin")
@require_http_methods(["GET", "POST", "PUT"])
def currency_list_create_update(request):
    client_id = get_tenant_client_id(request)
    if client_id is None:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    if request.method == "GET":
        records = Currency.objects.filter(client_id=client_id)
        return JsonResponse([_serialize(r) for r in records], safe=False)

    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)

    if request.method == "POST":
        code = str(body.get("code", "")).strip()
        name = str(body.get("name", "")).strip()
        if not code:
            return JsonResponse({"code": ["Code is required."]}, status=400)
        if len(code) > 20:
            return JsonResponse({"code": ["Code must be 20 characters or fewer."]}, status=400)
        if not name:
            return JsonResponse({"name": ["Name is required."]}, status=400)
        if len(name) > 100:
            return JsonResponse({"name": ["Name must be 100 characters or fewer."]}, status=400)
        try:
            rec = Currency.objects.create(
                client_id=client_id,
                code=code,
                name=name,
                status=body.get("status", "ACTIVE"),
            )
        except IntegrityError:
            return JsonResponse({"error": "A record with this code or name already exists for this client."}, status=400)
        return JsonResponse(_serialize(rec), status=201)

    # PUT
    record_id = body.get("id")
    if not record_id:
        return JsonResponse({"error": "id is required for update"}, status=400)
    try:
        rec = Currency.objects.get(id=record_id, client_id=client_id)
    except Currency.DoesNotExist:
        return JsonResponse({"detail": "Currency not found."}, status=404)

    code = str(body.get("code", rec.code)).strip()
    name = str(body.get("name", rec.name)).strip()
    if not code:
        return JsonResponse({"code": ["Code is required."]}, status=400)
    if not name:
        return JsonResponse({"name": ["Name is required."]}, status=400)

    rec.code = code
    rec.name = name
    rec.status = body.get("status", rec.status)
    try:
        rec.save()
    except IntegrityError:
        return JsonResponse({"error": "A record with this code or name already exists for this client."}, status=400)
    return JsonResponse(_serialize(rec))


@require_jwt("admin")
@require_http_methods(["GET", "DELETE"])
def currency_detail_delete(request, pk):
    client_id = get_tenant_client_id(request)
    if client_id is None:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        rec = Currency.objects.get(id=pk, client_id=client_id)
    except Currency.DoesNotExist:
        return JsonResponse({"detail": "Currency not found."}, status=404)

    if request.method == "GET":
        return JsonResponse(_serialize(rec))

    # DELETE — HTTP 204 No Content
    rec.delete()
    return HttpResponse(status=204)
