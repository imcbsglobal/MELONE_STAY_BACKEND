import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction
import requests
import urllib3

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from .authentication import issue_access_token, password_matches_and_upgrade, require_jwt, get_tenant_client_id
from .models import AdminAccount

logger = logging.getLogger(__name__)


def _fetch_project_data():
    try:
        api_response = requests.get(
            settings.PROJECT_API_URL,
            timeout=settings.PROJECT_API_TIMEOUT,
            verify=False  # Disable SSL verification for development
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
            verify=False  # Disable SSL verification for development
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

    # Admin created by superuser - NOT a demo user
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
        is_demo_user=False,  # Explicitly mark as admin-created
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

    # ── 1. Pull live data from Project Activation API ─────────────────
    live_status = _live_client_status(client_id)
    # If API fails or user not found, use database status
    if live_status is None or live_status == "":
        current_status = admin.status
        logger.info(f"Using database status for {username}: {current_status}")
    else:
        current_status = _sync_admin_status(admin, live_status)
        logger.info(f"Using live API status for {username}: {current_status}")

    # ── 2. Resolve expiry_date ─────────────────────────────────────────
    # Use DB value first; fall back to live API if we can expand _fetch_project_data
    expiry_date = admin.expiry_date.strip() if admin.expiry_date else ""

    # ── 3. Check license expiry BEFORE the generic inactive check ──────
    # Expired accounts on the Project API often come back as "Inactive",
    # so we must detect the expiry date first to show the correct page.
    from datetime import date, datetime

    if expiry_date:
        try:
            expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            if expiry < date.today():
                return JsonResponse(
                    {
                        "error": "License expired",
                        "license_expired": True,
                        "expiry_date": expiry_date,
                        "customer_name": admin.customer_name,
                    },
                    status=403,
                )
        except ValueError:
            pass  # unrecognised date format — fall through to status check

    # ── 4. If status is non-active AND expiry_date is empty or missing, ─
    # treat as license expired (Project API returns Inactive for expired)
    if current_status.lower() not in ("active",):
        # Try to get expiry/is_expired from the live API customer record
        customers = _fetch_project_data()
        live_expiry = ""
        is_expired_flag = False
        if customers:
            for c in customers:
                if c.get("client_id", "").strip() == client_id:
                    validity = c.get("license_validity") or {}
                    live_expiry = validity.get("expiry_date", "")
                    is_expired_flag = bool(validity.get("is_expired", False))
                    break

        # Use is_expired flag from API (most reliable)
        if is_expired_flag:
            if live_expiry and admin.expiry_date != live_expiry:
                admin.expiry_date = live_expiry
                admin.save(update_fields=["expiry_date"])
            return JsonResponse(
                {
                    "error": "License expired",
                    "license_expired": True,
                    "expiry_date": live_expiry or expiry_date,
                    "customer_name": admin.customer_name,
                },
                status=403,
            )

        # Also check expiry_date manually as fallback
        if live_expiry:
            try:
                expiry = datetime.strptime(live_expiry, "%Y-%m-%d").date()
                if expiry < date.today():
                    if admin.expiry_date != live_expiry:
                        admin.expiry_date = live_expiry
                        admin.save(update_fields=["expiry_date"])
                    return JsonResponse(
                        {
                            "error": "License expired",
                            "license_expired": True,
                            "expiry_date": live_expiry,
                            "customer_name": admin.customer_name,
                        },
                        status=403,
                    )
            except ValueError:
                pass

        # Genuinely inactive (not expired) — show inactive message
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
    # Only show admin-created users (NOT demo/signup users)
    admins = AdminAccount.objects.filter(is_demo_user=False).order_by("-created_at")

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


@require_POST
def signup(request):
    """
    Complete signup flow integrating:
    1. Google Authentication data
    2. User details from frontend form
    3. Project Activation API
    4. Superuser API
    5. User Master API
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid request body"}, status=400)
    if not isinstance(body, dict):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    # Extract form data from frontend
    email = str(body.get("email", "")).strip()
    organization_name = str(body.get("organizationName", "")).strip()
    city = str(body.get("city", "")).strip()
    country = str(body.get("country", "")).strip()
    phone_number = str(body.get("phoneNumber", "")).strip()
    address = str(body.get("address", "")).strip()
    username = str(body.get("username", "")).strip()
    password = body.get("password", "")
    financial_year = str(body.get("financialYear", "")).strip()

    # Validate required fields
    if not all([email, organization_name, username]) or not isinstance(password, str) or not password:
        logger.warning(f"Signup validation failed for email: {email}")
        return JsonResponse({
            "error": "Email, organization name, username and password are required"
        }, status=400)

    # Check if user already exists
    if AdminAccount.objects.filter(username=username).exists():
        logger.warning(f"Signup attempt with existing username: {username}")
        return JsonResponse({"error": "Username already exists"}, status=409)
    
    if AdminAccount.objects.filter(client_id=email).exists():
        logger.warning(f"Signup attempt with existing email: {email}")
        return JsonResponse({
            "error": "An account with this email already exists"
        }, status=409)

    logger.info(f"Starting signup process for email: {email}, username: {username}")

    # Initialize default values
    license_key = ""
    package = "Platinum"
    module_name = "Melone Stay"
    expiry_date = ""
    status = "Active"

    # Step 1: Call Project Activation API to validate/get customer data (non-blocking)
    try:
        logger.debug("Calling Project Activation API...")
        project_response = requests.get(
            settings.PROJECT_API_URL,
            timeout=settings.PROJECT_API_TIMEOUT,
            verify=False  # Disable SSL verification for development
        )
        project_response.raise_for_status()
        project_data = project_response.json()
        logger.info("Project Activation API call successful")

        if project_data.get("success"):
            # Find customer data by email (client_id)
            customers = project_data.get("customers", [])
            customer_data = None
            for customer in customers:
                if customer.get("client_id", "").strip() == email:
                    customer_data = customer
                    logger.info(f"Found existing customer data for email: {email}")
                    break

            # If customer exists, use their data
            if customer_data:
                license_key = customer_data.get("license_key", "")
                package = customer_data.get("package", "Platinum")
                modules = customer_data.get("modules", [])
                module_name = modules[0].get("module_name", "") if modules else "Melone Stay"
                license_validity = customer_data.get("license_validity", {})
                expiry_date = license_validity.get("expiry_date", "")
                status = customer_data.get("status", "Active")
    except Exception as e:
        logger.warning(f"Project Activation API failed (non-critical): {str(e)}")
        # Continue with default values

    # Step 2: Call Superuser API to verify system is active (non-blocking)
    superuser_active = False
    try:
        logger.debug("Calling Superuser API to verify status...")
        superuser_response = requests.get(
            settings.SUPERUSER_API_URL,
            timeout=settings.SUPERUSER_API_TIMEOUT,
            verify=False  # Disable SSL verification for development
        )
        superuser_response.raise_for_status()
        superuser_data = superuser_response.json()
        superuser_active = superuser_data.get("status") == "active"
        logger.info(f"Superuser API status check successful: active={superuser_active}")
    except Exception as e:
        logger.warning(f"Superuser API check failed (non-critical): {str(e)}")
        # Continue anyway - don't block signup if superuser API is down
        superuser_active = True  # Allow signup to proceed

    # Step 3: Call User Master API to register user in central system (non-blocking)
    user_master_payload = {
        "name": username,
        "email": email,
        "phone": phone_number,
        "organization": organization_name,
        "city": city,
        "country": country,
        "address": address,
        "melone_stay": True,
        "live_menu": False,
        "inventory": False,
        "qr_menu": False,
        "pos": False,
        "delivery": False,
        "aggregator": False,
        "table_booking": False,
        "feedback": False,
        "analytics": False
    }
    
    user_master_success = False
    try:
        logger.debug("Calling User Master API...")
        user_master_response = requests.post(
            settings.USER_MASTER_API_URL,
            json=user_master_payload,
            headers={"Content-Type": "application/json"},
            timeout=settings.USER_MASTER_API_TIMEOUT,
            verify=False  # Disable SSL verification for development
        )
        user_master_response.raise_for_status()
        user_master_data = user_master_response.json()
        user_master_success = user_master_data.get("success", False)
        logger.info(f"User Master API call successful: {user_master_success}")
    except Exception as e:
        logger.warning(f"User Master API failed (non-critical): {str(e)}")
        # Continue anyway - don't block signup if user master API is down
        user_master_success = False  # Mark as failed but continue

    # Step 4: Create admin account in local database
    try:
        with transaction.atomic():
            logger.debug("Creating local admin account...")
            
            # Truncate financial_year to 20 characters to prevent database errors
            financial_year_truncated = financial_year[:20] if financial_year else ""
            
            # Log all field values and their lengths for debugging
            logger.debug(f"Field values: client_id={email} (len={len(email)}), "
                        f"customer_name={organization_name} (len={len(organization_name)}), "
                        f"license_key={license_key} (len={len(license_key)}), "
                        f"package={package} (len={len(package)}), "
                        f"module_name={module_name} (len={len(module_name)}), "
                        f"expiry_date={expiry_date} (len={len(expiry_date)}), "
                        f"status={status} (len={len(status)}), "
                        f"username={username} (len={len(username)}), "
                        f"financial_year={financial_year_truncated} (len={len(financial_year_truncated)}) [original: {financial_year}]")
            
            # Mark signup users as demo users
            admin = AdminAccount.objects.create(
                client_id=email,
                customer_name=organization_name,
                license_key=license_key,
                package=package,
                module_name=module_name,
                expiry_date=expiry_date,
                status=status,
                username=username,
                password=make_password(password),
                is_demo_user=True,  # Mark as demo/signup user
                financial_year=financial_year_truncated,  # Store truncated financial year
            )

            logger.info(f"Signup completed successfully for username: {username}, id: {admin.id}")

            return JsonResponse({
                "success": True,
                "message": "Account created successfully",
                "admin": {
                    "id": admin.id,
                    "username": admin.username,
                    "email": admin.client_id,
                    "customer_name": admin.customer_name,
                    "package": admin.package,
                    "module_name": admin.module_name,
                    "expiry_date": admin.expiry_date,
                    "status": admin.status,
                },
                "token": issue_access_token(
                    subject=admin.username,
                    role="admin",
                    client_id=admin.client_id,
                ),
            }, status=201)
    except Exception as e:
        logger.exception(f"Failed to create admin account: {str(e)}")
        return JsonResponse({
            "error": "Failed to create account",
            "details": str(e)
        }, status=500)



@require_GET
def superuser_credentials(request):
    """
    Return superuser username/password from the external Superuser API.
    Used by the signup Done step to display credentials to the new user.
    """
    try:
        api_response = requests.get(
            settings.SUPERUSER_API_URL,
            timeout=settings.SUPERUSER_API_TIMEOUT,
            verify=False  # Disable SSL verification for development
        )
        api_response.raise_for_status()
        data = api_response.json()
    except (requests.exceptions.RequestException, ValueError):
        return JsonResponse({"success": False, "error": "Could not fetch superuser credentials"}, status=503)

    if data.get("status") != "active":
        return JsonResponse({"success": False, "error": "Superuser account is inactive"}, status=503)

    return JsonResponse({
        "success": True,
        "credentials": {
            "username": data.get("username", ""),
            "password": data.get("password", ""),
        },
    })


@require_GET
def activity_log_proxy(request):
    """
    Proxy endpoint for fetching activity logs from the external Activity Log Master API.
    Bypasses CORS restrictions by making the request server-side.
    """
    client_id = request.GET.get('client_id', '').strip()
    
    if not client_id:
        return JsonResponse({"error": "client_id parameter is required"}, status=400)
    
    try:
        api_url = f"https://centralmastermanagement.imcbs.com/api/activity-log-master/?client_id={client_id}"
        api_response = requests.get(
            api_url,
            timeout=10,
            verify=False  # Disable SSL verification for development
        )
        api_response.raise_for_status()
        data = api_response.json()
        return JsonResponse(data, safe=False)
    except requests.exceptions.RequestException as e:
        logger.error(f"Activity log proxy error: {str(e)}")
        return JsonResponse({"error": "Failed to fetch activity logs"}, status=503)
    except ValueError:
        return JsonResponse({"error": "Invalid response from activity log API"}, status=503)


@require_POST
def activity_log_create_proxy(request):
    """
    Proxy endpoint for creating activity logs in the external Activity Log Master API.
    Bypasses CORS restrictions by making the request server-side.
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid request body"}, status=400)
    
    if not isinstance(body, dict):
        return JsonResponse({"error": "Invalid request body"}, status=400)
    
    # Validate required fields
    required_fields = ['client_id', 'project_name', 'username', 'action', 'description']
    for field in required_fields:
        if not body.get(field):
            return JsonResponse({"error": f"{field} is required"}, status=400)
    
    try:
        api_url = "https://centralmastermanagement.imcbs.com/api/activity-log-master/"
        api_response = requests.post(
            api_url,
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=10,
            verify=False  # Disable SSL verification for development
        )
        api_response.raise_for_status()
        data = api_response.json()
        return JsonResponse(data, safe=False)
    except requests.exceptions.RequestException as e:
        logger.error(f"Activity log create proxy error: {str(e)}")
        return JsonResponse({"error": "Failed to create activity log"}, status=503)
    except ValueError:
        return JsonResponse({"error": "Invalid response from activity log API"}, status=503)


@require_GET
@require_jwt("superuser")
def list_signup_users(request):
    """
    List all users who signed up through the public signup form.
    Returns only demo users (is_demo_user=True).
    """
    try:
        # Only show signup/demo users (NOT admin-created users)
        admins = AdminAccount.objects.filter(is_demo_user=True).order_by('-id')
        users_list = [{
            "id": admin.id,
            "username": admin.username,
            "email": admin.client_id,
            "customer_name": admin.customer_name,
            "license_key": admin.license_key,
            "package": admin.package,
            "module_name": admin.module_name,
            "expiry_date": admin.expiry_date,
            "status": admin.status,
        } for admin in admins]
        
        return JsonResponse({"success": True, "users": users_list})
    except Exception as e:
        logger.exception(f"Failed to list signup users: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_POST
@require_jwt("superuser")
def delete_demo_user(request):
    """Delete a demo user (signup user)"""
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid request body"}, status=400)
    if not isinstance(body, dict):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    user_id = body.get("id")
    password = body.get("password", "")

    if not user_id:
        return JsonResponse({"error": "User ID is required"}, status=400)

    if not password:
        return JsonResponse({"error": "Superuser password is required"}, status=400)

    # Verify superuser password
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

    # Find and delete the demo user
    try:
        user = AdminAccount.objects.get(id=user_id, is_demo_user=True)
    except AdminAccount.DoesNotExist:
        return JsonResponse({"error": "Demo user not found"}, status=404)

    user.delete()
    return JsonResponse({"success": True})


@require_POST
@require_jwt("superuser")
def edit_demo_user(request):
    """Edit a demo user (signup user)"""
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid request body"}, status=400)
    if not isinstance(body, dict):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    user_id = body.get("id")
    new_username = str(body.get("username", "")).strip()
    new_password = body.get("password", "")
    superuser_password = body.get("superuser_password", "")

    if not user_id:
        return JsonResponse({"error": "User ID is required"}, status=400)

    if not new_username:
        return JsonResponse({"error": "Username is required"}, status=400)

    if not isinstance(new_password, str) or not isinstance(superuser_password, str) or not superuser_password:
        return JsonResponse({"error": "Superuser password is required"}, status=400)

    # Verify superuser password
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

    # Find the demo user
    try:
        user = AdminAccount.objects.get(id=user_id, is_demo_user=True)
    except AdminAccount.DoesNotExist:
        return JsonResponse({"error": "Demo user not found"}, status=404)

    # Check if username is already taken by another user
    if AdminAccount.objects.filter(username=new_username).exclude(id=user_id).exists():
        return JsonResponse({"error": "Username already exists"}, status=409)

    # Update user
    user.username = new_username
    update_fields = ["username"]
    if new_password:
        user.password = make_password(new_password)
        update_fields.append("password")
    user.save(update_fields=update_fields)

    return JsonResponse({"success": True})

@require_jwt("admin")
def user_master_proxy(request):
    """
    Proxy for the external User Master API to avoid CORS issues.
    Supports GET (list), POST (create), PUT (replace), PATCH (partial), DELETE (remove).
    """
    base_url = settings.USER_MASTER_API_URL  # https://centralmastermanagement.imcbs.com/api/user-master/
    client_id = get_tenant_client_id(request)
    if client_id is None:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    headers = {"Content-Type": "application/json"}
    timeout = settings.USER_MASTER_API_TIMEOUT

    if request.method == "GET":
        # Filter list by client_id using query param
        params = {"client_id": client_id}
        try:
            resp = requests.get(base_url, params=params, headers=headers, timeout=timeout, verify=False)
            return JsonResponse(resp.json(), safe=False, status=resp.status_code)
        except requests.exceptions.RequestException as e:
            logger.error("user_master GET error: %s", e)
            return JsonResponse({"error": "Failed to reach User Master API"}, status=503)

    if request.method == "POST":
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid request body"}, status=400)
        body["client_id"] = client_id
        try:
            resp = requests.post(base_url, json=body, headers=headers, timeout=timeout, verify=False)
            if resp.status_code == 204:
                from django.http import HttpResponse
                return HttpResponse(status=204)
            return JsonResponse(resp.json(), safe=False, status=resp.status_code)
        except requests.exceptions.RequestException as e:
            logger.error("user_master POST error: %s", e)
            return JsonResponse({"error": "Failed to reach User Master API"}, status=503)

    if request.method in ("PUT", "PATCH"):
        # Extract pk from path: /api/user-master/<pk>/
        pk = request.resolver_match.kwargs.get("pk")
        url = f"{base_url}{pk}/" if pk else base_url
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid request body"}, status=400)
        body["client_id"] = client_id
        fn = requests.put if request.method == "PUT" else requests.patch
        try:
            resp = fn(url, json=body, headers=headers, timeout=timeout, verify=False)
            if resp.status_code == 204:
                from django.http import HttpResponse
                return HttpResponse(status=204)
            return JsonResponse(resp.json(), safe=False, status=resp.status_code)
        except requests.exceptions.RequestException as e:
            logger.error("user_master %s error: %s", request.method, e)
            return JsonResponse({"error": "Failed to reach User Master API"}, status=503)

    if request.method == "DELETE":
        pk = request.resolver_match.kwargs.get("pk")
        url = f"{base_url}{pk}/"
        try:
            resp = requests.delete(url, headers=headers, timeout=timeout, verify=False)
            from django.http import HttpResponse
            return HttpResponse(status=resp.status_code)
        except requests.exceptions.RequestException as e:
            logger.error("user_master DELETE error: %s", e)
            return JsonResponse({"error": "Failed to reach User Master API"}, status=503)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@require_GET
def countries_proxy(request):
    """Proxy for the external country/financial-year API to avoid CORS issues."""
    COUNTRIES_API_URL = 'https://centralmastermanagement.imcbs.com/api/financial-year/country-wise/'
    try:
        response = requests.get(COUNTRIES_API_URL, timeout=10, verify=False)
        response.raise_for_status()
        return JsonResponse(response.json(), safe=False)
    except requests.exceptions.RequestException as e:
        logger.error('Failed to fetch countries from external API: %s', e)
        return JsonResponse({'error': 'Failed to fetch country list. Please try again.'}, status=502)
