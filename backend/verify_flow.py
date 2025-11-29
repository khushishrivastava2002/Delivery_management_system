import requests
import time
import os

BASE_URL = "http://localhost:8000/api"

def test_flow():
    print("Starting verification flow...")

    # 1. Create Delivery Person
    email = f"test_{int(time.time())}@example.com"
    phone = 919876543210
    password = "password123"
    
    print(f"Creating delivery person: {email}")
    res = requests.post(f"{BASE_URL}/admin/delivery-person", json={
        "name": "Test Driver",
        "email": email,
        "password": password,
        "phone": phone
    })
    if res.status_code != 200:
        print(f"Failed to create DP: {res.text}")
        return
    dp_id = res.json()["id"]

    # 2. Login
    print("Logging in...")
    res = requests.post(f"{BASE_URL}/login", json={
        "email": email,
        "password": password
    })
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Activate Status
    print("Activating status...")
    requests.patch(f"{BASE_URL}/delivery-person/status", json={"status": "active"}, headers=headers)

    # 4. Create Order (Admin)
    print("Creating order...")
    # Order location: 12.9716, 77.5946 (Bangalore)
    order_lat = 12.9716
    order_long = 77.5946
    
    res = requests.post(f"{BASE_URL}/admin/orders", json={
        "customer_name": "John Doe",
        "customer_phone": 919988776655,
        "delivery_address": "MG Road, Bangalore",
        "items": ["Pizza", "Coke"],
        "delivery_person_id": dp_id,
        "latitude": order_lat,
        "longitude": order_long
    })
    if res.status_code != 200:
        print(f"Failed to create order: {res.text}")
        return
    order_id = res.json()["id"]
    print(f"Order created: {order_id}")

    # 5. Update status to in_transit
    print("Updating status to in_transit...")
    requests.patch(f"{BASE_URL}/orders/{order_id}/status?status=in_transit", headers=headers)

    # 6. Track Location (Far away)
    print("Tracking location (Far)...")
    # 1km away
    requests.post(f"{BASE_URL}/location/track", json={
        "latitude": 12.9800, 
        "longitude": 77.6000
    }, headers=headers)

    # Check status
    res = requests.get(f"{BASE_URL}/orders/current", headers=headers)
    order = next((o for o in res.json() if o["id"] == order_id), None)
    print(f"Status after far location: {order['status']}")
    assert order['status'] == 'in_transit'

    # 7. Track Location (Near)
    print("Tracking location (Near)...")
    # Same location
    requests.post(f"{BASE_URL}/location/track", json={
        "latitude": order_lat, 
        "longitude": order_long
    }, headers=headers)

    # Check status
    res = requests.get(f"{BASE_URL}/orders/current", headers=headers)
    order = next((o for o in res.json() if o["id"] == order_id), None)
    print(f"Status after near location: {order['status']}")
    assert order['status'] == 'reached'

    # 8. Complete Order
    print("Completing order with proof...")
    # Create dummy image
    with open("proof.jpg", "wb") as f:
        f.write(b"dummy image content")

    with open("proof.jpg", "rb") as f:
        files = {"file": ("proof.jpg", f, "image/jpeg")}
        res = requests.post(f"{BASE_URL}/orders/{order_id}/complete", headers=headers, files=files)
    
    if res.status_code == 200:
        print("Order completed successfully!")
        print(f"Proof image: {res.json()['proof_image']}")
    else:
        print(f"Failed to complete order: {res.text}")

    # Cleanup
    if os.path.exists("proof.jpg"):
        os.remove("proof.jpg")

if __name__ == "__main__":
    test_flow()
