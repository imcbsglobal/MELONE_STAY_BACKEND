# Signup API Integration Documentation

## Overview
This document describes the complete signup flow integration with three external APIs.

## Signup Endpoint
**URL:** `/api/signup/`  
**Method:** `POST`  
**Authentication:** Not required (public endpoint)

### Request Body
```json
{
  "email": "user@example.com",
  "organizationName": "Hotel Paradise",
  "city": "Mumbai",
  "country": "India",
  "phoneNumber": "+91 9876543210",
  "address": "123 Main Street, Mumbai",
  "username": "hotelparadise",
  "password": "SecurePass123!"
}
```

### Required Fields
- `email` (String): User's email - used as client_id
- `organizationName` (String): Hotel/Organization name
- `username` (String): Login username
- `password` (String): Login password

### Optional Fields
- `city` (String): City/location
- `country` (String): Country
- `phoneNumber` (String): Contact phone number
- `address` (String): Full address

## Integration Flow

### Step 1: Project Activation API
**URL:** `https://activate.imcbs.com/mobileapp/api/project/melonestay/`  
**Method:** `GET`  
**Purpose:** Validate customer exists and get license details

**Response Structure:**
```json
{
  "success": true,
  "customers": [
    {
      "client_id": "user@example.com",
      "customer_name": "Hotel Paradise",
      "license_key": "LICENSE123",
      "package": "Platinum",
      "status": "Active",
      "modules": [
        {
          "module_name": "Melone Stay"
        }
      ],
      "license_validity": {
        "expiry_date": "2025-12-31"
      }
    }
  ]
}
```

### Step 2: Superuser API
**URL:** `https://su.myimc.in/api/superusers/endpoint/MELONESTAY/CYKOWV0Z/`  
**Method:** `GET`  
**Purpose:** Verify system is active and ready for new signups

**Response Structure:**
```json
{
  "username": "superuser",
  "password": "********",
  "status": "active",
  "project_name": "MELONESTAY"
}
```

### Step 3: User Master API
**URL:** `https://centralmastermanagement.imcbs.com/api/user-master/`  
**Method:** `POST`  
**Content-Type:** `application/json`  
**Purpose:** Register user in central management system

**Request Body:**
```json
{
  "name": "hotelparadise",
  "email": "user@example.com",
  "phone": "+91 9876543210",
  "organization": "Hotel Paradise",
  "city": "Mumbai",
  "country": "India",
  "address": "123 Main Street, Mumbai",
  "melone_stay": true,
  "live_menu": false,
  "inventory": false,
  "qr_menu": false,
  "pos": false,
  "delivery": false,
  "aggregator": false,
  "table_booking": false,
  "feedback": false,
  "analytics": false
}
```

**Response Structure:**
```json
{
  "success": true,
  "message": "User registered successfully",
  "user_id": "USER123"
}
```

### Step 4: Local Database Storage
After successful API calls, create AdminAccount record:

```python
AdminAccount.objects.create(
    client_id=email,
    customer_name=organization_name,
    license_key=license_key,
    package=package,
    module_name=module_name,
    expiry_date=expiry_date,
    status=status,
    username=username,
    password=make_password(password),
)
```

## Success Response
```json
{
  "success": true,
  "message": "Account created successfully",
  "admin": {
    "id": 1,
    "username": "hotelparadise",
    "email": "user@example.com",
    "customer_name": "Hotel Paradise",
    "package": "Platinum",
    "module_name": "Melone Stay",
    "expiry_date": "2025-12-31",
    "status": "Active"
  },
  "user_master_id": "USER123",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

## Error Responses

### Validation Error (400)
```json
{
  "error": "Email, organization name, username and password are required"
}
```

### Duplicate User (409)
```json
{
  "error": "Username already exists"
}
```

or

```json
{
  "error": "An account with this email already exists"
}
```

### Service Unavailable (503)
```json
{
  "error": "Failed to connect to project activation service",
  "details": "Connection timeout"
}
```

### System Unavailable (503)
```json
{
  "error": "System is currently unavailable for new signups"
}
```

### User Master Registration Failed (400)
```json
{
  "error": "Failed to register user in central system"
}
```

## Product Access Configuration
The User Master API call sets product access flags:
- **melone_stay:** `true` (enabled for this application)
- **All other products:** `false` (disabled)

This ensures users are only registered for the Melone Stay application.

## Database Schema
The AdminAccount model stores:
- `client_id`: Email address
- `customer_name`: Organization name
- `license_key`: License key from Project API
- `package`: Package type (e.g., "Platinum")
- `module_name`: Module name (e.g., "Melone Stay")
- `expiry_date`: License expiry date
- `status`: Account status (e.g., "Active")
- `username`: Login username
- `password`: Hashed password
- `created_at`: Timestamp

**Table Name:** `melonestay_adminaccount`

## Frontend Integration
The SignupPage component collects data through a 4-step wizard:
1. **Step 1:** Google sign-in (collects email, username, password)
2. **Step 2:** Company details (organization, city, country, phone, address)
3. **Step 3:** Plan selection (Platinum plan)
4. **Step 4:** Done (shows credentials and completion)

When user clicks "Create free account" in Step 3, all APIs are called in sequence.

## Security Notes
- Password is hashed using Django's `make_password()` before storage
- JWT token is issued upon successful signup
- All API calls include proper error handling and timeouts
- Transaction atomicity ensures data consistency

## Configuration
API URLs and timeouts are configured in `settings.py`:
```python
SUPERUSER_API_URL = "https://su.myimc.in/api/superusers/endpoint/MELONESTAY/CYKOWV0Z/"
SUPERUSER_API_TIMEOUT = 5

PROJECT_API_URL = "https://activate.imcbs.com/mobileapp/api/project/melonestay/"
PROJECT_API_TIMEOUT = 2

USER_MASTER_API_URL = "https://centralmastermanagement.imcbs.com/api/user-master/"
USER_MASTER_API_TIMEOUT = 10
```
