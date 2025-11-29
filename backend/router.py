from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.security import HTTPAuthorizationCredentials
from beanie import PydanticObjectId
from beanie.operators import In, And, Or
from typing import List
import time
import shutil
import logging
from datetime import datetime, timedelta

from model import DeliveryPerson, Order, LocationTracking, TokenBlacklist, GeoObject
from schemas import (
    DeliveryPersonCreate, DeliveryPersonResponse, DeliveryPersonLogin, 
    DeliveryPersonStatusUpdate, LocationStatusUpdate, LocationTrack, 
    OrderCreate, OrderResponse, OrderStats
)
from services import (
    hash_password, verify_password, create_token, calculate_distance, 
    get_current_user, security
)
from enums import DeliveryPersonStatus, OrderStatus
from settings import UPLOAD_DIR

api_router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)

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
        In(Order.status, [OrderStatus.IN_TRANSIT, OrderStatus.PENDING])
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
            order.status = OrderStatus.REACHED
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
            In(Order.status, [OrderStatus.PENDING, OrderStatus.IN_TRANSIT, OrderStatus.REACHED]),
            And(Order.status == OrderStatus.DELIVERED, Order.delivered_at >= cutoff_time)
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
        Order.status == OrderStatus.DELIVERED,
        Order.delivered_at >= today_start
    ).count()
    
    # This week's orders
    dt = datetime.fromtimestamp(now)
    week_start_dt = dt - timedelta(days=dt.weekday())
    week_start = int(datetime(week_start_dt.year, week_start_dt.month, week_start_dt.day).timestamp())
    
    week_orders = await Order.find(
        Order.delivery_person_id == delivery_person_id,
        Order.status == OrderStatus.DELIVERED,
        Order.delivered_at >= week_start
    ).count()
    
    # This month's orders
    month_start = int(datetime(dt.year, dt.month, 1).timestamp())
    
    month_orders = await Order.find(
        Order.delivery_person_id == delivery_person_id,
        Order.status == OrderStatus.DELIVERED,
        Order.delivered_at >= month_start
    ).count()
    
    return OrderStats(today=today_orders, this_week=week_orders, this_month=month_orders)

# Update order status
@api_router.patch("/orders/{order_id}/status")
async def update_order_status(order_id: str, status: OrderStatus, delivery_person_id: str = Depends(get_current_user)):

    
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
    if status == OrderStatus.DELIVERED and order.status != OrderStatus.REACHED:
         raise HTTPException(status_code=400, detail="Order must be 'reached' before it can be 'delivered'")

    order.status = status
    if status == OrderStatus.DELIVERED:
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
    
    if order.status != OrderStatus.REACHED:
        raise HTTPException(status_code=400, detail="Order must be 'reached' before completion")

    # Save file
    file_ext = file.filename.split('.')[-1]
    filename = f"{order_id}_{int(time.time())}.{file_ext}"
    file_path = UPLOAD_DIR / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    order.proof_image = f"/uploads/{filename}"
    order.status = OrderStatus.DELIVERED
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
        status=OrderStatus.PENDING,
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
