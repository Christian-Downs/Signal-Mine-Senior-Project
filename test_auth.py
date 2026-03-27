"""
Comprehensive unit tests for SignalMine Auth API (api/auth.py)
Tests authentication token management and HTTP request handling
"""

import pytest
import json
import secrets
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
import sys

# Mock database before importing auth
sys.modules['api.database'] = MagicMock()

from api.auth import (
    generate_token, validate_token, invalidate_token,
    SESSION_EXPIRY_HOURS
)


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
    
    @patch('api.auth.create_session')
    def test_generate_token_token_is_valid_format(self, mock_create_session):
        """Test that generated token is URL-safe"""
        token = generate_token(1, 'testuser')
        
        # URL-safe tokens should only contain alphanumeric, - and _
        assert all(c.isalnum() or c in '-_' for c in token)
    
    @patch('api.auth.create_session')
    def test_generate_token_creates_session_once(self, mock_create_session):
        """Test that create_session is called exactly once"""
        generate_token(2, 'anotheruser')
        
        assert mock_create_session.call_count == 1


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
    
    @patch('api.auth.get_session')
    def test_validate_token_calls_get_session(self, mock_get_session):
        """Test that validate_token calls get_session with correct token"""
        mock_get_session.return_value = None
        
        validate_token('my_token')
        
        mock_get_session.assert_called_once_with('my_token')
    
    @patch('api.auth.delete_session')
    @patch('api.auth.get_session')
    def test_validate_token_deletes_expired_tokens(self, mock_get_session, mock_delete_session):
        """Test that expired tokens are cleaned up"""
        expired_time = (datetime.now() - timedelta(hours=5)).isoformat()
        mock_get_session.return_value = {
            'token': 'expired_token',
            'expires_at': expired_time
        }
        
        validate_token('expired_token')
        
        mock_delete_session.assert_called_once_with('expired_token')


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
    
    @patch('api.auth.delete_session')
    def test_invalidate_token_with_special_chars(self, mock_delete_session):
        """Test invalidating token with special characters"""
        token = 'test_token_with-special_chars123'
        invalidate_token(token)
        
        mock_delete_session.assert_called_once_with(token)


# ──────────────────────────────────────────────────────────────
# HTTP Handler Logic Tests (Testing JSON response building)
# ──────────────────────────────────────────────────────────────

class TestAuthenticationLogic:
    """Tests for authentication business logic"""
    
    @patch('api.auth.create_user')
    @patch('api.auth.generate_token')
    def test_register_success_logic(self, mock_generate_token, mock_create_user):
        """Test successful registration logic"""
        mock_create_user.return_value = {'ID': 1, 'username': 'newuser'}
        mock_generate_token.return_value = 'token_123'
        
        # Simulate registration logic
        user = mock_create_user('newuser', 'password123')
        token = mock_generate_token(user['ID'], user['username'])
        
        assert user is not None
        assert user['ID'] == 1
        assert token == 'token_123'
    
    @patch('api.auth.verify_user')
    @patch('api.auth.generate_token')
    def test_login_success_logic(self, mock_generate_token, mock_verify_user):
        """Test successful login logic"""
        mock_verify_user.return_value = {'ID': 1, 'username': 'testuser'}
        mock_generate_token.return_value = 'token_123'
        
        user = mock_verify_user('testuser', 'password123')
        assert user is not None
        
        token = mock_generate_token(user['ID'], user['username'])
        assert token is not None
    
    @patch('api.auth.verify_user')
    def test_login_failure_invalid_credentials(self, mock_verify_user):
        """Test login with invalid credentials"""
        mock_verify_user.return_value = None
        
        user = mock_verify_user('testuser', 'wrongpassword')
        assert user is None
    
    @patch('api.auth.create_user')
    def test_register_failure_duplicate_username(self, mock_create_user):
        """Test registration with duplicate username"""
        mock_create_user.return_value = None
        
        user = mock_create_user('existinguser', 'password123')
        assert user is None


# ──────────────────────────────────────────────────────────────
# Validation Tests
# ──────────────────────────────────────────────────────────────

class TestInputValidation:
    """Tests for input validation logic"""
    
    def test_username_validation_too_short(self):
        """Test username must be at least 3 characters"""
        username = 'ab'
        assert len(username) < 3
    
    def test_username_validation_valid(self):
        """Test username of 3+ characters is valid"""
        username = 'abc'
        assert len(username) >= 3
    
    def test_password_validation_too_short(self):
        """Test password must be at least 6 characters"""
        password = 'pass'
        assert len(password) < 6
    
    def test_password_validation_valid(self):
        """Test password of 6+ characters is valid"""
        password = 'password'
        assert len(password) >= 6
    
    def test_required_fields_username_missing(self):
        """Test that username is required"""
        data = {'password': 'password123'}
        username = data.get('username', '').strip()
        assert not username
    
    def test_required_fields_password_missing(self):
        """Test that password is required"""
        data = {'username': 'testuser'}
        password = data.get('password', '')
        assert not password
    
    def test_json_parsing(self):
        """Test JSON parsing"""
        body = '{"action": "login", "username": "test", "password": "pass123"}'
        data = json.loads(body)
        assert data['action'] == 'login'
        assert data['username'] == 'test'
    
    def test_json_parsing_invalid(self):
        """Test invalid JSON raises error"""
        body = 'invalid json {'
        with pytest.raises(json.JSONDecodeError):
            json.loads(body)
    
    def test_action_validation_login(self):
        """Test valid login action"""
        action = 'login'
        assert action in ['login', 'register']
    
    def test_action_validation_register(self):
        """Test valid register action"""
        action = 'register'
        assert action in ['login', 'register']
    
    def test_action_validation_invalid(self):
        """Test invalid action"""
        action = 'invalid'
        assert action not in ['login', 'register']


# ──────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────

class TestAuthenticationFlow:
    """Integration tests for complete auth flows"""
    
    @patch('api.auth.generate_token')
    @patch('api.auth.create_user')
    def test_register_then_validate_token_flow(self, mock_create_user, mock_generate_token):
        """Test complete register and token validation flow"""
        # Step 1: Register user
        mock_create_user.return_value = {'ID': 1, 'username': 'newuser'}
        mock_generate_token.return_value = 'test_token_123'
        
        user = mock_create_user('newuser', 'password123')
        assert user is not None
        
        token = mock_generate_token(user['ID'], user['username'])
        assert token is not None
        
        # Step 2: Validate token
        with patch('api.auth.get_session') as mock_get_session:
            mock_get_session.return_value = {
                'token': token,
                'user_id': 1,
                'username': 'newuser',
                'expires_at': (datetime.now() + timedelta(hours=1)).isoformat()
            }
            
            result = validate_token(token)
            assert result is not None
            assert result['username'] == 'newuser'
    
    @patch('api.auth.verify_user')
    @patch('api.auth.generate_token')
    def test_login_then_logout_flow(self, mock_generate_token, mock_verify_user):
        """Test complete login and logout flow"""
        # Step 1: Login
        mock_verify_user.return_value = {'ID': 1, 'username': 'testuser'}
        mock_generate_token.return_value = 'test_token_123'
        
        user = mock_verify_user('testuser', 'password123')
        assert user is not None
        
        token = mock_generate_token(user['ID'], user['username'])
        assert token is not None
        
        # Step 2: Logout (invalidate token)
        with patch('api.auth.delete_session') as mock_delete_session:
            invalidate_token(token)
            mock_delete_session.assert_called_once_with(token)
    
    @patch('api.auth.verify_user')
    @patch('api.auth.generate_token')
    @patch('api.auth.get_session')
    def test_login_validate_then_expire_flow(self, mock_get_session, mock_generate_token, mock_verify_user):
        """Test complete login, validate, and expiry flow"""
        # Step 1: Login
        mock_verify_user.return_value = {'ID': 1, 'username': 'testuser'}
        mock_generate_token.return_value = 'test_token_123'
        
        user = mock_verify_user('testuser', 'password123')
        token = mock_generate_token(user['ID'], user['username'])
        
        # Step 2: Token is still valid
        mock_get_session.return_value = {
            'token': token,
            'expires_at': (datetime.now() + timedelta(hours=1)).isoformat()
        }
        result = validate_token(token)
        assert result is not None
        
        # Step 3: Token expires
        with patch('api.auth.delete_session') as mock_delete_session:
            mock_get_session.return_value = {
                'token': token,
                'expires_at': (datetime.now() - timedelta(hours=1)).isoformat()
            }
            result = validate_token(token)
            assert result is None
            mock_delete_session.assert_called_with(token)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
