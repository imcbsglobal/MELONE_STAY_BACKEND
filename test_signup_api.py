#!/usr/bin/env python
"""
Test script for Signup API Integration
Run this to test the signup endpoint and external API integrations
"""

import json
import requests

BASE_URL = "http://localhost:8000"

def test_signup():
    """Test the complete signup flow"""
    
    print("=" * 60)
    print("Testing Melone Stay Signup API Integration")
    print("=" * 60)
    
    # Test data
    signup_data = {
        "email": "test@example.com",
        "organizationName": "Test Hotel",
        "city": "Mumbai",
        "country": "India",
        "phoneNumber": "+91 9876543210",
        "address": "123 Test Street, Mumbai",
        "username": "testhotel",
        "password": "TestPass123!"
    }
    
    print("\n1. Testing Signup Endpoint")
    print("-" * 60)
    print(f"URL: {BASE_URL}/api/signup/")
    print(f"Data: {json.dumps(signup_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/signup/",
            json=signup_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201 or response.status_code == 200:
            print("\n✓ Signup successful!")
            data = response.json()
            if data.get("success"):
                print(f"  - Admin ID: {data['admin']['id']}")
                print(f"  - Username: {data['admin']['username']}")
                print(f"  - Email: {data['admin']['email']}")
                print(f"  - Package: {data['admin']['package']}")
                print(f"  - Token: {data['token'][:50]}...")
        elif response.status_code == 409:
            print("\n⚠ User already exists - this is expected if running test multiple times")
        else:
            print("\n✗ Signup failed")
            
    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Could not connect to the server.")
        print("  Make sure Django server is running on port 8000")
        print("  Run: python manage.py runserver")
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
    
    print("\n" + "=" * 60)


def test_external_apis():
    """Test connectivity to external APIs"""
    
    print("\n2. Testing External API Connectivity")
    print("-" * 60)
    
    apis = [
        {
            "name": "Project Activation API",
            "url": "https://activate.imcbs.com/mobileapp/api/project/melonestay/",
            "method": "GET"
        },
        {
            "name": "Superuser API",
            "url": "https://su.myimc.in/api/superusers/endpoint/MELONESTAY/CYKOWV0Z/",
            "method": "GET"
        },
        {
            "name": "User Master API",
            "url": "https://centralmastermanagement.imcbs.com/api/user-master/",
            "method": "POST"
        }
    ]
    
    for api in apis:
        print(f"\nTesting: {api['name']}")
        print(f"URL: {api['url']}")
        try:
            if api['method'] == 'GET':
                response = requests.get(api['url'], timeout=10)
            else:
                # For POST, just test connectivity with minimal data
                response = requests.post(
                    api['url'],
                    json={"test": "connectivity"},
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
            print(f"Status: {response.status_code} - ✓ Reachable")
        except requests.exceptions.Timeout:
            print("Status: Timeout - ⚠ API is slow or unreachable")
        except requests.exceptions.ConnectionError:
            print("Status: Connection Error - ✗ Cannot connect")
        except Exception as e:
            print(f"Status: Error - {str(e)}")
    
    print("\n" + "=" * 60)


def test_validation():
    """Test validation errors"""
    
    print("\n3. Testing Validation")
    print("-" * 60)
    
    test_cases = [
        {
            "name": "Missing email",
            "data": {
                "organizationName": "Test Hotel",
                "username": "testuser",
                "password": "pass123"
            }
        },
        {
            "name": "Missing organization name",
            "data": {
                "email": "test@example.com",
                "username": "testuser",
                "password": "pass123"
            }
        },
        {
            "name": "Missing username",
            "data": {
                "email": "test@example.com",
                "organizationName": "Test Hotel",
                "password": "pass123"
            }
        },
        {
            "name": "Missing password",
            "data": {
                "email": "test@example.com",
                "organizationName": "Test Hotel",
                "username": "testuser"
            }
        }
    ]
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        try:
            response = requests.post(
                f"{BASE_URL}/api/signup/",
                json=test['data'],
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 400:
                print(f"✓ Validation working: {response.json().get('error')}")
            else:
                print(f"⚠ Unexpected status: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("✗ Server not running")
            break
        except Exception as e:
            print(f"✗ Error: {str(e)}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("\nMake sure Django server is running: python manage.py runserver\n")
    
    # Run tests
    test_signup()
    test_external_apis()
    test_validation()
    
    print("\n✓ Testing completed!")
