# src/llm/context_manager.py
import json
from typing import Dict, Any, List
from datetime import datetime

class ContextManager:
    """Manage conversation context using LLM"""
    
    def __init__(self, mistral_client):
        self.client = mistral_client
        self.model = "mistral-tiny"
    
    async def update_context(self, session: Dict, user_message: str, assistant_response: str = "") -> Dict:
        """Let LLM decide what context to keep/update"""
        
        current_context = session.get("context", {})
        history = session.get("history", [])
        
        prompt = f"""
You are a context manager for a hospital appointment system.

Current context:
{json.dumps(current_context, indent=2)}

Conversation history (last 5 messages):
{json.dumps(history[-5:], indent=2)}

New user message: "{user_message}"
Assistant response: "{assistant_response}"

Task: Update the context based on this new exchange.

Rules:
1. Keep all existing context unless explicitly contradicted
2. Extract any new information (doctor, date, time, intent, appointment_id)
3. Track conversation state: "collecting_info", "confirming", "booking", "completed"
4. Track missing information that still needs to be collected
5. Return ONLY valid JSON with this structure:

{{
  "context": {{
    "intent": "book|cancel|reschedule|check|greeting|unknown",
    "doctor": "doctor name or null",
    "date": "YYYY-MM-DD or natural language or null",
    "time": "HH:MM or natural language or null",
    "appointment_id": "id or null",
    "state": "collecting_info|confirming|booking|completed|error",
    "missing_info": ["doctor", "date", "time"],
    "confirmed_slots": [],
    "selected_slot_id": null,
    "conversation_summary": "brief summary of what happened so far"
  }}
}}

Return ONLY the JSON object, no other text.
"""
        
        try:
            response = await self.client.chat.complete_async(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise context manager. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            # Clean JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content)
            return result.get("context", {})
            
        except Exception as e:
            print(f"Context update error: {e}")
            return current_context
    
    async def generate_action(self, context: Dict, user_message: str) -> Dict:
        """Let LLM decide what action to take"""
        
        prompt = f"""
You are an action planner for a hospital appointment system.

Current context:
{json.dumps(context, indent=2)}

User message: "{user_message}"

Based on the context and user message, decide what action to take.

Return ONLY JSON:
{{
  "action": "ask_for_info|check_availability|book_slot|cancel_slot|confirm_booking|say_goodbye|transfer_to_human",
  "response_template": "What to say to the user",
  "missing_info": ["doctor", "date", "time"],
  "booking_params": {{
    "doctor": "name or null",
    "date": "date or null", 
    "time": "time or null",
    "slot_id": "id or null"
  }},
  "reasoning": "brief explanation of why this action"
}}
"""
        
        try:
            response = await self.client.chat.complete_async(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an action planner. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=400
            )
            
            content = response.choices[0].message.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            
            return json.loads(content)
            
        except Exception as e:
            print(f"Action planning error: {e}")
            return {
                "action": "ask_for_info",
                "response_template": "How can I help you with your appointment?",
                "missing_info": []
            }