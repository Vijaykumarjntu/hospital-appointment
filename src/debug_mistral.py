import os
from dotenv import load_dotenv
from mistralai.client import Mistral

load_dotenv()

api_key = os.getenv("MISTRAL_API_KEY")
print("=== DEBUG INFO ===")
print("Key length:", len(api_key) if api_key else 0)
print("Key preview:", api_key[:20] + "..." + api_key[-10:] if api_key else "None")

client = Mistral(api_key=api_key)

try:
    response = client.chat.complete(
        model="mistral-tiny",
        messages=[{"role": "user", "content": "Hello, reply with only the word OK"}],
        max_tokens=10
    )
    print("\n✅ SUCCESS! Response:", response.choices[0].message.content)
except Exception as e:
    print("\n❌ FAILED:", str(e)[:300])