"""
Simple test to verify /issues route integration.
"""
import requests

BASE_URL = "http://localhost:8000"

def test_issues_route():
    """Test the /issues route integration."""
    print("🧪 Testing /issues route integration...")
    
    try:
        # Test unauthenticated access (should redirect to login)
        response = requests.get(f"{BASE_URL}/issues")
        
        if response.status_code == 302:
            print("✅ Unauthenticated access properly redirects to login")
            return True
        elif response.status_code == 200:
            print("✅ Issues page loads successfully")
            if "工单管理" in response.text:
                print("✅ Page contains ticket management content")
                return True
            else:
                print("❌ Page doesn't contain expected content")
                return False
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

def test_admin_dashboard_links():
    """Test that admin dashboard has proper links."""
    print("🧪 Testing admin dashboard links...")
    
    try:
        response = requests.get(f"{BASE_URL}/admin/dashboard")
        
        if response.status_code == 302:
            print("✅ Admin dashboard properly requires authentication")
            return True
        elif response.status_code == 200:
            if '故障工单' in response.text and '/issues' in response.text:
                print("✅ Admin dashboard contains issues link")
                return True
            else:
                print("❌ Admin dashboard missing issues link")
                return False
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

def main():
    """Run integration tests."""
    print("🚀 Testing Issues Route Integration\n")
    
    tests = [
        test_issues_route,
        test_admin_dashboard_links
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()  # Empty line
        except Exception as e:
            print(f"❌ Test crashed: {str(e)}\n")
    
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 Issues integration successful!")
    else:
        print("⚠️  Some integration tests failed.")
    
    print("\n💡 Manual verification:")
    print(f"   1. Visit: {BASE_URL}/admin")
    print(f"   2. Login with admin credentials")
    print(f"   3. Click '故障工单' button")
    print(f"   4. Should see ticket management interface")
    print(f"   5. Direct access: {BASE_URL}/issues")

if __name__ == "__main__":
    main() 