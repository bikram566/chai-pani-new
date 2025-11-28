from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any
import json
import io
import csv
from datetime import datetime, timedelta
from middleware.auth import check_role
from database import get_db_connection

router = APIRouter(prefix="/api/sales", tags=["sales"])

@router.get("/stats", dependencies=[Depends(check_role(["admin", "manager"]))])
async def get_sales_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get today's start
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    stats = {
        "today": 0.0,
        "week": 0.0,
        "month": 0.0,
        "total_orders_today": 0
    }
    
    # Fetch all completed/paid orders
    # Assuming 'paid' is the final status for revenue
    cursor.execute("SELECT total_amount, created_at FROM orders WHERE status = 'paid'")
    rows = cursor.fetchall()
    
    for row in rows:
        amount = row['total_amount']
        created_at = datetime.strptime(row['created_at'], '%Y-%m-%d %H:%M:%S')
        
        if created_at >= today:
            stats["today"] += amount
            stats["total_orders_today"] += 1
            
        if created_at >= week_start:
            stats["week"] += amount
            
        if created_at >= month_start:
            stats["month"] += amount
            
    conn.close()
    return stats

@router.get("/top-items", dependencies=[Depends(check_role(["admin", "manager"]))])
async def get_top_items(limit: int = 5):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch all completed/paid orders
    cursor.execute("SELECT items FROM orders WHERE status IN ('paid', 'completed')")
    rows = cursor.fetchall()
    
    item_counts = {}
    
    for row in rows:
        items = json.loads(row['items'])
        for item in items:
            name = item['name']
            quantity = item['quantity']
            if name in item_counts:
                item_counts[name] += quantity
            else:
                item_counts[name] = quantity
                
    # Sort by quantity desc
    sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Format for response
    top_items = [{"name": name, "quantity": quantity} for name, quantity in sorted_items[:limit]]
    
    conn.close()
    return top_items

@router.get("/daily-report", dependencies=[Depends(check_role(["admin", "manager"]))])
async def download_daily_report(date: str = None):
    """
    Download daily sales report as CSV showing sales per item.
    Date format: YYYY-MM-DD (defaults to today)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Parse date or use today
    if date:
        try:
            report_date = datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        report_date = datetime.now()
    
    # Get start and end of the day
    start_of_day = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    
    # Fetch paid orders for the day
    cursor.execute(
        "SELECT items, total_amount, created_at FROM orders WHERE status = 'paid' AND created_at >= ? AND created_at < ?",
        (start_of_day.strftime('%Y-%m-%d %H:%M:%S'), end_of_day.strftime('%Y-%m-%d %H:%M:%S'))
    )
    orders = cursor.fetchall()
    
    # Aggregate items
    item_sales = {}
    
    for order in orders:
        items = json.loads(order['items'])
        for item in items:
            name = item['name']
            quantity = item['quantity']
            price = item['price']
            revenue = quantity * price
            
            if name in item_sales:
                item_sales[name]['quantity'] += quantity
                item_sales[name]['revenue'] += revenue
            else:
                item_sales[name] = {
                    'quantity': quantity,
                    'revenue': revenue
                }
    
    conn.close()
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Date', 'Item Name', 'Quantity Sold', 'Revenue (₹)'])
    
    # Write data
    date_str = report_date.strftime('%Y-%m-%d')
    for item_name, data in sorted(item_sales.items()):
        writer.writerow([
            date_str,
            item_name,
            data['quantity'],
            f"{data['revenue']:.2f}"
        ])
    
    # If no data, add a note
    if not item_sales:
        writer.writerow([date_str, 'No sales data', 0, '0.00'])
    
    # Prepare CSV for download
    output.seek(0)
    
    # Create filename
    filename = f"sales_report_{date_str}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
