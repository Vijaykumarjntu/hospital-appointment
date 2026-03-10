from mistralai import Mistral
from src.config import settings
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

class MistralHandler:
    def __init__(self):
        """Initialize Mistral client"""
        self.api_key = settings.MISTRAL_API_KEY
        if not self.api_key:
            print("⚠️  MISTRAL_API_KEY not found in .env file")
            self.client = None
        else:
            self.client = Mistral(api_key=self.api_key)
            self.model = "mistral-tiny"  # Free tier model
            print("✅ Mistral LLM initialized")
    
    async def extract_intent(self, text: str, language: str = "en") -> Dict[str, Any]:
        """
        Extract intent and entities from user message
        Returns: {
            "intent": "book|cancel|reschedule|check|greeting|unknown",
            "doctor": "dr sharma",
            "date": "2024-01-20",
            "time": "15:00",
            "confidence": 0.95
        }
        """
        if not self.client:
            return self._fallback_extraction(text)
        
        prompt = f"""
        Extract intent and entities from this {language} message.
        User said: "{text}"
        
        Return JSON with:
        - intent: one of [book, cancel, reschedule, check, greeting, unknown]
        - doctor: doctor name if mentioned (Dr. Sharma, Dr. Patel, Dr. Kumar, Dr. Priya)
        - date: date if mentioned (in YYYY-MM-DD format)
        - time: time if mentioned (in HH:MM format)
        - confidence: number 0-1
        
        Examples:
        "I want to book with Dr. Sharma tomorrow at 3pm" 
        -> {{"intent": "book", "doctor": "Dr. Sharma", "date": "2024-01-20", "time": "15:00", "confidence": 0.95}}
        
        "cancel my appointment"
        -> {{"intent": "cancel", "doctor": null, "date": null, "time": null, "confidence": 0.9}}
        
        Return ONLY the JSON, no other text.
        """
        
        try:
            response = await self.client.chat.complete_async(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an intent extraction assistant. Return only JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"Mistral API error: {e}")
            return self._fallback_extraction(text)
    
    async def generate_response(self, 
                              user_message: str,
                              intent: str,
                              context: Dict,
                              available_slots: Optional[list] = None,
                              language: str = "en") -> str:
        """
        Generate natural response based on intent and context
        """
        if not self.client:
            return self._fallback_response(intent, context, language)
        
        # Build context for response
        slots_text = ""
        if available_slots:
            slots = [s.strftime("%I:%M %p") for s in available_slots]
            slots_text = f"Available slots: {', '.join(slots)}"
        
        prompt = f"""
        Generate a friendly response in {language} for a medical appointment assistant.
        
        Context:
        - User message: "{user_message}"
        - Detected intent: {intent}
        - Current state: {context.get('state', 'conversation')}
        - Selected doctor: {context.get('doctor', 'unknown')}
        - Selected date: {context.get('date', 'unknown')}
        - {slots_text}
        
        Rules:
        1. Be helpful and concise
        2. If asking for information, be specific
        3. If confirming booking, be warm
        4. If error, be apologetic and offer help
        5. Match user's language
        
        Return only the response text, no explanations.
        """
        
        try:
            response = await self.client.chat.complete_async(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful medical appointment assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Mistral response error: {e}")
            return self._fallback_response(intent, context, language)
    
    def _fallback_extraction(self, text: str) -> Dict:
        """Simple fallback when Mistral is unavailable"""
        text_lower = text.lower()
        
        # Basic intent detection
        if any(word in text_lower for word in ["book", "appointment", "see", "meet"]):
            intent = "book"
        elif any(word in text_lower for word in ["cancel", "cancel"]):
            intent = "cancel"
        elif any(word in text_lower for word in ["hello", "hi", "hey"]):
            intent = "greeting"
        else:
            intent = "unknown"
        
        # Simple doctor detection
        doctor = None
        for d in ["sharma", "patel", "kumar", "priya"]:
            if d in text_lower:
                doctor = f"Dr. {d.capitalize()}"
                break
        
        return {
            "intent": intent,
            "doctor": doctor,
            "date": None,
            "time": None,
            "confidence": 0.5
        }
    
    def _fallback_response(self, intent: str, context: Dict, language: str) -> str:
        """Simple fallback responses"""
        responses = {
            "book": {
                "en": "I can help you book an appointment. Which doctor would you like to see?",
                "hi": "मैं आपके लिए अपॉइंटमेंट बुक कर सकता हूँ। आप किस डॉक्टर से मिलना चाहेंगे?",
                "ta": "நான் உங்களுக்கு சந்திப்பு பதிவு செய்ய உதவ முடியும். நீங்கள் எந்த டாக்டரை சந்திக்க விரும்புகிறீர்கள்?"
            },
            "cancel": {
                "en": "I can help you cancel. Please tell me your appointment details.",
                "hi": "मैं रद्द करने में मदद कर सकता हूँ। कृपया मुझे अपॉइंटमेंट विवरण बताएं।",
                "ta": "ரத்து செய்ய நான் உதவ முடியும். தயவுசெய்து உங்கள் சந்திப்பு விவரங்களை சொல்லுங்கள்."
            },
            "greeting": {
                "en": "Hello! How can I help you with your appointment today?",
                "hi": "नमस्ते! आज मैं आपकी अपॉइंटमेंट में कैसे मदद कर सकता हूँ?",
                "ta": "வணக்கம்! இன்று உங்கள் சந்திப்பில் நான் எப்படி உதவ முடியும்?"
            }
        }
        
        return responses.get(intent, {}).get(language, responses["greeting"]["en"])