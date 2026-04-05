# src/outbound/call_handler.py
from twilio.twiml.voice_response import VoiceResponse, Gather
from fastapi import Request, Response
from src.voice.free_tts import FreeTextToSpeech
from src.voice.free_stt import FreeSpeechToText
import base64

class OutboundCallHandler:
    """Handle outbound call interactions"""
    
    def __init__(self):
        self.tts = FreeTextToSpeech()
        self.stt = FreeSpeechToText()
        self.active_calls = {}
    
    async def handle_outbound_response(self, request: Request) -> Response:
        """Handle patient's response during outbound call"""
        form = await request.form()
        call_sid = form.get("CallSid")
        speech_result = form.get("SpeechResult")
        
        call_data = self.active_calls.get(call_sid, {})
        
        response = VoiceResponse()
        
        if not speech_result:
            # No response, repeat the message
            gather = Gather(input="speech", timeout=3)
            gather.say(
                "Hello, this is a reminder about your appointment tomorrow. "
                "Please say confirm to confirm, reschedule to change, or cancel to cancel.",
                language="en-US"
            )
            response.append(gather)
        else:
            # Process speech result
            speech_lower = speech_result.lower()
            
            if "confirm" in speech_lower:
                response.say("Great! Your appointment is confirmed. Thank you. Goodbye!")
                # Update database
                await self.update_appointment_status(call_data.get("appointment_id"), "confirmed")
                
            elif "reschedule" in speech_lower:
                response.say("We'll contact you shortly to reschedule. Thank you. Goodbye!")
                await self.update_appointment_status(call_data.get("appointment_id"), "needs_reschedule")
                
            elif "cancel" in speech_lower:
                response.say("Your appointment has been cancelled. Goodbye!")
                await self.update_appointment_status(call_data.get("appointment_id"), "cancelled")
                
            else:
                response.say("I didn't understand. Please call us back. Goodbye!")
            
            response.hangup()
        
        return Response(content=str(response), media_type="application/xml")
    
    async def update_appointment_status(self, appointment_id: int, status: str):
        """Update appointment status in database"""
        from sqlalchemy import update
        from src.database.connection import AsyncSessionLocal
        from src.database.models import Appointment
        
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Appointment)
                .where(Appointment.id == appointment_id)
                .values(
                    reminder_called=True,
                    reminder_confirmed=(status == "confirmed"),
                    status=status if status in ["cancelled", "needs_reschedule"] else Appointment.status
                )
            )
            await db.commit()