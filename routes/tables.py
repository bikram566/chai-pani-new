from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from middleware.auth import check_role, get_current_active_user
from database import get_db_connection

router = APIRouter(prefix="/api/tables", tags=["tables"])

class TableCreate(BaseModel):
    table_number: str
    capacity: int

class TableUpdate(BaseModel):
    capacity: Optional[int] = None
    status: Optional[str] = None # available, occupied, reserved

@router.get("/")
async def get_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tables")
    tables = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tables

@router.post("/", dependencies=[Depends(check_role(["admin", "manager"]))])
async def create_table(table: TableCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO tables (table_number, capacity) VALUES (?, ?)",
            (table.table_number, table.capacity)
        )
        conn.commit()
        table_id = cursor.lastrowid
    except Exception:
        conn.close()
        raise HTTPException(status_code=400, detail="Table number already exists")
        
    conn.close()
    return {**table.dict(), "id": table_id, "status": "available"}

@router.put("/{table_id}", dependencies=[Depends(check_role(["admin", "manager", "staff"]))])
async def update_table(table_id: int, table: TableUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    update_data = table.dict(exclude_unset=True)
    if not update_data:
        conn.close()
        return {"message": "No changes provided"}
        
    set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
    values = list(update_data.values())
    values.append(table_id)
    
    cursor.execute(f"UPDATE tables SET {set_clause} WHERE id = ?", values)
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Table not found")
        
    conn.commit()
    conn.close()
    return {"message": "Table updated"}

@router.delete("/{table_id}", dependencies=[Depends(check_role(["admin", "manager"]))])
async def delete_table(table_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tables WHERE id = ?", (table_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Table not found")
    conn.commit()
    conn.close()
    return {"message": "Table deleted"}
