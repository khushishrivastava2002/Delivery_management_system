from enum import Enum

class DeliveryPersonStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class OrderStatus(str, Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    REACHED = "reached"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
