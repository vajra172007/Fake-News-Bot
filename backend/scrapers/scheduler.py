"""Scheduler for automated daily scraping of fact-check websites."""

import os
import sys
import schedule
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.scrapers.run_all_scrapers import run_all_scrapers, get_database_stats


def scraping_job():
    """Job that runs all scrapers."""
    print("\n" + "🔔" * 35)
    print("🤖 SCHEDULED SCRAPING JOB STARTED")
    print("🔔" * 35)
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        # Run all scrapers (3 pages per source by default)
        total_added = run_all_scrapers(max_pages=3)
        
        print(f"\n✅ Scraping job completed successfully!")
        print(f"📊 {total_added} new fact-checks added to database\n")
        
    except Exception as e:
        print(f"\n❌ Error in scraping job: {e}")
        import traceback
        traceback.print_exc()


def start_scheduler(run_at_hour: int = 2, run_at_minute: int = 0, run_immediately: bool = False):
    """
    Start the scheduler for automated scraping.
    
    Args:
        run_at_hour: Hour to run scraping (0-23, default: 2 AM)
        run_at_minute: Minute to run scraping (0-59, default: 0)
        run_immediately: Whether to run scraping immediately on start
    """
    print("\n" + "="*70)
    print("🤖 FACT-CHECK SCRAPER SCHEDULER")
    print("="*70)
    print(f"⏰ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 Scheduled to run daily at {run_at_hour:02d}:{run_at_minute:02d}")
    print(f"🌐 Sources: AltNews, PIB, Boom Live, WebQoof, Vishvas News")
    print(f"📄 Pages per source: 3")
    print("="*70 + "\n")
    
    # Schedule the job
    schedule_time = f"{run_at_hour:02d}:{run_at_minute:02d}"
    schedule.every().day.at(schedule_time).do(scraping_job)
    
    print(f"✅ Scheduler started successfully!")
    print(f"⏳ Next run: {schedule.next_run()}\n")
    
    # Run immediately if requested
    if run_immediately:
        print("🚀 Running scraping immediately as requested...")
        scraping_job()
    
    # Show current database stats
    print("\n📊 Current Database Statistics:")
    get_database_stats()
    
    print("\n♾️  Scheduler is now running... (Press Ctrl+C to stop)\n")
    
    # Keep running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n\n🛑 Scheduler stopped by user")
        print("👋 Goodbye!\n")


def setup_cron_job():
    """
    Generate instructions for setting up a cron job.
    This is an alternative to running the scheduler continuously.
    """
    script_path = os.path.abspath(__file__)
    python_path = sys.executable
    
    cron_command = f"0 2 * * * cd {os.path.dirname(script_path)} && {python_path} -c 'from backend.scrapers.run_all_scrapers import run_all_scrapers; run_all_scrapers(max_pages=3)' >> /tmp/scraper.log 2>&1"
    
    print("\n" + "="*70)
    print("⚙️  CRON JOB SETUP INSTRUCTIONS")
    print("="*70)
    print("\nTo set up automated scraping using cron:")
    print("\n1. Open crontab editor:")
    print("   crontab -e")
    print("\n2. Add this line to run scraper daily at 2 AM:")
    print(f"\n{cron_command}")
    print("\n3. Save and exit")
    print("\n📝 Logs will be saved to: /tmp/scraper.log")
    print("="*70 + "\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Scheduler for automated fact-check scraping')
    parser.add_argument('--hour', type=int, default=2, help='Hour to run (0-23, default: 2)')
    parser.add_argument('--minute', type=int, default=0, help='Minute to run (0-59, default: 0)')
    parser.add_argument('--now', action='store_true', help='Run scraping immediately')
    parser.add_argument('--cron', action='store_true', help='Show cron job setup instructions')
    
    args = parser.parse_args()
    
    if args.cron:
        setup_cron_job()
    else:
        start_scheduler(
            run_at_hour=args.hour,
            run_at_minute=args.minute,
            run_immediately=args.now
        )
