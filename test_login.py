#!/usr/bin/env python3
"""
Test script to verify login endpoint is working
Run this after starting Flask with: python frontend.py
"""

import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:5000"

def test_login(username, password):
    """Test login endpoint"""
    url = f"{BASE_URL}/api/login"
    data = json.dumps({"username": username, "password": password}).encode()
    
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print(f"✅ Login successful: {username}")
            print(f"   Token: {result['token'][:20]}...")
            return True
    except urllib.error.HTTPError as e:
        error_data = json.loads(e.read().decode())
        print(f"❌ Login failed for {username}: {error_data['error']}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing SignalMine Login Endpoint")
    print("=" * 50)
    
    # Test valid credentials
    test_login("admin", "password123")
    test_login("user", "user123")
    test_login("demo", "demo")
    
    print()
    
    # Test invalid credentials
    test_login("admin", "wrongpassword")
    test_login("nonexistent", "password123")
    
    print("\n" + "=" * 50)
    print("Test complete!")
