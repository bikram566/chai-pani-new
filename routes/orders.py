from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
from middleware.auth import check_role, get_current_active_user
from database import get_db_connection

router = APIRouter(prefix="/api/orders", tags=["orders"])

class OrderItem(BaseModel):
    menu_item_id: int
    name: str
    quantity: int
    price: float
    notes: Optional[str] = None

class OrderCreate(BaseModel):
    table_id: int
    items: List[OrderItem]
    total_amount: float

class OrderUpdate(BaseModel):
    status: str # pending, preparing, ready, completed, paid

@router.get("/")
async def get_orders(status: Optional[str] = None, table_id: Optional[int] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM orders WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = ?"
        params.append(status)
        
    if table_id:
        query += " AND table_id = ?"
        params.append(table_id)
        
    query += " ORDER BY created_at DESC"
    
    cursor.execute(query, params)
    orders = []
    for row in cursor.fetchall():
        order = dict(row)
        order['items'] = json.loads(order['items'])
        orders.append(order)
        
    conn.close()
    return orders

@router.get("/{order_id}")
async def get_order(order_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
        
    order_dict = dict(order)
    order_dict['items'] = json.loads(order_dict['items'])
    
    # Fetch KOTs to get item-level status
    cursor.execute("SELECT items, status, created_at FROM kot WHERE order_id = ?", (order_id,))
    kots = cursor.fetchall()
    
    detailed_items = []
    for kot in kots:
        kot_items = json.loads(kot['items'])
        kot_status = kot['status']
        for item in kot_items:
            item['status'] = kot_status
            detailed_items.append(item)
            
    order_dict['detailed_items'] = detailed_items
    
    conn.close()
    return order_dict

@router.post("/", dependencies=[Depends(check_role(["admin", "manager", "staff"]))])
async def create_order(order: OrderCreate, current_user: dict = Depends(get_current_active_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify table exists
    cursor.execute("SELECT id, current_order_id FROM tables WHERE id = ?", (order.table_id,))
    table = cursor.fetchone()
    if not table:
        conn.close()
        raise HTTPException(status_code=404, detail="Table not found")
    
    # Check if table has an existing active order (not paid)
    existing_order_id = table['current_order_id']
    existing_order = None
    
    if existing_order_id:
        cursor.execute("SELECT * FROM orders WHERE id = ? AND status != 'paid'", (existing_order_id,))
        existing_order = cursor.fetchone()
    
    if existing_order:
        # Append items to existing order
        existing_items = json.loads(existing_order['items'])
        new_items = [item.dict() for item in order.items]
        
        # Merge items
        combined_items = existing_items + new_items
        combined_items_json = json.dumps(combined_items)
        
        # Update total amount
        new_total = existing_order['total_amount'] + order.total_amount
        
        # Update existing order
        cursor.execute(
            "UPDATE orders SET items = ?, total_amount = ? WHERE id = ?",
            (combined_items_json, new_total, existing_order_id)
        )
        
        # Create additional KOT for the new items
        new_items_json = json.dumps(new_items)
        cursor.execute(
            "INSERT INTO kot (order_id, items, status) VALUES (?, ?, 'pending')",
            (existing_order_id, new_items_json)
        )
        
        conn.commit()
        conn.close()
        
        return {
            "id": existing_order_id, 
            "message": f"Items added to existing order. New total: {new_total}",
            "appended": True
        }
    else:
        # Create new order as usual
        items_json = json.dumps([item.dict() for item in order.items])
        
        # Create Order
        cursor.execute(
            "INSERT INTO orders (table_id, items, total_amount, created_by) VALUES (?, ?, ?, ?)",
            (order.table_id, items_json, order.total_amount, current_user['id'])
        )
        order_id = cursor.lastrowid
        
        # Create KOT
        cursor.execute(
            "INSERT INTO kot (order_id, items, status) VALUES (?, ?, 'pending')",
            (order_id, items_json)
        )
        
        # Update Table Status
        cursor.execute(
            "UPDATE tables SET status = 'occupied', current_order_id = ? WHERE id = ?",
            (order_id, order.table_id)
        )
        
        conn.commit()
        conn.close()
        
        return {"id": order_id, "message": "Order created and KOT generated", "appended": False}


@router.patch("/{order_id}/status", dependencies=[Depends(check_role(["admin", "manager", "staff"]))])
async def update_order_status(order_id: int, status_update: OrderUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current order details
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Update order status
    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (status_update.status, order_id))
        
    # If order is marked as 'paid', also update related entities
    if status_update.status == 'paid':
        table_id = order['table_id']
        
        # Free up the table
        cursor.execute(
            "UPDATE tables SET status = 'available', current_order_id = NULL WHERE id = ?", 
            (table_id,)
        )
        
        # Update KOT status to completed
        cursor.execute(
            "UPDATE kot SET status = 'completed' WHERE order_id = ? AND status != 'completed'",
            (order_id,)
        )
            
    conn.commit()
    conn.close()
    
    message = f"Order status updated to {status_update.status}"
    if status_update.status == 'paid':
        message += " and table freed"
    
    return {"message": message}

