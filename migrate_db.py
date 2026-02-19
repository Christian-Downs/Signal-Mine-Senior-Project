"""
Database Migration Script
Adds missing columns to existing tables
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from api.database import get_db_cursor

def migrate():
    print("Running database migrations...")
    
    with get_db_cursor() as cursor:
        # Check if salt column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'Users' AND column_name = 'salt'
        """)
        
        if not cursor.fetchone():
            print("Adding 'salt' column to Users table...")
            cursor.execute("""
                ALTER TABLE "Users" 
                ADD COLUMN "salt" VARCHAR(64) NOT NULL DEFAULT ''
            """)
            print("✓ Salt column added")
        else:
            print("✓ Salt column already exists")
        
        # Check if created_at column exists in Users
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'Users' AND column_name = 'created_at'
        """)
        
        if not cursor.fetchone():
            print("Adding 'created_at' column to Users table...")
            cursor.execute("""
                ALTER TABLE "Users" 
                ADD COLUMN "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
            print("✓ created_at column added")
        else:
            print("✓ created_at column already exists")
        
        # Make username and password NOT NULL
        cursor.execute("""
            ALTER TABLE "Users" 
            ALTER COLUMN "username" SET NOT NULL,
            ALTER COLUMN "password" SET NOT NULL
        """)
        print("✓ Set username and password as NOT NULL")
        
        # Check if created_at column exists in Chat
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'Chat' AND column_name = 'created_at'
        """)
        
        if not cursor.fetchone():
            print("Adding 'created_at' column to Chat table...")
            cursor.execute("""
                ALTER TABLE "Chat" 
                ADD COLUMN "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
            print("✓ Chat created_at column added")
        else:
            print("✓ Chat created_at column already exists")
        
        # Check if updated_at column exists in Chat
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'Chat' AND column_name = 'updated_at'
        """)
        
        if not cursor.fetchone():
            print("Adding 'updated_at' column to Chat table...")
            cursor.execute("""
                ALTER TABLE "Chat" 
                ADD COLUMN "updated_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
            print("✓ Chat updated_at column added")
        else:
            print("✓ Chat updated_at column already exists")
        
        # Check if lastMessageId column exists in Chat
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'Chat' AND column_name = 'lastMessageId'
        """)
        
        if not cursor.fetchone():
            print("Adding 'lastMessageId' column to Chat table...")
            cursor.execute("""
                ALTER TABLE "Chat" 
                ADD COLUMN "lastMessageId" INTEGER
            """)
            print("✓ Chat lastMessageId column added")
        else:
            print("✓ Chat lastMessageId column already exists")
    
    print("\n✓ Migration complete!")

if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
