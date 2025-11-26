from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
from database import get_db_connection

router = APIRouter(prefix="/api/kds", tags=["kds"])

# Simple in-memory event queue for MVP
# In production, use Redis or similar
msg_queue = asyncio.Queue()

async def event_generator():
    while True:
        # Check for new messages
        if not msg_queue.empty():
            msg = await msg_queue.get()
            yield f"data: {json.dumps(msg)}\n\n"
        
        # Keep connection alive
        await asyncio.sleep(1)
        yield ": keep-alive\n\n"

@router.get("/stream")
async def message_stream(request: Request):
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Helper to broadcast updates
async def broadcast_update(message: dict):
    await msg_queue.put(message)

# Re-export KOT status updates here if we want to trigger broadcasts
# Or we can just call broadcast_update from the KOT/Orders routes
# For MVP, let's add a trigger endpoint or just rely on polling if SSE is too complex without Redis
# Actually, let's make a simple polling endpoint for "active" KOTs as a fallback
# And try to use the stream.

@router.get("/active")
async def get_active_kots():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get KOTs that are not completed
    query = """
        SELECT k.*, t.table_number 
        FROM kot k 
        JOIN orders o ON k.order_id = o.id 
        JOIN tables t ON o.table_id = t.id 
        WHERE k.status IN ('pending', 'preparing', 'ready')
        ORDER BY k.created_at ASC
    """
    
    cursor.execute(query)
    kots = []
    for row in cursor.fetchall():
        kot = dict(row)
        kot['items'] = json.loads(kot['items'])
        kots.append(kot)
        
    conn.close()
    return kots
