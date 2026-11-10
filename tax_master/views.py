import json

from django.db import IntegrityError
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods

from accounts.authentication import get_tenant_client_id, require_jwt

from .models import IndiaTax, OtherTax


def _load_body(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return None
    return body if isinstance(body, dict) else None


def _serialize_india(rec):
    return {
        "id": rec.id,
        "client_id": rec.client_id,
        "code": rec.code,
        "name": rec.name,
        "type": rec.type,
        "cgst": str(rec.cgst),
        "sgst": str(rec.sgst),
        "igst": str(rec.igst),
        "gst": str(rec.gst),
        "cal_method": rec.cal_method,
        "status": rec.status,
    }


def _serialize_other(rec):
    return {
        "id": rec.id,
        "client_id": rec.client_id,
        "code": rec.code,
        "name": rec.name,
        "tax": str(rec.tax),
        "cal_method": rec.cal_method,
        "status": rec.status,
    }


# ─── India ────────────────────────────────────────────────────────────────────

@require_jwt("admin")
@require_http_methods(["GET", "POST", "PUT"])
def india_list_create_update(request):
    client_id = get_tenant_client_id(request)
    if client_id is None:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    if request.method == "GET":
        records = IndiaTax.objects.filter(client_id=client_id)
        return JsonResponse([_serialize_india(r) for r in records], safe=False)

    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)

    if request.method == "POST":
        code = str(body.get("code", "")).strip()
        name = str(body.get("name", "")).strip()
        cal_method = str(body.get("cal_method", "")).strip()
        if not code:
            return JsonResponse({"code": ["Code is required."]}, status=400)
        if len(code) > 20:
            return JsonResponse({"code": ["Code must be 20 characters or fewer."]}, status=400)
        if not name:
            return JsonResponse({"name": ["Name is required."]}, status=400)
        if len(name) > 100:
            return JsonResponse({"name": ["Name must be 100 characters or fewer."]}, status=400)
        if not cal_method:
            return JsonResponse({"cal_method": ["Calculation method is required."]}, status=400)

        try:
            rec = IndiaTax.objects.create(
                client_id=client_id,
                code=code,
                name=name,
                type=str(body.get("type", "")).strip(),
                cgst=body.get("cgst") or 0,
                sgst=body.get("sgst") or 0,
                igst=body.get("igst") or 0,
                gst=body.get("gst") or 0,
                cal_method=cal_method,
                status=body.get("status", "ACTIVE"),
            )
        except IntegrityError:
            return JsonResponse({"error": "A record with this code or name already exists for this client."}, status=400)
        return JsonResponse(_serialize_india(rec), status=201)

    # PUT
    record_id = body.get("id")
    if not record_id:
        return JsonResponse({"error": "id is required for update"}, status=400)
    try:
        rec = IndiaTax.objects.get(id=record_id, client_id=client_id)
    except IndiaTax.DoesNotExist:
        return JsonResponse({"error": "Record not found"}, status=404)

    code = str(body.get("code", rec.code)).strip()
    name = str(body.get("name", rec.name)).strip()
    cal_method = str(body.get("cal_method", rec.cal_method)).strip()
    if not code:
        return JsonResponse({"code": ["Code is required."]}, status=400)
    if not name:
        return JsonResponse({"name": ["Name is required."]}, status=400)
    if not cal_method:
        return JsonResponse({"cal_method": ["Calculation method is required."]}, status=400)

    rec.code = code
    rec.name = name
    rec.type = str(body.get("type", rec.type)).strip()
    rec.cgst = body.get("cgst") if body.get("cgst") is not None else rec.cgst
    rec.sgst = body.get("sgst") if body.get("sgst") is not None else rec.sgst
    rec.igst = body.get("igst") if body.get("igst") is not None else rec.igst
    rec.gst = body.get("gst") if body.get("gst") is not None else rec.gst
    rec.cal_method = cal_method
    rec.status = body.get("status", rec.status)
    try:
        rec.save()
    except IntegrityError:
        return JsonResponse({"error": "A record with this code or name already exists for this client."}, status=400)
    return JsonResponse(_serialize_india(rec))


@require_jwt("admin")
@require_http_methods(["GET", "DELETE"])
def india_detail_delete(request, pk):
    client_id = get_tenant_client_id(request)
    if client_id is None:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        rec = IndiaTax.objects.get(id=pk, client_id=client_id)
    except IndiaTax.DoesNotExist:
        return JsonResponse({"detail": "Not found."}, status=404)

    if request.method == "GET":
        return JsonResponse(_serialize_india(rec))

    # DELETE — HTTP 204 No Content
    rec.delete()
    return HttpResponse(status=204)


# ─── Other ────────────────────────────────────────────────────────────────────

@require_jwt("admin")
@require_http_methods(["GET", "POST", "PUT"])
def other_list_create_update(request):
    client_id = get_tenant_client_id(request)
    if client_id is None:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    if request.method == "GET":
        records = OtherTax.objects.filter(client_id=client_id)
        return JsonResponse([_serialize_other(r) for r in records], safe=False)

    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)

    if request.method == "POST":
        code = str(body.get("code", "")).strip()
        name = str(body.get("name", "")).strip()
        cal_method = str(body.get("cal_method", "")).strip()
        if not code:
            return JsonResponse({"code": ["Code is required."]}, status=400)
        if len(code) > 20:
            return JsonResponse({"code": ["Code must be 20 characters or fewer."]}, status=400)
        if not name:
            return JsonResponse({"name": ["Name is required."]}, status=400)
        if len(name) > 100:
            return JsonResponse({"name": ["Name must be 100 characters or fewer."]}, status=400)
        if not cal_method:
            return JsonResponse({"cal_method": ["Calculation method is required."]}, status=400)

        try:
            rec = OtherTax.objects.create(
                client_id=client_id,
                code=code,
                name=name,
                tax=body.get("tax") or 0,
                cal_method=cal_method,
                status=body.get("status", "ACTIVE"),
            )
        except IntegrityError:
            return JsonResponse({"error": "A record with this code or name already exists for this client."}, status=400)
        return JsonResponse(_serialize_other(rec), status=201)

    # PUT
    record_id = body.get("id")
    if not record_id:
        return JsonResponse({"error": "id is required for update"}, status=400)
    try:
        rec = OtherTax.objects.get(id=record_id, client_id=client_id)
    except OtherTax.DoesNotExist:
        return JsonResponse({"error": "Record not found"}, status=404)

    code = str(body.get("code", rec.code)).strip()
    name = str(body.get("name", rec.name)).strip()
    cal_method = str(body.get("cal_method", rec.cal_method)).strip()
    if not code:
        return JsonResponse({"code": ["Code is required."]}, status=400)
    if not name:
        return JsonResponse({"name": ["Name is required."]}, status=400)
    if not cal_method:
        return JsonResponse({"cal_method": ["Calculation method is required."]}, status=400)

    rec.code = code
    rec.name = name
    rec.tax = body.get("tax") if body.get("tax") is not None else rec.tax
    rec.cal_method = cal_method
    rec.status = body.get("status", rec.status)
    try:
        rec.save()
    except IntegrityError:
        return JsonResponse({"error": "A record with this code or name already exists for this client."}, status=400)
    return JsonResponse(_serialize_other(rec))


@require_jwt("admin")
@require_http_methods(["GET", "DELETE"])
def other_detail_delete(request, pk):
    client_id = get_tenant_client_id(request)
    if client_id is None:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        rec = OtherTax.objects.get(id=pk, client_id=client_id)
    except OtherTax.DoesNotExist:
        return JsonResponse({"detail": "Not found."}, status=404)

    if request.method == "GET":
        return JsonResponse(_serialize_other(rec))

    # DELETE — HTTP 204 No Content
    rec.delete()
    return HttpResponse(status=204)
