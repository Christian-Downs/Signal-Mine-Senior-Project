"""
Comprehensive unit tests for SignalMine Flask Backend (frontend.py)
Tests authentication, models, and LP generation functionality
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from flask import Flask
import sys
import os

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Block database module to force in-memory mode (DB_AVAILABLE=False)
class BlockedModule:
    def __getattr__(self, name):
        raise ModuleNotFoundError(f"api.database module blocked in tests")

sys.modules['api'] = BlockedModule()
sys.modules['api.database'] = BlockedModule()

from frontend import (
    app, generate_token, validate_token, get_current_user,
    LinearProgram, LPResponse, DEFAULT_MODEL,
    build_response_message, memory_sessions, memory_users
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def clear_memory():
    """Clear in-memory storage before each test"""
    memory_sessions.clear()
    memory_users.clear()
    yield
    memory_sessions.clear()
    memory_users.clear()


@pytest.fixture
def auth_token():
    """Create a valid auth token for testing"""
    token = generate_token(1, "testuser")
    return token


@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers"""
    return {'Authorization': f'Bearer {auth_token}'}


# ──────────────────────────────────────────────────────────────
# Token & Session Tests
# ──────────────────────────────────────────────────────────────

class TestTokenManagement:
    """Tests for session token generation and validation"""
    
    def test_generate_token_creates_session(self):
        """Test that generate_token creates a valid session"""
        token = generate_token(1, "testuser")
        
        assert token is not None
        assert len(token) > 0
        assert token in memory_sessions
        assert memory_sessions[token]['user_id'] == 1
        assert memory_sessions[token]['username'] == "testuser"
    
    def test_validate_token_valid(self):
        """Test validating a valid token"""
        token = generate_token(1, "testuser")
        session = validate_token(token)
        
        assert session is not None
        assert session['user_id'] == 1
        assert session['username'] == "testuser"
    
    def test_validate_token_invalid(self):
        """Test validating an invalid token"""
        session = validate_token("invalid_token_12345")
        assert session is None
    
    def test_validate_token_expired(self):
        """Test validating an expired token"""
        token = generate_token(1, "testuser")
        
        # Manually expire the token
        session = memory_sessions[token]
        session['expires_at'] = (datetime.now() - timedelta(hours=1)).isoformat()
        
        result = validate_token(token)
        assert result is None
        assert token not in memory_sessions  # Should be deleted
    
    def test_validate_token_none(self):
        """Test validating None token"""
        session = validate_token(None)
        assert session is None
    
    def test_token_expiry_is_future(self):
        """Test that generated tokens have future expiry"""
        token = generate_token(1, "testuser")
        session = memory_sessions[token]
        expires_at = datetime.fromisoformat(session['expires_at'])
        
        assert expires_at > datetime.now()


# ──────────────────────────────────────────────────────────────
# Authentication Route Tests
# ──────────────────────────────────────────────────────────────

class TestAuthEndpoint:
    """Tests for /api/auth endpoint"""
    
    def test_auth_get_unauthenticated(self, client):
        """Test GET /api/auth without token"""
        response = client.get('/api/auth')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_auth_get_authenticated(self, client, auth_headers):
        """Test GET /api/auth with valid token"""
        response = client.get('/api/auth', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['authenticated'] is True
        assert data['user']['username'] == "testuser"
    
    def test_register_success(self, client):
        """Test successful user registration"""
        response = client.post(
            '/api/auth',
            json={'action': 'register', 'username': 'newuser', 'password': 'password123'},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'token' in data
        assert data['user']['username'] == 'newuser'
        # Verify user was added to memory
        assert 'newuser' in memory_users
    
    def test_register_duplicate_username(self, client):
        """Test registration with duplicate username"""
        # Register first user
        client.post(
            '/api/auth',
            json={'action': 'register', 'username': 'testuser', 'password': 'password123'},
            content_type='application/json'
        )
        
        # Try to register with same username
        response = client.post(
            '/api/auth',
            json={'action': 'register', 'username': 'testuser', 'password': 'password456'},
            content_type='application/json'
        )
        
        assert response.status_code == 409
        data = json.loads(response.data)
        assert 'Username already exists' in data.get('error', '')
    
    def test_register_short_username(self, client):
        """Test registration with username too short"""
        response = client.post(
            '/api/auth',
            json={'action': 'register', 'username': 'ab', 'password': 'password123'},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'at least 3 characters' in data['error']
    
    def test_register_short_password(self, client):
        """Test registration with password too short"""
        response = client.post(
            '/api/auth',
            json={'action': 'register', 'username': 'testuser', 'password': 'pass'},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'at least 6 characters' in data['error']
    
    def test_login_success(self, client):
        """Test successful login"""
        # Register first
        client.post(
            '/api/auth',
            json={'action': 'register', 'username': 'testuser', 'password': 'password123'},
            content_type='application/json'
        )
        
        # Login
        response = client.post(
            '/api/auth',
            json={'action': 'login', 'username': 'testuser', 'password': 'password123'},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'token' in data
    
    def test_login_invalid_password(self, client):
        """Test login with wrong password"""
        # Register first
        client.post(
            '/api/auth',
            json={'action': 'register', 'username': 'testuser', 'password': 'password123'},
            content_type='application/json'
        )
        
        # Try login with wrong password
        response = client.post(
            '/api/auth',
            json={'action': 'login', 'username': 'testuser', 'password': 'wrongpassword'},
            content_type='application/json'
        )
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'Invalid' in data['error']
    
    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user"""
        response = client.post(
            '/api/auth',
            json={'action': 'login', 'username': 'nonexistent', 'password': 'password123'},
            content_type='application/json'
        )
        
        assert response.status_code == 401
    
    def test_logout(self, client, auth_headers):
        """Test logout (DELETE /api/auth)"""
        # Create a token and verify it exists
        token = auth_headers['Authorization'].split(' ')[1]
        assert token in memory_sessions
        
        # Logout
        response = client.delete('/api/auth', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert token not in memory_sessions


# ──────────────────────────────────────────────────────────────
# Models Endpoint Tests
# ──────────────────────────────────────────────────────────────

class TestModelsEndpoint:
    """Tests for /api/models endpoint"""
    
    def test_get_available_models(self, client):
        """Test getting available models list"""
        response = client.get('/api/models')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'models' in data
        assert 'default' in data
        assert data['default'] == DEFAULT_MODEL
        assert len(data['models']) > 0
    
    def test_models_include_gpt_4o(self, client):
        """Test that available models include gpt-4o"""
        response = client.get('/api/models')
        data = json.loads(response.data)
        
        assert 'gpt-4o' in data['models']
        assert 'gpt-4o-mini' in data['models']


# ──────────────────────────────────────────────────────────────
# User Models Endpoint Tests
# ──────────────────────────────────────────────────────────────

class TestUserModelsEndpoint:
    """Tests for /api/user-models endpoints"""
    
    def test_get_providers_without_auth(self, client):
        """Test getting providers without authentication"""
        response = client.get('/api/user-models?providers=true')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'providers' in data
    
    def test_get_user_models_unauthenticated(self, client):
        """Test getting user models without authentication"""
        response = client.get('/api/user-models')
        
        assert response.status_code == 401
    
    @patch('frontend.DB_AVAILABLE', new=False)
    def test_post_user_model_no_database(self, client, auth_headers):
        """Test creating user model without database"""
        response = client.post(
            '/api/user-models',
            json={
                'name': 'My Model',
                'api_key': 'sk-test-123',
                'provider': 'openai'
            },
            headers=auth_headers,
            content_type='application/json'
        )
        
        assert response.status_code == 500


# ──────────────────────────────────────────────────────────────
# Chat Endpoints Tests
# ──────────────────────────────────────────────────────────────

class TestChatsEndpoint:
    """Tests for /api/chats endpoints"""
    
    @patch('frontend.DB_AVAILABLE', new=False)
    def test_get_chats_unauthenticated(self, client):
        """Test getting chats without authentication"""
        response = client.get('/api/chats')
        
        assert response.status_code == 401
    
    @patch('frontend.DB_AVAILABLE', new=False)
    def test_get_chats_authenticated(self, client, auth_headers):
        """Test getting chats with authentication (no DB)"""
        response = client.get('/api/chats', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'chats' in data
        assert data['chats'] == []
    
    @patch('frontend.DB_AVAILABLE', new=False)
    def test_create_chat_no_database(self, client, auth_headers):
        """Test creating chat without database"""
        response = client.post(
            '/api/chats',
            json={'name': 'Test Chat', 'original_prompt': 'Test prompt'},
            headers=auth_headers,
            content_type='application/json'
        )
        
        assert response.status_code == 500


# ──────────────────────────────────────────────────────────────
# Health Check Tests
# ──────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    """Tests for /health endpoint"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data


# ──────────────────────────────────────────────────────────────
# LP Generation Tests
# ──────────────────────────────────────────────────────────────

class TestLPGeneration:
    """Tests for LP generation and validation"""
    
    def test_linear_program_model_validation(self):
        """Test LinearProgram Pydantic model validation"""
        lp_data = {
            'problem_description': 'Maximize profit from production',
            'objective_type': 'maximize',
            'objective_function': '3x + 2y',
            'decision_variables': ['x', 'y'],
            'constraints': ['x + y <= 10', '2x + y <= 15'],
            'variable_bounds': {'x': '>= 0', 'y': '>= 0'}
        }
        
        lp = LinearProgram(**lp_data)
        assert lp.problem_description == 'Maximize profit from production'
        assert lp.objective_type == 'maximize'
        assert len(lp.decision_variables) == 2
    
    def test_lp_response_model_validation(self):
        """Test LPResponse Pydantic model validation"""
        lp_data = {
            'problem_description': 'Test problem',
            'objective_type': 'maximize',
            'objective_function': 'x + y',
            'decision_variables': ['x', 'y'],
            'constraints': ['x <= 5'],
            'variable_bounds': {'x': '>= 0'}
        }
        
        response_data = {
            'linear_program': lp_data,
            'explanation': 'This is a test LP',
            'assumptions': ['Test assumption'],
            'suggestions': ['Test suggestion']
        }
        
        response = LPResponse(**response_data)
        assert response.explanation == 'This is a test LP'
        assert len(response.assumptions) == 1
    
    def test_build_response_message(self):
        """Test building formatted response message"""
        lp = LinearProgram(
            problem_description='Test problem',
            objective_type='maximize',
            objective_function='3x + 2y',
            decision_variables=['x', 'y'],
            constraints=['x + y <= 10'],
            variable_bounds={'x': '>= 0', 'y': '>= 0'},
            latex_formulation='\\max 3x + 2y'
        )
        
        response = LPResponse(
            linear_program=lp,
            explanation='Test explanation',
            assumptions=['Assumption 1'],
            suggestions=['Suggestion 1']
        )
        
        message = build_response_message(lp, response, False)
        
        assert 'Linear Program Formulation' in message
        assert 'Test problem' in message
        assert 'maximize' in message
        assert '3x + 2y' in message
        assert 'Test explanation' in message
    
    def test_build_response_message_with_healing(self):
        """Test response message indicates healing was applied"""
        lp = LinearProgram(
            problem_description='Test',
            objective_type='maximize',
            objective_function='x',
            decision_variables=['x'],
            constraints=[]
        )
        
        response = LPResponse(linear_program=lp, explanation='Test')
        message = build_response_message(lp, response, True)
        
        assert 'Self-healing' in message


# ──────────────────────────────────────────────────────────────
# Chat Endpoint with LP Generation Tests
# ──────────────────────────────────────────────────────────────

class TestChatEndpoint:
    """Tests for /api/chat (LP generation) endpoint"""
    
    def test_chat_missing_prompt(self, client):
        """Test chat endpoint with missing prompt"""
        response = client.post(
            '/api/chat',
            json={'model': 'gpt-4o-mini'},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('frontend.generate_lp')
    @patch('frontend.DB_AVAILABLE', new=False)
    def test_chat_success(self, mock_generate_lp, client):
        """Test successful chat/LP generation"""
        mock_lp_response = {
            'linear_program': {
                'problem_description': 'Test problem',
                'objective_type': 'maximize',
                'objective_function': '3x + 2y',
                'decision_variables': ['x', 'y'],
                'constraints': ['x + y <= 10'],
                'variable_bounds': {'x': '>= 0', 'y': '>= 0'}
            },
            'explanation': 'Test explanation',
            'assumptions': [],
            'suggestions': []
        }
        
        mock_generate_lp.return_value = (mock_lp_response, json.dumps(mock_lp_response), 100)
        
        response = client.post(
            '/api/chat',
            json={'prompt': 'Maximize 3x + 2y subject to x + y <= 10', 'model': 'gpt-4o-mini'},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert 'linear_program' in data
        assert 'was_healed' in data
    
    @patch('frontend.generate_lp')
    @patch('frontend.DB_AVAILABLE', new=False)
    def test_chat_invalid_model_defaults(self, mock_generate_lp, client):
        """Test that invalid model name defaults to DEFAULT_MODEL"""
        mock_lp_response = {
            'linear_program': {
                'problem_description': 'Test',
                'objective_type': 'maximize',
                'objective_function': 'x',
                'decision_variables': ['x'],
                'constraints': [],
                'variable_bounds': {}
            },
            'explanation': 'Test',
            'assumptions': [],
            'suggestions': []
        }
        
        mock_generate_lp.return_value = (mock_lp_response, json.dumps(mock_lp_response), 100)
        
        response = client.post(
            '/api/chat',
            json={'prompt': 'Test prompt', 'model': 'invalid-model'},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        # Verify that generate_lp was called with DEFAULT_MODEL
        mock_generate_lp.assert_called()
        call_args = mock_generate_lp.call_args[0]
        assert call_args[1] == DEFAULT_MODEL


# ──────────────────────────────────────────────────────────────
# Error Handling Tests
# ──────────────────────────────────────────────────────────────

class TestErrorHandling:
    """Tests for error handling and edge cases"""
    
    def test_missing_authorization_header(self, client):
        """Test request without authorization header"""
        response = client.get(
            '/api/chats',
            headers={}
        )
        
        assert response.status_code == 401
    
    def test_malformed_authorization_header(self, client):
        """Test request with malformed authorization header"""
        response = client.get(
            '/api/chats',
            headers={'Authorization': 'InvalidFormat token123'}
        )
        
        assert response.status_code == 401
    
    @patch('frontend.generate_lp')
    @patch('frontend.DB_AVAILABLE', new=False)
    def test_chat_openai_error(self, mock_generate_lp, client):
        """Test chat endpoint with OpenAI API error"""
        mock_generate_lp.side_effect = ValueError("API Error")
        
        response = client.post(
            '/api/chat',
            json={'prompt': 'Test prompt'},
            content_type='application/json'
        )
        
        assert response.status_code == 422


# ──────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────

class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_register_and_auth_flow(self, client):
        """Test complete registration and authentication flow"""
        # Register
        reg_response = client.post(
            '/api/auth',
            json={'action': 'register', 'username': 'newuser', 'password': 'password123'},
            content_type='application/json'
        )
        
        assert reg_response.status_code == 200
        reg_data = json.loads(reg_response.data)
        token = reg_data['token']
        
        # Verify auth with token
        auth_response = client.get(
            '/api/auth',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        assert auth_response.status_code == 200
        auth_data = json.loads(auth_response.data)
        assert auth_data['authenticated'] is True
        assert auth_data['user']['username'] == 'newuser'
    
    def test_register_login_logout_flow(self, client):
        """Test complete flow: register, login, logout"""
        # Register
        client.post(
            '/api/auth',
            json={'action': 'register', 'username': 'flowuser', 'password': 'password123'},
            content_type='application/json'
        )
        
        # Login
        login_response = client.post(
            '/api/auth',
            json={'action': 'login', 'username': 'flowuser', 'password': 'password123'},
            content_type='application/json'
        )
        
        token = json.loads(login_response.data)['token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Verify authenticated
        auth_response = client.get('/api/auth', headers=headers)
        assert json.loads(auth_response.data)['authenticated'] is True
        
        # Logout
        logout_response = client.delete('/api/auth', headers=headers)
        assert json.loads(logout_response.data)['success'] is True
        
        # Verify token is invalid
        post_logout = client.get('/api/auth', headers=headers)
        assert post_logout.status_code == 401


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
