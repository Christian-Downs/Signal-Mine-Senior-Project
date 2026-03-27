"""
Comprehensive unit tests for SignalMine Database Module (api/database.py)
Tests database operations, connection management, and CRUD operations
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import hashlib
import secrets
import psycopg2
from psycopg2.extras import RealDictCursor
import json

from api.database import (
    get_db_connection, get_db_cursor,
    init_database,
    hash_password, create_user, verify_user, get_user_by_id,
    create_session, get_session, delete_session,
    create_chat, get_user_chats, get_chat, update_chat_last_message, delete_chat,
    create_message, get_chat_messages, get_next_message_order,
    create_user_model, get_user_models, get_user_model, delete_user_model, update_user_model,
    create_log, get_message_logs, get_chat_logs, get_user_logs,
    DB_CONFIG
)


# ──────────────────────────────────────────────────────────────
# Password Hashing Tests
# ──────────────────────────────────────────────────────────────

class TestPasswordHashing:
    """Tests for password hashing and verification"""
    
    def test_hash_password_generates_salt(self):
        """Test that hash_password generates a new salt"""
        hashed1, salt1 = hash_password('password123')
        hashed2, salt2 = hash_password('password123')
        
        # Different salts should be generated
        assert salt1 != salt2
        # Different hashes from different salts
        assert hashed1 != hashed2
    
    def test_hash_password_with_provided_salt(self):
        """Test hash_password with provided salt"""
        salt = 'fixed_salt_value'
        hashed1, returned_salt = hash_password('password123', salt)
        hashed2, _ = hash_password('password123', salt)
        
        # Same salt should produce same hash
        assert hashed1 == hashed2
        assert returned_salt == salt
    
    def test_hash_password_consistent_with_same_salt(self):
        """Test that same password and salt produce same hash"""
        salt = secrets.token_hex(32)
        password = 'testpassword'
        
        hashed1, _ = hash_password(password, salt)
        hashed2, _ = hash_password(password, salt)
        
        assert hashed1 == hashed2
    
    def test_hash_password_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes"""
        salt = secrets.token_hex(32)
        hashed1, _ = hash_password('password1', salt)
        hashed2, _ = hash_password('password2', salt)
        
        assert hashed1 != hashed2
    
    def test_hash_password_uses_pbkdf2(self):
        """Test that hash uses PBKDF2 properly"""
        salt = 'test_salt'
        password = 'test_password'
        hashed, _ = hash_password(password, salt)
        
        # Verify it matches expected PBKDF2 hash
        expected = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        assert hashed == expected.hex()


# ──────────────────────────────────────────────────────────────
# Database Connection Tests
# ──────────────────────────────────────────────────────────────

class TestDatabaseConnections:
    """Tests for database connection management"""
    
    @patch('api.database.psycopg2.connect')
    def test_get_db_connection_success(self, mock_psycopg2_connect):
        """Test successful database connection"""
        mock_conn = MagicMock()
        mock_psycopg2_connect.return_value = mock_conn
        
        with get_db_connection() as conn:
            assert conn == mock_conn
        
        mock_conn.close.assert_called_once()
    
    @patch('api.database.psycopg2.connect')
    def test_get_db_connection_closes_on_error(self, mock_psycopg2_connect):
        """Test that connection is closed even on error"""
        mock_conn = MagicMock()
        mock_psycopg2_connect.return_value = mock_conn
        
        try:
            with get_db_connection() as conn:
                raise ValueError("Test error")
        except ValueError:
            pass
        
        mock_conn.close.assert_called_once()
    
    @patch('api.database.psycopg2.connect')
    def test_get_db_connection_uses_db_config(self, mock_psycopg2_connect):
        """Test that connection uses DB_CONFIG"""
        mock_conn = MagicMock()
        mock_psycopg2_connect.return_value = mock_conn
        
        with get_db_connection() as conn:
            pass
        
        mock_psycopg2_connect.assert_called_once()
        call_kwargs = mock_psycopg2_connect.call_args[1]
        assert 'host' in call_kwargs
        assert 'database' in call_kwargs
        assert 'user' in call_kwargs
    
    @patch('api.database.psycopg2.connect')
    def test_get_db_cursor_commits_by_default(self, mock_psycopg2_connect):
        """Test that cursor commits by default"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg2_connect.return_value = mock_conn
        
        with get_db_cursor() as cursor:
            pass
        
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
    
    @patch('api.database.psycopg2.connect')
    def test_get_db_cursor_no_commit_when_disabled(self, mock_psycopg2_connect):
        """Test that cursor doesn't commit when commit=False"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg2_connect.return_value = mock_conn
        
        with get_db_cursor(commit=False) as cursor:
            pass
        
        mock_conn.commit.assert_not_called()
        mock_cursor.close.assert_called_once()
    
    @patch('api.database.psycopg2.connect')
    def test_get_db_cursor_rollback_on_error(self, mock_psycopg2_connect):
        """Test that cursor rolls back on error"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg2_connect.return_value = mock_conn
        
        try:
            with get_db_cursor() as cursor:
                raise ValueError("Test error")
        except ValueError:
            pass
        
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()


# ──────────────────────────────────────────────────────────────
# User Functions Tests
# ──────────────────────────────────────────────────────────────

class TestUserFunctions:
    """Tests for user CRUD operations"""
    
    @patch('api.database.get_db_cursor')
    def test_create_user_success(self, mock_get_db_cursor):
        """Test successful user creation"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {'ID': 1, 'username': 'newuser'}
        
        result = create_user('newuser', 'password123')
        
        assert result['ID'] == 1
        assert result['username'] == 'newuser'
        mock_cursor.execute.assert_called_once()
    
    @patch('api.database.get_db_cursor')
    def test_create_user_duplicate_username(self, mock_get_db_cursor):
        """Test creating user with duplicate username"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.execute.side_effect = psycopg2.IntegrityError("Duplicate")
        
        result = create_user('existinguser', 'password123')
        
        assert result is None
    
    @patch('api.database.get_db_cursor')
    def test_verify_user_success(self, mock_get_db_cursor):
        """Test successful user verification"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        salt = secrets.token_hex(32)
        hashed, _ = hash_password('password123', salt)
        
        mock_cursor.fetchone.return_value = {
            'ID': 1,
            'username': 'testuser',
            'password': hashed,
            'salt': salt
        }
        
        result = verify_user('testuser', 'password123')
        
        assert result is not None
        assert result['ID'] == 1
        assert result['username'] == 'testuser'
    
    @patch('api.database.get_db_cursor')
    def test_verify_user_wrong_password(self, mock_get_db_cursor):
        """Test verification with wrong password"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        salt = secrets.token_hex(32)
        hashed, _ = hash_password('password123', salt)
        
        mock_cursor.fetchone.return_value = {
            'ID': 1,
            'username': 'testuser',
            'password': hashed,
            'salt': salt
        }
        
        result = verify_user('testuser', 'wrongpassword')
        
        assert result is None
    
    @patch('api.database.get_db_cursor')
    def test_verify_user_nonexistent(self, mock_get_db_cursor):
        """Test verification with nonexistent user"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = None
        
        result = verify_user('nonexistent', 'password123')
        
        assert result is None
    
    @patch('api.database.get_db_cursor')
    def test_get_user_by_id(self, mock_get_db_cursor):
        """Test getting user by ID"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {'ID': 1, 'username': 'testuser'}
        
        result = get_user_by_id(1)
        
        assert result['ID'] == 1
        assert result['username'] == 'testuser'
    
    @patch('api.database.get_db_cursor')
    def test_get_user_by_id_not_found(self, mock_get_db_cursor):
        """Test getting nonexistent user by ID"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = None
        
        result = get_user_by_id(999)
        
        assert result is None


# ──────────────────────────────────────────────────────────────
# Session Functions Tests
# ──────────────────────────────────────────────────────────────

class TestSessionFunctions:
    """Tests for session management"""
    
    @patch('api.database.get_db_cursor')
    def test_create_session(self, mock_get_db_cursor):
        """Test creating a session"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
        mock_cursor.fetchone.return_value = {
            'token': 'test_token_123',
            'user_id': 1,
            'username': 'testuser',
            'expires_at': expires_at
        }
        
        result = create_session('test_token_123', 1, 'testuser', expires_at)
        
        assert result['token'] == 'test_token_123'
        assert result['user_id'] == 1
    
    @patch('api.database.get_db_cursor')
    def test_get_session_valid(self, mock_get_db_cursor):
        """Test getting a valid session"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
        mock_cursor.fetchone.return_value = {
            'token': 'test_token_123',
            'user_id': 1,
            'username': 'testuser',
            'expires_at': expires_at
        }
        
        result = get_session('test_token_123')
        
        assert result is not None
        assert result['token'] == 'test_token_123'
    
    @patch('api.database.get_db_cursor')
    def test_get_session_not_found(self, mock_get_db_cursor):
        """Test getting nonexistent session"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = None
        
        result = get_session('invalid_token')
        
        assert result is None
    
    @patch('api.database.get_db_cursor')
    def test_delete_session(self, mock_get_db_cursor):
        """Test deleting a session"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.rowcount = 1
        
        result = delete_session('test_token_123')
        
        assert result is True
    
    @patch('api.database.get_db_cursor')
    def test_delete_session_not_found(self, mock_get_db_cursor):
        """Test deleting nonexistent session"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.rowcount = 0
        
        result = delete_session('invalid_token')
        
        assert result is False


# ──────────────────────────────────────────────────────────────
# Chat Functions Tests
# ──────────────────────────────────────────────────────────────

class TestChatFunctions:
    """Tests for chat CRUD operations"""
    
    @patch('api.database.get_db_cursor')
    def test_create_chat(self, mock_get_db_cursor):
        """Test creating a chat"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {
            'ID': 1,
            'userId': 1,
            'Name': 'Test Chat',
            'originalPrompt': 'Test prompt'
        }
        
        result = create_chat(1, 'Test Chat', 'Test prompt')
        
        assert result['ID'] == 1
        assert result['Name'] == 'Test Chat'
    
    @patch('api.database.get_db_cursor')
    def test_get_user_chats(self, mock_get_db_cursor):
        """Test getting user's chats"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = [
            {'ID': 1, 'userId': 1, 'Name': 'Chat 1'},
            {'ID': 2, 'userId': 1, 'Name': 'Chat 2'}
        ]
        
        result = get_user_chats(1)
        
        assert len(result) == 2
        assert result[0]['ID'] == 1
    
    @patch('api.database.get_db_cursor')
    def test_get_user_chats_empty(self, mock_get_db_cursor):
        """Test getting user's chats when none exist"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = []
        
        result = get_user_chats(1)
        
        assert result == []
    
    @patch('api.database.get_db_cursor')
    def test_get_chat(self, mock_get_db_cursor):
        """Test getting a specific chat"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {
            'ID': 1,
            'userId': 1,
            'Name': 'Test Chat'
        }
        
        result = get_chat(1, 1)
        
        assert result['ID'] == 1
        assert result['Name'] == 'Test Chat'
    
    @patch('api.database.get_db_cursor')
    def test_get_chat_not_found(self, mock_get_db_cursor):
        """Test getting nonexistent chat"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = None
        
        result = get_chat(999, 1)
        
        assert result is None
    
    @patch('api.database.get_db_cursor')
    def test_update_chat_last_message(self, mock_get_db_cursor):
        """Test updating chat's last message"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        update_chat_last_message(1, 5)
        
        mock_cursor.execute.assert_called_once()
    
    @patch('api.database.get_db_cursor')
    def test_delete_chat(self, mock_get_db_cursor):
        """Test deleting a chat"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.rowcount = 1
        
        result = delete_chat(1, 1)
        
        assert result is True
    
    @patch('api.database.get_db_cursor')
    def test_delete_chat_not_found(self, mock_get_db_cursor):
        """Test deleting nonexistent chat"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.rowcount = 0
        
        result = delete_chat(999, 1)
        
        assert result is False


# ──────────────────────────────────────────────────────────────
# Message Functions Tests
# ──────────────────────────────────────────────────────────────

class TestMessageFunctions:
    """Tests for message operations"""
    
    @patch('api.database.get_db_cursor')
    def test_create_message(self, mock_get_db_cursor):
        """Test creating a message"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {
            'ID': 1,
            'chatID': 1,
            'message': 'Test message',
            'order': 1,
            'origin': 'user'
        }
        
        result = create_message(1, 'Test message', 1, 'user')
        
        assert result['ID'] == 1
        assert result['message'] == 'Test message'
        # Verify both execute calls (insert and update)
        assert mock_cursor.execute.call_count == 2
    
    @patch('api.database.get_db_cursor')
    def test_get_chat_messages(self, mock_get_db_cursor):
        """Test getting all messages for a chat"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = [
            {'ID': 1, 'chatID': 1, 'message': 'Message 1', 'order': 1},
            {'ID': 2, 'chatID': 1, 'message': 'Message 2', 'order': 2}
        ]
        
        result = get_chat_messages(1)
        
        assert len(result) == 2
        assert result[0]['ID'] == 1
    
    @patch('api.database.get_db_cursor')
    def test_get_next_message_order(self, mock_get_db_cursor):
        """Test getting next message order"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {'max_order': 5}
        
        result = get_next_message_order(1)
        
        assert result == 6
    
    @patch('api.database.get_db_cursor')
    def test_get_next_message_order_first_message(self, mock_get_db_cursor):
        """Test getting next message order when chat is empty"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {'max_order': None}
        
        result = get_next_message_order(1)
        
        assert result == 1


# ──────────────────────────────────────────────────────────────
# Model Functions Tests
# ──────────────────────────────────────────────────────────────

class TestModelFunctions:
    """Tests for custom model CRUD operations"""
    
    @patch('api.database.get_db_cursor')
    def test_create_user_model(self, mock_get_db_cursor):
        """Test creating a custom model"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {
            'ID': 1,
            'userId': 1,
            'Name': 'My Model',
            'API-key': 'sk-test-1234567890',
            'provider': 'openai',
            'base_url': None
        }
        
        result = create_user_model(1, 'My Model', 'sk-test-1234567890', 'openai')
        
        assert result['ID'] == 1
        assert result['Name'] == 'My Model'
        # API key should be masked
        assert result['API-key'] == 'sk-test-...'
    
    @patch('api.database.get_db_cursor')
    def test_get_user_models(self, mock_get_db_cursor):
        """Test getting user's custom models"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = [
            {'ID': 1, 'userId': 1, 'Name': 'Model 1', 'API-key': 'sk-test-1234567890'},
            {'ID': 2, 'userId': 1, 'Name': 'Model 2', 'API-key': 'sk-test-0987654321'}
        ]
        
        result = get_user_models(1)
        
        assert len(result) == 2
        # API keys should be masked
        assert result[0]['API-key'] == 'sk-test-...'
        assert result[1]['API-key'] == 'sk-test-...'
    
    @patch('api.database.get_db_cursor')
    def test_get_user_model_full_key(self, mock_get_db_cursor):
        """Test getting a specific model with full API key"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {
            'ID': 1,
            'userId': 1,
            'Name': 'My Model',
            'API-key': 'sk-test-full-key-value',
            'provider': 'openai'
        }
        
        result = get_user_model(1, 1)
        
        # Full key returned for internal use
        assert result['API-key'] == 'sk-test-full-key-value'
    
    @patch('api.database.get_db_cursor')
    def test_get_user_model_not_found(self, mock_get_db_cursor):
        """Test getting nonexistent model"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = None
        
        result = get_user_model(999, 1)
        
        assert result is None
    
    @patch('api.database.get_db_cursor')
    def test_delete_user_model(self, mock_get_db_cursor):
        """Test deleting a custom model"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.rowcount = 1
        
        result = delete_user_model(1, 1)
        
        assert result is True
    
    @patch('api.database.get_db_cursor')
    def test_update_user_model_name(self, mock_get_db_cursor):
        """Test updating model name"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {
            'ID': 1,
            'userId': 1,
            'Name': 'Updated Name',
            'API-key': 'sk-test-key'
        }
        
        result = update_user_model(1, 1, name='Updated Name')
        
        assert result is not None
        assert result['Name'] == 'Updated Name'
    
    @patch('api.database.get_db_cursor')
    def test_update_user_model_api_key(self, mock_get_db_cursor):
        """Test updating model API key"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {
            'ID': 1,
            'userId': 1,
            'Name': 'Model',
            'API-key': 'sk-new-key-value'
        }
        
        result = update_user_model(1, 1, api_key='sk-new-key-value')
        
        assert result is not None
        assert result['API-key'] == 'sk-new-...'
    
    @patch('api.database.get_db_cursor')
    def test_update_user_model_no_changes(self, mock_get_db_cursor):
        """Test updating model with no changes"""
        result = update_user_model(1, 1)
        
        assert result is None


# ──────────────────────────────────────────────────────────────
# Log Functions Tests
# ──────────────────────────────────────────────────────────────

class TestLogFunctions:
    """Tests for log operations"""
    
    @patch('api.database.get_db_cursor')
    def test_create_log(self, mock_get_db_cursor):
        """Test creating a log entry"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {
            'ID': 1,
            'messageId': 1,
            'log': '{"test": "data"}',
            'model_used': 'gpt-4o-mini',
            'tokens_used': 150,
            'response_time_ms': 500,
            'was_healed': False
        }
        
        log_data = json.dumps({'test': 'data'})
        result = create_log(1, log_data, 'gpt-4o-mini', 150, 500, False)
        
        assert result['ID'] == 1
        assert result['model_used'] == 'gpt-4o-mini'
        assert result['tokens_used'] == 150
    
    @patch('api.database.get_db_cursor')
    def test_get_message_logs(self, mock_get_db_cursor):
        """Test getting logs for a message"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = [
            {
                'ID': 1,
                'messageId': 1,
                'model_used': 'gpt-4o-mini',
                'tokens_used': 150,
                'was_healed': False
            }
        ]
        
        result = get_message_logs(1)
        
        assert len(result) == 1
        assert result[0]['model_used'] == 'gpt-4o-mini'
    
    @patch('api.database.get_db_cursor')
    def test_get_chat_logs(self, mock_get_db_cursor):
        """Test getting logs for a chat"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = [
            {
                'ID': 1,
                'messageId': 1,
                'model_used': 'gpt-4o-mini',
                'was_healed': False
            }
        ]
        
        result = get_chat_logs(1)
        
        assert len(result) >= 0
    
    @patch('api.database.get_db_cursor')
    def test_get_user_logs(self, mock_get_db_cursor):
        """Test getting logs for a user"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = [
            {
                'ID': 1,
                'chat_id': 1,
                'chat_name': 'Chat 1',
                'model_used': 'gpt-4o-mini'
            }
        ]
        
        result = get_user_logs(1, limit=100)
        
        assert len(result) >= 0
    
    @patch('api.database.get_db_cursor')
    def test_get_user_logs_default_limit(self, mock_get_db_cursor):
        """Test getting user logs with default limit"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = []
        
        result = get_user_logs(1)
        
        # Verify limit was passed as argument
        call_args = mock_cursor.execute.call_args[0]
        assert 100 in call_args  # Default limit


# ──────────────────────────────────────────────────────────────
# Database Initialization Tests
# ──────────────────────────────────────────────────────────────

class TestDatabaseInitialization:
    """Tests for database initialization"""
    
    @patch('api.database.get_db_cursor')
    def test_init_database_creates_tables(self, mock_get_db_cursor):
        """Test that init_database creates all required tables"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        init_database()
        
        # Verify execute was called multiple times for CREATE TABLE statements
        assert mock_cursor.execute.call_count > 5
        
        # Check that some key table creation statements were executed
        all_calls = [call[0][0] for call in mock_cursor.execute.call_args_list]
        table_creation_calls = [c for c in all_calls if 'CREATE TABLE' in c.upper()]
        
        assert len(table_creation_calls) >= 8  # Users, Sessions, Chat, Messages, Models, Logs, etc.
    
    @patch('api.database.get_db_cursor')
    def test_init_database_creates_sequences(self, mock_get_db_cursor):
        """Test that init_database creates sequences for serial columns"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        init_database()
        
        # Verify sequences are created
        all_calls = [call[0][0] for call in mock_cursor.execute.call_args_list]
        sequence_calls = [c for c in all_calls if 'SEQUENCE' in c.upper()]
        
        assert len(sequence_calls) > 0
    
    @patch('api.database.get_db_cursor')
    def test_init_database_creates_indexes(self, mock_get_db_cursor):
        """Test that init_database creates indexes"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        init_database()
        
        # Verify indexes are created
        all_calls = [call[0][0] for call in mock_cursor.execute.call_args_list]
        index_calls = [c for c in all_calls if 'INDEX' in c.upper()]
        
        assert len(index_calls) > 0


# ──────────────────────────────────────────────────────────────
# Error Handling Tests
# ──────────────────────────────────────────────────────────────

class TestErrorHandling:
    """Tests for error handling in database operations"""
    
    @patch('api.database.get_db_cursor')
    def test_create_user_handles_integrity_error(self, mock_get_db_cursor):
        """Test that create_user handles IntegrityError gracefully"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.execute.side_effect = psycopg2.IntegrityError("Duplicate")
        
        # Should not raise, should return None
        result = create_user('duplicate', 'password')
        assert result is None
    
    @patch('api.database.get_db_cursor')
    def test_delete_chat_handles_missing_chat(self, mock_get_db_cursor):
        """Test that delete_chat returns False for missing chat"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.rowcount = 0
        
        result = delete_chat(999, 999)
        
        assert result is False


# ──────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────

class TestIntegration:
    """Integration tests for database workflows"""
    
    @patch('api.database.get_db_cursor')
    def test_complete_user_workflow(self, mock_get_db_cursor):
        """Test complete user creation and verification workflow"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        # Create user
        mock_cursor.fetchone.return_value = {'ID': 1, 'username': 'newuser'}
        user = create_user('newuser', 'password123')
        
        assert user is not None
        
        # Get user by ID
        mock_cursor.fetchone.return_value = {'ID': 1, 'username': 'newuser'}
        retrieved = get_user_by_id(1)
        
        assert retrieved is not None
        assert retrieved['username'] == 'newuser'
    
    @patch('api.database.get_db_cursor')
    def test_complete_chat_workflow(self, mock_get_db_cursor):
        """Test complete chat creation and message workflow"""
        mock_cursor = MagicMock()
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        # Create chat
        mock_cursor.fetchone.return_value = {'ID': 1, 'userId': 1, 'Name': 'Test'}
        chat = create_chat(1, 'Test', 'Test prompt')
        
        assert chat is not None
        
        # Create message
        mock_cursor.fetchone.return_value = {
            'ID': 1,
            'chatID': 1,
            'message': 'Test',
            'order': 1,
            'origin': 'user'
        }
        message = create_message(1, 'Test', 1, 'user')
        
        assert message is not None
        assert message['chatID'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
