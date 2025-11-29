from pydantic import BaseModel, validator
from typing import List, Optional
from enums import DeliveryPersonStatus, OrderStatus

class DeliveryPersonCreate(BaseModel):
    name: str
    email: str
    password: str
    phone: int

    @validator('phone')
    def validate_phone(cls, v):
        s = str(v)
        if len(s) != 12:
            raise ValueError('Phone number must be exactly 12 digits')
        return v

class DeliveryPersonLogin(BaseModel):
    email: str
    password: str

class DeliveryPersonResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: int
    status: DeliveryPersonStatus
    is_location_on: bool
    created_at: int

class DeliveryPersonStatusUpdate(BaseModel):
    status: DeliveryPersonStatus

class LocationStatusUpdate(BaseModel):
    is_location_on: bool

class LocationTrack(BaseModel):
    latitude: float
    longitude: float

class OrderCreate(BaseModel):
    customer_name: str
    customer_phone: int
    delivery_address: str
    items: List[str]
    delivery_person_id: Optional[str] = None
    latitude: float
    longitude: float

    @validator('customer_phone')
    def validate_phone(cls, v):
        s = str(v)
        if len(s) != 12:
            raise ValueError('Phone number must be exactly 12 digits')
        return v

class OrderResponse(BaseModel):
    id: str
    customer_name: str
    customer_phone: int
    delivery_address: str
    items: List[str]
    status: OrderStatus
    delivery_person_id: Optional[str]
    latitude: float
    longitude: float
    proof_image: Optional[str]
    created_at: int
    delivered_at: Optional[int]

class OrderStats(BaseModel):
    today: int
    this_week: int
    this_month: int
