"""
Comprehensive unit tests for SignalMine Auth API (api/auth.py)
Tests authentication token management and HTTP request handling
"""

import pytest
import json
import secrets
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from io import BytesIO
import sys
import os

# Mock database before importing auth
sys.modules['api.database'] = MagicMock()

from api.auth import (
    generate_token, validate_token, invalidate_token,
    handler, SESSION_EXPIRY_HOURS
)


# ──────────────────────────────────────────────────────────────
# Helper Functions for Testing
# ──────────────────────────────────────────────────────────────

def create_mock_request_handler(method='GET', path='/', body=None, headers=None):
    """Create a mock HTTP request handler"""
    h = handler(
        MagicMock(),
        ('127.0.0.1', 8000),
        MagicMock()
    )
    
    # Mock necessary attributes
    h.command = method
    h.path = path
    h.headers = headers or {}
    
    # Mock file operations
    h.rfile = BytesIO(body.encode() if body else b'')
    h.wfile = BytesIO()
    
    # Track send_response calls
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


# ──────────────────────────────────────────────────────────────
# Token Generation Tests
# ──────────────────────────────────────────────────────────────

class TestTokenGeneration:
    """Tests for token generation"""
    
    @patch('api.auth.create_session')
    def test_generate_token_success(self, mock_create_session):
        """Test successful token generation"""
        token = generate_token(1, 'testuser')
        
        assert token is not None
        assert len(token) > 0
        mock_create_session.assert_called_once()
        
        # Verify create_session was called with correct args
        call_args = mock_create_session.call_args[0]
        assert call_args[0] == token
        assert call_args[1] == 1
        assert call_args[2] == 'testuser'
    
    @patch('api.auth.create_session')
    def test_generate_token_sets_expiry(self, mock_create_session):
        """Test that token generation sets expiry time"""
        generate_token(1, 'testuser')
        
        call_args = mock_create_session.call_args[0]
        expires_at = call_args[3]
        
        # Verify expiry is in the future
        expires_dt = datetime.fromisoformat(expires_at)
        assert expires_dt > datetime.now()
        assert expires_dt < datetime.now() + timedelta(hours=SESSION_EXPIRY_HOURS + 1)
    
    @patch('api.auth.create_session')
    def test_generate_token_failure_raises(self, mock_create_session):
        """Test that token generation raises on database error"""
        mock_create_session.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            generate_token(1, 'testuser')


# ──────────────────────────────────────────────────────────────
# Token Validation Tests
# ──────────────────────────────────────────────────────────────

class TestTokenValidation:
    """Tests for token validation"""
    
    @patch('api.auth.get_session')
    def test_validate_token_valid(self, mock_get_session):
        """Test validation of valid token"""
        mock_get_session.return_value = {
            'token': 'test_token',
            'user_id': 1,
            'username': 'testuser',
            'expires_at': (datetime.now() + timedelta(hours=1)).isoformat()
        }
        
        result = validate_token('test_token')
        
        assert result is not None
        assert result['user_id'] == 1
        assert result['username'] == 'testuser'
    
    @patch('api.auth.get_session')
    def test_validate_token_none_token(self, mock_get_session):
        """Test validation of None token"""
        result = validate_token(None)
        assert result is None
        mock_get_session.assert_not_called()
    
    @patch('api.auth.get_session')
    def test_validate_token_empty_string(self, mock_get_session):
        """Test validation of empty token string"""
        result = validate_token('')
        assert result is None
        mock_get_session.assert_not_called()
    
    @patch('api.auth.get_session')
    def test_validate_token_not_found(self, mock_get_session):
        """Test validation of non-existent token"""
        mock_get_session.return_value = None
        
        result = validate_token('invalid_token')
        assert result is None
    
    @patch('api.auth.delete_session')
    @patch('api.auth.get_session')
    def test_validate_token_expired(self, mock_get_session, mock_delete_session):
        """Test validation of expired token"""
        mock_get_session.return_value = {
            'token': 'test_token',
            'user_id': 1,
            'username': 'testuser',
            'expires_at': (datetime.now() - timedelta(hours=1)).isoformat()
        }
        
        result = validate_token('test_token')
        
        assert result is None
        mock_delete_session.assert_called_once_with('test_token')
    
    @patch('api.auth.get_session')
    def test_validate_token_datetime_object(self, mock_get_session):
        """Test validation with datetime object instead of string"""
        mock_get_session.return_value = {
            'token': 'test_token',
            'user_id': 1,
            'username': 'testuser',
            'expires_at': datetime.now() + timedelta(hours=1)
        }
        
        result = validate_token('test_token')
        assert result is not None
    
    @patch('api.auth.get_session')
    def test_validate_token_database_error(self, mock_get_session):
        """Test validation handles database errors gracefully"""
        mock_get_session.side_effect = Exception("Database error")
        
        result = validate_token('test_token')
        assert result is None


# ──────────────────────────────────────────────────────────────
# Token Invalidation Tests
# ──────────────────────────────────────────────────────────────

class TestTokenInvalidation:
    """Tests for token invalidation"""
    
    @patch('api.auth.delete_session')
    def test_invalidate_token_success(self, mock_delete_session):
        """Test successful token invalidation"""
        invalidate_token('test_token')
        mock_delete_session.assert_called_once_with('test_token')
    
    @patch('api.auth.delete_session')
    def test_invalidate_token_none(self, mock_delete_session):
        """Test invalidating None token does nothing"""
        invalidate_token(None)
        mock_delete_session.assert_not_called()
    
    @patch('api.auth.delete_session')
    def test_invalidate_token_empty_string(self, mock_delete_session):
        """Test invalidating empty token does nothing"""
        invalidate_token('')
        mock_delete_session.assert_not_called()
    
    @patch('api.auth.delete_session')
    def test_invalidate_token_database_error(self, mock_delete_session):
        """Test invalidation handles database errors gracefully"""
        mock_delete_session.side_effect = Exception("Database error")
        
        # Should not raise
        invalidate_token('test_token')


# ──────────────────────────────────────────────────────────────
# HTTP Handler: OPTIONS Tests
# ──────────────────────────────────────────────────────────────

class TestHandlerOptions:
    """Tests for OPTIONS request handling"""
    
    def test_options_returns_204(self):
        """Test OPTIONS request returns 204 No Content"""
        h = create_mock_request_handler(method='OPTIONS')
        h.do_OPTIONS()
        
        h.send_response.assert_called_once_with(204)
    
    def test_options_sets_cors_headers(self):
        """Test OPTIONS request sets CORS headers"""
        h = create_mock_request_handler(method='OPTIONS')
        h.do_OPTIONS()
        
        # Verify CORS headers were set
        header_calls = [call[0][1] for call in h.send_header.call_args_list]
        assert 'Access-Control-Allow-Origin' in header_calls
        assert 'Access-Control-Allow-Methods' in header_calls
        assert 'Access-Control-Allow-Headers' in header_calls


# ──────────────────────────────────────────────────────────────
# HTTP Handler: POST Tests (Register/Login)
# ──────────────────────────────────────────────────────────────

class TestHandlerPost:
    """Tests for POST request handling (login/register)"""
    
    @patch('api.auth.generate_token')
    @patch('api.auth.create_user')
    def test_post_register_success(self, mock_create_user, mock_generate_token):
        """Test successful user registration"""
        mock_create_user.return_value = {'ID': 1, 'username': 'newuser'}
        mock_generate_token.return_value = 'test_token_123'
        
        body = json.dumps({
            'action': 'register',
            'username': 'newuser',
            'password': 'password123'
        })
        
        h = create_mock_request_handler(
            method='POST',
            body=body,
            headers={'Content-Length': str(len(body))}
        )
        h.headers = {'Content-Length': str(len(body))}
        h.do_POST()
        
        h.send_response.assert_called_with(200)
        response = get_response_from_handler(h)
        
        assert response['success'] is True
        assert response['token'] == 'test_token_123'
        assert response['user']['username'] == 'newuser'
    
    @patch('api.auth.verify_user')
    @patch('api.auth.generate_token')
    def test_post_login_success(self, mock_generate_token, mock_verify_user):
        """Test successful login"""
        mock_verify_user.return_value = {'ID': 1, 'username': 'testuser'}
        mock_generate_token.return_value = 'test_token_123'
        
        body = json.dumps({
            'action': 'login',
            'username': 'testuser',
            'password': 'password123'
        })
        
        h = create_mock_request_handler(
            method='POST',
            body=body,
            headers={'Content-Length': str(len(body))}
        )
        h.headers = {'Content-Length': str(len(body))}
        h.do_POST()
        
        h.send_response.assert_called_with(200)
        response = get_response_from_handler(h)
        
        assert response['success'] is True
        assert response['message'] == 'Login successful'
    
    @patch('api.auth.verify_user')
    def test_post_login_invalid_credentials(self, mock_verify_user):
        """Test login with invalid credentials"""
        mock_verify_user.return_value = None
        
        body = json.dumps({
            'action': 'login',
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        h = create_mock_request_handler(
            method='POST',
            body=body,
            headers={'Content-Length': str(len(body))}
        )
        h.headers = {'Content-Length': str(len(body))}
        h.do_POST()
        
        h.send_response.assert_called_with(401)
        response = get_response_from_handler(h)
        assert 'Invalid username or password' in response['error']
    
    @patch('api.auth.create_user')
    def test_post_register_duplicate_username(self, mock_create_user):
        """Test registration with duplicate username"""
        mock_create_user.return_value = None
        
        body = json.dumps({
            'action': 'register',
            'username': 'existinguser',
            'password': 'password123'
        })
        
        h = create_mock_request_handler(
            method='POST',
            body=body,
            headers={'Content-Length': str(len(body))}
        )
        h.headers = {'Content-Length': str(len(body))}
        h.do_POST()
        
        h.send_response.assert_called_with(409)
        response = get_response_from_handler(h)
        assert 'Username already exists' in response['error']
    
    def test_post_missing_username(self):
        """Test POST with missing username"""
        body = json.dumps({
            'action': 'login',
            'password': 'password123'
        })
        
        h = create_mock_request_handler(
            method='POST',
            body=body,
            headers={'Content-Length': str(len(body))}
        )
        h.headers = {'Content-Length': str(len(body))}
        h.do_POST()
        
        h.send_response.assert_called_with(400)
        response = get_response_from_handler(h)
        assert 'Username and password are required' in response['error']
    
    def test_post_missing_password(self):
        """Test POST with missing password"""
        body = json.dumps({
            'action': 'login',
            'username': 'testuser'
        })
        
        h = create_mock_request_handler(
            method='POST',
            body=body,
            headers={'Content-Length': str(len(body))}
        )
        h.headers = {'Content-Length': str(len(body))}
        h.do_POST()
        
        h.send_response.assert_called_with(400)
        response = get_response_from_handler(h)
        assert 'Username and password are required' in response['error']
    
    def test_post_short_username(self):
        """Test POST with username less than 3 characters"""
        body = json.dumps({
            'action': 'login',
            'username': 'ab',
            'password': 'password123'
        })
        
        h = create_mock_request_handler(
            method='POST',
            body=body,
            headers={'Content-Length': str(len(body))}
        )
        h.headers = {'Content-Length': str(len(body))}
        h.do_POST()
        
        h.send_response.assert_called_with(400)
        response = get_response_from_handler(h)
        assert 'at least 3 characters' in response['error']
    
    def test_post_short_password(self):
        """Test POST with password less than 6 characters"""
        body = json.dumps({
            'action': 'login',
            'username': 'testuser',
            'password': 'pass'
        })
        
        h = create_mock_request_handler(
            method='POST',
            body=body,
            headers={'Content-Length': str(len(body))}
        )
        h.headers = {'Content-Length': str(len(body))}
        h.do_POST()
        
        h.send_response.assert_called_with(400)
        response = get_response_from_handler(h)
        assert 'at least 6 characters' in response['error']
    
    def test_post_invalid_json(self):
        """Test POST with invalid JSON"""
        body = 'invalid json {'
        
        h = create_mock_request_handler(
            method='POST',
            body=body,
            headers={'Content-Length': str(len(body))}
        )
        h.headers = {'Content-Length': str(len(body))}
        h.do_POST()
        
        h.send_response.assert_called_with(400)
        response = get_response_from_handler(h)
        assert 'Invalid JSON' in response['error']
    
    def test_post_invalid_action(self):
        """Test POST with invalid action"""
        body = json.dumps({
            'action': 'invalid',
            'username': 'testuser',
            'password': 'password123'
        })
        
        h = create_mock_request_handler(
            method='POST',
            body=body,
            headers={'Content-Length': str(len(body))}
        )
        h.headers = {'Content-Length': str(len(body))}
        h.do_POST()
        
        h.send_response.assert_called_with(400)
        response = get_response_from_handler(h)
        assert 'Invalid action' in response['error']


# ──────────────────────────────────────────────────────────────
# HTTP Handler: GET Tests (Token Validation)
# ──────────────────────────────────────────────────────────────

class TestHandlerGet:
    """Tests for GET request handling (token validation)"""
    
    @patch('api.auth.validate_token')
    def test_get_valid_token(self, mock_validate_token):
        """Test GET with valid token"""
        mock_validate_token.return_value = {
            'token': 'test_token',
            'user_id': 1,
            'username': 'testuser',
            'expires_at': (datetime.now() + timedelta(hours=1)).isoformat()
        }
        
        h = create_mock_request_handler(
            method='GET',
            headers={'Authorization': 'Bearer test_token'}
        )
        h.headers = {'Authorization': 'Bearer test_token'}
        h.do_GET()
        
        h.send_response.assert_called_with(200)
        response = get_response_from_handler(h)
        
        assert response['authenticated'] is True
        assert response['user']['id'] == 1
        assert response['user']['username'] == 'testuser'
    
    def test_get_missing_authorization_header(self):
        """Test GET without Authorization header"""
        h = create_mock_request_handler(method='GET', headers={})
        h.headers = {}
        h.do_GET()
        
        h.send_response.assert_called_with(401)
        response = get_response_from_handler(h)
        assert 'Missing or invalid Authorization header' in response['error']
    
    def test_get_malformed_authorization_header(self):
        """Test GET with malformed Authorization header"""
        h = create_mock_request_handler(
            method='GET',
            headers={'Authorization': 'InvalidFormat token'}
        )
        h.headers = {'Authorization': 'InvalidFormat token'}
        h.do_GET()
        
        h.send_response.assert_called_with(401)
        response = get_response_from_handler(h)
        assert 'Missing or invalid Authorization header' in response['error']
    
    @patch('api.auth.validate_token')
    def test_get_invalid_token(self, mock_validate_token):
        """Test GET with invalid token"""
        mock_validate_token.return_value = None
        
        h = create_mock_request_handler(
            method='GET',
            headers={'Authorization': 'Bearer invalid_token'}
        )
        h.headers = {'Authorization': 'Bearer invalid_token'}
        h.do_GET()
        
        h.send_response.assert_called_with(401)
        response = get_response_from_handler(h)
        assert 'Invalid or expired token' in response['error']


# ──────────────────────────────────────────────────────────────
# HTTP Handler: DELETE Tests (Logout)
# ──────────────────────────────────────────────────────────────

class TestHandlerDelete:
    """Tests for DELETE request handling (logout)"""
    
    @patch('api.auth.invalidate_token')
    def test_delete_logout_success(self, mock_invalidate_token):
        """Test successful logout"""
        h = create_mock_request_handler(
            method='DELETE',
            headers={'Authorization': 'Bearer test_token'}
        )
        h.headers = {'Authorization': 'Bearer test_token'}
        h.do_DELETE()
        
        h.send_response.assert_called_with(200)
        mock_invalidate_token.assert_called_once_with('test_token')
        
        response = get_response_from_handler(h)
        assert response['success'] is True
    
    @patch('api.auth.invalidate_token')
    def test_delete_logout_no_token(self, mock_invalidate_token):
        """Test DELETE without token still returns success"""
        h = create_mock_request_handler(method='DELETE', headers={})
        h.headers = {}
        h.do_DELETE()
        
        h.send_response.assert_called_with(200)
        mock_invalidate_token.assert_not_called()
        
        response = get_response_from_handler(h)
        assert response['success'] is True


# ──────────────────────────────────────────────────────────────
# Error Handling Tests
# ──────────────────────────────────────────────────────────────

class TestErrorHandling:
    """Tests for error handling"""
    
    @patch('api.auth.create_user')
    def test_server_error_on_post(self, mock_create_user):
        """Test server error handling on POST"""
        mock_create_user.side_effect = Exception("Database error")
        
        body = json.dumps({
            'action': 'register',
            'username': 'newuser',
            'password': 'password123'
        })
        
        h = create_mock_request_handler(
            method='POST',
            body=body,
            headers={'Content-Length': str(len(body))}
        )
        h.headers = {'Content-Length': str(len(body))}
        h.do_POST()
        
        h.send_response.assert_called_with(500)
        response = get_response_from_handler(h)
        assert 'Server error' in response['error']
    
    @patch('api.auth.validate_token')
    def test_server_error_on_get(self, mock_validate_token):
        """Test server error handling on GET"""
        mock_validate_token.side_effect = Exception("Unexpected error")
        
        h = create_mock_request_handler(
            method='GET',
            headers={'Authorization': 'Bearer test_token'}
        )
        h.headers = {'Authorization': 'Bearer test_token'}
        h.do_GET()
        
        h.send_response.assert_called_with(500)
        response = get_response_from_handler(h)
        assert 'Server error' in response['error']


# ──────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────

class TestIntegration:
    """Integration tests for complete auth flows"""
    
    @patch('api.auth.generate_token')
    @patch('api.auth.create_user')
    def test_register_then_login_flow(self, mock_create_user, mock_generate_token):
        """Test complete register and login flow"""
        mock_create_user.return_value = {'ID': 1, 'username': 'newuser'}
        mock_generate_token.return_value = 'test_token_123'
        
        # Register
        body = json.dumps({
            'action': 'register',
            'username': 'newuser',
            'password': 'password123'
        })
        
        h1 = create_mock_request_handler(
            method='POST',
            body=body,
            headers={'Content-Length': str(len(body))}
        )
        h1.headers = {'Content-Length': str(len(body))}
        h1.do_POST()
        
        response1 = get_response_from_handler(h1)
        assert response1['success'] is True
        token = response1['token']
        
        # Now validate token
        mock_validate_token = MagicMock(return_value={
            'token': token,
            'user_id': 1,
            'username': 'newuser'
        })
        
        with patch('api.auth.validate_token', mock_validate_token):
            h2 = create_mock_request_handler(
                method='GET',
                headers={'Authorization': f'Bearer {token}'}
            )
            h2.headers = {'Authorization': f'Bearer {token}'}
            h2.do_GET()
            
            response2 = get_response_from_handler(h2)
            assert response2['authenticated'] is True
            assert response2['user']['username'] == 'newuser'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
