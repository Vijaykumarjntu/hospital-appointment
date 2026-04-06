# src/scheduling/conflict_resolver.py
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import TimeSlot, Appointment

class ConflictResolver:
    """Handle appointment conflicts and double-booking prevention"""
    
    @staticmethod
    async def check_and_lock_slot(db: AsyncSession, slot_id: int, patient_id: int) -> dict:
        """
        Check if slot is available and lock it atomically
        Returns: {'success': True/False, 'message': '...', 'slot': slot_object}
        """
        # Use SELECT FOR UPDATE to lock the row
        result = await db.execute(
            select(TimeSlot)
            .where(TimeSlot.id == slot_id)
            .with_for_update()  # Locks the row!
        )
        slot = result.scalar_one_or_none()
        
        if not slot:
            return {'success': False, 'message': 'Slot not found'}
        
        if slot.is_booked:
            return {'success': False, 'message': 'Slot already booked'}
        
        # Lock it
        slot.is_booked = True
        slot.booked_by_patient_id = patient_id
        
        await db.flush()
        
        return {'success': True, 'message': 'Slot locked', 'slot': slot}
    
    @staticmethod
    async def find_alternative_slots(db: AsyncSession, doctor_id: int, preferred_time: datetime, buffer_hours: int = 2) -> list:
        """Find alternative slots near preferred time"""
        
        # Search +/- buffer_hours
        start_window = preferred_time - timedelta(hours=buffer_hours)
        end_window = preferred_time + timedelta(hours=buffer_hours)
        
        result = await db.execute(
            select(TimeSlot)
            .where(
                TimeSlot.doctor_id == doctor_id,
                TimeSlot.slot_time.between(start_window, end_window),
                TimeSlot.is_booked == False
            )
            .order_by(TimeSlot.slot_time)
            .limit(5)
        )
        
        return result.scalars().all()
    
    @staticmethod
    async def book_slot_transaction(db: AsyncSession, slot_id: int, patient_id: int, appointment_data: dict) -> dict:
        """
        Complete booking with transaction
        Everything succeeds or everything fails
        """
        try:
            # 1. Lock and check slot
            result = await ConflictResolver.check_and_lock_slot(db, slot_id, patient_id)
            
            if not result['success']:
                await db.rollback()
                return result
            
            # 2. Create appointment
            appointment = Appointment(
                patient_id=patient_id,
                doctor_id=result['slot'].doctor_id,
                appointment_time=result['slot'].slot_time,
                status='scheduled',
                **appointment_data
            )
            db.add(appointment)
            
            # 3. Commit everything
            await db.commit()
            
            return {
                'success': True, 
                'message': 'Appointment booked successfully',
                'appointment_id': appointment.id,
                'slot': result['slot']
            }
            
        except Exception as e:
            await db.rollback()
            return {'success': False, 'message': f'Booking failed: {str(e)}'}