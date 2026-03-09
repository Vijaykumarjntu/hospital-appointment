from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from contextlib import asynccontextmanager

from src.config import settings
from src.database.connection import init_db, close_db, get_db, redis_client
from src.database.models import Patient, Doctor

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"Starting {settings.APP_NAME}...")
    await init_db()
    
    # Test Redis
    await redis_client.set("test_key", "Redis is working!")
    test_value = await redis_client.get("test_key")
    print(f"✅ {test_value}")
    
    yield
    
    # Shutdown
    await close_db()
    print("👋 Shutdown complete")

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "environment": settings.ENVIRONMENT
    }

@app.get("/health")
async def health_check():
    # Check PostgreSQL
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {e}"
    
    # Check Redis
    try:
        await redis_client.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {e}"
    
    return {
        "status": "ok",
        "database": db_status,
        "redis": redis_status
    }

@app.get("/patients")
async def get_patients(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Patient))
    patients = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "phone": p.phone_number,
            "language": p.preferred_language
        }
        for p in patients
    ]

@app.get("/doctors/{doctor_id}/slots/{date}")
async def get_doctor_slots(
    doctor_id: int, 
    date: str,
    db: AsyncSession = Depends(get_db)
):
    """Get available slots for a doctor on a specific date"""
    from datetime import datetime
    
    target_date = datetime.strptime(date, "%Y-%m-%d").date()
    
    stmt = select(TimeSlot).where(
        TimeSlot.doctor_id == doctor_id,
        TimeSlot.slot_time.cast(Date) == target_date,
        TimeSlot.is_booked == False
    ).order_by(TimeSlot.slot_time)
    
    result = await db.execute(stmt)
    slots = result.scalars().all()
    
    return [
        {
            "id": s.id,
            "time": s.slot_time.strftime("%I:%M %p"),
            "datetime": s.slot_time.isoformat()
        }
        for s in slots
    ]

# Import for type hints
from sqlalchemy import Date
from src.database.connection import AsyncSessionLocal
from src.database.models import TimeSlot