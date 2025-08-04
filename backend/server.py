from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict
from datetime import datetime, date
import pymongo
import os
import uuid
from bson import ObjectId

# Environment variables
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/apartment_booking')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'placeholder_stripe_secret_key')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'placeholder_stripe_publishable_key')

# MongoDB connection
client = pymongo.MongoClient(MONGO_URL)
db = client.apartment_booking

app = FastAPI(title="Apartment Booking API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class BookingCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    address: str
    guests: int
    pets_allowed: bool
    check_in: date
    check_out: date
    nights: int
    nightly_rate: float
    subtotal: float
    cleaning_fee: float
    security_deposit: float
    total_price: float
    arrival_time: str
    special_requests: Optional[str] = ""

    @validator('guests')
    def validate_guests(cls, v):
        if v < 1 or v > 4:
            raise ValueError('Number of guests must be between 1 and 4')
        return v

    @validator('check_out')
    def validate_dates(cls, v, values):
        if 'check_in' in values and v <= values['check_in']:
            raise ValueError('Check-out date must be after check-in date')
        return v

class BookingResponse(BaseModel):
    booking_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    address: str
    guests: int
    pets_allowed: bool
    check_in: date
    check_out: date
    nights: int
    nightly_rate: float
    subtotal: float
    cleaning_fee: float
    security_deposit: float
    total_price: float
    arrival_time: str
    special_requests: str
    status: str
    created_at: datetime

class PricingResponse(BaseModel):
    date: str
    rate: float
    available: bool

class DynamicPricing(BaseModel):
    date: str
    rate: float

class PricingConfiguration(BaseModel):
    cleaning_fee: float
    security_deposit: float
    default_rate: float
    min_rate: float
    max_rate: float

class PaymentIntent(BaseModel):
    amount: int
    currency: str = "eur"
    booking_id: str

# Constants
CLEANING_FEE = 45.0
SECURITY_DEPOSIT = 600.0
DEFAULT_RATE = 140.0
MIN_RATE = 140.0
MAX_RATE = 280.0

# Helper functions
def booking_dict_to_response(booking: dict) -> BookingResponse:
    """Convert booking document to response model"""
    check_in = booking['check_in']
    check_out = booking['check_out']
    
    if isinstance(check_in, str):
        check_in = datetime.fromisoformat(check_in).date()
    if isinstance(check_out, str):
        check_out = datetime.fromisoformat(check_out).date()
    
    return BookingResponse(
        booking_id=booking['booking_id'],
        first_name=booking['first_name'],
        last_name=booking['last_name'],
        email=booking['email'],
        phone=booking['phone'],
        address=booking['address'],
        guests=booking['guests'],
        pets_allowed=booking['pets_allowed'],
        check_in=check_in,
        check_out=check_out,
        nights=booking['nights'],
        nightly_rate=booking['nightly_rate'],
        subtotal=booking['subtotal'],
        cleaning_fee=booking['cleaning_fee'],
        security_deposit=booking['security_deposit'],
        total_price=booking['total_price'],
        arrival_time=booking['arrival_time'],
        special_requests=booking['special_requests'],
        status=booking['status'],
        created_at=booking['created_at']
    )

def get_rate_for_date(target_date: date) -> float:
    """Get rate for specific date from database or return default"""
    try:
        date_str = target_date.isoformat()
        pricing = db.dynamic_pricing.find_one({'date': date_str})
        if pricing:
            return pricing['rate']
        return DEFAULT_RATE
    except Exception:
        return DEFAULT_RATE

def check_date_availability(check_in: date, check_out: date) -> bool:
    """Check if dates are available for booking"""
    check_in_str = check_in.isoformat()
    check_out_str = check_out.isoformat()
    
    existing_bookings = db.bookings.find({
        'status': {'$ne': 'cancelled'},
        '$or': [
            {
                'check_in': {'$lt': check_out_str},
                'check_out': {'$gt': check_in_str}
            }
        ]
    })
    
    return list(existing_bookings) == []

def calculate_average_nightly_rate(check_in: date, check_out: date) -> float:
    """Calculate average nightly rate for date range"""
    total_rate = 0
    current_date = check_in
    nights = 0
    
    while current_date < check_out:
        rate = get_rate_for_date(current_date)
        total_rate += rate
        nights += 1
        current_date = date.fromordinal(current_date.toordinal() + 1)
    
    return total_rate / nights if nights > 0 else DEFAULT_RATE

# API Routes
@app.get("/")
async def root():
    return {"message": "Apartment Booking API is running"}

@app.get("/api/bookings", response_model=List[BookingResponse])
async def get_bookings():
    """Get all bookings"""
    try:
        bookings = list(db.bookings.find({'status': {'$ne': 'cancelled'}}).sort('created_at', -1))
        return [booking_dict_to_response(booking) for booking in bookings]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching bookings: {str(e)}")

@app.post("/api/bookings", response_model=BookingResponse)
async def create_booking(booking: BookingCreate):
    """Create a new booking"""
    try:
        # Check date availability
        if not check_date_availability(booking.check_in, booking.check_out):
            raise HTTPException(
                status_code=400, 
                detail="Les dates sélectionnées ne sont pas disponibles"
            )
        
        # Generate unique booking ID
        booking_id = str(uuid.uuid4())
        
        # Create booking document
        booking_doc = {
            'booking_id': booking_id,
            'first_name': booking.first_name,
            'last_name': booking.last_name,
            'email': booking.email,
            'phone': booking.phone,
            'address': booking.address,
            'guests': booking.guests,
            'pets_allowed': booking.pets_allowed,
            'check_in': booking.check_in.isoformat(),
            'check_out': booking.check_out.isoformat(),
            'nights': booking.nights,
            'nightly_rate': booking.nightly_rate,
            'subtotal': booking.subtotal,
            'cleaning_fee': booking.cleaning_fee,
            'security_deposit': booking.security_deposit,
            'total_price': booking.total_price,
            'arrival_time': booking.arrival_time,
            'special_requests': booking.special_requests,
            'status': 'pending_payment',
            'created_at': datetime.utcnow()
        }
        
        # Insert booking
        result = db.bookings.insert_one(booking_doc)
        
        if result.inserted_id:
            return booking_dict_to_response(booking_doc)
        else:
            raise HTTPException(status_code=500, detail="Failed to create booking")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating booking: {str(e)}")

@app.get("/api/bookings/{booking_id}", response_model=BookingResponse)
async def get_booking(booking_id: str):
    """Get a specific booking by ID"""
    try:
        booking = db.bookings.find_one({'booking_id': booking_id})
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        return booking_dict_to_response(booking)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching booking: {str(e)}")

@app.put("/api/bookings/{booking_id}/cancel")
async def cancel_booking(booking_id: str):
    """Cancel a booking"""
    try:
        result = db.bookings.update_one(
            {'booking_id': booking_id},
            {'$set': {'status': 'cancelled', 'cancelled_at': datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        return {"message": "Booking cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling booking: {str(e)}")

@app.get("/api/pricing/dates/{check_in}/{check_out}")
async def get_pricing_for_dates(check_in: str, check_out: str):
    """Get pricing information for date range"""
    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        
        if check_in_date >= check_out_date:
            raise HTTPException(status_code=400, detail="Check-out date must be after check-in date")
        
        # Calculate nights
        nights = (check_out_date - check_in_date).days
        
        # Get average nightly rate
        avg_nightly_rate = calculate_average_nightly_rate(check_in_date, check_out_date)
        
        # Calculate pricing breakdown
        subtotal = nights * avg_nightly_rate
        cleaning_fee = CLEANING_FEE
        security_deposit = SECURITY_DEPOSIT
        total = subtotal + cleaning_fee + security_deposit
        
        return {
            "check_in": check_in_date,
            "check_out": check_out_date,
            "nights": nights,
            "avg_nightly_rate": round(avg_nightly_rate, 2),
            "subtotal": round(subtotal, 2),
            "cleaning_fee": cleaning_fee,
            "security_deposit": security_deposit,
            "total_price": round(total, 2),
            "available": check_date_availability(check_in_date, check_out_date)
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating pricing: {str(e)}")

@app.get("/api/pricing/configuration")
async def get_pricing_configuration():
    """Get pricing configuration"""
    return {
        "cleaning_fee": CLEANING_FEE,
        "security_deposit": SECURITY_DEPOSIT,
        "default_rate": DEFAULT_RATE,
        "min_rate": MIN_RATE,
        "max_rate": MAX_RATE
    }

@app.post("/api/pricing/dates")
async def set_pricing_for_dates(pricing_data: List[DynamicPricing]):
    """Set custom pricing for specific dates"""
    try:
        for pricing in pricing_data:
            # Validate rate within bounds
            if pricing.rate < MIN_RATE or pricing.rate > MAX_RATE:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Rate must be between €{MIN_RATE} and €{MAX_RATE}"
                )
            
            # Upsert pricing for date
            db.dynamic_pricing.update_one(
                {'date': pricing.date},
                {
                    '$set': {
                        'date': pricing.date,
                        'rate': pricing.rate,
                        'updated_at': datetime.utcnow()
                    }
                },
                upsert=True
            )
        
        return {"message": f"Pricing updated for {len(pricing_data)} dates"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating pricing: {str(e)}")

@app.get("/api/availability/{check_in}/{check_out}")
async def check_availability(check_in: str, check_out: str):
    """Check if dates are available"""
    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        
        if check_in_date >= check_out_date:
            raise HTTPException(status_code=400, detail="Check-out date must be after check-in date")
        
        is_available = check_date_availability(check_in_date, check_out_date)
        
        return {
            "available": is_available,
            "check_in": check_in_date,
            "check_out": check_out_date
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking availability: {str(e)}")

# Stripe Payment Routes (Placeholder - will be implemented when keys are provided)
@app.post("/api/create-payment-intent")
async def create_payment_intent(payment: PaymentIntent):
    """Create Stripe payment intent (placeholder)"""
    if STRIPE_SECRET_KEY == 'placeholder_stripe_secret_key':
        return {
            "client_secret": "placeholder_client_secret",
            "message": "Stripe keys not configured. Please add STRIPE_SECRET_KEY to environment variables."
        }
    
    # TODO: Implement actual Stripe integration when keys are provided
    return {
        "client_secret": "placeholder_client_secret",
        "amount": payment.amount,
        "currency": payment.currency,
        "booking_id": payment.booking_id
    }

@app.post("/api/confirm-payment/{booking_id}")
async def confirm_payment(booking_id: str):
    """Confirm payment for booking"""
    try:
        result = db.bookings.update_one(
            {'booking_id': booking_id},
            {'$set': {'status': 'confirmed', 'confirmed_at': datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        return {"message": "Payment confirmed, booking is now confirmed"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error confirming payment: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)