# Melone Stay Signup Integration Guide

## Overview
This guide explains how to use and test the complete signup flow that integrates three external APIs with the Melone Stay application.

## Architecture

### Flow Diagram
```
User Submits Signup Form
          ↓
    Validate Input
          ↓
Check User Doesn't Exist
          ↓
Call Project Activation API ──→ Get license details
          ↓
Call Superuser API ──────────→ Verify system is active
          ↓
Call User Master API ─────────→ Register in central system
          ↓
Create Local Admin Account
          ↓
Return Success + JWT Token
```

## Setup Instructions

### Backend Setup

1. **Ensure all dependencies are installed:**
   ```bash
   cd MELONE_STAY_BACKEND
   pip install -r requirements.txt
   ```

2. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

3. **Start the Django development server:**
   ```bash
   python manage.py runserver
   ```

### Frontend Setup

1. **Install dependencies:**
   ```bash
   cd MELONE_STAY_FRONTEND
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm run dev
   ```

3. **Access the application:**
   Open browser to `http://localhost:5173`

## Using the Signup Flow

### Frontend UI Steps

1. **Step 1: Sign in with Google**
   - Click "Continue with Google" button
   - This populates email, username, and password
   - (Currently simulated - implement real Google OAuth in production)

2. **Step 2: Company Details**
   - Fill in Hotel/Organization Name (required)
   - Add City, Country, Phone Number, Address (optional)
   - Click "Continue"

3. **Step 3: Choose Plan**
   - Platinum plan is pre-selected
   - Click "Create free account"
   - System makes all API calls in the background

4. **Step 4: Done**
   - View your credentials
   - Copy login details
   - Click "Go to Login"

### Backend Processing

When user clicks "Create free account", the backend:

1. **Validates input data**
2. **Checks for existing users** (by username and email)
3. **Calls Project Activation API** to get license details
4. **Calls Superuser API** to verify system status
5. **Calls User Master API** to register user centrally
6. **Creates local admin account** in database
7. **Issues JWT token** for immediate login

## Testing

### Automated Testing

Run the test script:
```bash
cd MELONE_STAY_BACKEND
python test_signup_api.py
```

This tests:
- Complete signup flow
- External API connectivity
- Input validation
- Error handling

### Manual Testing

#### Test Case 1: Successful Signup
```bash
curl -X POST http://localhost:8000/api/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "organizationName": "Grand Hotel",
    "city": "Mumbai",
    "country": "India",
    "phoneNumber": "+91 9876543210",
    "address": "123 Main St, Mumbai",
    "username": "grandhotel",
    "password": "SecurePass123!"
  }'
```

**Expected Response (201):**
```json
{
  "success": true,
  "message": "Account created successfully",
  "admin": {
    "id": 1,
    "username": "grandhotel",
    "email": "newuser@example.com",
    "customer_name": "Grand Hotel",
    "package": "Platinum",
    "module_name": "Melone Stay",
    "expiry_date": "",
    "status": "Active"
  },
  "user_master_id": "USER123",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Test Case 2: Duplicate Username
```bash
curl -X POST http://localhost:8000/api/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "another@example.com",
    "organizationName": "Hotel",
    "username": "grandhotel",
    "password": "Pass123!"
  }'
```

**Expected Response (409):**
```json
{
  "error": "Username already exists"
}
```

#### Test Case 3: Missing Required Fields
```bash
curl -X POST http://localhost:8000/api/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser"
  }'
```

**Expected Response (400):**
```json
{
  "error": "Email, organization name, username and password are required"
}
```

## API Endpoints

### Signup Endpoint
- **URL:** `/api/signup/`
- **Method:** `POST`
- **Auth:** None (public endpoint)
- **Content-Type:** `application/json`

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | User's email (used as client_id) |
| organizationName | string | Yes | Hotel/Organization name |
| username | string | Yes | Login username |
| password | string | Yes | Login password |
| city | string | No | City/location |
| country | string | No | Country |
| phoneNumber | string | No | Contact phone |
| address | string | No | Full address |

## External APIs

### 1. Project Activation API
- **URL:** `https://activate.imcbs.com/mobileapp/api/project/melonestay/`
- **Method:** `GET`
- **Purpose:** Retrieve customer license information
- **Timeout:** 2 seconds

### 2. Superuser API
- **URL:** `https://su.myimc.in/api/superusers/endpoint/MELONESTAY/CYKOWV0Z/`
- **Method:** `GET`
- **Purpose:** Verify system is active for signups
- **Timeout:** 5 seconds

### 3. User Master API
- **URL:** `https://centralmastermanagement.imcbs.com/api/user-master/`
- **Method:** `POST`
- **Purpose:** Register user in central management system
- **Timeout:** 10 seconds

## Logging

Signup operations are logged to:
- **Console:** Real-time logs during development
- **File:** `MELONE_STAY_BACKEND/signup.log`

Log levels:
- `INFO`: Successful operations
- `WARNING`: Validation failures, duplicate users
- `ERROR`: API failures, invalid responses
- `DEBUG`: API call details (when DEBUG=True)

View logs:
```bash
tail -f signup.log
```

## Error Handling

### Client Errors (4xx)

| Status | Error | Description |
|--------|-------|-------------|
| 400 | Invalid request body | JSON parsing failed |
| 400 | Missing required fields | Email, org name, username, or password missing |
| 409 | Username already exists | Username is taken |
| 409 | Email already exists | Account with this email exists |

### Server Errors (5xx)

| Status | Error | Description |
|--------|-------|-------------|
| 502 | Project API error | Project activation service failed |
| 503 | Service unavailable | External API timeout or connection error |
| 503 | System unavailable | Superuser API returned inactive status |
| 500 | Failed to create account | Database error |

## Security Considerations

1. **Password Hashing:** All passwords are hashed using Django's `make_password()` before storage
2. **JWT Tokens:** Secure tokens issued for authentication
3. **Transaction Safety:** Database operations wrapped in atomic transactions
4. **Input Validation:** All inputs sanitized and validated
5. **CORS Configuration:** Only allowed origins can access the API

## Database Schema

The signup creates a record in the `melonestay_adminaccount` table:

```sql
CREATE TABLE melonestay_adminaccount (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(50),           -- Email address
    customer_name VARCHAR(200),      -- Organization name
    license_key VARCHAR(50),         -- From Project API
    package VARCHAR(50),             -- "Platinum"
    module_name VARCHAR(200),        -- "Melone Stay"
    expiry_date VARCHAR(20),         -- License expiry
    status VARCHAR(20),              -- "Active"
    username VARCHAR(150) UNIQUE,    -- Login username
    password VARCHAR(200),           -- Hashed password
    created_at TIMESTAMP            -- Auto timestamp
);
```

## Configuration

All API URLs and timeouts are in `settings.py`:

```python
# Project Activation API
PROJECT_API_URL = "https://activate.imcbs.com/mobileapp/api/project/melonestay/"
PROJECT_API_TIMEOUT = 2

# Superuser API  
SUPERUSER_API_URL = "https://su.myimc.in/api/superusers/endpoint/MELONESTAY/CYKOWV0Z/"
SUPERUSER_API_TIMEOUT = 5

# User Master API
USER_MASTER_API_URL = "https://centralmastermanagement.imcbs.com/api/user-master/"
USER_MASTER_API_TIMEOUT = 10
```

## Troubleshooting

### Issue: "Failed to connect to project activation service"
**Solution:** 
- Check internet connectivity
- Verify Project API URL is correct
- Check if Project API is up and running

### Issue: "Username already exists"
**Solution:**
- Choose a different username
- Or delete the existing user from database

### Issue: "System is currently unavailable for new signups"
**Solution:**
- Contact system administrator
- Check Superuser API status

### Issue: Frontend can't reach backend
**Solution:**
- Ensure Django server is running on port 8000
- Check CORS settings in `settings.py`
- Verify Vite proxy configuration

## Production Deployment

### Before deploying to production:

1. **Enable Real Google OAuth:**
   - Set up Google OAuth 2.0 credentials
   - Implement proper OAuth flow in frontend
   - Securely handle OAuth tokens

2. **Update Settings:**
   - Change `DEBUG = False`
   - Set proper `SECRET_KEY`
   - Configure `ALLOWED_HOSTS`
   - Use production database

3. **Security:**
   - Enable HTTPS
   - Set up proper CORS origins
   - Use environment variables for secrets
   - Enable rate limiting

4. **Monitoring:**
   - Set up error tracking (e.g., Sentry)
   - Configure production logging
   - Monitor API response times
   - Set up alerts for failures

## Support

For issues or questions:
- Check logs in `signup.log`
- Review API documentation
- Contact system administrator

## Version History

- **v1.0.0** - Initial implementation
  - Google Authentication integration
  - Three external API integrations
  - Complete signup flow
  - Error handling and logging
