"""
Database Connection Module for SignalMine
Uses Neon PostgreSQL
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
import hashlib
import secrets

# Database connection settings
DB_CONFIG = {
    'host': os.environ.get('PGHOST', 'ep-solitary-math-aijp7w88-pooler.c-4.us-east-1.aws.neon.tech'),
    'database': os.environ.get('PGDATABASE', 'neondb'),
    'user': os.environ.get('PGUSER', 'neondb_owner'),
    'password': os.environ.get('PGPASSWORD', 'npg_dzlxwm34eWZY'),
    'sslmode': os.environ.get('PGSSLMODE', 'require'),
}


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
    finally:
        if conn:
            conn.close()


@contextmanager
def get_db_cursor(commit=True):
    """Context manager for database cursors with auto-commit"""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()


def init_database():
    """Initialize database tables if they don't exist"""
    with get_db_cursor() as cursor:
        # Users table with proper SERIAL sequence
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "Users" (
                "ID" SERIAL PRIMARY KEY,
                "username" VARCHAR(255) UNIQUE NOT NULL,
                "password" VARCHAR(255) NOT NULL,
                "salt" VARCHAR(64) NOT NULL,
                "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Ensure the sequence exists and is linked
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_class WHERE relname = 'Users_ID_seq'
                ) THEN
                    CREATE SEQUENCE "Users_ID_seq";
                    ALTER TABLE "Users" ALTER COLUMN "ID" SET DEFAULT nextval('"Users_ID_seq"');
                    ALTER SEQUENCE "Users_ID_seq" OWNED BY "Users"."ID";
                END IF;
            END $$;
        """)
        
        # Sessions table for persistent authentication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "Sessions" (
                "token" VARCHAR(255) PRIMARY KEY,
                "user_id" INTEGER REFERENCES "Users"("ID") ON DELETE CASCADE,
                "username" VARCHAR(255) NOT NULL,
                "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "expires_at" TIMESTAMP NOT NULL
            )
        """)
        
        # Index on expires_at for cleanup
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_expires 
            ON "Sessions"("expires_at")
        """)
        
        # Chat table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "Chat" (
                "ID" SERIAL PRIMARY KEY,
                "userId" INTEGER REFERENCES "Users"("ID") ON DELETE CASCADE,
                "Name" VARCHAR(255),
                "originalPrompt" TEXT,
                "lastMessageId" INTEGER,
                "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updated_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "Messages" (
                "ID" SERIAL PRIMARY KEY,
                "chatID" INTEGER REFERENCES "Chat"("ID") ON DELETE CASCADE,
                "message" TEXT NOT NULL,
                "order" INTEGER NOT NULL,
                "origin" VARCHAR(50) NOT NULL,
                "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add foreign key for lastMessageId after Messages table exists
        cursor.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name = 'FK_Chat_lastMessageId'
                ) THEN
                    ALTER TABLE "Chat" 
                    ADD CONSTRAINT "FK_Chat_lastMessageId" 
                    FOREIGN KEY ("lastMessageId") REFERENCES "Messages"("ID") ON DELETE SET NULL;
                END IF;
            END $$;
        """)
        
        # Models table (for custom API keys)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "Models" (
                "ID" SERIAL PRIMARY KEY,
                "userId" INTEGER REFERENCES "Users"("ID") ON DELETE CASCADE,
                "Name" VARCHAR(255) NOT NULL,
                "API-key" TEXT NOT NULL,
                "provider" VARCHAR(100) DEFAULT 'openai',
                "base_url" TEXT,
                "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Logs table (for model communication tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "Logs" (
                "ID" SERIAL PRIMARY KEY,
                "messageId" INTEGER REFERENCES "Messages"("ID") ON DELETE CASCADE,
                "log" TEXT NOT NULL,
                "model_used" VARCHAR(255),
                "tokens_used" INTEGER,
                "response_time_ms" INTEGER,
                "was_healed" BOOLEAN DEFAULT FALSE,
                "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Ensure ALL sequences exist and are properly linked
        # (SERIAL may not create sequences on some Neon PostgreSQL setups)
        tables_with_serial = [
            ('Chat', 'ID'), ('Messages', 'ID'), ('Logs', 'ID'), ('Models', 'ID')
        ]
        for table, col in tables_with_serial:
            seq_name = f'{table}_{col}_seq'
            cursor.execute(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = '{seq_name}') THEN
                        CREATE SEQUENCE "{seq_name}";
                    END IF;
                    ALTER TABLE "{table}" ALTER COLUMN "{col}" SET DEFAULT nextval('"{seq_name}"');
                    ALTER SEQUENCE "{seq_name}" OWNED BY "{table}"."{col}";
                    PERFORM setval('"{seq_name}"', COALESCE((SELECT MAX("{col}") FROM "{table}"), 0) + 1, false);
                END $$;
            """)


# ──────────────────────────────────────────────────────────────
# User Functions
# ──────────────────────────────────────────────────────────────

def hash_password(password: str, salt: str = None) -> tuple:
    """Hash a password with salt"""
    if salt is None:
        salt = secrets.token_hex(32)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return hashed.hex(), salt


def create_user(username: str, password: str) -> Optional[Dict]:
    """Create a new user"""
    hashed_password, salt = hash_password(password)
    
    with get_db_cursor() as cursor:
        try:
            cursor.execute(
                'INSERT INTO "Users" ("username", "password", "salt") VALUES (%s, %s, %s) RETURNING "ID", "username"',
                (username, hashed_password, salt)
            )
            return dict(cursor.fetchone())
        except psycopg2.IntegrityError:
            return None  # Username already exists


def verify_user(username: str, password: str) -> Optional[Dict]:
    """Verify user credentials"""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute('SELECT * FROM "Users" WHERE "username" = %s', (username,))
        user = cursor.fetchone()
        
        if user:
            hashed_password, _ = hash_password(password, user['salt'])
            if hashed_password == user['password']:
                return {'ID': user['ID'], 'username': user['username']}
    return None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Get user by ID"""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute('SELECT "ID", "username" FROM "Users" WHERE "ID" = %s', (user_id,))
        result = cursor.fetchone()
        return dict(result) if result else None


# ──────────────────────────────────────────────────────────────
# Session Functions
# ──────────────────────────────────────────────────────────────

def create_session(token: str, user_id: int, username: str, expires_at: str) -> Dict:
    """Create a new session"""
    with get_db_cursor() as cursor:
        cursor.execute(
            'INSERT INTO "Sessions" ("token", "user_id", "username", "expires_at") VALUES (%s, %s, %s, %s) RETURNING *',
            (token, user_id, username, expires_at)
        )
        return dict(cursor.fetchone())


def get_session(token: str) -> Optional[Dict]:
    """Get a session by token"""
    with get_db_cursor(commit=True) as cursor:
        # Clean up expired sessions first
        cursor.execute('DELETE FROM "Sessions" WHERE "expires_at" < CURRENT_TIMESTAMP')
        
        cursor.execute('SELECT * FROM "Sessions" WHERE "token" = %s', (token,))
        result = cursor.fetchone()
        return dict(result) if result else None


def delete_session(token: str) -> bool:
    """Delete a session"""
    with get_db_cursor() as cursor:
        cursor.execute('DELETE FROM "Sessions" WHERE "token" = %s', (token,))
        return cursor.rowcount > 0


# ──────────────────────────────────────────────────────────────
# Chat Functions
# ──────────────────────────────────────────────────────────────

def create_chat(user_id: int, name: str, original_prompt: str) -> Dict:
    """Create a new chat"""
    with get_db_cursor() as cursor:
        cursor.execute(
            'INSERT INTO "Chat" ("userId", "Name", "originalPrompt") VALUES (%s, %s, %s) RETURNING *',
            (user_id, name, original_prompt)
        )
        return dict(cursor.fetchone())


def get_user_chats(user_id: int) -> List[Dict]:
    """Get all chats for a user"""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute(
            'SELECT * FROM "Chat" WHERE "userId" = %s ORDER BY "updated_at" DESC',
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_chat(chat_id: int, user_id: int = None) -> Optional[Dict]:
    """Get a specific chat"""
    with get_db_cursor(commit=False) as cursor:
        if user_id:
            cursor.execute('SELECT * FROM "Chat" WHERE "ID" = %s AND "userId" = %s', (chat_id, user_id))
        else:
            cursor.execute('SELECT * FROM "Chat" WHERE "ID" = %s', (chat_id,))
        result = cursor.fetchone()
        return dict(result) if result else None


def update_chat_last_message(chat_id: int, message_id: int):
    """Update the last message ID for a chat"""
    with get_db_cursor() as cursor:
        cursor.execute(
            'UPDATE "Chat" SET "lastMessageId" = %s, "updated_at" = CURRENT_TIMESTAMP WHERE "ID" = %s',
            (message_id, chat_id)
        )


def delete_chat(chat_id: int, user_id: int) -> bool:
    """Delete a chat"""
    with get_db_cursor() as cursor:
        cursor.execute('DELETE FROM "Chat" WHERE "ID" = %s AND "userId" = %s', (chat_id, user_id))
        return cursor.rowcount > 0


# ──────────────────────────────────────────────────────────────
# Message Functions
# ──────────────────────────────────────────────────────────────

def create_message(chat_id: int, message: str, order: int, origin: str) -> Dict:
    """Create a new message and update the chat's last message in one transaction"""
    with get_db_cursor() as cursor:
        cursor.execute(
            'INSERT INTO "Messages" ("chatID", "message", "order", "origin") VALUES (%s, %s, %s, %s) RETURNING *',
            (chat_id, message, order, origin)
        )
        result = dict(cursor.fetchone())
        
        # Update chat's last message within the SAME transaction
        cursor.execute(
            'UPDATE "Chat" SET "lastMessageId" = %s, "updated_at" = CURRENT_TIMESTAMP WHERE "ID" = %s',
            (result['ID'], chat_id)
        )
        
        return result


def get_chat_messages(chat_id: int) -> List[Dict]:
    """Get all messages for a chat"""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute(
            'SELECT * FROM "Messages" WHERE "chatID" = %s ORDER BY "order" ASC',
            (chat_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_next_message_order(chat_id: int) -> int:
    """Get the next message order number for a chat"""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute('SELECT MAX("order") as max_order FROM "Messages" WHERE "chatID" = %s', (chat_id,))
        result = cursor.fetchone()
        return (result['max_order'] or 0) + 1


# ──────────────────────────────────────────────────────────────
# Model Functions (Custom API Keys)
# ──────────────────────────────────────────────────────────────

def create_user_model(user_id: int, name: str, api_key: str, provider: str = 'openai', base_url: str = None) -> Dict:
    """Create a custom model configuration for a user"""
    with get_db_cursor() as cursor:
        cursor.execute(
            'INSERT INTO "Models" ("userId", "Name", "API-key", "provider", "base_url") VALUES (%s, %s, %s, %s, %s) RETURNING *',
            (user_id, name, api_key, provider, base_url)
        )
        result = dict(cursor.fetchone())
        # Don't return full API key
        result['API-key'] = result['API-key'][:8] + '...' if result['API-key'] else None
        return result


def get_user_models(user_id: int) -> List[Dict]:
    """Get all custom models for a user"""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute('SELECT * FROM "Models" WHERE "userId" = %s', (user_id,))
        results = [dict(row) for row in cursor.fetchall()]
        # Mask API keys
        for r in results:
            if r.get('API-key'):
                r['API-key'] = r['API-key'][:8] + '...'
        return results


def get_user_model(model_id: int, user_id: int) -> Optional[Dict]:
    """Get a specific model with full API key (for internal use)"""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute('SELECT * FROM "Models" WHERE "ID" = %s AND "userId" = %s', (model_id, user_id))
        result = cursor.fetchone()
        return dict(result) if result else None


def delete_user_model(model_id: int, user_id: int) -> bool:
    """Delete a custom model"""
    with get_db_cursor() as cursor:
        cursor.execute('DELETE FROM "Models" WHERE "ID" = %s AND "userId" = %s', (model_id, user_id))
        return cursor.rowcount > 0


def update_user_model(model_id: int, user_id: int, name: str = None, api_key: str = None, provider: str = None, base_url: str = None) -> Optional[Dict]:
    """Update a custom model"""
    updates = []
    values = []
    
    if name:
        updates.append('"Name" = %s')
        values.append(name)
    if api_key:
        updates.append('"API-key" = %s')
        values.append(api_key)
    if provider:
        updates.append('"provider" = %s')
        values.append(provider)
    if base_url is not None:
        updates.append('"base_url" = %s')
        values.append(base_url)
    
    if not updates:
        return None
    
    values.extend([model_id, user_id])
    
    with get_db_cursor() as cursor:
        cursor.execute(
            f'UPDATE "Models" SET {", ".join(updates)} WHERE "ID" = %s AND "userId" = %s RETURNING *',
            values
        )
        result = cursor.fetchone()
        if result:
            result = dict(result)
            result['API-key'] = result['API-key'][:8] + '...' if result['API-key'] else None
        return result


# ──────────────────────────────────────────────────────────────
# Log Functions
# ──────────────────────────────────────────────────────────────

def create_log(message_id: int, log: str, model_used: str = None, tokens_used: int = None, 
               response_time_ms: int = None, was_healed: bool = False) -> Dict:
    """Create a log entry for model communication"""
    with get_db_cursor() as cursor:
        cursor.execute(
            '''INSERT INTO "Logs" ("messageId", "log", "model_used", "tokens_used", "response_time_ms", "was_healed") 
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING *''',
            (message_id, log, model_used, tokens_used, response_time_ms, was_healed)
        )
        return dict(cursor.fetchone())


def get_message_logs(message_id: int) -> List[Dict]:
    """Get all logs for a message"""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute('SELECT * FROM "Logs" WHERE "messageId" = %s ORDER BY "created_at" ASC', (message_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_chat_logs(chat_id: int) -> List[Dict]:
    """Get all logs for a chat"""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute('''
            SELECT l.*, m."order" as message_order, m."origin" as message_origin
            FROM "Logs" l
            JOIN "Messages" m ON l."messageId" = m."ID"
            WHERE m."chatID" = %s
            ORDER BY l."created_at" ASC
        ''', (chat_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_user_logs(user_id: int, limit: int = 100) -> List[Dict]:
    """Get recent logs for a user"""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute('''
            SELECT l.*, c."Name" as chat_name, c."ID" as chat_id
            FROM "Logs" l
            JOIN "Messages" m ON l."messageId" = m."ID"
            JOIN "Chat" c ON m."chatID" = c."ID"
            WHERE c."userId" = %s
            ORDER BY l."created_at" DESC
            LIMIT %s
        ''', (user_id, limit))
        return [dict(row) for row in cursor.fetchall()]
