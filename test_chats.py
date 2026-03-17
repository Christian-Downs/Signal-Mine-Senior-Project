"""
Comprehensive unit tests for SignalMine Chats API (api/chats.py)
Tests chat management, retrieval, creation, and deletion operations
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from io import BytesIO
import sys
import os
from urllib.parse import urlencode

# Mock database and auth before importing chats
sys.modules['api.database'] = MagicMock()
sys.modules['api.auth'] = MagicMock()

from api.chats import (
    get_auth_user, handler
)


# ──────────────────────────────────────────────────────────────
# Helper Functions for Testing
# ──────────────────────────────────────────────────────────────

def create_mock_handler(method='GET', path='/api/chats', body=None, headers=None):
    """Create a mock HTTP handler"""
    h = handler(
        MagicMock(),
        ('127.0.0.1', 8000),
        MagicMock()
    )
    
    h.command = method
    h.path = path
    h.headers = headers or {}
    h.rfile = BytesIO(body.encode() if body else b'')
    h.wfile = BytesIO()
    
    h.send_response = MagicMock()
    h.send_header = MagicMock()
    h.end_headers = MagicMock()
    
    return h


def get_response_from_handler(handler_obj):
    """Extract JSON response from handler"""
    handler_obj.wfile.seek(0)
    response_data = handler_obj.wfile.read().decode()
    if response_data:
        return json.loads(response_data)
    return None


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


# ──────────────────────────────────────────────────────────────
# OPTIONS Request Tests
# ──────────────────────────────────────────────────────────────

class TestHandlerOptions:
    """Tests for OPTIONS request handling"""
    
    def test_options_returns_204(self):
        """Test OPTIONS request returns 204 No Content"""
        h = create_mock_handler(method='OPTIONS')
        h.do_OPTIONS()
        
        h.send_response.assert_called_once_with(204)
    
    def test_options_sets_cors_headers(self):
        """Test OPTIONS request sets CORS headers"""
        h = create_mock_handler(method='OPTIONS')
        h.do_OPTIONS()
        
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        assert 'Access-Control-Allow-Origin' in header_dict
        assert 'Access-Control-Allow-Methods' in header_dict
        assert 'Access-Control-Allow-Headers' in header_dict


# ──────────────────────────────────────────────────────────────
# GET Request Tests
# ──────────────────────────────────────────────────────────────

class TestHandlerGetAllChats:
    """Tests for GET /api/chats (list all chats)"""
    
    @patch('api.chats.get_user_chats')
    @patch('api.chats.get_auth_user')
    def test_get_all_chats_success(self, mock_get_auth_user, mock_get_user_chats):
        """Test getting all chats for user"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_chats.return_value = [
            {'ID': 1, 'userId': 1, 'Name': 'Chat 1'},
            {'ID': 2, 'userId': 1, 'Name': 'Chat 2'}
        ]
        
        h = create_mock_handler(
            method='GET',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        h.send_response.assert_called_with(200)
        response = get_response_from_handler(h)
        
        assert 'chats' in response
        assert len(response['chats']) == 2
    
    @patch('api.chats.get_user_chats')
    @patch('api.chats.get_auth_user')
    def test_get_all_chats_empty(self, mock_get_auth_user, mock_get_user_chats):
        """Test getting all chats when user has none"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_chats.return_value = []
        
        h = create_mock_handler(
            method='GET',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        assert response['chats'] == []
    
    @patch('api.chats.get_auth_user')
    def test_get_all_chats_unauthenticated(self, mock_get_auth_user):
        """Test getting chats without authentication"""
        mock_get_auth_user.return_value = None
        
        h = create_mock_handler(method='GET', headers={})
        h.do_GET()
        
        h.send_response.assert_called_with(401)
        response = get_response_from_handler(h)
        assert 'error' in response


class TestHandlerGetSpecificChat:
    """Tests for GET /api/chats/{id} (get specific chat)"""
    
    @patch('api.chats.get_chat_messages')
    @patch('api.chats.get_chat')
    @patch('api.chats.get_auth_user')
    def test_get_specific_chat_success(self, mock_get_auth_user, mock_get_chat, mock_get_messages):
        """Test getting a specific chat with messages"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_chat.return_value = create_sample_chat()
        mock_get_messages.return_value = [create_sample_message()]
        
        h = create_mock_handler(
            method='GET',
            path='/api/chats/1',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        h.send_response.assert_called_with(200)
        response = get_response_from_handler(h)
        
        assert 'chat' in response
        assert 'messages' in response
        assert len(response['messages']) == 1
    
    @patch('api.chats.get_chat')
    @patch('api.chats.get_auth_user')
    def test_get_specific_chat_not_found(self, mock_get_auth_user, mock_get_chat):
        """Test getting nonexistent chat"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_chat.return_value = None
        
        h = create_mock_handler(
            method='GET',
            path='/api/chats/999',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        h.send_response.assert_called_with(404)
        response = get_response_from_handler(h)
        assert 'error' in response
    
    @patch('api.chats.get_chat_logs')
    @patch('api.chats.get_chat_messages')
    @patch('api.chats.get_chat')
    @patch('api.chats.get_auth_user')
    def test_get_specific_chat_with_logs(self, mock_get_auth_user, mock_get_chat, 
                                         mock_get_messages, mock_get_logs):
        """Test getting chat with logs included"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_chat.return_value = create_sample_chat()
        mock_get_messages.return_value = [create_sample_message()]
        mock_get_logs.return_value = [
            {'ID': 1, 'messageId': 1, 'model_used': 'gpt-4o-mini', 'tokens_used': 150}
        ]
        
        h = create_mock_handler(
            method='GET',
            path='/api/chats/1?include_logs=true',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        assert 'logs' in response
        assert len(response['logs']) == 1
    
    @patch('api.chats.get_auth_user')
    def test_get_specific_chat_invalid_id(self, mock_get_auth_user):
        """Test getting chat with invalid ID format"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        
        h = create_mock_handler(
            method='GET',
            path='/api/chats/abc',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        # Should list all chats when ID format is invalid
        h.send_response.assert_called_with(200)
    
    @patch('api.chats.get_chat')
    @patch('api.chats.get_auth_user')
    def test_get_chat_authorization_check(self, mock_get_auth_user, mock_get_chat):
        """Test that chat ownership is verified"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_chat.return_value = None  # Chat doesn't belong to user
        
        h = create_mock_handler(
            method='GET',
            path='/api/chats/1',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        # Verify get_chat was called with user_id
        call_args = mock_get_chat.call_args[0]
        assert call_args[0] == 1  # chat_id
        assert call_args[1] == 1  # user_id


# ──────────────────────────────────────────────────────────────
# POST Request Tests
# ──────────────────────────────────────────────────────────────

class TestHandlerPostCreateChat:
    """Tests for POST /api/chats (create chat)"""
    
    @patch('api.chats.create_chat')
    @patch('api.chats.get_auth_user')
    def test_post_create_chat_success(self, mock_get_auth_user, mock_create_chat):
        """Test successful chat creation"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_create_chat.return_value = create_sample_chat()
        
        body = json.dumps({
            'name': 'My Chat',
            'original_prompt': 'What is optimization?'
        })
        
        h = create_mock_handler(
            method='POST',
            body=body,
            headers={
                'Content-Length': str(len(body)),
                'Authorization': 'Bearer valid_token'
            }
        )
        h.headers['Content-Length'] = str(len(body))
        h.do_POST()
        
        h.send_response.assert_called_with(200)
        response = get_response_from_handler(h)
        
        assert response['success'] is True
        assert 'chat' in response
    
    @patch('api.chats.create_chat')
    @patch('api.chats.get_auth_user')
    def test_post_create_chat_auto_name_from_prompt(self, mock_get_auth_user, mock_create_chat):
        """Test chat creation with auto-generated name from prompt"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_create_chat.return_value = create_sample_chat()
        
        body = json.dumps({
            'original_prompt': 'This is a very long prompt that should be truncated to first 50 characters'
        })
        
        h = create_mock_handler(
            method='POST',
            body=body,
            headers={
                'Content-Length': str(len(body)),
                'Authorization': 'Bearer valid_token'
            }
        )
        h.headers['Content-Length'] = str(len(body))
        h.do_POST()
        
        # Verify create_chat was called with auto-generated name
        call_args = mock_create_chat.call_args[0]
        name = call_args[1]
        assert '...' in name or len(name) <= 50
    
    @patch('api.chats.create_chat')
    @patch('api.chats.get_auth_user')
    def test_post_create_chat_default_name(self, mock_get_auth_user, mock_create_chat):
        """Test chat creation with default name when no prompt or name"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_create_chat.return_value = create_sample_chat()
        
        body = json.dumps({})
        
        h = create_mock_handler(
            method='POST',
            body=body,
            headers={
                'Content-Length': str(len(body)),
                'Authorization': 'Bearer valid_token'
            }
        )
        h.headers['Content-Length'] = str(len(body))
        h.do_POST()
        
        # Verify create_chat was called with 'New Chat' as default
        call_args = mock_create_chat.call_args[0]
        name = call_args[1]
        assert name == 'New Chat'
    
    @patch('api.chats.get_auth_user')
    def test_post_create_chat_unauthenticated(self, mock_get_auth_user):
        """Test chat creation without authentication"""
        mock_get_auth_user.return_value = None
        
        body = json.dumps({'name': 'Test'})
        
        h = create_mock_handler(
            method='POST',
            body=body,
            headers={'Content-Length': str(len(body))}
        )
        h.headers['Content-Length'] = str(len(body))
        h.do_POST()
        
        h.send_response.assert_called_with(401)
    
    @patch('api.chats.get_auth_user')
    def test_post_create_chat_invalid_json(self, mock_get_auth_user):
        """Test chat creation with invalid JSON"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        
        body = 'invalid json {'
        
        h = create_mock_handler(
            method='POST',
            body=body,
            headers={
                'Content-Length': str(len(body)),
                'Authorization': 'Bearer valid_token'
            }
        )
        h.headers['Content-Length'] = str(len(body))
        h.do_POST()
        
        h.send_response.assert_called_with(400)
        response = get_response_from_handler(h)
        assert 'Invalid JSON' in response['error']


# ──────────────────────────────────────────────────────────────
# DELETE Request Tests
# ──────────────────────────────────────────────────────────────

class TestHandlerDeleteChat:
    """Tests for DELETE /api/chats/{id} (delete chat)"""
    
    @patch('api.chats.delete_chat')
    @patch('api.chats.get_auth_user')
    def test_delete_chat_success(self, mock_get_auth_user, mock_delete_chat):
        """Test successful chat deletion"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_delete_chat.return_value = True
        
        h = create_mock_handler(
            method='DELETE',
            path='/api/chats/1',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_DELETE()
        
        h.send_response.assert_called_with(200)
        response = get_response_from_handler(h)
        
        assert response['success'] is True
    
    @patch('api.chats.delete_chat')
    @patch('api.chats.get_auth_user')
    def test_delete_chat_not_found(self, mock_get_auth_user, mock_delete_chat):
        """Test deleting nonexistent chat"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_delete_chat.return_value = False
        
        h = create_mock_handler(
            method='DELETE',
            path='/api/chats/999',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_DELETE()
        
        h.send_response.assert_called_with(404)
        response = get_response_from_handler(h)
        assert 'error' in response
    
    @patch('api.chats.get_auth_user')
    def test_delete_chat_unauthenticated(self, mock_get_auth_user):
        """Test chat deletion without authentication"""
        mock_get_auth_user.return_value = None
        
        h = create_mock_handler(
            method='DELETE',
            path='/api/chats/1',
            headers={}
        )
        h.do_DELETE()
        
        h.send_response.assert_called_with(401)
    
    @patch('api.chats.get_auth_user')
    def test_delete_chat_no_id(self, mock_get_auth_user):
        """Test chat deletion without ID in path"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        
        h = create_mock_handler(
            method='DELETE',
            path='/api/chats/',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_DELETE()
        
        h.send_response.assert_called_with(400)
        response = get_response_from_handler(h)
        assert 'Chat ID required' in response['error']
    
    @patch('api.chats.get_auth_user')
    def test_delete_chat_invalid_id(self, mock_get_auth_user):
        """Test chat deletion with invalid ID format"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        
        h = create_mock_handler(
            method='DELETE',
            path='/api/chats/abc',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_DELETE()
        
        h.send_response.assert_called_with(400)
        response = get_response_from_handler(h)
        assert 'Chat ID required' in response['error']


# ──────────────────────────────────────────────────────────────
# Serialization Tests
# ──────────────────────────────────────────────────────────────

class TestSerializationMethods:
    """Tests for serialization helper methods"""
    
    def test_serialize_dict_with_datetime(self):
        """Test serializing dict with datetime objects"""
        h = create_mock_handler()
        
        dt = datetime(2026, 3, 16, 12, 30, 45)
        data = {
            'ID': 1,
            'name': 'Test',
            'created_at': dt
        }
        
        result = h._serialize_dict(data)
        
        assert result['ID'] == 1
        assert result['name'] == 'Test'
        assert isinstance(result['created_at'], str)
        assert '2026-03-16' in result['created_at']
    
    def test_serialize_dict_without_datetime(self):
        """Test serializing dict without datetime objects"""
        h = create_mock_handler()
        
        data = {
            'ID': 1,
            'name': 'Test',
            'count': 42
        }
        
        result = h._serialize_dict(data)
        
        assert result == data
    
    def test_serialize_dict_mixed(self):
        """Test serializing dict with mixed types"""
        h = create_mock_handler()
        
        dt = datetime.now()
        data = {
            'ID': 1,
            'name': 'Test',
            'created_at': dt,
            'count': 42,
            'active': True
        }
        
        result = h._serialize_dict(data)
        
        assert result['ID'] == 1
        assert isinstance(result['created_at'], str)
        assert result['count'] == 42
        assert result['active'] is True
    
    def test_serialize_dict_none(self):
        """Test serializing None"""
        h = create_mock_handler()
        result = h._serialize_dict(None)
        assert result is None
    
    def test_serialize_dict_empty(self):
        """Test serializing empty dict"""
        h = create_mock_handler()
        result = h._serialize_dict({})
        assert result == {}


# ──────────────────────────────────────────────────────────────
# JSON Response Tests
# ──────────────────────────────────────────────────────────────

class TestJsonResponses:
    """Tests for JSON response formatting"""
    
    def test_send_json_default_status(self):
        """Test sending JSON with default status 200"""
        h = create_mock_handler()
        h._send_json({'test': 'data'})
        
        h.send_response.assert_called_with(200)
    
    def test_send_json_custom_status(self):
        """Test sending JSON with custom status"""
        h = create_mock_handler()
        h._send_json({'error': 'Not found'}, 404)
        
        h.send_response.assert_called_with(404)
    
    def test_send_json_headers(self):
        """Test that JSON response sets correct headers"""
        h = create_mock_handler()
        h._send_json({'test': 'data'})
        
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        assert header_dict['Content-Type'] == 'application/json'
        assert header_dict['Access-Control-Allow-Origin'] == '*'


# ──────────────────────────────────────────────────────────────
# Path Parsing Tests
# ──────────────────────────────────────────────────────────────

class TestPathParsing:
    """Tests for URL path parsing"""
    
    @patch('api.chats.get_user_chats')
    @patch('api.chats.get_auth_user')
    def test_path_with_trailing_slash(self, mock_get_auth_user, mock_get_user_chats):
        """Test path parsing with trailing slash"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_chats.return_value = []
        
        h = create_mock_handler(
            method='GET',
            path='/api/chats/',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        # Should still work and list all chats
        h.send_response.assert_called_with(200)
    
    @patch('api.chats.get_chat_messages')
    @patch('api.chats.get_chat')
    @patch('api.chats.get_auth_user')
    def test_path_with_query_string(self, mock_get_auth_user, mock_get_chat, mock_get_messages):
        """Test path parsing with query string"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_chat.return_value = create_sample_chat()
        mock_get_messages.return_value = []
        
        h = create_mock_handler(
            method='GET',
            path='/api/chats/1?include_logs=true',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        h.send_response.assert_called_with(200)


# ──────────────────────────────────────────────────────────────
# Error Handling Tests
# ──────────────────────────────────────────────────────────────

class TestErrorHandling:
    """Tests for error handling"""
    
    @patch('api.chats.get_user_chats')
    @patch('api.chats.get_auth_user')
    def test_get_server_error(self, mock_get_auth_user, mock_get_user_chats):
        """Test handling server errors in GET"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_chats.side_effect = Exception("Database error")
        
        h = create_mock_handler(
            method='GET',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        h.send_response.assert_called_with(500)
        response = get_response_from_handler(h)
        assert 'Server error' in response['error']
    
    @patch('api.chats.create_chat')
    @patch('api.chats.get_auth_user')
    def test_post_server_error(self, mock_get_auth_user, mock_create_chat):
        """Test handling server errors in POST"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_create_chat.side_effect = Exception("Database error")
        
        body = json.dumps({'name': 'Test'})
        
        h = create_mock_handler(
            method='POST',
            body=body,
            headers={
                'Content-Length': str(len(body)),
                'Authorization': 'Bearer valid_token'
            }
        )
        h.headers['Content-Length'] = str(len(body))
        h.do_POST()
        
        h.send_response.assert_called_with(500)
    
    @patch('api.chats.delete_chat')
    @patch('api.chats.get_auth_user')
    def test_delete_server_error(self, mock_get_auth_user, mock_delete_chat):
        """Test handling server errors in DELETE"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_delete_chat.side_effect = Exception("Database error")
        
        h = create_mock_handler(
            method='DELETE',
            path='/api/chats/1',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_DELETE()
        
        h.send_response.assert_called_with(500)


# ──────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────

class TestIntegration:
    """Integration tests for chat workflows"""
    
    @patch('api.chats.create_chat')
    @patch('api.chats.get_user_chats')
    @patch('api.chats.get_auth_user')
    def test_create_then_list_chats(self, mock_get_auth_user, mock_get_user_chats, mock_create_chat):
        """Test creating chat then listing all chats"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        new_chat = create_sample_chat()
        mock_create_chat.return_value = new_chat
        
        # Create chat
        body = json.dumps({'name': 'New Chat', 'original_prompt': 'Test'})
        h1 = create_mock_handler(
            method='POST',
            body=body,
            headers={
                'Content-Length': str(len(body)),
                'Authorization': 'Bearer valid_token'
            }
        )
        h1.headers['Content-Length'] = str(len(body))
        h1.do_POST()
        
        response1 = get_response_from_handler(h1)
        assert response1['success'] is True
        
        # List chats
        mock_get_user_chats.return_value = [new_chat]
        h2 = create_mock_handler(
            method='GET',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h2.do_GET()
        
        response2 = get_response_from_handler(h2)
        assert len(response2['chats']) == 1
    
    @patch('api.chats.get_chat_messages')
    @patch('api.chats.delete_chat')
    @patch('api.chats.get_chat')
    @patch('api.chats.get_auth_user')
    def test_get_then_delete_chat(self, mock_get_auth_user, mock_get_chat, 
                                   mock_delete_chat, mock_get_messages):
        """Test getting chat then deleting it"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        chat = create_sample_chat()
        mock_get_chat.return_value = chat
        mock_get_messages.return_value = []
        
        # Get chat
        h1 = create_mock_handler(
            method='GET',
            path='/api/chats/1',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h1.do_GET()
        
        response1 = get_response_from_handler(h1)
        assert response1['chat']['ID'] == 1
        
        # Delete chat
        mock_delete_chat.return_value = True
        h2 = create_mock_handler(
            method='DELETE',
            path='/api/chats/1',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h2.do_DELETE()
        
        response2 = get_response_from_handler(h2)
        assert response2['success'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
