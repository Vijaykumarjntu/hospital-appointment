# src/outbound/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from src.outbound.campaign_manager import CampaignManager
import asyncio

class OutboundScheduler:
    """Schedule outbound campaigns"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.campaign_manager = CampaignManager()
    
    def start(self):
        """Start the scheduler"""
        # Run reminder campaign daily at 6 PM
        self.scheduler.add_job(
            func=self.run_reminder_campaign,
            trigger=CronTrigger(hour=18, minute=0),  # 6 PM
            id="reminder_campaign",
            name="Daily appointment reminders",
            replace_existing=True
        )
        
        # Run follow-up campaign daily at 10 AM
        self.scheduler.add_job(
            func=self.run_followup_campaign,
            trigger=CronTrigger(hour=10, minute=0),
            id="followup_campaign",
            name="Post-visit follow-ups",
            replace_existing=True
        )
        
        self.scheduler.start()
        print("✅ Outbound scheduler started")
        print("   - Reminder campaign: Daily at 6 PM")
        print("   - Follow-up campaign: Daily at 10 AM")
    
    def run_reminder_campaign(self):
        """Run reminder campaign (runs in background)"""
        print("\n" + "="*50)
        print("📞 Running reminder campaign...")
        print("="*50)
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.campaign_manager.start_reminder_campaign())
        loop.run_until_complete(self.campaign_manager.process_call_queue())
        loop.close()
    
    def run_followup_campaign(self):
        """Run follow-up campaign for recent visits"""
        print("\n" + "="*50)
        print("📞 Running follow-up campaign...")
        print("="*50)
        # Similar to reminder campaign
        # Would query patients who visited 2 days ago
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        print("Outbound scheduler stopped")