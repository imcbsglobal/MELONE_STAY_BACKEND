from datetime import datetime, timedelta, timezone
from functools import wraps
import secrets

import jwt
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils.crypto import constant_time_compare
from django.http import JsonResponse


JWT_ISSUER = "melonestay"
JWT_AUDIENCE = "melonestay-api"


def issue_access_token(*, subject, role, client_id=None):
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(subject),
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=settings.JWT_ACCESS_TOKEN_LIFETIME),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "jti": secrets.token_urlsafe(16),
    }
    if client_id is not None:
        claims["client_id"] = client_id
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm="HS256")


def require_jwt(*allowed_roles):
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            authorization = request.headers.get("Authorization", "")
            scheme, separator, token = authorization.partition(" ")
            if not separator or scheme.lower() != "bearer" or not token.strip():
                return JsonResponse({"error": "Bearer token required"}, status=401)
            try:
                claims = jwt.decode(
                    token.strip(),
                    settings.JWT_SECRET_KEY,
                    algorithms=["HS256"],
                    issuer=JWT_ISSUER,
                    audience=JWT_AUDIENCE,
                    options={"require": ["sub", "role", "iat", "exp", "iss", "aud"]},
                )
            except jwt.InvalidTokenError:
                return JsonResponse({"error": "Invalid or expired token"}, status=401)
            if claims.get("role") not in allowed_roles:
                return JsonResponse({"error": "You are not authorized to perform this action"}, status=403)
            request.jwt_claims = claims
            return view(request, *args, **kwargs)

        return wrapped

    return decorate


def get_tenant_client_id(request, requested_client_id=None):
    token_client_id = request.jwt_claims.get("client_id")
    if not token_client_id:
        return None
    if requested_client_id is not None and requested_client_id != token_client_id:
        return None
    return token_client_id


def password_matches_and_upgrade(account, raw_password):
    if not isinstance(raw_password, str):
        return False
    if check_password(raw_password, account.password):
        return True
    if not constant_time_compare(account.password, raw_password):
        return False
    account.password = make_password(raw_password)
    account.save(update_fields=["password"])
    return True
