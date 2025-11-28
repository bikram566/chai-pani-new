import requests
import sys

BASE_URL = "http://localhost:8001"
USERNAME = "admin"
PASSWORD = "adminpassword"

def run():
    # 1. Login
    print("Logging in...")
    try:
        resp = requests.post(f"{BASE_URL}/token", data={"username": USERNAME, "password": PASSWORD})
        if resp.status_code != 200:
            print("Login failed")
            return
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # 2. Reset Table 1
    print("Resetting Table 1...")
    tables = requests.get(f"{BASE_URL}/tables/", headers=headers).json()
    for t in tables:
        if t['id'] == 1 and t['status'] == 'occupied':
            requests.patch(f"{BASE_URL}/api/orders/{t['current_order_id']}/status", 
                         json={"status": "paid"}, headers=headers)

    # 3. Create Order 1
    print("Creating Order 1...")
    o1 = requests.post(f"{BASE_URL}/api/orders/", headers=headers, json={
        "table_id": 1,
        "items": [{"menu_item_id": 1, "name": "Item 1", "quantity": 1, "price": 10}],
        "total_amount": 10
    }).json()
    print(f"Order 1 ID: {o1['id']}")

    # 4. Create Order 2 (Append)
    print("Creating Order 2 (Append)...")
    o2 = requests.post(f"{BASE_URL}/api/orders/", headers=headers, json={
        "table_id": 1,
        "items": [{"menu_item_id": 2, "name": "Item 2", "quantity": 1, "price": 20}],
        "total_amount": 20
    }).json()
    print(f"Order 2 ID: {o2['id']}, Appended: {o2.get('appended')}")

    if o1['id'] == o2['id'] and o2.get('appended'):
        print("SUCCESS: Order appended.")
    else:
        print("FAIL: Order not appended.")

    # 5. Pay
    print("Paying...")
    requests.patch(f"{BASE_URL}/api/orders/{o1['id']}/status", headers=headers, json={"status": "paid"})

    # 6. Check Table
    print("Checking Table...")
    tables = requests.get(f"{BASE_URL}/tables/", headers=headers).json()
    t1 = next(t for t in tables if t['id'] == 1)
    if t1['status'] == 'available':
        print("SUCCESS: Table available.")
    else:
        print(f"FAIL: Table status is {t1['status']}")

if __name__ == "__main__":
    run()
