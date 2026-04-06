# create_appointment.py
import asyncio
from datetime import datetime, timedelta
from src.database.connection import AsyncSessionLocal
from src.database.models import Appointment, Patient, Doctor
from sqlalchemy import select

async def create_appointment():
    async with AsyncSessionLocal() as db:
        # Get first patient
        patient_result = await db.execute(select(Patient).limit(1))
        patient = patient_result.scalar_one()
        print(f'Found patient: {patient.name} ({patient.phone_number})')
        
        # Get first doctor
        doctor_result = await db.execute(select(Doctor).limit(1))
        doctor = doctor_result.scalar_one()
        print(f'Found doctor: {doctor.name}')
        
        # Create appointment for TOMORROW at 10 AM
        tomorrow = datetime.now() + timedelta(days=1)
        appointment_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_time=appointment_time,
            status='scheduled',
            reminder_called=False,
            mdata={}
        )
        db.add(appointment)
        await db.commit()
        
        print("\n" + "="*50)
        print("APPOINTMENT CREATED SUCCESSFULLY!")
        print("="*50)
        print(f"Patient: {patient.name}")
        print(f"Doctor: {doctor.name}")
        print(f"Date/Time: {appointment_time.strftime('%Y-%m-%d %I:%M %p')}")
        print(f"Phone will ring at: {patient.phone_number}")
        print("\nRun: python test_outbound.py to get the call!")

if __name__ == "__main__":
    asyncio.run(create_appointment())