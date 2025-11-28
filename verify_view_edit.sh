#!/bin/bash

BASE_URL="http://localhost:8001"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc2NDM0NTc3OX0.ulDu54rOPplCjwo38AiOc3Fa70pBM5qsotocPu56K8E"
AUTH_HEADER="Authorization: Bearer $TOKEN"

# 1. Reset Table 1 (Pay existing order if any)
# Find current order for table 1
CURRENT_ORDER=$(curl -s -H "$AUTH_HEADER" "$BASE_URL/tables/" | python3 -c "import sys, json; tables=json.load(sys.stdin); print(next((t['current_order_id'] for t in tables if t['id']==1), 'None'))")
if [ "$CURRENT_ORDER" != "None" ]; then
    echo "Clearing existing order $CURRENT_ORDER..."
    curl -s -X PATCH "$BASE_URL/api/orders/$CURRENT_ORDER/status" -H "$AUTH_HEADER" -H "Content-Type: application/json" -d '{"status": "paid"}'
fi

# 2. Create Order 1
echo "Creating Order 1..."
ORDER_1_RESP=$(curl -s -X POST "$BASE_URL/api/orders/" -H "$AUTH_HEADER" -H "Content-Type: application/json" -d '{
    "table_id": 1,
    "items": [{"menu_item_id": 1, "name": "Chai", "quantity": 1, "price": 10.0}],
    "total_amount": 10.0
}')
echo "Order 1 Response: $ORDER_1_RESP"
ID=$(echo $ORDER_1_RESP | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

# 3. Create Order 2 (Append)
echo "Creating Order 2 (Append)..."
ORDER_2_RESP=$(curl -s -X POST "$BASE_URL/api/orders/" -H "$AUTH_HEADER" -H "Content-Type: application/json" -d '{
    "table_id": 1,
    "items": [{"menu_item_id": 2, "name": "Samosa", "quantity": 1, "price": 20.0}],
    "total_amount": 20.0
}')
echo "Order 2 Response: $ORDER_2_RESP"

# 4. Get Order Details (Check detailed_items)
echo "Getting Order Details..."
DETAILS=$(curl -s "$BASE_URL/api/orders/$ID" -H "$AUTH_HEADER")
echo "Order Details: $DETAILS"

# Verify detailed_items exists
HAS_DETAILED=$(echo $DETAILS | python3 -c "import sys, json; print('detailed_items' in json.load(sys.stdin))")
if [ "$HAS_DETAILED" == "True" ]; then
    echo "SUCCESS: detailed_items found in response."
else
    echo "FAIL: detailed_items NOT found."
fi
