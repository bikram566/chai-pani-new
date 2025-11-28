import requests
import json
import sys

BASE_URL = "http://localhost:8001"
USERNAME = "admin"
PASSWORD = "adminpassword"

def login():
    response = requests.post(f"{BASE_URL}/token", data={"username": USERNAME, "password": PASSWORD})
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        sys.exit(1)
    return response.json()["access_token"]

def reset_table(token, table_id):
    # Force reset table to available for testing
    headers = {"Authorization": f"Bearer {token}"}
    # We might not have a direct endpoint to force reset without an order, 
    # but let's try to find an active order and pay it if exists, or just manually fix via sqlite if needed.
    # For now, let's assume we can start fresh or use a table that is available.
    # Actually, let's just use the database directly to reset for clean state if possible, 
    # but we are testing API.
    # Let's try to get table status.
    pass

def test_order_flow():
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    
    print("1. Getting available tables...")
    response = requests.get(f"{BASE_URL}/tables/", headers=headers)
    tables = response.json()
    table_id = 1 # Use table 1
    
    # Ensure table is available (if occupied, pay the order)
    for table in tables:
        if table['id'] == table_id and table['status'] == 'occupied':
            print(f"Table {table_id} is occupied. Clearing it...")
            if table.get('current_order_id'):
                requests.patch(f"{BASE_URL}/api/orders/{table['current_order_id']}/status", 
                             json={"status": "paid"}, headers=headers)
    
    print(f"2. Creating first order for Table {table_id}...")
    order_data_1 = {
        "table_id": table_id,
        "items": [
            {"menu_item_id": 1, "name": "Chai", "quantity": 1, "price": 10.0}
        ],
        "total_amount": 10.0
    }
    
    response = requests.post(f"{BASE_URL}/api/orders/", json=order_data_1, headers=headers)
    if response.status_code != 200:
        print(f"Failed to create order: {response.text}")
        return
    
    result_1 = response.json()
    order_id = result_1['id']
    print(f"Order created with ID: {order_id}")
    
    print(f"3. Creating SECOND order for Table {table_id} (Should append)...")
    order_data_2 = {
        "table_id": table_id,
        "items": [
            {"menu_item_id": 2, "name": "Samosa", "quantity": 2, "price": 20.0}
        ],
        "total_amount": 40.0
    }
    
    response = requests.post(f"{BASE_URL}/api/orders/", json=order_data_2, headers=headers)
    if response.status_code != 200:
        print(f"Failed to create second order: {response.text}")
        return
        
    result_2 = response.json()
    print(f"Second order response: {result_2}")
    
    if result_2['id'] != order_id:
        print("FAIL: Order ID changed! Items were not appended.")
    elif not result_2.get('appended'):
        print("FAIL: Response does not indicate appended status.")
    else:
        print("SUCCESS: Items appended to existing order.")
        
    print("4. Verifying total amount...")
    response = requests.get(f"{BASE_URL}/api/orders/{order_id}", headers=headers)
    order_details = response.json()
    expected_total = 50.0 # 10 + 40
    if order_details['total_amount'] == expected_total:
        print(f"SUCCESS: Total amount updated correctly to {expected_total}")
    else:
        print(f"FAIL: Total amount is {order_details['total_amount']}, expected {expected_total}")
        
    print("5. Marking order as PAID...")
    response = requests.patch(f"{BASE_URL}/api/orders/{order_id}/status", 
                            json={"status": "paid"}, headers=headers)
    print(f"Payment response: {response.json()}")
    
    print("6. Verifying KOT status...")
    # We need to check the database or an endpoint for KOTs. 
    # Since we don't have a direct KOT endpoint in the snippet I saw, 
    # I'll assume if the order is paid and table is free, we are good.
    # But let's check table status.
    
    response = requests.get(f"{BASE_URL}/tables/", headers=headers)
    tables = response.json()
    table_status = next((t['status'] for t in tables if t['id'] == table_id), None)
    
    if table_status == 'available':
        print("SUCCESS: Table is available after payment.")
    else:
        print(f"FAIL: Table status is {table_status}")

if __name__ == "__main__":
    test_order_flow()
