from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, HTTPBasic, HTTPBasicCredentials
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, Document, PydanticObjectId
from beanie.operators import In, And, Or
from pymongo import IndexModel, ASCENDING
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime, timedelta
import bcrypt
import jwt
from bson import ObjectId
from contextlib import asynccontextmanager
from enum import Enum
import secrets
import time
import math
import shutil

from settings import (
    SECRET_KEY, ALGORITHM, DOCS_USERNAME, DOCS_PASSWORD, 
    MONGO_URL, DB_NAME, UPLOAD_DIR
)

security = HTTPBearer()
security_basic = HTTPBasic()



def get_current_username(credentials: HTTPBasicCredentials = Depends(security_basic)):
    correct_username = secrets.compare_digest(credentials.username, DOCS_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, DOCS_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# ============= Database Models (Beanie Documents) =============

class GeoObject(BaseModel):
    type: str = "Point"
    coordinates: List[float]

class DeliveryPersonStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

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
    status: str = "pending"
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

# ============= Pydantic Schemas =============

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
    status: str
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

# ============= Helper Functions =============

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(delivery_person_id: str) -> str:
    payload = {
        "sub": delivery_person_id,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371e3  # Earth radius in meters
    phi1 = lat1 * math.pi / 180
    phi2 = lat2 * math.pi / 180
    delta_phi = (lat2 - lat1) * math.pi / 180
    delta_lambda = (lon2 - lon1) * math.pi / 180

    a = math.sin(delta_phi / 2) * math.sin(delta_phi / 2) + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2) * math.sin(delta_lambda / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        
        # Check blacklist
        if await TokenBlacklist.find_one(TokenBlacklist.token == token):
             raise HTTPException(status_code=401, detail="Token has been revoked")

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        delivery_person_id = payload.get("sub")
        if not delivery_person_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        delivery_person = await DeliveryPerson.get(PydanticObjectId(delivery_person_id))
        if not delivery_person:
            raise HTTPException(status_code=401, detail="User not found")
        
        return str(delivery_person.id)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ============= Lifespan & App =============

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    client = AsyncIOMotorClient(MONGO_URL)
    await init_beanie(database=client[DB_NAME], document_models=[DeliveryPerson, Order, LocationTracking, TokenBlacklist])
    
    yield
    
    # Shutdown
    client.close()

app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
api_router = APIRouter(prefix="/api")

# ============= Docs Routes =============

@app.get("/docs", include_in_schema=False)
async def get_documentation(username: str = Depends(get_current_username)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")

@app.get("/openapi.json", include_in_schema=False)
async def openapi():
    return get_openapi(title="Delivery App API", version="1.0.0", routes=app.routes)

@app.get("/redoc", include_in_schema=False)
async def redoc():
    return get_redoc_html(
        openapi_url="/openapi.json", 
        title="redoc",
        redoc_js_url="https://unpkg.com/redoc@2.0.0-rc.55/bundles/redoc.standalone.js"
    )

# ============= Routes =============

@api_router.get("/")
async def root():
    return {"message": "Delivery App API"}

# Register endpoint
@api_router.post("/register", response_model=DeliveryPersonResponse)
async def register(person: DeliveryPersonCreate):
    # Check if email or phone already exists
    existing_email = await DeliveryPerson.find_one(DeliveryPerson.email == person.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    existing_phone = await DeliveryPerson.find_one(DeliveryPerson.phone == person.phone)
    if existing_phone:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    new_person = DeliveryPerson(
        name=person.name,
        email=person.email,
        password=hash_password(person.password),
        phone=person.phone,
        status=DeliveryPersonStatus.INACTIVE
    )
    
    await new_person.insert()
    
    return DeliveryPersonResponse(
        id=str(new_person.id),
        name=new_person.name,
        email=new_person.email,
        phone=new_person.phone,
        status=new_person.status,
        is_location_on=new_person.is_location_on,
        created_at=new_person.created_at
    )

# Get all delivery persons (Admin)
@api_router.get("/admin/delivery-persons", response_model=List[DeliveryPersonResponse])
async def get_all_delivery_persons():
    persons = await DeliveryPerson.find_all().to_list()
    return [
        DeliveryPersonResponse(
            id=str(p.id),
            name=p.name,
            email=p.email,
            phone=p.phone,
            status=p.status,
            is_location_on=p.is_location_on,
            created_at=p.created_at
        ) for p in persons
    ]

# Get delivery person by ID (Admin)
@api_router.get("/admin/delivery-persons/{person_id}", response_model=DeliveryPersonResponse)
async def get_delivery_person_by_id(person_id: str):
    try:
        oid = PydanticObjectId(person_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    person = await DeliveryPerson.get(oid)
    if not person:
        raise HTTPException(status_code=404, detail="Delivery person not found")
    
    return DeliveryPersonResponse(
        id=str(person.id),
        name=person.name,
        email=person.email,
        phone=person.phone,
        status=person.status,
        is_location_on=person.is_location_on,
        created_at=person.created_at
    )

# Login endpoint
@api_router.post("/login")
async def login(credentials: DeliveryPersonLogin):
    delivery_person = await DeliveryPerson.find_one(DeliveryPerson.email == credentials.email)
    if not delivery_person:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(credentials.password, delivery_person.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_token(str(delivery_person.id))
    
    return {
        "token": token,
        "delivery_person": {
            "id": str(delivery_person.id),
            "name": delivery_person.name,
            "email": delivery_person.email,
            "phone": delivery_person.phone,
            "status": delivery_person.status,
            "is_location_on": delivery_person.is_location_on
        }
    }

# Logout endpoint
@api_router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    logger.info(f"Logout request received for token: {token[:10]}...")
    await TokenBlacklist(token=token).insert()
    logger.info("Token blacklisted successfully")
    return {"message": "Successfully logged out"}

# Update status endpoint
@api_router.patch("/delivery-person/status", response_model=DeliveryPersonResponse)
async def update_status(status_update: DeliveryPersonStatusUpdate, delivery_person_id: str = Depends(get_current_user)):
    delivery_person = await DeliveryPerson.get(PydanticObjectId(delivery_person_id))
    if not delivery_person:
        raise HTTPException(status_code=404, detail="User not found")
    
    delivery_person.status = status_update.status
    await delivery_person.save()
    
    return DeliveryPersonResponse(
        id=str(delivery_person.id),
        name=delivery_person.name,
        email=delivery_person.email,
        phone=delivery_person.phone,
        status=delivery_person.status,
        is_location_on=delivery_person.is_location_on,
        created_at=delivery_person.created_at
    )

# Update location status endpoint
@api_router.patch("/delivery-person/location-status", response_model=DeliveryPersonResponse)
async def update_location_status(status_update: LocationStatusUpdate, delivery_person_id: str = Depends(get_current_user)):
    delivery_person = await DeliveryPerson.get(PydanticObjectId(delivery_person_id))
    if not delivery_person:
        raise HTTPException(status_code=404, detail="User not found")
    
    delivery_person.is_location_on = status_update.is_location_on
    await delivery_person.save()
    
    return DeliveryPersonResponse(
        id=str(delivery_person.id),
        name=delivery_person.name,
        email=delivery_person.email,
        phone=delivery_person.phone,
        status=delivery_person.status,
        is_location_on=delivery_person.is_location_on,
        created_at=delivery_person.created_at
    )

# Location tracking endpoint
@api_router.post("/location/track")
async def track_location(location: LocationTrack, delivery_person_id: str = Depends(get_current_user)):
    location_data = LocationTracking(
        delivery_person_id=delivery_person_id,
        current_location=GeoObject(
            type="Point",
            coordinates=[location.longitude, location.latitude]
        )
    )
    
    await location_data.insert()

    # Check for nearby orders and update status to 'reached'
    active_orders = await Order.find(
        Order.delivery_person_id == delivery_person_id,
        In(Order.status, ["in_transit", "pending"])
    ).to_list()

    updated_count = 0
    for order in active_orders:
        # Calculate distance using GeoJSON coordinates
        # coordinates are [longitude, latitude]
        order_lon, order_lat = order.delivery_location.coordinates
        
        distance = calculate_distance(
            location.latitude, location.longitude,
            order_lat, order_lon
        )
        
        # If within 100 meters, update status to reached
        if distance <= 100:
            order.status = "reached"
            await order.save()
            updated_count += 1
            logger.info(f"Order {order.id} status updated to reached. Distance: {distance}m")
    
    return {
        "message": "Location tracked successfully", 
        "timestamp": location_data.timestamp,
        "updated_orders": updated_count
    }

# Get current orders for delivery person
@api_router.get("/orders/current", response_model=List[OrderResponse])
async def get_current_orders(delivery_person_id: str = Depends(get_current_user)):
    # Calculate 24 hours ago timestamp
    cutoff_time = int(time.time()) - (24 * 60 * 60)

    orders = await Order.find(
        Order.delivery_person_id == delivery_person_id,
        Or(
            In(Order.status, ["pending", "in_transit", "reached"]),
            And(Order.status == "delivered", Order.delivered_at >= cutoff_time)
        )
    ).to_list(100)
    
    result = []
    for order in orders:
        # Extract lat/long from GeoJSON for response
        lon, lat = order.delivery_location.coordinates
        
        result.append(OrderResponse(
            id=str(order.id),
            customer_name=order.customer_name,
            customer_phone=order.customer_phone,
            delivery_address=order.delivery_address,
            items=order.items,
            status=order.status,
            delivery_person_id=order.delivery_person_id,
            latitude=lat,
            longitude=lon,
            proof_image=order.proof_image,
            created_at=order.created_at,
            delivered_at=order.delivered_at
        ))
    
    return result

# Get order statistics
@api_router.get("/stats/orders", response_model=OrderStats)
async def get_order_stats(delivery_person_id: str = Depends(get_current_user)):
    now = int(time.time())
    
    # Helper to get start of day timestamp
    def get_start_of_day(timestamp):
        dt = datetime.fromtimestamp(timestamp)
        start_of_day = datetime(dt.year, dt.month, dt.day)
        return int(start_of_day.timestamp())

    today_start = get_start_of_day(now)
    
    # Today's orders
    today_orders = await Order.find(
        Order.delivery_person_id == delivery_person_id,
        Order.status == "delivered",
        Order.delivered_at >= today_start
    ).count()
    
    # This week's orders
    dt = datetime.fromtimestamp(now)
    week_start_dt = dt - timedelta(days=dt.weekday())
    week_start = int(datetime(week_start_dt.year, week_start_dt.month, week_start_dt.day).timestamp())
    
    week_orders = await Order.find(
        Order.delivery_person_id == delivery_person_id,
        Order.status == "delivered",
        Order.delivered_at >= week_start
    ).count()
    
    # This month's orders
    month_start = int(datetime(dt.year, dt.month, 1).timestamp())
    
    month_orders = await Order.find(
        Order.delivery_person_id == delivery_person_id,
        Order.status == "delivered",
        Order.delivered_at >= month_start
    ).count()
    
    return OrderStats(today=today_orders, this_week=week_orders, this_month=month_orders)

# Update order status
@api_router.patch("/orders/{order_id}/status")
async def update_order_status(order_id: str, status: str, delivery_person_id: str = Depends(get_current_user)):
    if status not in ["pending", "in_transit", "reached", "delivered", "cancelled"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    try:
        oid = PydanticObjectId(order_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID")

    order = await Order.find_one(
        Order.id == oid,
        Order.delivery_person_id == delivery_person_id
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Validation for status transitions
    if status == "delivered" and order.status != "reached":
         raise HTTPException(status_code=400, detail="Order must be 'reached' before it can be 'delivered'")

    order.status = status
    if status == "delivered":
        order.delivered_at = int(time.time())
    
    await order.save()
    
    return {"message": "Order status updated successfully"}

# Complete order with proof
@api_router.post("/orders/{order_id}/complete")
async def complete_order(
    order_id: str, 
    file: UploadFile = File(...), 
    delivery_person_id: str = Depends(get_current_user)
):
    try:
        oid = PydanticObjectId(order_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID")

    order = await Order.find_one(
        Order.id == oid,
        Order.delivery_person_id == delivery_person_id
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != "reached":
        raise HTTPException(status_code=400, detail="Order must be 'reached' before completion")

    # Save file
    file_ext = file.filename.split('.')[-1]
    filename = f"{order_id}_{int(time.time())}.{file_ext}"
    file_path = UPLOAD_DIR / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    order.proof_image = f"/uploads/{filename}"
    order.status = "delivered"
    order.delivered_at = int(time.time())
    
    await order.save()
    
    return {"message": "Order completed successfully", "proof_image": order.proof_image}

# Admin endpoint to create and assign orders
@api_router.post("/admin/orders", response_model=OrderResponse)
async def create_order(order: OrderCreate):
    # Validate delivery person status if assigned
    if order.delivery_person_id:
        try:
            dp_oid = PydanticObjectId(order.delivery_person_id)
            delivery_person = await DeliveryPerson.get(dp_oid)
            if not delivery_person:
                raise HTTPException(status_code=404, detail="Delivery person not found")
            if delivery_person.status != DeliveryPersonStatus.ACTIVE:
                raise HTTPException(status_code=400, detail="Delivery person is inactive and cannot be assigned orders")
        except Exception as e:
             if isinstance(e, HTTPException):
                 raise e
             raise HTTPException(status_code=400, detail="Invalid delivery person ID")

    new_order = Order(
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        delivery_address=order.delivery_address,
        items=order.items,
        status="pending",
        delivery_person_id=order.delivery_person_id,
        delivery_location=GeoObject(
            type="Point",
            coordinates=[order.longitude, order.latitude]
        )
    )
    
    await new_order.insert()
    
    return OrderResponse(
        id=str(new_order.id),
        customer_name=new_order.customer_name,
        customer_phone=new_order.customer_phone,
        delivery_address=new_order.delivery_address,
        items=new_order.items,
        status=new_order.status,
        delivery_person_id=new_order.delivery_person_id,
        latitude=order.latitude,
        longitude=order.longitude,
        proof_image=new_order.proof_image,
        created_at=new_order.created_at,
        delivered_at=new_order.delivered_at
    )

# Get profile
@api_router.get("/profile", response_model=DeliveryPersonResponse)
async def get_profile(delivery_person_id: str = Depends(get_current_user)):
    # get_current_user already verifies existence and status
    delivery_person = await DeliveryPerson.get(PydanticObjectId(delivery_person_id))
    
    return DeliveryPersonResponse(
        id=str(delivery_person.id),
        name=delivery_person.name,
        email=delivery_person.email,
        phone=delivery_person.phone,
        status=delivery_person.status,
        is_location_on=delivery_person.is_location_on,
        created_at=delivery_person.created_at
    )

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
