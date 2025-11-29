from beanie import Document
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from pymongo import IndexModel, ASCENDING
import time
from enums import DeliveryPersonStatus, OrderStatus

class GeoObject(BaseModel):
    type: str = "Point"
    coordinates: List[float]

class DeliveryPerson(Document):
    name: str
    email: str
    password: str
    phone: int
    status: DeliveryPersonStatus = DeliveryPersonStatus.INACTIVE
    is_location_on: bool = False
    created_at: int = Field(default_factory=lambda: int(time.time()))

    class Settings:
        name = "delivery_persons"
        indexes = [
            IndexModel([("email", ASCENDING)], unique=True),
            IndexModel([("phone", ASCENDING)], unique=True),
        ]

class Order(Document):
    customer_name: str
    customer_phone: int
    delivery_address: str
    items: List[str]
    status: OrderStatus = OrderStatus.PENDING
    delivery_person_id: Optional[str] = None
    delivery_location: GeoObject
    proof_image: Optional[str] = None
    created_at: int = Field(default_factory=lambda: int(time.time()))
    delivered_at: Optional[int] = None

    @validator('items', pre=True)
    def parse_items(cls, v):
        if isinstance(v, str):
            return [v]
        return v

    class Settings:
        name = "orders"
        indexes = [
            IndexModel([("delivery_location", "2dsphere")])
        ]

class LocationTracking(Document):
    delivery_person_id: str
    current_location: GeoObject
    timestamp: int = Field(default_factory=lambda: int(time.time()))

    class Settings:
        name = "location_tracking"
        indexes = [
            IndexModel([("current_location", "2dsphere")])
        ]

class TokenBlacklist(Document):
    token: str
    created_at: int = Field(default_factory=lambda: int(time.time()))
    
    class Settings:
        name = "token_blacklist"
