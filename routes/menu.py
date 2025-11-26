from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from middleware.auth import check_role, get_current_active_user
from database import get_db_connection
import sqlite3

router = APIRouter(prefix="/api/menu", tags=["menu"])

class MenuItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    price: float
    image_url: Optional[str] = None
    available: bool = True

class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    available: Optional[bool] = None

@router.get("/", response_model=List[dict])
async def get_menu_items(category: Optional[str] = None, available_only: bool = False):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM menu_items WHERE 1=1"
    params = []
    
    if category:
        query += " AND category = ?"
        params.append(category)
        
    if available_only:
        query += " AND available = 1"
        
    cursor.execute(query, params)
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items

@router.get("/{item_id}")
async def get_menu_item(item_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu_items WHERE id = ?", (item_id,))
    item = cursor.fetchone()
    conn.close()
    
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return dict(item)

@router.post("/", dependencies=[Depends(check_role(["admin", "manager"]))])
async def create_menu_item(item: MenuItemCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO menu_items (name, description, category, price, image_url, available) VALUES (?, ?, ?, ?, ?, ?)",
        (item.name, item.description, item.category, item.price, item.image_url, item.available)
    )
    conn.commit()
    item_id = cursor.lastrowid
    conn.close()
    
    return {**item.dict(), "id": item_id}

@router.put("/{item_id}", dependencies=[Depends(check_role(["admin", "manager"]))])
async def update_menu_item(item_id: int, item: MenuItemUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute("SELECT id FROM menu_items WHERE id = ?", (item_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    update_data = item.dict(exclude_unset=True)
    if not update_data:
        conn.close()
        return {"message": "No changes provided"}
        
    set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
    values = list(update_data.values())
    values.append(item_id)
    
    cursor.execute(f"UPDATE menu_items SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
    
    return {"message": "Menu item updated successfully"}

@router.delete("/{item_id}", dependencies=[Depends(check_role(["admin"]))])
async def delete_menu_item(item_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Menu item not found")
        
    conn.commit()
    conn.close()
    return {"message": "Menu item deleted"}

@router.patch("/{item_id}/availability", dependencies=[Depends(check_role(["admin", "manager"]))])
async def toggle_availability(item_id: int, available: bool):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE menu_items SET available = ? WHERE id = ?", (available, item_id))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Menu item not found")
        
    conn.commit()
    conn.close()
    return {"message": f"Availability set to {available}"}
