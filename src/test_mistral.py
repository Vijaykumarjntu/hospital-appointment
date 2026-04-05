# test_mistral.py - Test Mistral API connection (Fixed for mistralai >= 2.x)
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("MISTRAL API CONNECTION TEST")
print("=" * 60)

# Test 1: Check if API key exists
print("\nTEST 1: Check API Key")
api_key = os.getenv("MISTRAL_API_KEY")
if api_key:
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-5:]}")
else:
    print("❌ MISTRAL_API_KEY not found in .env file")
    exit(1)

# Test 2: Import Mistral Client (Correct import for v2.x)
print("\nTEST 2: Import Mistral Client")
try:
    from mistralai.client import Mistral
    print("✅ Mistral client imported successfully (from mistralai.client)")
except ImportError as e:
    print(f"❌ Failed to import Mistral: {e}")
    print("\n🔧 Fix: Make sure you have the latest version:")
    print("   pip install --upgrade mistralai")
    exit(1)

# Test 3: Initialize client and make a simple request
print("\nTEST 3: Initialize Client & Simple Chat Request")

async def test_basic_chat():
    try:
        client = Mistral(api_key=api_key)
        print("✅ Mistral client initialized")

        print("\n📤 Sending test prompt...")

        response = await client.chat.complete_async(
            model="mistral-tiny",   # or "mistral-small-latest" for better quality
            messages=[
                {
                    "role": "user",
                    "content": "Say 'Hello, Mistral is working perfectly!' in one short sentence."
                }
            ],
            temperature=0.1,
            max_tokens=50
        )

        reply = response.choices[0].message.content.strip()
        print(f"📥 Response: {reply}")
        print("✅ Basic chat test passed!")
        return True

    except Exception as e:
        print(f"❌ Error during basic chat: {e}")
        if "401" in str(e):
            print("   → Invalid API key. Get a new one from https://console.mistral.ai/api-keys")
        elif "429" in str(e):
            print("   → Rate limit exceeded. Try again later.")
        else:
            print(f"   → Error type: {type(e).__name__}")
        return False


# Test 4: Test Intent Extraction (JSON mode)
print("\nTEST 4: Intent Extraction Test")

async def test_intent_extraction():
    try:
        client = Mistral(api_key=api_key)

        test_message = "I want to book an appointment with Dr. Sharma tomorrow at 3pm"

        response = await client.chat.complete_async(
            model="mistral-tiny",
            messages=[
                {
                    "role": "system",
                    "content": "You are an intent extraction assistant. Return ONLY valid JSON, nothing else."
                },
                {
                    "role": "user",
                    "content": f'Extract the intent from this message: "{test_message}". '
                               f'Return JSON in this exact format: '
                               f'{{"intent": "book_appointment", "doctor": "Dr. Sharma", "date": "tomorrow", "time": "15:00"}}'
                }
            ],
            temperature=0.1,
            max_tokens=150
        )

        result = response.choices[0].message.content.strip()
        print(f"✅ Intent extraction successful!")
        print(f"   Input : {test_message}")
        print(f"   Output: {result}")
        return True

    except Exception as e:
        print(f"❌ Intent extraction failed: {e}")
        return False


# Run all tests
async def run_all_tests():
    print("\n" + "🎯" * 30)
    print("RUNNING ALL MISTRAL TESTS")
    print("🎯" * 30 + "\n")

    test3_ok = await test_basic_chat()

    if test3_ok:
        await test_intent_extraction()
        print("\n" + "=" * 60)
        print("✅✅✅ ALL TESTS PASSED! Mistral connection is WORKING.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌❌❌ Some tests failed. Check the errors above.")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())