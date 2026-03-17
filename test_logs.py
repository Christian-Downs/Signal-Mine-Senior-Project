"""
Comprehensive unit tests for SignalMine Logs API (api/logs.py)
Tests log retrieval and summary statistics
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from io import BytesIO
import sys
import os

# Mock database and auth before importing logs
sys.modules['api.database'] = MagicMock()
sys.modules['api.auth'] = MagicMock()

from api.logs import (
    get_auth_user, handler
)


# ──────────────────────────────────────────────────────────────
# Helper Functions for Testing
# ──────────────────────────────────────────────────────────────

def create_mock_handler(method='GET', path='/api/logs', headers=None):
    """Create a mock HTTP handler"""
    h = handler(
        MagicMock(),
        ('127.0.0.1', 8000),
        MagicMock()
    )
    
    h.command = method
    h.path = path
    h.headers = headers or {}
    h.rfile = BytesIO(b'')
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


def create_sample_log():
    """Create a sample log object"""
    return {
        'ID': 1,
        'messageId': 1,
        'log': '{"request": {}, "response": {}}',
        'model_used': 'gpt-4o-mini',
        'tokens_used': 150,
        'response_time_ms': 500,
        'was_healed': False,
        'created_at': datetime.now().isoformat()
    }


def create_sample_logs(count=5):
    """Create multiple sample logs"""
    logs = []
    for i in range(count):
        log = create_sample_log()
        log['ID'] = i + 1
        log['tokens_used'] = 100 + (i * 10)
        log['response_time_ms'] = 400 + (i * 20)
        log['was_healed'] = i % 2 == 0
        logs.append(log)
    return logs


# ──────────────────────────────────────────────────────────────
# Authentication Tests
# ──────────────────────────────────────────────────────────────

class TestGetAuthUser:
    """Tests for extracting authenticated user from headers"""
    
    @patch('api.logs.validate_token')
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
    
    @patch('api.logs.validate_token')
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
        assert 'GET' in header_dict.get('Access-Control-Allow-Methods', '')


# ──────────────────────────────────────────────────────────────
# GET Request Tests - User Logs
# ──────────────────────────────────────────────────────────────

class TestHandlerGetUserLogs:
    """Tests for GET /api/logs (user logs)"""
    
    @patch('api.logs.get_user_logs')
    @patch('api.logs.get_auth_user')
    def test_get_user_logs_success(self, mock_get_auth_user, mock_get_user_logs):
        """Test getting user's logs"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_logs.return_value = create_sample_logs(3)
        
        h = create_mock_handler(
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        h.send_response.assert_called_with(200)
        response = get_response_from_handler(h)
        
        assert 'logs' in response
        assert 'summary' in response
        assert len(response['logs']) == 3
    
    @patch('api.logs.get_user_logs')
    @patch('api.logs.get_auth_user')
    def test_get_user_logs_empty(self, mock_get_auth_user, mock_get_user_logs):
        """Test getting user logs when none exist"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_logs.return_value = []
        
        h = create_mock_handler(
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        assert response['logs'] == []
        assert response['summary']['total_requests'] == 0
    
    @patch('api.logs.get_user_logs')
    @patch('api.logs.get_auth_user')
    def test_get_user_logs_default_limit(self, mock_get_auth_user, mock_get_user_logs):
        """Test getting user logs with default limit"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_logs.return_value = []
        
        h = create_mock_handler(
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        # Verify get_user_logs was called with default limit
        call_args = mock_get_user_logs.call_args[0]
        assert call_args[1] == 100  # Default limit
    
    @patch('api.logs.get_user_logs')
    @patch('api.logs.get_auth_user')
    def test_get_user_logs_custom_limit(self, mock_get_auth_user, mock_get_user_logs):
        """Test getting user logs with custom limit"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_logs.return_value = create_sample_logs(2)
        
        h = create_mock_handler(
            path='/api/logs?limit=50',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        # Verify get_user_logs was called with custom limit
        call_args = mock_get_user_logs.call_args[0]
        assert call_args[1] == 50


# ──────────────────────────────────────────────────────────────
# GET Request Tests - Chat Logs
# ──────────────────────────────────────────────────────────────

class TestHandlerGetChatLogs:
    """Tests for GET /api/logs?chat_id=X"""
    
    @patch('api.logs.get_chat_logs')
    @patch('api.logs.get_auth_user')
    def test_get_chat_logs_success(self, mock_get_auth_user, mock_get_chat_logs):
        """Test getting logs for a specific chat"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_chat_logs.return_value = create_sample_logs(2)
        
        h = create_mock_handler(
            path='/api/logs?chat_id=5',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        h.send_response.assert_called_with(200)
        response = get_response_from_handler(h)
        
        assert 'logs' in response
        assert 'chat_id' in response
        assert response['chat_id'] == 5
        assert len(response['logs']) == 2
    
    @patch('api.logs.get_chat_logs')
    @patch('api.logs.get_auth_user')
    def test_get_chat_logs_empty(self, mock_get_auth_user, mock_get_chat_logs):
        """Test getting logs for chat with no logs"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_chat_logs.return_value = []
        
        h = create_mock_handler(
            path='/api/logs?chat_id=1',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        assert response['logs'] == []
        assert response['chat_id'] == 1


# ──────────────────────────────────────────────────────────────
# GET Request Tests - Message Logs
# ──────────────────────────────────────────────────────────────

class TestHandlerGetMessageLogs:
    """Tests for GET /api/logs?message_id=X"""
    
    @patch('api.logs.get_message_logs')
    @patch('api.logs.get_auth_user')
    def test_get_message_logs_success(self, mock_get_auth_user, mock_get_message_logs):
        """Test getting logs for a specific message"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_message_logs.return_value = [create_sample_log()]
        
        h = create_mock_handler(
            path='/api/logs?message_id=10',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        h.send_response.assert_called_with(200)
        response = get_response_from_handler(h)
        
        assert 'logs' in response
        assert 'message_id' in response
        assert response['message_id'] == 10
        assert len(response['logs']) == 1


# ──────────────────────────────────────────────────────────────
# Authentication Tests - GET
# ──────────────────────────────────────────────────────────────

class TestHandlerGetAuthentication:
    """Tests for authentication in GET requests"""
    
    @patch('api.logs.get_auth_user')
    def test_get_logs_unauthenticated(self, mock_get_auth_user):
        """Test getting logs without authentication"""
        mock_get_auth_user.return_value = None
        
        h = create_mock_handler(headers={})
        h.do_GET()
        
        h.send_response.assert_called_with(401)
        response = get_response_from_handler(h)
        assert 'error' in response


# ──────────────────────────────────────────────────────────────
# Summary Statistics Tests
# ──────────────────────────────────────────────────────────────

class TestSummaryStatistics:
    """Tests for summary statistics calculation"""
    
    @patch('api.logs.get_user_logs')
    @patch('api.logs.get_auth_user')
    def test_summary_total_requests(self, mock_get_auth_user, mock_get_user_logs):
        """Test total requests count in summary"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_logs.return_value = create_sample_logs(5)
        
        h = create_mock_handler(
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        assert response['summary']['total_requests'] == 5
    
    @patch('api.logs.get_user_logs')
    @patch('api.logs.get_auth_user')
    def test_summary_total_tokens(self, mock_get_auth_user, mock_get_user_logs):
        """Test total tokens sum in summary"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        logs = [
            {'tokens_used': 100, 'response_time_ms': 400, 'was_healed': False, 'model_used': 'gpt-4'},
            {'tokens_used': 150, 'response_time_ms': 500, 'was_healed': False, 'model_used': 'gpt-4'},
            {'tokens_used': 200, 'response_time_ms': 600, 'was_healed': False, 'model_used': 'gpt-4'}
        ]
        mock_get_user_logs.return_value = logs
        
        h = create_mock_handler(
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        assert response['summary']['total_tokens'] == 450  # 100 + 150 + 200
    
    @patch('api.logs.get_user_logs')
    @patch('api.logs.get_auth_user')
    def test_summary_total_tokens_with_none_values(self, mock_get_auth_user, mock_get_user_logs):
        """Test total tokens with None values"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        logs = [
            {'tokens_used': 100, 'response_time_ms': 400, 'was_healed': False, 'model_used': 'gpt-4'},
            {'tokens_used': None, 'response_time_ms': 500, 'was_healed': False, 'model_used': 'gpt-4'},
            {'tokens_used': 200, 'response_time_ms': 600, 'was_healed': False, 'model_used': 'gpt-4'}
        ]
        mock_get_user_logs.return_value = logs
        
        h = create_mock_handler(
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        assert response['summary']['total_tokens'] == 300  # 100 + 0 + 200
    
    @patch('api.logs.get_user_logs')
    @patch('api.logs.get_auth_user')
    def test_summary_avg_response_time(self, mock_get_auth_user, mock_get_user_logs):
        """Test average response time calculation"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        logs = [
            {'tokens_used': 100, 'response_time_ms': 400, 'was_healed': False, 'model_used': 'gpt-4'},
            {'tokens_used': 150, 'response_time_ms': 600, 'was_healed': False, 'model_used': 'gpt-4'},
            {'tokens_used': 200, 'response_time_ms': 800, 'was_healed': False, 'model_used': 'gpt-4'}
        ]
        mock_get_user_logs.return_value = logs
        
        h = create_mock_handler(
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        # (400 + 600 + 800) / 3 = 600
        assert response['summary']['avg_response_time_ms'] == 600.0
    
    @patch('api.logs.get_user_logs')
    @patch('api.logs.get_auth_user')
    def test_summary_healed_count(self, mock_get_auth_user, mock_get_user_logs):
        """Test healed count in summary"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        logs = [
            {'tokens_used': 100, 'response_time_ms': 400, 'was_healed': True, 'model_used': 'gpt-4'},
            {'tokens_used': 150, 'response_time_ms': 500, 'was_healed': False, 'model_used': 'gpt-4'},
            {'tokens_used': 200, 'response_time_ms': 600, 'was_healed': True, 'model_used': 'gpt-4'}
        ]
        mock_get_user_logs.return_value = logs
        
        h = create_mock_handler(
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        assert response['summary']['healed_count'] == 2
    
    @patch('api.logs.get_user_logs')
    @patch('api.logs.get_auth_user')
    def test_summary_models_used(self, mock_get_auth_user, mock_get_user_logs):
        """Test models used list in summary"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        logs = [
            {'tokens_used': 100, 'response_time_ms': 400, 'was_healed': False, 'model_used': 'gpt-4o'},
            {'tokens_used': 150, 'response_time_ms': 500, 'was_healed': False, 'model_used': 'gpt-4o-mini'},
            {'tokens_used': 200, 'response_time_ms': 600, 'was_healed': False, 'model_used': 'gpt-4o'}
        ]
        mock_get_user_logs.return_value = logs
        
        h = create_mock_handler(
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        models = response['summary']['models_used']
        assert 'gpt-4o' in models
        assert 'gpt-4o-mini' in models
        assert len(set(models)) == 2  # Should have 2 unique models


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
            'model': 'gpt-4',
            'created_at': dt
        }
        
        result = h.serialize_dict(data)
        
        assert result['ID'] == 1
        assert isinstance(result['created_at'], str)
        assert '2026-03-16' in result['created_at']
    
    def test_serialize_dict_without_datetime(self):
        """Test serializing dict without datetime objects"""
        h = create_mock_handler()
        
        data = {
            'ID': 1,
            'tokens_used': 150,
            'response_time_ms': 500
        }
        
        result = h.serialize_dict(data)
        
        assert result == data


# ──────────────────────────────────────────────────────────────
# Error Handling Tests
# ──────────────────────────────────────────────────────────────

class TestErrorHandling:
    """Tests for error handling"""
    
    @patch('api.logs.get_user_logs')
    @patch('api.logs.get_auth_user')
    def test_get_server_error(self, mock_get_auth_user, mock_get_user_logs):
        """Test handling server errors"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_logs.side_effect = Exception("Database error")
        
        h = create_mock_handler(
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        h.send_response.assert_called_with(500)
        response = get_response_from_handler(h)
        assert 'error' in response
    
    @patch('api.logs.get_user_logs')
    @patch('api.logs.get_auth_user')
    def test_get_invalid_limit_parameter(self, mock_get_auth_user, mock_get_user_logs):
        """Test handling invalid limit parameter"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_logs.return_value = []
        
        h = create_mock_handler(
            path='/api/logs?limit=invalid',
            headers={'Authorization': 'Bearer valid_token'}
        )
        # Should handle ValueError from int() conversion
        try:
            h.do_GET()
        except ValueError:
            pass  # Expected behavior


# ──────────────────────────────────────────────────────────────
# Query Parameter Tests
# ──────────────────────────────────────────────────────────────

class TestQueryParameterParsing:
    """Tests for query parameter parsing"""
    
    @patch('api.logs.get_chat_logs')
    @patch('api.logs.get_auth_user')
    def test_parse_chat_id_parameter(self, mock_get_auth_user, mock_get_chat_logs):
        """Test parsing chat_id query parameter"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_chat_logs.return_value = []
        
        h = create_mock_handler(
            path='/api/logs?chat_id=42',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        # Verify get_chat_logs was called with correct ID
        call_args = mock_get_chat_logs.call_args[0]
        assert call_args[0] == 42
    
    @patch('api.logs.get_message_logs')
    @patch('api.logs.get_auth_user')
    def test_parse_message_id_parameter(self, mock_get_auth_user, mock_get_message_logs):
        """Test parsing message_id query parameter"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_message_logs.return_value = []
        
        h = create_mock_handler(
            path='/api/logs?message_id=99',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        # Verify get_message_logs was called with correct ID
        call_args = mock_get_message_logs.call_args[0]
        assert call_args[0] == 99
    
    @patch('api.logs.get_user_logs')
    @patch('api.logs.get_auth_user')
    def test_parse_limit_parameter(self, mock_get_auth_user, mock_get_user_logs):
        """Test parsing limit query parameter"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_logs.return_value = []
        
        h = create_mock_handler(
            path='/api/logs?limit=250',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        # Verify get_user_logs was called with custom limit
        call_args = mock_get_user_logs.call_args[0]
        assert call_args[1] == 250


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
# Priority Testing
# ──────────────────────────────────────────────────────────────

class TestParameterPriority:
    """Tests for query parameter priority"""
    
    @patch('api.logs.get_chat_logs')
    @patch('api.logs.get_message_logs')
    @patch('api.logs.get_user_logs')
    @patch('api.logs.get_auth_user')
    def test_chat_id_takes_priority_over_message_id(self, mock_get_auth_user, 
                                                     mock_get_user_logs, 
                                                     mock_get_message_logs,
                                                     mock_get_chat_logs):
        """Test that chat_id parameter takes priority over message_id"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_chat_logs.return_value = []
        
        h = create_mock_handler(
            path='/api/logs?chat_id=5&message_id=10',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        # Should call get_chat_logs, not get_message_logs
        mock_get_chat_logs.assert_called_once()
        mock_get_message_logs.assert_not_called()


# ──────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────

class TestIntegration:
    """Integration tests for log workflows"""
    
    @patch('api.logs.get_user_logs')
    @patch('api.logs.get_auth_user')
    def test_complete_user_logs_workflow(self, mock_get_auth_user, mock_get_user_logs):
        """Test complete user logs retrieval with summary"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        logs = create_sample_logs(5)
        mock_get_user_logs.return_value = logs
        
        h = create_mock_handler(
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        # Verify complete response structure
        assert 'logs' in response
        assert 'summary' in response
        assert response['summary']['total_requests'] == 5
        assert 'total_tokens' in response['summary']
        assert 'avg_response_time_ms' in response['summary']
        assert 'healed_count' in response['summary']
        assert 'models_used' in response['summary']
    
    @patch('api.logs.get_chat_logs')
    @patch('api.logs.get_auth_user')
    def test_chat_logs_retrieval_workflow(self, mock_get_auth_user, mock_get_chat_logs):
        """Test chat logs retrieval workflow"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_chat_logs.return_value = create_sample_logs(2)
        
        h = create_mock_handler(
            path='/api/logs?chat_id=5',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        assert 'logs' in response
        assert response['chat_id'] == 5
        assert len(response['logs']) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
