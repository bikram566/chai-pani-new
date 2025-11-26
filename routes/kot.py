from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
from middleware.auth import check_role
from database import get_db_connection

router = APIRouter(prefix="/api/kot", tags=["kot"])

class KOTUpdate(BaseModel):
    status: str # pending, preparing, ready, completed

@router.get("/")
async def get_kots(status: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT k.*, t.table_number FROM kot k JOIN orders o ON k.order_id = o.id JOIN tables t ON o.table_id = t.id WHERE 1=1"
    params = []
    
    if status:
        query += " AND k.status = ?"
        params.append(status)
        
    query += " ORDER BY k.created_at ASC"
    
    cursor.execute(query, params)
    kots = []
    for row in cursor.fetchall():
        kot = dict(row)
        kot['items'] = json.loads(kot['items'])
        kots.append(kot)
        
    conn.close()
    return kots

@router.get("/{kot_id}")
async def get_kot(kot_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM kot WHERE id = ?", (kot_id,))
    kot = cursor.fetchone()
    conn.close()
    
    if not kot:
        raise HTTPException(status_code=404, detail="KOT not found")
        
    kot_dict = dict(kot)
    kot_dict['items'] = json.loads(kot_dict['items'])
    return kot_dict

@router.patch("/{kot_id}/status", dependencies=[Depends(check_role(["admin", "manager", "kitchen"]))])
async def update_kot_status(kot_id: int, status_update: KOTUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE kot SET status = ? WHERE id = ?", (status_update.status, kot_id))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="KOT not found")
        
    conn.commit()
    conn.close()
    return {"message": f"KOT status updated to {status_update.status}"}
