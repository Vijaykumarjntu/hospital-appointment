# src/outbound/campaign_manager.py
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import AsyncSessionLocal
from src.database.models import Appointment, Patient, Doctor
from src.config import settings

class CampaignManager:
    """Manage outbound calling campaigns"""
    
    def __init__(self):
        self.active_campaigns = {}
        self.call_queue = []
        self.is_running = False
        
    async def start_reminder_campaign(self):
        """Start daily reminder campaign for tomorrow's appointments"""
        print("📞 Starting reminder campaign...")
        
        # Find appointments for tomorrow
        tomorrow = datetime.now().date() + timedelta(days=1)
        
        async with AsyncSessionLocal() as db:
            # Get all scheduled appointments for tomorrow
            stmt = select(Appointment, Patient, Doctor).join(
                Patient, Appointment.patient_id == Patient.id
            ).join(
                Doctor, Appointment.doctor_id == Doctor.id
            ).where(
                Appointment.appointment_time.cast(Date) == tomorrow,
                Appointment.status == "scheduled",
                Appointment.reminder_called == False
            )
            
            result = await db.execute(stmt)
            appointments = result.all()
            
            print(f"Found {len(appointments)} appointments for tomorrow")
            
            # Queue calls
            for apt, patient, doctor in appointments:
                await self.queue_reminder_call(
                    appointment_id=apt.id,
                    patient_id=patient.id,
                    phone=patient.phone_number,
                    patient_name=patient.name,
                    doctor_name=doctor.name,
                    appointment_time=apt.appointment_time,
                    language=patient.preferred_language or "en"
                )
    
    async def queue_reminder_call(self, **kwargs):
        """Add a reminder call to the queue"""
        call_data = {
            "type": "reminder",
            "created_at": datetime.now().isoformat(),
            "status": "queued",
            **kwargs
        }
        self.call_queue.append(call_data)
        print(f"📞 Queued reminder for {kwargs.get('patient_name')} at {kwargs.get('phone')}")
    
    async def process_call_queue(self, rate_per_minute: int = 5):
        """Process queued calls with rate limiting"""
        self.is_running = True
        
        while self.is_running and self.call_queue:
            # Process calls in batches
            batch = self.call_queue[:rate_per_minute]
            self.call_queue = self.call_queue[rate_per_minute:]
            
            # Process batch concurrently
            tasks = [self.make_outbound_call(call) for call in batch]
            await asyncio.gather(*tasks)
            
            # Wait for rate limit (60 seconds / rate_per_minute)
            if self.call_queue:
                await asyncio.sleep(60 / rate_per_minute)
        
        self.is_running = False
    
    async def make_outbound_call(self, call_data: Dict):
        """Make the actual outbound call"""
        print(f"📞 Calling {call_data.get('patient_name')} at {call_data.get('phone')}")
        
        # Update call status
        call_data["status"] = "calling"
        call_data["called_at"] = datetime.now().isoformat()
        
        # Here we would integrate with Twilio/SIP
        # For now, simulate the call
        await self.simulate_call(call_data)
    
    async def simulate_call(self, call_data: Dict):
        """Simulate an outbound call (for testing without Twilio)"""
        print(f"🎤 Simulating call to {call_data['patient_name']}")
        
        # Simulate call duration
        await asyncio.sleep(2)
        
        # Simulate patient response (for demo)
        # In production, this would be real speech recognition
        import random
        responses = ["confirm", "reschedule", "voicemail", "no_answer"]
        outcome = random.choice(responses)
        
        await self.handle_call_response(call_data, outcome)
    
    async def handle_call_response(self, call_data: Dict, outcome: str):
        """Handle patient's response to the call"""
        print(f"📝 Call outcome for {call_data['patient_name']}: {outcome}")
        
        async with AsyncSessionLocal() as db:
            if outcome == "confirm":
                # Update appointment as confirmed
                await db.execute(
                    update(Appointment)
                    .where(Appointment.id == call_data["appointment_id"])
                    .values(
                        reminder_called=True,
                        reminder_confirmed=True,
                        status="confirmed"
                    )
                )
                print(f"✅ {call_data['patient_name']} confirmed appointment")
                
            elif outcome == "reschedule":
                # Mark for reschedule follow-up
                await db.execute(
                    update(Appointment)
                    .where(Appointment.id == call_data["appointment_id"])
                    .values(
                        reminder_called=True,
                        status="needs_reschedule"
                    )
                )
                print(f"🔄 {call_data['patient_name']} wants to reschedule")
                
            elif outcome == "voicemail":
                # Leave voicemail (handled by Twilio)
                await db.execute(
                    update(Appointment)
                    .where(Appointment.id == call_data["appointment_id"])
                    .values(reminder_called=True)
                )
                print(f"📼 Left voicemail for {call_data['patient_name']}")
                
            else:  # no_answer
                print(f"⚠️ No answer from {call_data['patient_name']}")
            
            await db.commit()
        
        # Update call data
        call_data["status"] = "completed"
        call_data["outcome"] = outcome
        call_data["completed_at"] = datetime.now().isoformat()