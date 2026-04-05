# mistral_handler.py
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
            # Better model recommendation (tiny is too weak for reliable JSON)
            self.model = "mistral-small-latest"   # or "mistral-tiny" if you must
            print(f"✅ Mistral LLM initialized with model: {self.model}")
    
    async def extract_intent(self, text: str, language: str = "en") -> Dict[str, Any]:
        """
        Extract intent and entities from user message.
        Returns clean dict or fallback.
        """
        if not self.client:
            return self._fallback_extraction(text)
        
        prompt = f"""
You are an intent extraction assistant for a hospital appointment system.

User message ({language}): "{text}"

Extract the following and return **ONLY** valid JSON (no extra text, no explanations, no markdown):

{{
  "intent": "book" | "cancel" | "reschedule" | "check" | "greeting" | "unknown",
  "doctor": "Dr. Sharma" or null,
  "date": "YYYY-MM-DD" or null,
  "time": "HH:MM" or null,
  "confidence": 0.0 to 1.0
}}

Doctor names to look for: Dr. Sharma, Dr. Patel, Dr. Kumar, Dr. Priya.
"""

        try:
            response = await self.client.chat.complete_async(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise JSON-only extractor. Never add any text outside the JSON object."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,          # Lower temperature = more consistent output
                max_tokens=300,
                response_format={"type": "json_object"}   # Important: Enables JSON mode
            )

            content = response.choices[0].message.content.strip()

            # Robust cleaning: remove markdown, extra text, backticks, etc.
            if "```json
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            # Try to parse
            result = json.loads(content)
            return result

        except json.JSONDecodeError as je:
            print(f"JSON parse error. Raw response was: {content[:500]}")
            print(f"JSONDecodeError: {je}")
            return self._fallback_extraction(text)
        
        except Exception as e:
            print(f"Mistral API error in extract_intent: {e}")
            return self._fallback_extraction(text)
    
    async def generate_response(self, 
                              user_message: str,
                              intent: str,
                              context: Dict,
                              available_slots: Optional[list] = None,
                              language: str = "en") -> str:
        """Generate natural response (this part usually works better)"""
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
Do not add any extra explanations.
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
            print(f"Mistral response error in generate_response: {e}")
            return self._fallback_response(intent, context, language)
    
    # Your fallback methods remain the same (good to keep)
    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        # ... (your existing fallback code) ...
        pass
    
    def _fallback_response(self, intent: str, context: Dict, language: str) -> str:
        # ... (your existing fallback code) ...
        pass