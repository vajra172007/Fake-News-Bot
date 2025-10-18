"""Database initialization and connection management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv
from models.database import Base

load_dotenv()


class Database:
    """Database manager for the fake news detection system."""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://fakenews_user:password@localhost:5432/fakenews_db')
        self.engine = None
        self.Session = None
        
    def init_db(self):
        """Initialize database connection and create tables."""
        self.engine = create_engine(
            self.database_url,
            pool_size=int(os.getenv('DATABASE_POOL_SIZE', 10)),
            max_overflow=int(os.getenv('DATABASE_MAX_OVERFLOW', 20)),
            echo=os.getenv('DEBUG', 'False').lower() == 'true'
        )
        
        # Create all tables
        Base.metadata.create_all(self.engine)
        
        # Create session factory
        session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(session_factory)
        
        print("✓ Database initialized successfully")
        
    def get_session(self):
        """Get a new database session."""
        if self.Session is None:
            self.init_db()
        return self.Session()
    
    def close_session(self, session):
        """Close a database session."""
        if session:
            session.close()


# Global database instance
db = Database()


def get_db_session():
    """Get a database session (for use in API endpoints)."""
    session = db.get_session()
    try:
        yield session
    finally:
        db.close_session(session)


if __name__ == "__main__":
    """Run this script to set up the database."""
    print("Setting up database...")
    db.init_db()
    print("\nDatabase setup complete!")
    print("\nTables created:")
    print("- fact_checks")
    print("- image_hashes")
    print("- unreliable_domains")
    print("- user_queries")
    print("- scraper_logs")
