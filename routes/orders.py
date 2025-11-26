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
    conn.close()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    order_dict = dict(order)
    order_dict['items'] = json.loads(order_dict['items'])
    return order_dict

@router.post("/", dependencies=[Depends(check_role(["admin", "manager", "staff"]))])
async def create_order(order: OrderCreate, current_user: dict = Depends(get_current_active_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify table exists
    cursor.execute("SELECT id FROM tables WHERE id = ?", (order.table_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Table not found")
    
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
    
    return {"id": order_id, "message": "Order created and KOT generated"}

@router.patch("/{order_id}/status", dependencies=[Depends(check_role(["admin", "manager", "staff"]))])
async def update_order_status(order_id: int, status_update: OrderUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (status_update.status, order_id))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
        
    # If order is completed or paid, free up the table? 
    # Usually paid means table is free. Let's assume 'paid' frees the table.
    if status_update.status == 'paid':
        cursor.execute("SELECT table_id FROM orders WHERE id = ?", (order_id,))
        result = cursor.fetchone()
        if result:
            table_id = result['table_id']
            cursor.execute("UPDATE tables SET status = 'available', current_order_id = NULL WHERE id = ?", (table_id,))
            
    conn.commit()
    conn.close()
    return {"message": f"Order status updated to {status_update.status}"}
