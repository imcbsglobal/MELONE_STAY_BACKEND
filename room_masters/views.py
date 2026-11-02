import json
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from accounts.authentication import get_tenant_client_id, require_jwt
from room_categories.models import RoomCategory

from .models import Room, RoomPrice


def _load_body(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return None
    return body if isinstance(body, dict) else None


def _validate_payload(body):
    client_id = str(body.get("client_id", "")).strip()
    code = str(body.get("code", "")).strip()
    name = str(body.get("name", "")).strip()
    floor = str(body.get("floor", "")).strip()
    air_conditioning = body.get("air_conditioning")
    if not all([client_id, code, name, floor]):
        return None, "client_id, code, name and floor are required"
    if len(client_id) > 50 or len(code) > 30 or len(name) > 120 or len(floor) > 60:
        return None, "One or more room fields are too long"
    if air_conditioning not in ("AC", "Non-AC"):
        return None, "air_conditioning must be AC or Non-AC"
    try:
        category_id = int(body.get("category_id"))
        tax = Decimal(str(body.get("tax")))
    except (ValueError, TypeError, InvalidOperation):
        return None, "A valid category_id and tax are required"
    if category_id <= 0 or not tax.is_finite() or tax < 0 or tax > 100 or tax.as_tuple().exponent < -2:
        return None, "Category and tax values are out of range"
    raw_prices = body.get("prices")
    if not isinstance(raw_prices, list) or not raw_prices:
        return None, "At least one room price is required"
    prices = []
    for price in raw_prices:
        if not isinstance(price, dict):
            return None, "Each room price must include an amount"
        price_name = str(price.get("name", "")).strip()
        try:
            amount = Decimal(str(price.get("amount")))
        except (ValueError, TypeError, InvalidOperation):
            return None, "Each room price must have a valid amount"
        if len(price_name) > 60 or not amount.is_finite() or amount < 0 or amount >= Decimal("100000000") or amount.as_tuple().exponent < -2:
            return None, "Each room price must have a non-negative amount"
        prices.append({"name": price_name, "amount": amount})
    return {
        "client_id": client_id,
        "code": code,
        "name": name,
        "category_id": category_id,
        "air_conditioning": air_conditioning,
        "floor": floor,
        "tax": tax,
        "prices": prices,
    }, None


def _serialize(room):
    return {
        "id": room.id,
        "client_id": room.client_id,
        "code": room.code,
        "name": room.name,
        "category_id": room.category_id,
        "category_name": room.category.name,
        "air_conditioning": room.air_conditioning,
        "floor": room.floor,
        "tax": str(room.tax),
        "is_favorite": room.is_favorite,
        "prices": [
            {"id": price.id, "name": price.name, "amount": str(price.amount)}
            for price in room.prices.all()
        ],
        "created_at": room.created_at.strftime("%Y-%m-%d %H:%M"),
    }


def _room_queryset():
    return Room.objects.select_related("category").prefetch_related("prices")


def _get_category(client_id, category_id):
    try:
        return RoomCategory.objects.get(id=category_id, client_id=client_id)
    except (RoomCategory.DoesNotExist, ValueError, TypeError):
        return None


def _save_prices(room, prices):
    room.prices.all().delete()
    RoomPrice.objects.bulk_create([
        RoomPrice(room=room, name=price["name"], amount=price["amount"])
        for price in prices
    ])


@require_jwt("admin")
@require_GET
def list_rooms(request):
    requested_client_id = request.GET.get("client_id", "").strip() or None
    client_id = get_tenant_client_id(request, requested_client_id)
    if client_id is None:
        return JsonResponse({"error": "You are not authorized to access this client"}, status=403)
    rooms = _room_queryset().filter(client_id=client_id)
    return JsonResponse({"success": True, "rooms": [_serialize(room) for room in rooms]})


@require_jwt("admin")
@require_POST
def create_room(request):
    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)
    values, error = _validate_payload(body)
    if error:
        return JsonResponse({"error": error}, status=400)
    client_id = get_tenant_client_id(request, values["client_id"])
    if client_id is None:
        return JsonResponse({"error": "You are not authorized to access this client"}, status=403)
    values["client_id"] = client_id
    category = _get_category(values["client_id"], values["category_id"])
    if category is None:
        return JsonResponse({"error": "Room category not found"}, status=400)
    try:
        with transaction.atomic():
            room = Room.objects.create(
                client_id=values["client_id"],
                code=values["code"],
                name=values["name"],
                category=category,
                air_conditioning=values["air_conditioning"],
                floor=values["floor"],
                tax=values["tax"],
            )
            _save_prices(room, values["prices"])
    except IntegrityError:
        return JsonResponse({"error": "A room with this code already exists"}, status=409)
    return JsonResponse({"success": True, "room": _serialize(_room_queryset().get(id=room.id))}, status=201)


@require_jwt("admin")
@require_POST
def edit_room(request):
    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)
    values, error = _validate_payload(body)
    if error:
        return JsonResponse({"error": error}, status=400)
    client_id = get_tenant_client_id(request, values["client_id"])
    if client_id is None:
        return JsonResponse({"error": "You are not authorized to access this client"}, status=403)
    values["client_id"] = client_id
    try:
        room = Room.objects.get(id=body.get("id"), client_id=values["client_id"])
    except (Room.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"error": "Room not found"}, status=404)
    category = _get_category(values["client_id"], values["category_id"])
    if category is None:
        return JsonResponse({"error": "Room category not found"}, status=400)
    if Room.objects.filter(client_id=values["client_id"], code=values["code"]).exclude(id=room.id).exists():
        return JsonResponse({"error": "A room with this code already exists"}, status=409)
    try:
        with transaction.atomic():
            room.code = values["code"]
            room.name = values["name"]
            room.category = category
            room.air_conditioning = values["air_conditioning"]
            room.floor = values["floor"]
            room.tax = values["tax"]
            room.save()
            _save_prices(room, values["prices"])
    except IntegrityError:
        return JsonResponse({"error": "A room with this code already exists"}, status=409)
    return JsonResponse({"success": True, "room": _serialize(_room_queryset().get(id=room.id))})


@require_jwt("admin")
@require_POST
def delete_room(request):
    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)
    requested_client_id = str(body.get("client_id", "")).strip() or None
    client_id = get_tenant_client_id(request, requested_client_id)
    if client_id is None:
        return JsonResponse({"error": "You are not authorized to access this client"}, status=403)
    try:
        room = Room.objects.get(id=body.get("id"), client_id=client_id)
    except (Room.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"error": "Room not found"}, status=404)
    room.delete()
    return JsonResponse({"success": True})


@require_jwt("admin")
@require_POST
def set_room_favorite(request):
    body = _load_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid request body"}, status=400)
    requested_client_id = str(body.get("client_id", "")).strip() or None
    client_id = get_tenant_client_id(request, requested_client_id)
    if client_id is None:
        return JsonResponse({"error": "You are not authorized to access this client"}, status=403)
    is_favorite = body.get("is_favorite")
    if not isinstance(is_favorite, bool):
        return JsonResponse({"error": "is_favorite must be a boolean"}, status=400)
    try:
        room = Room.objects.get(id=body.get("id"), client_id=client_id)
    except (Room.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"error": "Room not found"}, status=404)
    room.is_favorite = is_favorite
    room.save(update_fields=["is_favorite"])
    return JsonResponse({"success": True, "room": _serialize(_room_queryset().get(id=room.id))})
