import asyncio
from sqlalchemy import select
from src.database.connection import AsyncSessionLocal
from src.database.models import Patient,Doctor

async def patients_list():
    async with AsyncSessionLocal() as db:
        # Execute the select query
        result = await db.execute(select(Patient))
        result1 = await db.execute(select(Doctor))
        patients = result.scalars().all()
        doctors = result1.scalars().all()
        print("=" * 50)
        print("PATIENTS IN DATABASE")
        print("=" * 50)
        
        if not patients:
            print("No patients found!")
            return
        
        for p in patients:
            print(f"ID: {p.id}")
            print(f"Name: {p.name}")
            print(f"Phone: {p.phone_number}")
            print(f"Language: {p.preferred_language}")
            print("-" * 30)

        print("=" * 50)
        print("Doctors IN DATABASE")
        print("=" * 50)

        if not patients:
            print("No doctors found!")
            return

        for p in doctors:
            print(f"ID: {p.id}")
            print(f"Name: {p.name}")
            print(f"specialization: {p.specialization}")
            
            print("-" * 30)

if __name__ == "__main__":
    asyncio.run(patients_list())