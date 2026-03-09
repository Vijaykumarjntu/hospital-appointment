from datetime import time, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio

from src.database.models import (
    Patient, Doctor, DoctorSchedule, 
    Appointment, TimeSlot
)
from src.database.connection import AsyncSessionLocal

async def seed_doctors(session: AsyncSession):
    """Seed doctor data"""
    doctors = [
        Doctor(
            name="Dr. Sharma",
            specialization="Cardiologist",
            time_slot_duration=30,
            buffer_time=5
        ),
        Doctor(
            name="Dr. Patel",
            specialization="General Physician",
            time_slot_duration=30,
            buffer_time=5
        ),
        Doctor(
            name="Dr. Kumar",
            specialization="Pediatrician",
            time_slot_duration=30,
            buffer_time=5
        ),
        Doctor(
            name="Dr. Priya",
            specialization="Dermatologist",
            time_slot_duration=30,
            buffer_time=5
        ),
    ]
    
    session.add_all(doctors)
    await session.commit()
    
    print(f"✅ Seeded {len(doctors)} doctors")
    return doctors

async def seed_schedules(session: AsyncSession, doctors):
    """Seed doctor schedules (Mon-Sat, 9 AM - 5 PM)"""
    schedules = []
    
    for doctor in doctors:
        # Monday to Saturday (1-6)
        for day in range(1, 7):  # 1=Monday, 6=Saturday
            schedule = DoctorSchedule(
                doctor_id=doctor.id,
                day_of_week=day,
                start_time=time(9, 0),  # 9 AM
                end_time=time(17, 0),   # 5 PM
                is_available=True
            )
            schedules.append(schedule)
    
    session.add_all(schedules)
    await session.commit()
    print(f"✅ Seeded schedules for {len(doctors)} doctors")

async def seed_patients(session: AsyncSession):
    """Seed sample patients"""
    patients = [
        Patient(
            phone_number="+919876543210",
            name="Rajesh Kumar",
            preferred_language="hi",  # Hindi
            mdata={"city": "Mumbai"}
        ),
        Patient(
            phone_number="+919876543211",
            name="Priya Singh",
            preferred_language="en",  # English
            mdata={"city": "Delhi"}
        ),
        Patient(
            phone_number="+919876543212",
            name="Karthik",
            preferred_language="ta",  # Tamil
            mdata={"city": "Chennai"}
        ),
    ]
    
    session.add_all(patients)
    await session.commit()
    print(f"✅ Seeded {len(patients)} patients")
    return patients

async def seed_appointments(session: AsyncSession, patients, doctors):
    """Seed some past and future appointments"""
    appointments = []
    
    # Past appointment (completed)
    past_date = datetime.now() - timedelta(days=5)
    appointments.append(
        Appointment(
            patient_id=patients[0].id,
            doctor_id=doctors[0].id,
            appointment_time=past_date.replace(hour=10, minute=0),
            status="completed"
        )
    )
    
    # Future appointment (scheduled)
    future_date = datetime.now() + timedelta(days=2)
    appointments.append(
        Appointment(
            patient_id=patients[0].id,
            doctor_id=doctors[0].id,
            appointment_time=future_date.replace(hour=15, minute=0),
            status="scheduled"
        )
    )
    
    # Another future appointment
    future_date2 = datetime.now() + timedelta(days=3)
    appointments.append(
        Appointment(
            patient_id=patients[1].id,
            doctor_id=doctors[1].id,
            appointment_time=future_date2.replace(hour=11, minute=30),
            status="scheduled"
        )
    )
    
    session.add_all(appointments)
    await session.commit()
    print(f"✅ Seeded {len(appointments)} appointments")
    return appointments

async def seed_time_slots(session: AsyncSession, doctors, days_ahead=14):
    """Pre-generate time slots for next N days"""
    slots = []
    
    for doctor in doctors:
        # Get doctor's schedule
        stmt = select(DoctorSchedule).where(DoctorSchedule.doctor_id == doctor.id)
        result = await session.execute(stmt)
        schedules = result.scalars().all()
        
        # Generate slots for next 14 days
        for day_offset in range(1, days_ahead + 1):
            slot_date = datetime.now() + timedelta(days=day_offset)
            weekday = slot_date.isoweekday()  # 1=Monday, 7=Sunday
            
            # Check if doctor works this day
            schedule = next(
                (s for s in schedules if s.day_of_week == weekday), 
                None
            )
            
            if schedule:
                # Generate slots every 30 minutes
                current_time = datetime.combine(slot_date.date(), schedule.start_time)
                end_time = datetime.combine(slot_date.date(), schedule.end_time)
                
                while current_time < end_time:
                    # Check if slot already exists (avoid duplicates)
                    stmt = select(TimeSlot).where(
                        TimeSlot.doctor_id == doctor.id,
                        TimeSlot.slot_time == current_time
                    )
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()
                    
                    if not existing:
                        slot = TimeSlot(
                            doctor_id=doctor.id,
                            slot_time=current_time,
                            is_booked=False
                        )
                        slots.append(slot)
                    
                    current_time += timedelta(minutes=doctor.time_slot_duration)
    
    # Batch insert
    if slots:
        session.add_all(slots)
        await session.commit()
        print(f"✅ Seeded {len(slots)} time slots")

async def seed_all():
    """Run all seed functions"""
    async with AsyncSessionLocal() as session:
        # Clear existing data (optional - careful in production!)
        # await session.execute("TRUNCATE TABLE time_slots, appointments, doctor_schedules, doctors, patients CASCADE")
        
        doctors = await seed_doctors(session)
        await seed_schedules(session, doctors)
        patients = await seed_patients(session)
        await seed_appointments(session, patients, doctors)
        await seed_time_slots(session, doctors)
        
    print("\n✅✅✅ Database seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_all())