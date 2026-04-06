# test_outbound.py
import asyncio
# from src.outbound.campaign_manager import CampaignManager
from src.outbound.campaign_manager import CampaignManager
import os
from dotenv import load_dotenv
load_dotenv()


async def test_outbound():
    print("Testing outbound campaign system...")
    print("=" * 50)
    print("STARTING OUTBOUND CALL TEST")
    print("=" * 50)
    
    print(f"\nYour phone number: {os.getenv('MY_PHONE_NUMBER')}")
    print(f"Twilio number: {os.getenv('TWILIO_PHONE_NUMBER')}")
    print(f"Ngrok URL: {os.getenv('PUBLIC_URL')}")
    
    manager = CampaignManager()
    
    # Manually trigger a reminder campaign
    # await manager.start_reminder_campaign()
    
    # # Process the queue
    # await manager.process_call_queue(rate_per_minute=2)  # 2 calls per minute for testing
    await manager.make_outbound_call()
    print("Outbound test completed!")

if __name__ == "__main__":
    asyncio.run(test_outbound())