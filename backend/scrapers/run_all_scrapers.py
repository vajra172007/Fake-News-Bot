"""Run all fact-checking scrapers and populate the database with deduplication."""

import os
import sys
import time
from datetime import datetime
from typing import List, Dict

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from fact_check_scrapers import (
    PIBFactCheckScraper, 
    AltNewsScraper, 
    BoomLiveScraper,
    WebQoofScraper,
    VishvasNewsScraper
)
from scrapers.deduplicator import Deduplicator
from database.setup_db import db
from models.database import FactCheck, ScraperLog


def save_fact_checks_to_db(fact_checks: List[Dict], scraper_name: str, session) -> int:
    """Save fact-checks to database."""
    saved_count = 0
    
    print(f"\n💾 Saving {len(fact_checks)} fact-checks from {scraper_name}...")
    
    for fc in fact_checks:
        try:
            # Check if URL already exists
            existing = session.query(FactCheck).filter(
                FactCheck.source_url == fc['source_url']
            ).first()
            
            if existing:
                print(f"  ⏭️  Skipping (URL exists): {fc['claim'][:50]}...")
                continue
            
            # Create FactCheck object
            fact_check = FactCheck(
                claim=fc['claim'],
                verdict=fc['verdict'],
                explanation=fc.get('explanation', ''),
                source=fc['source'],
                source_url=fc['source_url'],
                original_url=fc.get('original_url'),
                published_date=fc.get('published_date'),
                scraped_date=datetime.utcnow(),
                language=fc.get('language', 'en'),
                keywords=fc.get('keywords'),
                embedding=fc.get('embedding'),
                source_type=fc.get('source_type', 'scraped'),
                confidence_score=fc.get('confidence_score'),
                gemini_generated=fc.get('gemini_generated', False),
                red_flags=fc.get('red_flags')
            )
            
            session.add(fact_check)
            saved_count += 1
            print(f"  ✓ Saved: {fc['claim'][:60]}...")
            
        except Exception as e:
            print(f"  ❌ Error saving fact-check: {e}")
            continue
    
    try:
        session.commit()
        print(f"✓ Successfully saved {saved_count} fact-checks from {scraper_name}")
    except Exception as e:
        print(f"❌ Error committing to database: {e}")
        session.rollback()
        saved_count = 0
    
    return saved_count


def run_scraper(scraper_class, scraper_name: str, session, deduplicator, **kwargs) -> int:
    """Run a single scraper with deduplication."""
    print(f"\n{'='*70}")
    print(f"🔧 Running {scraper_name} Scraper")
    print(f"{'='*70}")
    
    # Create scraper log
    log = ScraperLog(
        scraper_name=scraper_name,
        start_time=datetime.utcnow(),
        status='running',
        articles_scraped=0,
        errors=[]
    )
    session.add(log)
    session.commit()
    log_id = log.id
    
    try:
        # Initialize and run scraper
        scraper = scraper_class()
        raw_fact_checks = scraper.scrape_all()
        
        print(f"\n📊 Scraped {len(raw_fact_checks)} fact-checks")
        
        if not raw_fact_checks:
            print(f"⚠️  No fact-checks found")
            log.status = 'no_data'
            log.end_time = datetime.utcnow()
            session.commit()
            return 0
        
        # Deduplicate
        unique_fact_checks = deduplicator.filter_duplicates(raw_fact_checks, session)
        
        print(f"✓ {len(unique_fact_checks)} unique fact-checks after deduplication")
        
        # Save to database
        saved_count = save_fact_checks_to_db(unique_fact_checks, scraper_name, session)
        
        # Update log
        log = session.query(ScraperLog).get(log_id)
        log.end_time = datetime.utcnow()
        log.status = 'success'
        log.articles_scraped = saved_count
        session.commit()
        
        return saved_count
        
    except Exception as e:
        print(f"\n❌ Error running {scraper_name}: {e}")
        import traceback
        traceback.print_exc()
        
        # Update log with error
        log = session.query(ScraperLog).get(log_id)
        log.end_time = datetime.utcnow()
        log.status = 'failure'
        log.errors = [str(e)]
        session.commit()
        
        return 0


def run_all_scrapers(max_pages: int = 3):
    """Run all scrapers with deduplication."""
    print("\n" + "="*70)
    print("🚀 STARTING AUTOMATED FACT-CHECK SCRAPING SYSTEM")
    print("="*70)
    print(f"⏰ Start time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"📄 Max pages per source: {max_pages}")
    print("="*70 + "\n")
    
    session = db.get_session()
    deduplicator = Deduplicator(similarity_threshold=0.85)
    
    total_saved = 0
    
    # Define scrapers to run (working scrapers with deduplication)
    scrapers = [
        (AltNewsScraper, "AltNews", {}),
        (BoomLiveScraper, "Boom Live", {}),
        (PIBFactCheckScraper, "PIB Fact Check", {}),
        # Note: WebQoof and Vishvas can be added later after interface alignment
    ]
    
    results = {}
    
    for scraper_class, scraper_name, kwargs in scrapers:
        saved_count = run_scraper(scraper_class, scraper_name, session, deduplicator, **kwargs)
        results[scraper_name] = saved_count
        total_saved += saved_count
        
        # Brief pause between scrapers
        time.sleep(3)
    
    session.close()
    
    # Print summary
    print("\n" + "="*70)
    print("📊 SCRAPING SUMMARY")
    print("="*70)
    print(f"⏰ End time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"\n📈 Results by Source:")
    for scraper_name, count in results.items():
        print(f"  • {scraper_name}: {count} fact-checks")
    print(f"\n✅ Total new fact-checks added: {total_saved}")
    print("="*70 + "\n")
    
    return total_saved


def get_database_stats():
    """Get current database statistics."""
    session = db.get_session()
    
    try:
        total = session.query(FactCheck).count()
        scraped = session.query(FactCheck).filter(FactCheck.source_type == 'scraped').count()
        gemini = session.query(FactCheck).filter(FactCheck.gemini_generated == True).count()
        
        by_source = {}
        for source in ['AltNews', 'PIB Fact Check', 'Boom Live', 'WebQoof', 'Vishvas News', 'Gemini AI']:
            count = session.query(FactCheck).filter(FactCheck.source == source).count()
            by_source[source] = count
        
        by_verdict = {}
        for verdict in ['false', 'misleading', 'true', 'unverified']:
            count = session.query(FactCheck).filter(FactCheck.verdict == verdict).count()
            by_verdict[verdict] = count
        
        print("\n" + "="*70)
        print("📊 DATABASE STATISTICS")
        print("="*70)
        print(f"Total fact-checks: {total}")
        print(f"  • Scraped: {scraped}")
        print(f"  • Gemini-generated: {gemini}")
        print(f"\n📰 By Source:")
        for source, count in by_source.items():
            if count > 0:
                print(f"  • {source}: {count}")
        print(f"\n⚖️  By Verdict:")
        for verdict, count in by_verdict.items():
            if count > 0:
                print(f"  • {verdict.title()}: {count}")
        print("="*70 + "\n")
        
    finally:
        session.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run fact-check scrapers')
    parser.add_argument('--pages', type=int, default=3, help='Max pages to scrape per source (default: 3)')
    parser.add_argument('--stats', action='store_true', help='Show database statistics only')
    
    args = parser.parse_args()
    
    if args.stats:
        get_database_stats()
    else:
        # Show stats before
        print("📊 Database statistics BEFORE scraping:")
        get_database_stats()
        
        # Run scrapers
        total_added = run_all_scrapers(max_pages=args.pages)
        
        # Show stats after
        print("\n📊 Database statistics AFTER scraping:")
        get_database_stats()
        
        if total_added > 0:
            print(f"🎉 Successfully added {total_added} new fact-checks to the database!")
        else:
            print("ℹ️  No new fact-checks were added (all were duplicates or errors occurred)")
