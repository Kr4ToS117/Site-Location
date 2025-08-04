import requests
import sys
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any

class ExtendedApartmentBookingAPITester:
    def __init__(self, base_url="https://16606a58-6aec-4f49-9b4b-f7e04f0ceb1e.preview.emergentagent.com"):
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

    def test_pricing_configuration(self):
        """Test getting pricing configuration with fixed fees"""
        success, response = self.run_test("Get Pricing Configuration", "GET", "api/pricing/configuration", 200)
        if success:
            # Verify expected configuration values
            expected_cleaning_fee = 45.0
            expected_security_deposit = 600.0
            expected_min_rate = 140.0
            expected_max_rate = 280.0
            
            if (response.get('cleaning_fee') == expected_cleaning_fee and
                response.get('security_deposit') == expected_security_deposit and
                response.get('min_rate') == expected_min_rate and
                response.get('max_rate') == expected_max_rate):
                print(f"   ✅ Pricing configuration correct: Cleaning €{expected_cleaning_fee}, Deposit €{expected_security_deposit}, Rate €{expected_min_rate}-€{expected_max_rate}")
                return True
            else:
                print(f"   ❌ Pricing configuration mismatch")
                return False
        return success

    def test_pricing_for_dates(self):
        """Test getting pricing for specific date range"""
        # Use future dates
        check_in = (datetime.now() + timedelta(days=7)).date()
        check_out = (datetime.now() + timedelta(days=10)).date()
        
        success, response = self.run_test(
            "Get Pricing for Date Range", 
            "GET", 
            f"api/pricing/dates/{check_in.isoformat()}/{check_out.isoformat()}", 
            200
        )
        
        if success:
            # Verify pricing calculation
            nights = response.get('nights', 0)
            avg_rate = response.get('avg_nightly_rate', 0)
            subtotal = response.get('subtotal', 0)
            cleaning_fee = response.get('cleaning_fee', 0)
            security_deposit = response.get('security_deposit', 0)
            total = response.get('total_price', 0)
            
            expected_nights = (check_out - check_in).days
            expected_subtotal = nights * avg_rate
            expected_total = expected_subtotal + cleaning_fee + security_deposit
            
            if (nights == expected_nights and 
                abs(subtotal - expected_subtotal) < 0.01 and
                cleaning_fee == 45.0 and
                security_deposit == 600.0 and
                abs(total - expected_total) < 0.01):
                print(f"   ✅ Pricing calculation correct: {nights} nights × €{avg_rate} + €{cleaning_fee} + €{security_deposit} = €{total}")
                return True
            else:
                print(f"   ❌ Pricing calculation incorrect")
                return False
        return success

    def test_set_dynamic_pricing(self):
        """Test setting custom pricing for specific dates"""
        # Set custom pricing for future dates
        future_date = (datetime.now() + timedelta(days=15)).date()
        custom_rate = 200.0
        
        pricing_data = [
            {
                "date": future_date.isoformat(),
                "rate": custom_rate
            }
        ]
        
        success, response = self.run_test(
            "Set Dynamic Pricing", 
            "POST", 
            "api/pricing/dates", 
            200,
            pricing_data
        )
        
        if success and "message" in response:
            print(f"   ✅ Dynamic pricing set successfully")
            
            # Verify the pricing was set by getting pricing for that date
            check_out = future_date + timedelta(days=1)
            verify_success, verify_response = self.run_test(
                "Verify Dynamic Pricing", 
                "GET", 
                f"api/pricing/dates/{future_date.isoformat()}/{check_out.isoformat()}", 
                200
            )
            
            if verify_success and abs(verify_response.get('avg_nightly_rate', 0) - custom_rate) < 0.01:
                print(f"   ✅ Dynamic pricing verification successful: €{custom_rate}")
                return True
            else:
                print(f"   ❌ Dynamic pricing verification failed")
                return False
        return success

    def test_get_bookings(self):
        """Test getting all bookings"""
        success, response = self.run_test("Get All Bookings", "GET", "api/bookings", 200)
        if success:
            print(f"   📊 Found {len(response)} existing bookings")
        return success

    def test_create_extended_booking(self):
        """Test creating a booking with all new extended fields"""
        # Use future dates to avoid conflicts
        check_in = (datetime.now() + timedelta(days=20)).date()
        check_out = (datetime.now() + timedelta(days=23)).date()
        nights = (check_out - check_in).days
        
        # Calculate pricing first
        pricing_success, pricing_response = self.run_test(
            "Get Pricing for Extended Booking", 
            "GET", 
            f"api/pricing/dates/{check_in.isoformat()}/{check_out.isoformat()}", 
            200
        )
        
        if not pricing_success:
            print("   ❌ Failed to get pricing for booking")
            return False
        
        avg_rate = pricing_response.get('avg_nightly_rate', 140.0)
        subtotal = pricing_response.get('subtotal', nights * avg_rate)
        cleaning_fee = pricing_response.get('cleaning_fee', 45.0)
        security_deposit = pricing_response.get('security_deposit', 600.0)
        total_price = pricing_response.get('total_price', subtotal + cleaning_fee + security_deposit)
        
        # Extended booking data with all new fields
        booking_data = {
            "first_name": "Sophie",
            "last_name": "Dubois",
            "email": "sophie.dubois@example.com", 
            "phone": "+33123456789",
            "address": "123 Rue de la Paix, 75001 Paris, France",
            "guests": 2,
            "pets_allowed": True,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "nights": nights,
            "nightly_rate": avg_rate,
            "subtotal": subtotal,
            "cleaning_fee": cleaning_fee,
            "security_deposit": security_deposit,
            "total_price": total_price,
            "arrival_time": "16:00 - 18:00",
            "special_requests": "Traveling with a small dog, please provide pet amenities"
        }
        
        success, response = self.run_test("Create Extended Booking", "POST", "api/bookings", 200, booking_data)
        if success and 'booking_id' in response:
            self.created_booking_id = response['booking_id']
            print(f"   ✅ Extended booking created with ID: {self.created_booking_id}")
            
            # Verify all new fields are present and correct
            if (response['first_name'] == booking_data['first_name'] and 
                response['last_name'] == booking_data['last_name'] and
                response['address'] == booking_data['address'] and
                response['pets_allowed'] == booking_data['pets_allowed'] and
                response['status'] == 'pending_payment' and
                response['cleaning_fee'] == cleaning_fee and
                response['security_deposit'] == security_deposit):
                print(f"   ✅ All extended booking fields verified correctly")
                print(f"   ✅ Status correctly set to 'pending_payment'")
                return True
            else:
                print(f"   ❌ Extended booking field verification failed")
                return False
        return success

    def test_create_booking_without_pets(self):
        """Test creating a booking with pets_allowed=false"""
        # Use different future dates
        check_in = (datetime.now() + timedelta(days=25)).date()
        check_out = (datetime.now() + timedelta(days=27)).date()
        nights = (check_out - check_in).days
        
        booking_data = {
            "first_name": "Pierre",
            "last_name": "Martin",
            "email": "pierre.martin@example.com", 
            "phone": "+33987654321",
            "address": "456 Avenue des Champs, 75008 Paris, France",
            "guests": 1,
            "pets_allowed": False,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "nights": nights,
            "nightly_rate": 140.0,
            "subtotal": nights * 140.0,
            "cleaning_fee": 45.0,
            "security_deposit": 600.0,
            "total_price": (nights * 140.0) + 45.0 + 600.0,
            "arrival_time": "14:00 - 16:00",
            "special_requests": ""
        }
        
        success, response = self.run_test("Create Booking Without Pets", "POST", "api/bookings", 200, booking_data)
        if success and response.get('pets_allowed') == False:
            print(f"   ✅ Booking without pets created successfully")
            return True
        return success

    def test_get_specific_extended_booking(self):
        """Test getting a specific booking with extended fields"""
        if not self.created_booking_id:
            print("   ⚠️  Skipping - No booking ID available")
            return True
            
        success, response = self.run_test(
            "Get Specific Extended Booking", 
            "GET", 
            f"api/bookings/{self.created_booking_id}", 
            200
        )
        
        if success and response.get('booking_id') == self.created_booking_id:
            # Verify extended fields are present
            required_fields = ['first_name', 'last_name', 'address', 'pets_allowed', 'cleaning_fee', 'security_deposit']
            missing_fields = [field for field in required_fields if field not in response]
            
            if not missing_fields:
                print(f"   ✅ All extended fields present in retrieved booking")
                return True
            else:
                print(f"   ❌ Missing extended fields: {missing_fields}")
                return False
        return success

    def test_check_availability(self):
        """Test availability checking still works"""
        # Test available dates
        future_date1 = (datetime.now() + timedelta(days=30)).date()
        future_date2 = (datetime.now() + timedelta(days=33)).date()
        
        success, response = self.run_test(
            "Check Availability", 
            "GET", 
            f"api/availability/{future_date1.isoformat()}/{future_date2.isoformat()}", 
            200
        )
        
        if success and response.get('available') == True:
            print(f"   ✅ Availability check working correctly")
            return True
        return success

    def test_invalid_extended_booking_data(self):
        """Test validation with invalid extended booking data"""
        invalid_data = {
            "first_name": "",  # Empty first name
            "last_name": "",   # Empty last name
            "email": "invalid-email",  # Invalid email
            "phone": "123",
            "address": "",     # Empty address
            "guests": 10,      # Too many guests (max is 4)
            "pets_allowed": "not_boolean",  # Invalid boolean
            "check_in": "2024-01-01",
            "check_out": "2023-12-31",  # Check-out before check-in
            "nights": 1,
            "nightly_rate": 140.0,
            "subtotal": 140.0,
            "cleaning_fee": 45.0,
            "security_deposit": 600.0,
            "total_price": 785.0,
            "arrival_time": "16:00 - 18:00"
        }
        
        success, response = self.run_test(
            "Create Extended Booking with Invalid Data (Should Fail)", 
            "POST", 
            "api/bookings", 
            422,  # Expecting validation error
            invalid_data
        )
        
        if success:
            print(f"   ✅ Extended input validation working correctly")
            return True
        return False

def main():
    print("🚀 Starting Extended Apartment Booking API Tests")
    print("=" * 60)
    print("Testing new features:")
    print("- Extended booking model with new fields")
    print("- Dynamic pricing by dates")
    print("- Fixed fees calculation (cleaning + security deposit)")
    print("=" * 60)
    
    tester = ExtendedApartmentBookingAPITester()
    
    # Run all tests
    test_results = []
    
    test_results.append(tester.test_root_endpoint())
    test_results.append(tester.test_pricing_configuration())
    test_results.append(tester.test_pricing_for_dates())
    test_results.append(tester.test_set_dynamic_pricing())
    test_results.append(tester.test_get_bookings())
    test_results.append(tester.test_create_extended_booking())
    test_results.append(tester.test_create_booking_without_pets())
    test_results.append(tester.test_get_specific_extended_booking())
    test_results.append(tester.test_check_availability())
    test_results.append(tester.test_invalid_extended_booking_data())
    
    # Print final results
    print("\n" + "=" * 60)
    print("📊 EXTENDED BOOKING API TEST RESULTS")
    print("=" * 60)
    print(f"Tests run: {tester.tests_run}")
    print(f"Tests passed: {tester.tests_passed}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All extended booking tests passed!")
        return 0
    else:
        print("❌ Some extended booking tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())