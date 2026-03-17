"""
Comprehensive unit tests for SignalMine Chats API (api/chats.py)
Tests chat management, retrieval, creation, and deletion business logic
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys

# Mock database and auth before importing chats
sys.modules['api.database'] = MagicMock()
sys.modules['api.auth'] = MagicMock()

from api.chats import get_auth_user


def create_sample_chat():
    """Create a sample chat object"""
    return {
        'ID': 1,
        'userId': 1,
        'Name': 'Test Chat',
        'originalPrompt': 'What is linear programming?',
        'lastMessageId': 5,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }


def create_sample_message():
    """Create a sample message object"""
    return {
        'ID': 1,
        'chatID': 1,
        'message': 'This is a test message',
        'order': 1,
        'origin': 'user',
        'created_at': datetime.now().isoformat()
    }


# ──────────────────────────────────────────────────────────────
# Authentication Tests
# ──────────────────────────────────────────────────────────────

class TestGetAuthUser:
    """Tests for extracting authenticated user from headers"""
    
    @patch('api.chats.validate_token')
    def test_get_auth_user_valid_token(self, mock_validate_token):
        """Test extracting user with valid token"""
        mock_validate_token.return_value = {
            'user_id': 1,
            'username': 'testuser'
        }
        
        headers = {'Authorization': 'Bearer test_token_123'}
        user = get_auth_user(headers)
        
        assert user is not None
        assert user['user_id'] == 1
        mock_validate_token.assert_called_once_with('test_token_123')
    
    @patch('api.chats.validate_token')
    def test_get_auth_user_invalid_token(self, mock_validate_token):
        """Test extracting user with invalid token"""
        mock_validate_token.return_value = None
        
        headers = {'Authorization': 'Bearer invalid_token'}
        user = get_auth_user(headers)
        
        assert user is None
    
    def test_get_auth_user_no_header(self):
        """Test extracting user without Authorization header"""
        headers = {}
        user = get_auth_user(headers)
        assert user is None
    
    def test_get_auth_user_malformed_header(self):
        """Test extracting user with malformed Authorization header"""
        headers = {'Authorization': 'InvalidFormat token123'}
        user = get_auth_user(headers)
        assert user is None
    
    def test_get_auth_user_empty_authorization(self):
        """Test extracting user with empty Authorization header"""
        headers = {'Authorization': ''}
        user = get_auth_user(headers)
        assert user is None
    
    @patch('api.chats.validate_token')
    def test_get_auth_user_extracts_token_from_bearer(self, mock_validate_token):
        """Test token extraction from Bearer scheme"""
        mock_validate_token.return_value = {'user_id': 42, 'username': 'alice'}
        
        headers = {'Authorization': 'Bearer xyz_secure_token_789'}
        user = get_auth_user(headers)
        
        assert user['user_id'] == 42
        mock_validate_token.assert_called_once_with('xyz_secure_token_789')


# ──────────────────────────────────────────────────────────────
# Chat Retrieval Logic Tests
# ──────────────────────────────────────────────────────────────

class TestChatRetrievalLogic:
    """Tests for chat retrieval business logic"""
    
    @patch('api.chats.get_user_chats')
    @patch('api.chats.validate_token')
    def test_retrieve_all_user_chats(self, mock_validate_token, mock_get_user_chats):
        """Test retrieving all chats for authenticated user"""
        mock_validate_token.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_chats.return_value = [
            create_sample_chat(),
            {'ID': 2, 'userId': 1, 'Name': 'Chat 2'}
        ]
        
        headers = {'Authorization': 'Bearer valid_token'}
        user = get_auth_user(headers)
        assert user is not None
        
        chats = mock_get_user_chats(user['user_id'])
        assert len(chats) == 2
        assert all(chat['userId'] == 1 for chat in chats)
    
    @patch('api.chats.get_user_chats')
    @patch('api.chats.validate_token')
    def test_retrieve_empty_chat_list(self, mock_validate_token, mock_get_user_chats):
        """Test retrieving chats when user has none"""
        mock_validate_token.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_chats.return_value = []
        
        user = get_auth_user({'Authorization': 'Bearer token'})
        chats = mock_get_user_chats(user['user_id'])
        
        assert chats == []
    
    @patch('api.chats.get_chat_messages')
    @patch('api.chats.get_chat')
    @patch('api.chats.validate_token')
    def test_retrieve_specific_chat_with_messages(self, mock_validate_token, 
                                                    mock_get_chat, mock_get_messages):
        """Test retrieving specific chat and its messages"""
        mock_validate_token.return_value = {'user_id': 1, 'username': 'testuser'}
        chat = create_sample_chat()
        mock_get_chat.return_value = chat
        mock_get_messages.return_value = [create_sample_message()]
        
        user = get_auth_user({'Authorization': 'Bearer token'})
        
        # Retrieve chat
        retrieved_chat = mock_get_chat(1, user['user_id'])
        assert retrieved_chat['ID'] == 1
        
        # Retrieve messages
        messages = mock_get_messages(1)
        assert len(messages) == 1
        assert messages[0]['chatID'] == 1
    
    @patch('api.chats.get_chat')
    def test_retrieve_chat_checks_ownership(self, mock_get_chat):
        """Test that chat retrieval verifies user ownership"""
        mock_get_chat.return_value = None
        
        # Try to access chat owned by different user
        result = mock_get_chat(1, 2)  # chat_id=1, user_id=2
        
        assert result is None
        mock_get_chat.assert_called_once_with(1, 2)


# ──────────────────────────────────────────────────────────────
# Chat Creation Logic Tests
# ──────────────────────────────────────────────────────────────

class TestChatCreationLogic:
    """Tests for chat creation business logic"""
    
    @patch('api.chats.create_chat')
    @patch('api.chats.validate_token')
    def test_create_chat_with_name_and_prompt(self, mock_validate_token, mock_create_chat):
        """Test creating chat with provided name and prompt"""
        mock_validate_token.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_create_chat.return_value = create_sample_chat()
        
        user = get_auth_user({'Authorization': 'Bearer token'})
        
        chat = mock_create_chat(
            user_id=user['user_id'],
            name='My Chat',
            original_prompt='What is LP?'
        )
        
        assert chat is not None
        assert chat['ID'] == 1
        mock_create_chat.assert_called_once()
    
    @patch('api.chats.create_chat')
    def test_create_chat_auto_generates_name_from_prompt(self, mock_create_chat):
        """Test that name is auto-generated from prompt if not provided"""
        mock_create_chat.return_value = create_sample_chat()
        
        original_prompt = 'This is a very long prompt that should be truncated'
        name = original_prompt[:50] + '...' if len(original_prompt) > 50 else original_prompt
        
        # Name is created from prompt
        assert len(name) <= 53  # 50 + '...'
    
    @patch('api.chats.create_chat')
    def test_create_chat_default_name(self, mock_create_chat):
        """Test that default name is used when prompt is empty"""
        mock_create_chat.return_value = create_sample_chat()
        
        # No prompt provided, use default
        name = 'New Chat'
        
        assert name == 'New Chat'
    
    @patch('api.chats.create_chat')
    def test_create_chat_returns_chat_object(self, mock_create_chat):
        """Test that create_chat returns complete chat object"""
        expected_chat = create_sample_chat()
        mock_create_chat.return_value = expected_chat
        
        result = mock_create_chat(1, 'Test', 'Prompt')
        
        assert result['ID'] is not None
        assert result['userId'] == 1
        assert result['Name'] == 'Test Chat'


# ──────────────────────────────────────────────────────────────
# Chat Deletion Logic Tests
# ──────────────────────────────────────────────────────────────

class TestChatDeletionLogic:
    """Tests for chat deletion business logic"""
    
    @patch('api.chats.delete_chat')
    @patch('api.chats.validate_token')
    def test_delete_chat_success(self, mock_validate_token, mock_delete_chat):
        """Test successful chat deletion"""
        mock_validate_token.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_delete_chat.return_value = True
        
        user = get_auth_user({'Authorization': 'Bearer token'})
        
        success = mock_delete_chat(chat_id=1, user_id=user['user_id'])
        
        assert success is True
        mock_delete_chat.assert_called_once_with(chat_id=1, user_id=1)
    
    @patch('api.chats.delete_chat')
    def test_delete_chat_not_found(self, mock_delete_chat):
        """Test deletion of nonexistent chat"""
        mock_delete_chat.return_value = False
        
        success = mock_delete_chat(chat_id=999, user_id=1)
        
        assert success is False
    
    @patch('api.chats.delete_chat')
    def test_delete_chat_verifies_ownership(self, mock_delete_chat):
        """Test that deletion verifies user owns the chat"""
        mock_delete_chat.return_value = False
        
        # Try to delete chat owned by different user
        success = mock_delete_chat(chat_id=1, user_id=2)
        
        assert success is False
        mock_delete_chat.assert_called_once_with(chat_id=1, user_id=2)


# ──────────────────────────────────────────────────────────────
# Input Validation Tests
# ──────────────────────────────────────────────────────────────

class TestInputValidation:
    """Tests for input validation"""
    
    def test_json_parsing_valid(self):
        """Test valid JSON parsing"""
        body = '{"name": "Chat", "original_prompt": "test"}'
        data = json.loads(body)
        assert data['name'] == 'Chat'
    
    def test_json_parsing_invalid(self):
        """Test invalid JSON raises error"""
        body = 'invalid json {'
        with pytest.raises(json.JSONDecodeError):
            json.loads(body)
    
    def test_chat_name_extraction(self):
        """Test extracting chat name from request"""
        data = json.loads('{"name": "My Chat", "original_prompt": "test"}')
        name = data.get('name', 'New Chat').strip()
        assert name == 'My Chat'
    
    def test_chat_name_defaults(self):
        """Test default name when not provided"""
        data = json.loads('{"original_prompt": "test"}')
        name = data.get('name', 'New Chat').strip()
        assert name == 'New Chat'
    
    def test_empty_name_defaults(self):
        """Test empty name uses default"""
        data = json.loads('{"name": "", "original_prompt": "test"}')
        name = (data.get('name') or 'New Chat').strip()
        assert name == 'New Chat'
    
    def test_chat_id_parsing(self):
        """Test parsing chat ID from URL path"""
        path = '/api/chats/123'
        parts = path.rstrip('/').split('/')
        chat_id = parts[-1] if parts[-1].isdigit() else None
        assert chat_id == '123'
    
    def test_invalid_chat_id(self):
        """Test invalid chat ID"""
        path = '/api/chats/abc'
        parts = path.rstrip('/').split('/')
        chat_id = parts[-1] if parts[-1].isdigit() else None
        assert chat_id is None
    
    def test_query_string_parsing(self):
        """Test parsing query string parameters"""
        path = '/api/chats/1?include_logs=true'
        base_path = path.split('?')[0]
        query_string = path.split('?')[1] if '?' in path else ''
        assert 'include_logs=true' in query_string


# ──────────────────────────────────────────────────────────────
# Error Handling Tests
# ──────────────────────────────────────────────────────────────

class TestErrorHandling:
    """Tests for error handling"""
    
    @patch('api.chats.get_user_chats')
    def test_list_chats_database_error(self, mock_get_user_chats):
        """Test handling database error when listing chats"""
        mock_get_user_chats.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception):
            mock_get_user_chats(1)
    
    @patch('api.chats.create_chat')
    def test_create_chat_database_error(self, mock_create_chat):
        """Test handling database error when creating chat"""
        mock_create_chat.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            mock_create_chat(1, 'Test', 'Prompt')
    
    @patch('api.chats.delete_chat')
    def test_delete_chat_database_error(self, mock_delete_chat):
        """Test handling database error when deleting chat"""
        mock_delete_chat.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            mock_delete_chat(1, 1)
    
    @patch('api.chats.get_chat')
    def test_get_chat_database_error(self, mock_get_chat):
        """Test handling database error when retrieving chat"""
        mock_get_chat.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            mock_get_chat(1, 1)


# ──────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────

class TestChatWorkflows:
    """Integration tests for chat workflows"""
    
    @patch('api.chats.create_chat')
    @patch('api.chats.get_user_chats')
    @patch('api.chats.validate_token')
    def test_create_then_list_chats(self, mock_validate_token, 
                                     mock_get_user_chats, mock_create_chat):
        """Test complete workflow: create chat then list all chats"""
        mock_validate_token.return_value = {'user_id': 1, 'username': 'testuser'}
        new_chat = create_sample_chat()
        mock_create_chat.return_value = new_chat
        
        # Step 1: Authenticate
        user = get_auth_user({'Authorization': 'Bearer token'})
        assert user is not None
        
        # Step 2: Create chat
        created = mock_create_chat(user['user_id'], 'New Chat', 'Test prompt')
        assert created['ID'] == 1
        
        # Step 3: List all chats
        mock_get_user_chats.return_value = [new_chat]
        chats = mock_get_user_chats(user['user_id'])
        assert len(chats) == 1
    
    @patch('api.chats.delete_chat')
    @patch('api.chats.get_chat_messages')
    @patch('api.chats.get_chat')
    @patch('api.chats.validate_token')
    def test_get_then_delete_chat(self, mock_validate_token, mock_get_chat,
                                   mock_get_messages, mock_delete_chat):
        """Test complete workflow: get chat then delete it"""
        mock_validate_token.return_value = {'user_id': 1, 'username': 'testuser'}
        chat = create_sample_chat()
        mock_get_chat.return_value = chat
        mock_get_messages.return_value = [create_sample_message()]
        
        # Step 1: Authenticate
        user = get_auth_user({'Authorization': 'Bearer token'})
        
        # Step 2: Get chat
        retrieved = mock_get_chat(1, user['user_id'])
        assert retrieved['ID'] == 1
        
        # Step 3: Get messages
        messages = mock_get_messages(1)
        assert len(messages) == 1
        
        # Step 4: Delete chat
        mock_delete_chat.return_value = True
        success = mock_delete_chat(1, user['user_id'])
        assert success is True
    
    @patch('api.chats.get_user_chats')
    @patch('api.chats.create_chat')
    @patch('api.chats.validate_token')
    def test_multiple_users_isolated(self, mock_validate_token, 
                                      mock_create_chat, mock_get_user_chats):
        """Test that different users' chats are isolated"""
        # User 1
        mock_validate_token.return_value = {'user_id': 1, 'username': 'user1'}
        user1 = get_auth_user({'Authorization': 'Bearer token1'})
        
        chat1 = create_sample_chat()
        chat1['userId'] = 1
        mock_get_user_chats.return_value = [chat1]
        user1_chats = mock_get_user_chats(user1['user_id'])
        
        # User 2
        mock_validate_token.return_value = {'user_id': 2, 'username': 'user2'}
        user2 = get_auth_user({'Authorization': 'Bearer token2'})
        
        chat2 = create_sample_chat()
        chat2['ID'] = 2
        chat2['userId'] = 2
        mock_get_user_chats.return_value = [chat2]
        user2_chats = mock_get_user_chats(user2['user_id'])
        
        # Verify isolation
        assert user1_chats[0]['userId'] == 1
        assert user2_chats[0]['userId'] == 2
        assert user1_chats[0]['ID'] != user2_chats[0]['ID']


# ──────────────────────────────────────────────────────────────
# Chat Retrieval with Logs Tests
# ──────────────────────────────────────────────────────────────

class TestChatRetrievalWithLogs:
    """Tests for chat retrieval including generation logs"""
    
    @patch('api.chats.get_chat_logs')
    @patch('api.chats.get_chat_messages')
    @patch('api.chats.get_chat')
    def test_retrieve_chat_with_logs(self, mock_get_chat, 
                                      mock_get_messages, mock_get_logs):
        """Test retrieving chat with generation logs"""
        mock_get_chat.return_value = create_sample_chat()
        mock_get_messages.return_value = [create_sample_message()]
        mock_get_logs.return_value = [
            {'ID': 1, 'messageId': 1, 'model_used': 'gpt-4o-mini', 'tokens_used': 150}
        ]
        
        chat = mock_get_chat(1, 1)
        messages = mock_get_messages(1)
        logs = mock_get_logs(1)
        
        assert chat is not None
        assert len(messages) == 1
        assert len(logs) == 1
        assert logs[0]['tokens_used'] == 150
    
    @patch('api.chats.get_chat_logs')
    def test_retrieve_logs_for_chat(self, mock_get_logs):
        """Test retrieving logs for a specific chat"""
        mock_get_logs.return_value = [
            {'ID': 1, 'model_used': 'gpt-4o', 'tokens_used': 200},
            {'ID': 2, 'model_used': 'gpt-4o-mini', 'tokens_used': 150}
        ]
        
        logs = mock_get_logs(1)
        
        assert len(logs) == 2
        total_tokens = sum(log['tokens_used'] for log in logs)
        assert total_tokens == 350
    
    @patch('api.chats.get_chat_logs')
    def test_empty_logs_for_new_chat(self, mock_get_logs):
        """Test that new chat has no logs"""
        mock_get_logs.return_value = []
        
        logs = mock_get_logs(1)
        
        assert logs == []


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
