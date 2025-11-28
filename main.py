from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import init_db
from routes import auth, menu, inventory, tables, orders, kot, kds, sales

# Initialize Database
init_db()

app = FastAPI(title="Chai-Pani Restaurant Management System")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for MVP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["http://localhsost:3000","https://chai-pani-new.onrender.com"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(menu.router)
app.include_router(inventory.router)
app.include_router(tables.router)
app.include_router(orders.router)
app.include_router(kot.router)
app.include_router(kds.router)
app.include_router(sales.router)

# Mount static files for frontend
app.mount("/", StaticFiles(directory="public", html=True), name="public")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
