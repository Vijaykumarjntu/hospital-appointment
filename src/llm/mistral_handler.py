# src/llm/mistral_handler.py
from mistralai.client import Mistral
from src.config import settings
import json
from typing import Optional, Dict, Any

class MistralHandler:
    def __init__(self):
        """Initialize Mistral client"""
        self.api_key = settings.MISTRAL_API_KEY
        if not self.api_key:
            print("⚠️  MISTRAL_API_KEY not found in .env file")
            self.client = None
        else:
            self.client = Mistral(api_key=self.api_key)
            self.model = "mistral-small-latest"   # Better than tiny for JSON
            print(f"✅ Mistral LLM initialized with model: {self.model}")
    
    async def extract_intent(self, text: str, language: str = "en",  history: list = []) -> Dict[str, Any]:
        """
        Extract intent and entities from user message.
        Returns clean dict or fallback on failure.
        """
        if not self.client:
            return self._fallback_extraction(text)
        
        history_text = ""
        if history:
            history_text = "\n".join([
                f"{m['role'].upper()}: {m['content']}" 
                for m in history[-6:]  # last 6 messages only
            ])

        prompt = f"""
You are an intent extraction assistant for a hospital appointment system.

Previous conversation:
{history_text}

User message ({language}): "{text}"

Return **ONLY** valid JSON with no extra text, no markdown, no explanations:

{{
  "intent": "book" | "cancel" | "reschedule" | "check" | "greeting" | "unknown",
  "doctor": "Dr. Sharma" or null,
  "date": "YYYY-MM-DD" or null,
  "time": "HH:MM" or null,
  "confidence": 0.0 to 1.0
}}

Look for these doctors: Dr. Sharma, Dr. Patel, Dr. Kumar, Dr. Priya.
"""

        try:
            response = await self.client.chat.complete_async(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise assistant. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=300,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content.strip()

            # Clean common issues (markdown, backticks, extra text)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            # Remove any leading/trailing whitespace or quotes
            content = content.strip().strip('"')

            result = json.loads(content)
            return result

        except json.JSONDecodeError as je:
            print(f"❌ JSON parse failed. Raw response: {content[:400]}")
            print(f"JSON Error: {je}")
            return self._fallback_extraction(text)
        
        except Exception as e:
            print(f"❌ Mistral API error in extract_intent: {e}")
            return self._fallback_extraction(text)
    
    async def generate_response(self, 
                              user_message: str,
                              intent: str,
                              context: Dict,
                              available_slots: Optional[list] = None,
                              language: str = "en") -> str:
        """Generate natural language response"""
        if not self.client:
            return self._fallback_response(intent, context, language)
        
        slots_text = ""
        if available_slots:
            slots = [s.strftime("%I:%M %p") for s in available_slots]
            slots_text = f"Available slots: {', '.join(slots)}"

        prompt = f"""
You are a friendly hospital appointment assistant.

User said: "{user_message}"
Detected intent: {intent}
Context: {context}
{slots_text}

Reply in {language} language. Be polite, helpful, and concise.
Return only the response text.
"""

        try:
            response = await self.client.chat.complete_async(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful and professional medical appointment assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"❌ Mistral response error in generate_response: {e}")
            return self._fallback_response(intent, context, language)
    
    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """Simple rule-based fallback"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["book", "appointment", "see", "meet", "schedule"]):
            intent = "book"
        elif any(word in text_lower for word in ["cancel", "delete", "remove"]):
            intent = "cancel"
        elif any(word in text_lower for word in ["reschedule", "change", "move"]):
            intent = "reschedule"
        elif any(word in text_lower for word in ["hello", "hi", "hey", "namaste", "vanakkam"]):
            intent = "greeting"
        else:
            intent = "unknown"
        
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