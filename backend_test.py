import requests
import sys
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any

class ApartmentBookingAPITester:
    def __init__(self, base_url="https://14c9d617-f9ed-4416-9528-c716ba728f62.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.created_booking_id = None

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, data: Dict[Any, Any] = None) -> tuple:
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2, default=str)}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root endpoint"""
        return self.run_test("Root Endpoint", "GET", "", 200)

    def test_get_pricing(self):
        """Test getting pricing information"""
        success, response = self.run_test("Get Pricing", "GET", "api/pricing", 200)
        if success and 'base_rate' in response:
            expected_rate = 120.0
            actual_rate = response['base_rate']
            if actual_rate == expected_rate:
                print(f"   ✅ Base rate correct: €{actual_rate}")
                return True
            else:
                print(f"   ❌ Base rate mismatch: expected €{expected_rate}, got €{actual_rate}")
                return False
        return success

    def test_get_bookings(self):
        """Test getting all bookings"""
        success, response = self.run_test("Get All Bookings", "GET", "api/bookings", 200)
        if success:
            print(f"   📊 Found {len(response)} existing bookings")
        return success

    def test_create_booking(self):
        """Test creating a new booking"""
        # Use future dates to avoid conflicts
        check_in = (datetime.now() + timedelta(days=7)).date()
        check_out = (datetime.now() + timedelta(days=10)).date()
        nights = (check_out - check_in).days
        
        booking_data = {
            "name": "Jean Dupont",
            "email": "jean.dupont@test.com", 
            "phone": "0123456789",
            "guests": 2,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "nights": nights,
            "total_price": nights * 120.0,
            "arrival_time": "16:00 - 18:00",
            "special_requests": "Arrivée tardive prévue"
        }
        
        success, response = self.run_test("Create Booking", "POST", "api/bookings", 200, booking_data)
        if success and 'booking_id' in response:
            self.created_booking_id = response['booking_id']
            print(f"   ✅ Booking created with ID: {self.created_booking_id}")
            
            # Verify booking data
            if (response['name'] == booking_data['name'] and 
                response['email'] == booking_data['email'] and
                response['guests'] == booking_data['guests']):
                print(f"   ✅ Booking data verified correctly")
                return True
            else:
                print(f"   ❌ Booking data mismatch")
                return False
        return success

    def test_get_specific_booking(self):
        """Test getting a specific booking by ID"""
        if not self.created_booking_id:
            print("   ⚠️  Skipping - No booking ID available")
            return True
            
        success, response = self.run_test(
            "Get Specific Booking", 
            "GET", 
            f"api/bookings/{self.created_booking_id}", 
            200
        )
        
        if success and response.get('booking_id') == self.created_booking_id:
            print(f"   ✅ Retrieved booking matches created booking")
            return True
        return success

    def test_check_availability(self):
        """Test availability checking"""
        # Test available dates
        future_date1 = (datetime.now() + timedelta(days=30)).date()
        future_date2 = (datetime.now() + timedelta(days=33)).date()
        
        success, response = self.run_test(
            "Check Availability (Available Dates)", 
            "GET", 
            f"api/availability/{future_date1.isoformat()}/{future_date2.isoformat()}", 
            200
        )
        
        if success and response.get('available') == True:
            print(f"   ✅ Availability check working correctly")
            return True
        return success

    def test_date_conflict_prevention(self):
        """Test that overlapping bookings are prevented"""
        if not self.created_booking_id:
            print("   ⚠️  Skipping - No existing booking to conflict with")
            return True
            
        # Try to book overlapping dates
        check_in = (datetime.now() + timedelta(days=8)).date()  # Overlaps with existing booking
        check_out = (datetime.now() + timedelta(days=11)).date()
        nights = (check_out - check_in).days
        
        conflict_booking_data = {
            "name": "Marie Martin",
            "email": "marie.martin@test.com",
            "phone": "0987654321", 
            "guests": 1,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "nights": nights,
            "total_price": nights * 120.0,
            "arrival_time": "14:00 - 16:00",
            "special_requests": ""
        }
        
        success, response = self.run_test(
            "Create Conflicting Booking (Should Fail)", 
            "POST", 
            "api/bookings", 
            400,  # Expecting 400 Bad Request for conflict
            conflict_booking_data
        )
        
        if success:
            print(f"   ✅ Date conflict prevention working correctly")
            return True
        return False

    def test_cancel_booking(self):
        """Test cancelling a booking"""
        if not self.created_booking_id:
            print("   ⚠️  Skipping - No booking ID available")
            return True
            
        success, response = self.run_test(
            "Cancel Booking", 
            "PUT", 
            f"api/bookings/{self.created_booking_id}/cancel", 
            200
        )
        
        if success and 'message' in response:
            print(f"   ✅ Booking cancelled successfully")
            return True
        return success

    def test_invalid_booking_data(self):
        """Test validation with invalid booking data"""
        invalid_data = {
            "name": "",  # Empty name
            "email": "invalid-email",  # Invalid email
            "phone": "123",
            "guests": 10,  # Too many guests (max is 4)
            "check_in": "2024-01-01",
            "check_out": "2023-12-31",  # Check-out before check-in
            "nights": 1,
            "total_price": 120.0,
            "arrival_time": "16:00 - 18:00"
        }
        
        success, response = self.run_test(
            "Create Booking with Invalid Data (Should Fail)", 
            "POST", 
            "api/bookings", 
            422,  # Expecting validation error
            invalid_data
        )
        
        if success:
            print(f"   ✅ Input validation working correctly")
            return True
        return False

def main():
    print("🚀 Starting Apartment Booking API Tests")
    print("=" * 50)
    
    tester = ApartmentBookingAPITester()
    
    # Run all tests
    test_results = []
    
    test_results.append(tester.test_root_endpoint())
    test_results.append(tester.test_get_pricing())
    test_results.append(tester.test_get_bookings())
    test_results.append(tester.test_create_booking())
    test_results.append(tester.test_get_specific_booking())
    test_results.append(tester.test_check_availability())
    test_results.append(tester.test_date_conflict_prevention())
    test_results.append(tester.test_cancel_booking())
    test_results.append(tester.test_invalid_booking_data())
    
    # Print final results
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    print(f"Tests run: {tester.tests_run}")
    print(f"Tests passed: {tester.tests_passed}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())