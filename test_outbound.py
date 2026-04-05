# test_outbound.py
import asyncio
# from src.outbound.campaign_manager import CampaignManager
from src.outbound.campaign_manager import CampaignManager

async def test_outbound():
    print("Testing outbound campaign system...")
    
    manager = CampaignManager()
    
    # Manually trigger a reminder campaign
    await manager.start_reminder_campaign()
    
    # Process the queue
    await manager.process_call_queue(rate_per_minute=2)  # 2 calls per minute for testing
    
    print("Outbound test completed!")

if __name__ == "__main__":
    asyncio.run(test_outbound())