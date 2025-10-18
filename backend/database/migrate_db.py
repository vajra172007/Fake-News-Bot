"""Database migration to add new columns for dynamic system."""

import os
import sys

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database.setup_db import db
from sqlalchemy import text


def migrate_database():
    """Add new columns to fact_checks table."""
    print("\n" + "="*70)
    print("🔧 DATABASE MIGRATION")
    print("="*70)
    print("Adding new columns for dynamic scraping system...")
    
    session = db.get_session()
    
    try:
        # Check if columns already exist
        result = session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'fact_checks' 
            AND column_name IN ('source_type', 'confidence_score', 'gemini_generated', 'red_flags');
        """))
        
        existing_columns = [row[0] for row in result]
        
        if len(existing_columns) == 4:
            print("✓ All columns already exist. No migration needed.")
            session.close()
            return
        
        print(f"Found {len(existing_columns)} existing columns: {existing_columns}")
        print("Adding missing columns...")
        
        # Add source_type column
        if 'source_type' not in existing_columns:
            print("  → Adding 'source_type' column...")
            session.execute(text("""
                ALTER TABLE fact_checks 
                ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) DEFAULT 'scraped';
            """))
            print("    ✓ Added")
        
        # Add confidence_score column
        if 'confidence_score' not in existing_columns:
            print("  → Adding 'confidence_score' column...")
            session.execute(text("""
                ALTER TABLE fact_checks 
                ADD COLUMN IF NOT EXISTS confidence_score FLOAT;
            """))
            print("    ✓ Added")
        
        # Add gemini_generated column
        if 'gemini_generated' not in existing_columns:
            print("  → Adding 'gemini_generated' column...")
            session.execute(text("""
                ALTER TABLE fact_checks 
                ADD COLUMN IF NOT EXISTS gemini_generated BOOLEAN DEFAULT FALSE;
            """))
            print("    ✓ Added")
        
        # Add red_flags column
        if 'red_flags' not in existing_columns:
            print("  → Adding 'red_flags' column...")
            session.execute(text("""
                ALTER TABLE fact_checks 
                ADD COLUMN IF NOT EXISTS red_flags JSON;
            """))
            print("    ✓ Added")
        
        session.commit()
        
        print("\n✅ Database migration completed successfully!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def verify_migration():
    """Verify that all columns exist."""
    print("\n🔍 Verifying migration...")
    
    session = db.get_session()
    
    try:
        result = session.execute(text("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns 
            WHERE table_name = 'fact_checks' 
            AND column_name IN ('source_type', 'confidence_score', 'gemini_generated', 'red_flags')
            ORDER BY column_name;
        """))
        
        columns = result.fetchall()
        
        print("\n📊 Column details:")
        for col_name, col_type, col_default in columns:
            default = col_default if col_default else 'NULL'
            print(f"  • {col_name}: {col_type} (default: {default})")
        
        if len(columns) == 4:
            print("\n✅ All 4 new columns verified successfully!")
        else:
            print(f"\n⚠️  Only {len(columns)}/4 columns found!")
        
    finally:
        session.close()


if __name__ == "__main__":
    try:
        migrate_database()
        verify_migration()
    except Exception as e:
        print(f"\n💥 Error: {e}")
        sys.exit(1)
