from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from middleware.auth import check_role
from database import get_db_connection

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

class InventoryItemCreate(BaseModel):
    item_name: str
    quantity: float
    unit: str
    low_stock_threshold: float = 10.0
    supplier: Optional[str] = None

class InventoryItemUpdate(BaseModel):
    quantity: Optional[float] = None
    low_stock_threshold: Optional[float] = None
    supplier: Optional[str] = None

@router.get("/", dependencies=[Depends(check_role(["admin", "manager"]))])
async def get_inventory():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory")
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items

@router.get("/low-stock", dependencies=[Depends(check_role(["admin", "manager"]))])
async def get_low_stock():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory WHERE quantity <= low_stock_threshold")
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items

@router.post("/", dependencies=[Depends(check_role(["admin", "manager"]))])
async def add_inventory_item(item: InventoryItemCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO inventory (item_name, quantity, unit, low_stock_threshold, supplier) VALUES (?, ?, ?, ?, ?)",
        (item.item_name, item.quantity, item.unit, item.low_stock_threshold, item.supplier)
    )
    conn.commit()
    item_id = cursor.lastrowid
    conn.close()
    
    return {**item.dict(), "id": item_id}

@router.put("/{item_id}", dependencies=[Depends(check_role(["admin", "manager"]))])
async def update_inventory_item(item_id: int, item: InventoryItemUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    update_data = item.dict(exclude_unset=True)
    if not update_data:
        conn.close()
        return {"message": "No changes provided"}
        
    set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
    values = list(update_data.values())
    values.append(item_id)
    
    cursor.execute(f"UPDATE inventory SET {set_clause}, last_updated = CURRENT_TIMESTAMP WHERE id = ?", values)
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found")
        
    conn.commit()
    conn.close()
    return {"message": "Inventory updated"}

@router.delete("/{item_id}", dependencies=[Depends(check_role(["admin"]))])
async def delete_inventory_item(item_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found")
    conn.commit()
    conn.close()
    return {"message": "Item deleted"}
