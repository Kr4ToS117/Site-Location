from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime, date
import pymongo
import os
import uuid
from bson import ObjectId

# Environment variables
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/apartment_booking')

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
    name: str
    email: EmailStr
    phone: str
    guests: int
    check_in: date
    check_out: date
    nights: int
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
    name: str
    email: str
    phone: str
    guests: int
    check_in: date
    check_out: date
    nights: int
    total_price: float
    arrival_time: str
    special_requests: str
    status: str
    created_at: datetime

class PricingResponse(BaseModel):
    base_rate: float
    cleaning_fee: Optional[float] = 0
    security_deposit: Optional[float] = 0

class PricingUpdate(BaseModel):
    base_rate: float
    cleaning_fee: Optional[float] = 0
    security_deposit: Optional[float] = 0

# Helper functions
def booking_dict_to_response(booking: dict) -> BookingResponse:
    # Convert string dates back to date objects for response
    check_in = booking['check_in']
    check_out = booking['check_out']
    
    if isinstance(check_in, str):
        check_in = datetime.fromisoformat(check_in).date()
    if isinstance(check_out, str):
        check_out = datetime.fromisoformat(check_out).date()
    
    return BookingResponse(
        booking_id=booking['booking_id'],
        name=booking['name'],
        email=booking['email'],
        phone=booking['phone'],
        guests=booking['guests'],
        check_in=check_in,
        check_out=check_out,
        nights=booking['nights'],
        total_price=booking['total_price'],
        arrival_time=booking['arrival_time'],
        special_requests=booking['special_requests'],
        status=booking['status'],
        created_at=booking['created_at']
    )

def check_date_availability(check_in: date, check_out: date) -> bool:
    """Check if dates are available for booking"""
    # Convert dates to strings for MongoDB query
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
            'name': booking.name,
            'email': booking.email,
            'phone': booking.phone,
            'guests': booking.guests,
            'check_in': booking.check_in.isoformat(),
            'check_out': booking.check_out.isoformat(),
            'nights': booking.nights,
            'total_price': booking.total_price,
            'arrival_time': booking.arrival_time,
            'special_requests': booking.special_requests,
            'status': 'confirmed',
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

@app.get("/api/pricing", response_model=PricingResponse)
async def get_pricing():
    """Get current pricing configuration"""
    try:
        pricing = db.pricing.find_one({'active': True})
        if not pricing:
            # Set default pricing if none exists
            default_pricing = {
                'base_rate': 120.0,
                'cleaning_fee': 0.0,
                'security_deposit': 0.0,
                'active': True,
                'created_at': datetime.utcnow()
            }
            db.pricing.insert_one(default_pricing)
            pricing = default_pricing
        
        return PricingResponse(
            base_rate=pricing['base_rate'],
            cleaning_fee=pricing.get('cleaning_fee', 0.0),
            security_deposit=pricing.get('security_deposit', 0.0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching pricing: {str(e)}")

@app.put("/api/pricing")
async def update_pricing(pricing: PricingUpdate):
    """Update pricing configuration"""
    try:
        # Deactivate current pricing
        db.pricing.update_many({'active': True}, {'$set': {'active': False}})
        
        # Insert new pricing
        new_pricing = {
            'base_rate': pricing.base_rate,
            'cleaning_fee': pricing.cleaning_fee,
            'security_deposit': pricing.security_deposit,
            'active': True,
            'created_at': datetime.utcnow()
        }
        
        result = db.pricing.insert_one(new_pricing)
        
        if result.inserted_id:
            return {"message": "Pricing updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update pricing")
            
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)