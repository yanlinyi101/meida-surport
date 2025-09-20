"""
Simple test script for tickets API endpoints.
"""
import requests
import json
from datetime import date, time, datetime

BASE_URL = "http://localhost:8000"

def test_public_booking():
    """Test public booking endpoint."""
    print("🧪 Testing public booking...")
    
    booking_data = {
        "name": "测试用户",
        "phone": "13800138000",
        "address": "测试地址123号",
        "date": str(date.today()),
        "time": "14:00",
        "issue": "测试问题描述"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/public/booking",
            json=booking_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Booking successful: {result['message']}")
            print(f"   Ticket ID: {result.get('booking_id', 'N/A')}")
            return True
        else:
            print(f"❌ Booking failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Booking error: {str(e)}")
        return False


def test_health_endpoint():
    """Test health endpoint."""
    print("🧪 Testing health endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Health check passed: {result['status']}")
            print(f"   Service: {result['service']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        return False


def test_tickets_list_unauthorized():
    """Test tickets list without authentication."""
    print("🧪 Testing tickets list (unauthorized)...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/tickets")
        
        if response.status_code == 401:
            print("✅ Unauthorized access properly blocked")
            return True
        else:
            print(f"❌ Expected 401, got: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        return False


def test_file_upload_unauthorized():
    """Test file upload without authentication."""
    print("🧪 Testing file upload (unauthorized)...")
    
    try:
        # Create a dummy file
        files = {'file': ('test.jpg', b'fake image content', 'image/jpeg')}
        response = requests.post(
            f"{BASE_URL}/api/tickets/dummy-id/images",
            files=files
        )
        
        if response.status_code == 401:
            print("✅ Unauthorized file upload properly blocked")
            return True
        else:
            print(f"❌ Expected 401, got: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        return False


def main():
    """Run all tests."""
    print("🚀 Running Tickets API Tests...\n")
    
    tests = [
        test_health_endpoint,
        test_public_booking,
        test_tickets_list_unauthorized,
        test_file_upload_unauthorized
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
        print()  # Empty line between tests
    
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    
    print("\n💡 Next steps:")
    print("   1. Run: python -m backend.scripts.seed_tickets")
    print("   2. Login to admin panel: http://localhost:8000/admin")
    print("   3. View tickets: http://localhost:8000/admin/tickets")


if __name__ == "__main__":
    main() 