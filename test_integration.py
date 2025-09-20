"""
End-to-end integration test for the complete ticket workflow.
Tests the full journey: booking → confirm → assign → upload → complete
"""
import requests
import json
import time
from datetime import date, datetime

BASE_URL = "http://localhost:8000"

class TicketWorkflowTest:
    def __init__(self):
        self.session = requests.Session()
        self.ticket_id = None
        self.admin_cookies = None

    def test_1_public_booking(self):
        """Step 1: Create a new booking (public endpoint)"""
        print("🎫 Step 1: Creating public booking...")
        
        booking_data = {
            "name": "集成测试用户",
            "phone": "13900000000", 
            "address": "测试地址456号",
            "date": str(date.today()),
            "time": "15:30",
            "issue": "集成测试问题描述 - 需要检修设备"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/public/booking",
            json=booking_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Booking created successfully")
            print(f"   Message: {result['message']}")
            print(f"   Booking ID: {result['booking_id']}")
            return True
        else:
            print(f"❌ Booking failed: {response.status_code} - {response.text}")
            return False

    def test_2_admin_login(self):
        """Step 2: Login as admin to get authentication cookies"""
        print("\n🔐 Step 2: Admin login...")
        
        # First get the login page to establish session
        response = self.session.get(f"{BASE_URL}/admin")
        
        # Login with admin credentials
        login_data = {
            "email": "admin@example.com",  # Default admin email
            "password": "admin123"  # Default admin password
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json=login_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Admin login successful")
            print(f"   User: {result.get('username', 'Unknown')}")
            self.admin_cookies = self.session.cookies
            return True
        else:
            print(f"❌ Admin login failed: {response.status_code} - {response.text}")
            return False

    def test_3_list_tickets(self):
        """Step 3: List tickets and find our test ticket"""
        print("\n📋 Step 3: Listing tickets...")
        
        response = self.session.get(
            f"{BASE_URL}/api/tickets?q=集成测试用户"
        )
        
        if response.status_code == 200:
            result = response.json()
            tickets = result.get('tickets', [])
            
            if tickets:
                self.ticket_id = tickets[0]['id']
                print(f"✅ Found test ticket")
                print(f"   Ticket ID: {self.ticket_id}")
                print(f"   Status: {tickets[0]['status']}")
                print(f"   Customer: {tickets[0]['customer_name']}")
                return True
            else:
                print("❌ Test ticket not found")
                return False
        else:
            print(f"❌ Failed to list tickets: {response.status_code} - {response.text}")
            return False

    def test_4_confirm_ticket(self):
        """Step 4: Confirm the ticket"""
        print("\n✅ Step 4: Confirming ticket...")
        
        if not self.ticket_id:
            print("❌ No ticket ID available")
            return False
        
        response = self.session.post(
            f"{BASE_URL}/api/tickets/{self.ticket_id}/confirm"
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ticket confirmed successfully")
            print(f"   Status: {result['status']}")
            return True
        else:
            print(f"❌ Ticket confirmation failed: {response.status_code} - {response.text}")
            return False

    def test_5_assign_technician(self):
        """Step 5: Auto-assign technician to ticket"""
        print("\n👨‍🔧 Step 5: Auto-assigning technician...")
        
        if not self.ticket_id:
            print("❌ No ticket ID available")
            return False
        
        assign_data = {
            "auto": True,
            "version": 1,
            "note": "集成测试自动分配"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/tickets/{self.ticket_id}/assign",
            json=assign_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Technician assigned successfully")
            print(f"   Status: {result['status']}")
            print(f"   Technician: {result['technician']['name']}")
            print(f"   Version: {result['version']}")
            return True
        else:
            print(f"❌ Technician assignment failed: {response.status_code} - {response.text}")
            return False

    def test_6_upload_receipt(self):
        """Step 6: Upload a mock receipt image"""
        print("\n📷 Step 6: Uploading receipt image...")
        
        if not self.ticket_id:
            print("❌ No ticket ID available")
            return False
        
        # Create a mock image file
        mock_image_content = b"Mock image content for integration test"
        files = {
            'file': ('integration_test_receipt.jpg', mock_image_content, 'image/jpeg')
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/tickets/{self.ticket_id}/images",
            files=files
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Receipt uploaded successfully")
            print(f"   Image ID: {result['image']['id']}")
            print(f"   File name: {result['image']['file_name']}")
            print(f"   Size: {result['image']['size_bytes']} bytes")
            return True
        else:
            print(f"❌ Receipt upload failed: {response.status_code} - {response.text}")
            return False

    def test_7_complete_ticket(self):
        """Step 7: Complete the ticket"""
        print("\n🏁 Step 7: Completing ticket...")
        
        if not self.ticket_id:
            print("❌ No ticket ID available")
            return False
        
        response = self.session.post(
            f"{BASE_URL}/api/tickets/{self.ticket_id}/complete"
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ticket completed successfully")
            print(f"   Status: {result['status']}")
            return True
        else:
            print(f"❌ Ticket completion failed: {response.status_code} - {response.text}")
            return False

    def test_8_verify_final_state(self):
        """Step 8: Verify the final ticket state"""
        print("\n🔍 Step 8: Verifying final ticket state...")
        
        if not self.ticket_id:
            print("❌ No ticket ID available")
            return False
        
        response = self.session.get(
            f"{BASE_URL}/api/tickets/{self.ticket_id}"
        )
        
        if response.status_code == 200:
            ticket = response.json()
            print(f"✅ Final ticket state verified")
            print(f"   Status: {ticket['status']}")
            print(f"   Customer: {ticket['customer_name']}")
            print(f"   Technician: {ticket.get('technician', {}).get('name', 'None')}")
            print(f"   Images: {len(ticket.get('images', []))}")
            print(f"   Events: {len(ticket.get('events', []))}")
            print(f"   Completed at: {ticket.get('completed_at', 'None')}")
            
            # Verify expected state
            expected_checks = [
                (ticket['status'] == 'COMPLETED', "Status should be COMPLETED"),
                (ticket['customer_name'] == '集成测试用户', "Customer name should match"),
                (len(ticket.get('images', [])) >= 1, "Should have at least one image"),
                (len(ticket.get('events', [])) >= 4, "Should have multiple events"),
                (ticket.get('completed_at') is not None, "Should have completion time"),
                (ticket.get('technician') is not None, "Should have assigned technician")
            ]
            
            all_passed = True
            for check, description in expected_checks:
                if check:
                    print(f"   ✅ {description}")
                else:
                    print(f"   ❌ {description}")
                    all_passed = False
            
            return all_passed
        else:
            print(f"❌ Failed to get final ticket state: {response.status_code} - {response.text}")
            return False

    def run_full_workflow(self):
        """Run the complete workflow test"""
        print("🚀 Starting End-to-End Ticket Workflow Test")
        print("=" * 60)
        
        test_steps = [
            self.test_1_public_booking,
            self.test_2_admin_login,
            self.test_3_list_tickets,
            self.test_4_confirm_ticket,
            self.test_5_assign_technician,
            self.test_6_upload_receipt,
            self.test_7_complete_ticket,
            self.test_8_verify_final_state
        ]
        
        passed = 0
        total = len(test_steps)
        
        for i, test_step in enumerate(test_steps, 1):
            try:
                if test_step():
                    passed += 1
                else:
                    print(f"\n❌ Test step {i} failed. Stopping workflow test.")
                    break
                    
                # Small delay between steps
                if i < total:
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"\n💥 Test step {i} crashed: {str(e)}")
                break
        
        print("\n" + "=" * 60)
        print(f"📊 Workflow Test Results: {passed}/{total} steps passed")
        
        if passed == total:
            print("🎉 Complete workflow test PASSED!")
            print("✨ The ticket management system is working correctly!")
        else:
            print("⚠️  Workflow test FAILED at some steps.")
            print("🔧 Please check the errors above and fix the issues.")
        
        print("\n💡 Manual verification:")
        print(f"   - Check admin panel: {BASE_URL}/admin/tickets")
        print(f"   - Look for ticket: 集成测试用户")
        if self.ticket_id:
            print(f"   - Ticket ID: {self.ticket_id}")
        
        return passed == total


def main():
    """Main test runner"""
    print("🧪 Integration Test Suite for Ticket Management System")
    print(f"🌐 Testing against: {BASE_URL}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Server health check failed: {response.status_code}")
            return
        print("✅ Server is running and healthy")
        print()
    except Exception as e:
        print(f"❌ Cannot connect to server: {str(e)}")
        print("💡 Make sure the server is running: python -m backend.app.main")
        return
    
    # Run the workflow test
    test_runner = TicketWorkflowTest()
    success = test_runner.run_full_workflow()
    
    print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success:
        print("\n🎯 All tests passed! The system is ready for production.")
    else:
        print("\n🚨 Some tests failed. Please review and fix the issues.")


if __name__ == "__main__":
    main() 