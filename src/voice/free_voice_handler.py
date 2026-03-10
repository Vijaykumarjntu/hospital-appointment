from fastapi import Request, Response, WebSocket, WebSocketDisconnect
import json
import base64
import tempfile
import os
from typing import Optional
import asyncio

from src.voice.free_stt import FreeSpeechToText
from src.voice.free_tts import FreeTextToSpeech
from src.voice.sip_handler import SimpleSIPHandler
from src.database.connection import AsyncSessionLocal

from src.llm.mistral_handler import MistralHandler



class FreeVoiceHandler:
    """Unified voice handler using free open-source components"""
    
    def __init__(self):
        # Initialize STT (Whisper)
        print("Initializing Free STT (Whisper)...")
        self.stt = FreeSpeechToText(model_size="base")  # Use "tiny" for faster, "large" for better
        
        # Initialize TTS (Coqui)
        print("Initializing Free TTS (Coqui)...")
        try:
            # Try multilingual model first
            self.tts = FreeTextToSpeech("tts_models/multilingual/multi-dataset/your_tts")
              # Initialize Mistral
            self.llm = MistralHandler()

            self.db_session = AsyncSessionLocal
        
            print("✅ Free Voice Handler with LLM initialized")
    
        
        except:
            # Fallback to English model
            print("Multilingual model failed, falling back to English")
            self.tts = FreeTextToSpeech("tts_models/en/ljspeech/tacotron2-DDC")
        
        # Initialize SIP (for real calls)
        self.sip = SimpleSIPHandler()
        
        # Active sessions
        self.active_sessions = {}
        
        print("✅ Free Voice Handler initialized")

    async def _process_with_llm(self, text: str, session: dict) -> dict:
        """Process user input with LLM"""
        # Extract intent
        intent_data = await self.llm.extract_intent(text, session.get("language", "en"))
        
        # If we have doctor/date/time, store in session
        if intent_data.get("doctor"):
            session["context"]["doctor"] = intent_data["doctor"]
        if intent_data.get("date"):
            session["context"]["date"] = intent_data["date"]
        if intent_data.get("time"):
            session["context"]["time"] = intent_data["time"]

         # Handle different intents
        if intent_data["intent"] == "book":
            return await self._handle_booking_intent(session, intent_data)
        elif intent_data["intent"] == "cancel":
            return await self._handle_cancel_intent(session, intent_data)
        elif intent_data["intent"] == "greeting":
            session["state"] = "conversation"
            return await self.llm.generate_response(text, "greeting", session, language=session["language"])
        else:
            return await self.llm.generate_response(text, "unknown", session, language=session["language"])
    
    async def _handle_booking_intent(self, session: dict, intent: dict) -> str:
        """Handle booking flow with real slot checking"""
        
        # If we have all info, check slots
        if intent.get("doctor") and intent.get("date") and intent.get("time"):
            # Check if slot is available in database
            available = await self._check_slot_availability(
                intent["doctor"], 
                intent["date"], 
                intent["time"]
            )
            if available:
                # Book it!
                booking_result = await self._book_appointment(
                    session.get("patient_id"),
                    intent["doctor"],
                    intent["date"],
                    intent["time"]
                )
                if booking_result["success"]:
                    session["state"] = "confirmed"
                    return f"Great! Your appointment with {intent['doctor']} on {intent['date']} at {intent['time']} is confirmed. Your confirmation number is {booking_result['appointment_id']}."
                else:
                    return "I'm sorry, that slot was just taken. Let me find another for you."
            else:
                # Find alternatives
                alternatives = await self._find_alternative_slots(
                    intent["doctor"],
                    intent["date"],
                    intent["time"]
                )
                if alternatives:
                    times = [a.strftime("%I:%M %p") for a in alternatives]
                    return f"That time isn't available. Dr. {intent['doctor']} has these slots: {', '.join(times)}. Which works for you?"
                else:
                    return f"I don't see any availability for Dr. {intent['doctor']} on that day. Would you like to try another doctor or date?"
        
        # Missing info - ask for it
        elif not intent.get("doctor"):
            return "Which doctor would you like to see? We have Dr. Sharma, Dr. Patel, Dr. Kumar, and Dr. Priya."
        elif not intent.get("date"):
            return f"What date would you like to see Dr. {session['context'].get('doctor', 'the doctor')}?"
        elif not intent.get("time"):
            # Check available times for this doctor/date
            slots = await self._get_available_times(
                session["context"].get("doctor"),
                session["context"].get("date")
            )
            if slots:
                times = [s.strftime("%I:%M %p") for s in slots]
                return f"Available times on {session['context'].get('date')}: {', '.join(times)}. Which works for you?"
            else:
                return f"Sorry, no slots available on that date. Would you like to try another day?"
        
        return "How can I help you with your appointment?"


    async def _check_slot_availability(self, doctor: str, date: str, time: str) -> bool:
        """Check real database for slot availability"""
        async with self.db_session() as db:
            from src.database.models import TimeSlot, Doctor
            from sqlalchemy import select
            
            # Get doctor ID
            doctor_result = await db.execute(
                select(Doctor).where(Doctor.name == doctor)
            )
            doctor_obj = doctor_result.scalar_one_or_none()
            
            if not doctor_obj:
                return False
            
            from datetime import datetime
            slot_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            
            slot_result = await db.execute(
                select(TimeSlot).where(
                    TimeSlot.doctor_id == doctor_obj.id,
                    TimeSlot.slot_time == slot_time,
                    TimeSlot.is_booked == False
                )
            )
            slot = slot_result.scalar_one_or_none()
            
            return slot is not None

    async def _book_appointment(self, patient_id: int, doctor: str, date: str, time: str) -> dict:
        """Actually book the appointment in database"""
        async with self.db_session() as db:
            from src.database.models import TimeSlot, Doctor, Appointment
            from sqlalchemy import select
            from datetime import datetime
            
            try:
                # Get doctor
                doctor_result = await db.execute(
                    select(Doctor).where(Doctor.name == doctor)
                )
                doctor_obj = doctor_result.scalar_one()
                 # Get slot
                slot_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
                slot_result = await db.execute(
                    select(TimeSlot).where(
                        TimeSlot.doctor_id == doctor_obj.id,
                        TimeSlot.slot_time == slot_time,
                        TimeSlot.is_booked == False
                    ).with_for_update()
                )
                slot = slot_result.scalar_one()
                
                # Book slot
                slot.is_booked = True
                slot.booked_by_patient_id = patient_id

                # Create appointment
                appointment = Appointment(
                    patient_id=patient_id,
                    doctor_id=doctor_obj.id,
                    appointment_time=slot_time,
                    status="scheduled"
                )
                db.add(appointment)
                await db.commit()
                
                return {"success": True, "appointment_id": appointment.id}
            except Exception as e:
                await db.rollback()
                print(f"Booking error: {e}")
                return {"success": False, "error": str(e)}   

    async def _get_available_times(self, doctor: str, date: str) -> list:
        """Get available times for a doctor on a specific date"""
        async with self.db_session() as db:
            from src.database.models import TimeSlot, Doctor
            from sqlalchemy import select
            
            doctor_result = await db.execute(
                select(Doctor).where(Doctor.name == doctor)
            )
            doctor_obj = doctor_result.scalar_one_or_none()
            
            if not doctor_obj:
                return []
            from datetime import datetime
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            
            slots_result = await db.execute(
                select(TimeSlot).where(
                    TimeSlot.doctor_id == doctor_obj.id,
                    TimeSlot.slot_time.cast(Date) == target_date,
                    TimeSlot.is_booked == False
                ).order_by(TimeSlot.slot_time)
            )
            slots = slots_result.scalars().all()
            
            return [s.slot_time for s in slots]
            
    async def handle_webhook(self, request: Request) -> Response:
        """Handle webhook from SIP server"""
        try:
            data = await request.json()
            audio_url = data.get("audio_url")
            session_id = data.get("session_id")
            
            # Download audio (simplified)
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(audio_url)
                audio_bytes = response.content
            
            # Process with Whisper
            transcript = self.stt.transcribe(audio_bytes)
            
            # Get or create session
            session = self.active_sessions.get(session_id, {
                "state": "greeting",
                "language": transcript["language"],
                "context": {}
            })
            
            # Simple response logic (will be replaced with LLM)
            response_text = self._generate_response(transcript["text"], session)
            
            # Convert to speech
            audio_response = self.tts.synthesize(response_text, language=session["language"])
            
            # Update session
            self.active_sessions[session_id] = session
            
            return Response(
                content=base64.b64encode(audio_response).decode(),
                media_type="audio/wav"
            )
            
        except Exception as e:
            print(f"Webhook error: {e}")
            return Response(status_code=500)
    
    async def handle_websocket(self, websocket: WebSocket):
        """Handle WebSocket connection for real-time audio"""
        await websocket.accept()
        session_id = str(id(websocket))
        
        self.active_sessions[session_id] = {
            "state": "greeting",
            "language": "en",
            "context": {}
        }
        
        try:
            while True:
                # Receive audio chunk
                data = await websocket.receive_bytes()
                
                # Transcribe with Whisper
                transcript = self.stt.transcribe(data)
                
                if transcript["text"]:
                    # Generate response
                    response_text = self._generate_response(
                        transcript["text"], 
                        self.active_sessions[session_id]
                    )
                    
                    # Convert to speech
                    audio_response = self.tts.synthesize(
                        response_text, 
                        language=self.active_sessions[session_id]["language"]
                    )
                    
                    # Send back
                    await websocket.send_bytes(audio_response)
                
        except WebSocketDisconnect:
            del self.active_sessions[session_id]
        except Exception as e:
            print(f"WebSocket error: {e}")
            del self.active_sessions[session_id]
    
    def _generate_response(self, text: str, session: dict) -> str:
        """Generate simple rule-based responses (temp until LLM)"""
        text_lower = text.lower()
        
        # Simple intent detection
        if "book" in text_lower or "appointment" in text_lower:
            session["state"] = "booking"
            return {
                "en": "I can help you book an appointment. Which doctor would you like to see?",
                "hi": "मैं आपके लिए अपॉइंटमेंट बुक कर सकता हूँ। आप किस डॉक्टर से मिलना चाहेंगे?",
                "ta": "நான் உங்களுக்கு சந்திப்பு பதிவு செய்ய உதவ முடியும். நீங்கள் எந்த டாக்டரை சந்திக்க விரும்புகிறீர்கள்?"
            }.get(session["language"], "Which doctor would you like to see?")
        
        elif "cancel" in text_lower:
            session["state"] = "cancelling"
            return {
                "en": "I can help you cancel an appointment. Please tell me the appointment date.",
                "hi": "मैं आपके लिए अपॉइंटमेंट रद्द कर सकता हूँ। कृपया मुझे अपॉइंटमेंट की तारीख बताएं।",
                "ta": "நான் உங்களுக்கு சந்திப்பை ரத்து செய்ய உதவ முடியும். தயவுசெய்து சந்திப்பின் தேதியை சொல்லுங்கள்."
            }.get(session["language"], "Please tell me the appointment date.")
        
        elif "hello" in text_lower or "hi" in text_lower or "नमस्ते" in text_lower or "வணக்கம்" in text_lower:
            return {
                "en": "Hello! How can I help you today? You can book, cancel, or reschedule appointments.",
                "hi": "नमस्ते! आज मैं आपकी कैसे मदद कर सकता हूँ? आप अपॉइंटमेंट बुक, रद्द या पुनर्निर्धारित कर सकते हैं।",
                "ta": "வணக்கம்! இன்று நான் உங்களுக்கு எப்படி உதவ முடியும்? நீங்கள் சந்திப்புகளை பதிவு, ரத்து அல்லது மறு திட்டமிடலாம்."
            }.get(session["language"], "Hello! How can I help you?")
        
        else:
            return {
                "en": "I didn't understand that. You can say book, cancel, or reschedule an appointment.",
                "hi": "मैं समझ नहीं पाया। आप बुक, रद्द, या पुनर्निर्धारित कह सकते हैं।",
                "ta": "எனக்கு புரியவில்லை. நீங்கள் பதிவு, ரத்து, அல்லது மறு திட்டமிடு என்று சொல்லலாம்."
            }.get(session["language"], "I didn't understand that.")
    
    def start_sip_server(self):
        """Start SIP server for real calls"""
        self.sip.start(callback=self._sip_callback)
    
    def _sip_callback(self, audio_bytes: bytes):
        """Callback for SIP audio"""
        # Process audio asynchronously
        asyncio.create_task(self._process_sip_audio(audio_bytes))
    
    async def _process_sip_audio(self, audio_bytes: bytes):
        """Process SIP audio"""
        transcript = self.stt.transcribe(audio_bytes)
        print(f"User said: {transcript['text']} (in {transcript['language']})")
        
        # Simple response for demo
        if transcript["text"]:
            response = self._generate_response(transcript["text"], {
                "state": "conversation",
                "language": transcript["language"]
            })
            print(f"Agent: {response}")