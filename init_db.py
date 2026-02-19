"""
Database Initialization Script
Run this to set up the database tables in Neon PostgreSQL
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from api.database import init_database, get_db_cursor

def main():
    print("Initializing SignalMine database...")
    print(f"Host: {os.environ.get('PGHOST', 'Not set')}")
    print(f"Database: {os.environ.get('PGDATABASE', 'Not set')}")
    
    try:
        # Initialize tables
        init_database()
        print("✓ Database tables created successfully!")
        
        # Verify tables exist
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [row['table_name'] for row in cursor.fetchall()]
            
            print("\nTables in database:")
            for table in tables:
                print(f"  - {table}")
        
        print("\n✓ Database initialization complete!")
        
    except Exception as e:
        print(f"\n✗ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
