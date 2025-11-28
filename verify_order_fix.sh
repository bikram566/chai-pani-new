#!/bin/bash

BASE_URL="http://localhost:8001"
USERNAME="admin"
PASSWORD="adminpassword"

# 1. Login
echo "Logging in..."
TOKEN=$(curl -s -X POST "$BASE_URL/token" -d "username=$USERNAME&password=$PASSWORD" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
echo "Token: $TOKEN"

if [ -z "$TOKEN" ]; then
    echo "Login failed"
    exit 1
fi

AUTH_HEADER="Authorization: Bearer $TOKEN"

# 2. Reset Table 1 (Find active order and pay it)
echo "Checking Table 1 status..."
TABLE_STATUS=$(curl -s -H "$AUTH_HEADER" "$BASE_URL/tables/" | python3 -c "import sys, json; tables=json.load(sys.stdin); print(next((t['status'] for t in tables if t['id']==1), 'unknown'))")
CURRENT_ORDER=$(curl -s -H "$AUTH_HEADER" "$BASE_URL/tables/" | python3 -c "import sys, json; tables=json.load(sys.stdin); print(next((t['current_order_id'] for t in tables if t['id']==1), 'None'))")

echo "Table 1 Status: $TABLE_STATUS, Order: $CURRENT_ORDER"

if [ "$TABLE_STATUS" == "occupied" ] && [ "$CURRENT_ORDER" != "None" ]; then
    echo "Clearing existing order $CURRENT_ORDER..."
    curl -s -X PATCH "$BASE_URL/api/orders/$CURRENT_ORDER/status" -H "$AUTH_HEADER" -H "Content-Type: application/json" -d '{"status": "paid"}'
fi

# 3. Create First Order
echo "Creating First Order..."
ORDER_1_RESP=$(curl -s -X POST "$BASE_URL/api/orders/" -H "$AUTH_HEADER" -H "Content-Type: application/json" -d '{
    "table_id": 1,
    "items": [{"menu_item_id": 1, "name": "Chai", "quantity": 1, "price": 10.0}],
    "total_amount": 10.0
}')
echo "Order 1 Response: $ORDER_1_RESP"
ORDER_ID=$(echo $ORDER_1_RESP | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

# 4. Create Second Order (Should Append)
echo "Creating Second Order (Appending)..."
ORDER_2_RESP=$(curl -s -X POST "$BASE_URL/api/orders/" -H "$AUTH_HEADER" -H "Content-Type: application/json" -d '{
    "table_id": 1,
    "items": [{"menu_item_id": 2, "name": "Samosa", "quantity": 2, "price": 20.0}],
    "total_amount": 40.0
}')
echo "Order 2 Response: $ORDER_2_RESP"
ORDER_ID_2=$(echo $ORDER_2_RESP | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
APPENDED=$(echo $ORDER_2_RESP | python3 -c "import sys, json; print(json.load(sys.stdin).get('appended', False))")

if [ "$ORDER_ID" == "$ORDER_ID_2" ] && [ "$APPENDED" == "True" ]; then
    echo "SUCCESS: Order appended correctly."
else
    echo "FAIL: Order not appended. ID1: $ORDER_ID, ID2: $ORDER_ID_2"
fi

# 5. Verify Total
echo "Verifying Total..."
TOTAL=$(curl -s -H "$AUTH_HEADER" "$BASE_URL/api/orders/$ORDER_ID" | python3 -c "import sys, json; print(json.load(sys.stdin)['total_amount'])")
if [ "$TOTAL" == "50.0" ]; then
    echo "SUCCESS: Total amount is 50.0"
else
    echo "FAIL: Total amount is $TOTAL (Expected 50.0)"
fi

# 6. Pay Order
echo "Paying Order..."
PAY_RESP=$(curl -s -X PATCH "$BASE_URL/api/orders/$ORDER_ID/status" -H "$AUTH_HEADER" -H "Content-Type: application/json" -d '{"status": "paid"}')
echo "Pay Response: $PAY_RESP"

# 7. Check Table Status
echo "Checking Table Status..."
FINAL_STATUS=$(curl -s -H "$AUTH_HEADER" "$BASE_URL/tables/" | python3 -c "import sys, json; tables=json.load(sys.stdin); print(next((t['status'] for t in tables if t['id']==1), 'unknown'))")

if [ "$FINAL_STATUS" == "available" ]; then
    echo "SUCCESS: Table is available."
else
    echo "FAIL: Table status is $FINAL_STATUS"
fi
