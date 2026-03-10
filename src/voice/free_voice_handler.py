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
        except:
            # Fallback to English model
            print("Multilingual model failed, falling back to English")
            self.tts = FreeTextToSpeech("tts_models/en/ljspeech/tacotron2-DDC")
        
        # Initialize SIP (for real calls)
        self.sip = SimpleSIPHandler()
        
        # Active sessions
        self.active_sessions = {}
        
        print("✅ Free Voice Handler initialized")
    
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