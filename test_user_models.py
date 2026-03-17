"""
Comprehensive unit tests for SignalMine User Models API (api/user_models.py)
Tests custom AI model API key management
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, call
from io import BytesIO
import sys

from api.user_models import (
    handler, get_auth_user, PROVIDERS
)


# ──────────────────────────────────────────────────────────────
# Helper Functions for Testing
# ──────────────────────────────────────────────────────────────

def create_mock_handler(method='GET', path='/api/user-models', headers=None, body=''):
    """Create a mock HTTP handler for testing"""
    h = handler(
        MagicMock(),
        ('127.0.0.1', 8000),
        MagicMock()
    )
    
    h.command = method
    h.path = path
    h.headers = headers or {}
    h.rfile = BytesIO(body.encode() if isinstance(body, str) else body)
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


def create_sample_user_model():
    """Create a sample user model object"""
    return {
        'id': 1,
        'user_id': 1,
        'name': 'My GPT-4',
        'provider': 'openai',
        'api_key': 'sk-...masked',
        'base_url': 'https://api.openai.com/v1',
        'created_at': datetime.now().isoformat()
    }


def create_sample_user_models(count=3):
    """Create multiple sample user models"""
    models = []
    for i in range(count):
        model = create_sample_user_model()
        model['id'] = i + 1
        model['name'] = f'Model {i + 1}'
        models.append(model)
    return models


# ──────────────────────────────────────────────────────────────
# Authentication Tests
# ──────────────────────────────────────────────────────────────

class TestGetAuthUser:
    """Tests for extracting authenticated user from headers"""
    
    @patch('api.user_models.validate_token')
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
    
    @patch('api.user_models.validate_token')
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
        
        assert header_dict['Access-Control-Allow-Origin'] == '*'
    
    def test_options_allows_all_methods(self):
        """Test OPTIONS allows GET, POST, PUT, DELETE"""
        h = create_mock_handler(method='OPTIONS')
        h.do_OPTIONS()
        
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        methods = header_dict['Access-Control-Allow-Methods']
        assert 'GET' in methods
        assert 'POST' in methods
        assert 'PUT' in methods
        assert 'DELETE' in methods


# ──────────────────────────────────────────────────────────────
# GET Request Tests - Available Providers
# ──────────────────────────────────────────────────────────────

class TestHandlerGetProviders:
    """Tests for GET /api/user-models?providers"""
    
    def test_get_providers_no_auth_required(self):
        """Test getting providers doesn't require auth"""
        h = create_mock_handler(
            path='/api/user-models?providers=true',
            headers={}
        )
        h.do_GET()
        
        h.send_response.assert_called_with(200)
    
    def test_get_providers_returns_providers(self):
        """Test getting providers returns PROVIDERS constant"""
        h = create_mock_handler(
            path='/api/user-models?providers=true',
            headers={}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'providers' in response
        assert response['providers'] == PROVIDERS
    
    def test_get_providers_contains_openai(self):
        """Test providers includes OpenAI"""
        h = create_mock_handler(
            path='/api/user-models?providers=true',
            headers={}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'openai' in response['providers']
    
    def test_get_providers_contains_anthropic(self):
        """Test providers includes Anthropic"""
        h = create_mock_handler(
            path='/api/user-models?providers=true',
            headers={}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'anthropic' in response['providers']
    
    def test_get_providers_contains_google(self):
        """Test providers includes Google"""
        h = create_mock_handler(
            path='/api/user-models?providers=true',
            headers={}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'google' in response['providers']
    
    def test_get_providers_contains_groq(self):
        """Test providers includes Groq"""
        h = create_mock_handler(
            path='/api/user-models?providers=true',
            headers={}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'groq' in response['providers']
    
    def test_get_providers_contains_together(self):
        """Test providers includes Together"""
        h = create_mock_handler(
            path='/api/user-models?providers=true',
            headers={}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'together' in response['providers']
    
    def test_get_providers_contains_custom(self):
        """Test providers includes custom option"""
        h = create_mock_handler(
            path='/api/user-models?providers=true',
            headers={}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'custom' in response['providers']


# ──────────────────────────────────────────────────────────────
# GET Request Tests - User's Models
# ──────────────────────────────────────────────────────────────

class TestHandlerGetUserModels:
    """Tests for GET /api/user-models (user's models)"""
    
    @patch('api.user_models.get_user_models')
    @patch('api.user_models.get_auth_user')
    def test_get_user_models_success(self, mock_get_auth_user, mock_get_user_models):
        """Test getting user's custom models"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_models.return_value = create_sample_user_models(2)
        
        h = create_mock_handler(
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        h.send_response.assert_called_with(200)
        response = get_response_from_handler(h)
        
        assert 'models' in response
        assert 'providers' in response
        assert len(response['models']) == 2
    
    @patch('api.user_models.get_user_models')
    @patch('api.user_models.get_auth_user')
    def test_get_user_models_empty(self, mock_get_auth_user, mock_get_user_models):
        """Test getting user models when none exist"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_models.return_value = []
        
        h = create_mock_handler(
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert response['models'] == []
    
    @patch('api.user_models.get_auth_user')
    def test_get_user_models_unauthenticated(self, mock_get_auth_user):
        """Test getting user models without authentication"""
        mock_get_auth_user.return_value = None
        
        h = create_mock_handler(headers={})
        h.do_GET()
        
        h.send_response.assert_called_with(401)
        response = get_response_from_handler(h)
        assert 'error' in response


# ──────────────────────────────────────────────────────────────
# POST Request Tests - Create Model
# ──────────────────────────────────────────────────────────────

class TestHandlerPostCreateModel:
    """Tests for POST /api/user-models (create model)"""
    
    @patch('api.user_models.create_user_model')
    @patch('api.user_models.get_auth_user')
    def test_post_create_model_success(self, mock_get_auth_user, mock_create_user_model):
        """Test creating a new model successfully"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_create_user_model.return_value = create_sample_user_model()
        
        request_body = json.dumps({
            'name': 'My GPT-4',
            'api_key': 'sk-test123',
            'provider': 'openai'
        })
        
        h = create_mock_handler(
            method='POST',
            headers={
                'Authorization': 'Bearer valid_token',
                'Content-Length': str(len(request_body))
            },
            body=request_body
        )
        h.do_POST()
        
        h.send_response.assert_called_with(200)
        response = get_response_from_handler(h)
        assert response['success'] is True
    
    @patch('api.user_models.get_auth_user')
    def test_post_create_model_missing_name(self, mock_get_auth_user):
        """Test creating model without name"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        
        request_body = json.dumps({
            'api_key': 'sk-test123',
            'provider': 'openai'
        })
        
        h = create_mock_handler(
            method='POST',
            headers={
                'Authorization': 'Bearer valid_token',
                'Content-Length': str(len(request_body))
            },
            body=request_body
        )
        h.do_POST()
        
        h.send_response.assert_called_with(400)
        response = get_response_from_handler(h)
        assert 'error' in response
    
    @patch('api.user_models.get_auth_user')
    def test_post_create_model_missing_api_key(self, mock_get_auth_user):
        """Test creating model without API key"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        
        request_body = json.dumps({
            'name': 'My GPT-4',
            'provider': 'openai'
        })
        
        h = create_mock_handler(
            method='POST',
            headers={
                'Authorization': 'Bearer valid_token',
                'Content-Length': str(len(request_body))
            },
            body=request_body
        )
        h.do_POST()
        
        h.send_response.assert_called_with(400)
        response = get_response_from_handler(h)
        assert 'error' in response
    
    @patch('api.user_models.get_auth_user')
    def test_post_create_model_invalid_provider(self, mock_get_auth_user):
        """Test creating model with invalid provider"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        
        request_body = json.dumps({
            'name': 'My Model',
            'api_key': 'sk-test123',
            'provider': 'invalid_provider'
        })
        
        h = create_mock_handler(
            method='POST',
            headers={
                'Authorization': 'Bearer valid_token',
                'Content-Length': str(len(request_body))
            },
            body=request_body
        )
        h.do_POST()
        
        h.send_response.assert_called_with(400)
        response = get_response_from_handler(h)
        assert 'Invalid provider' in response['error']
    
    @patch('api.user_models.get_auth_user')
    def test_post_create_model_custom_without_base_url(self, mock_get_auth_user):
        """Test creating custom model without base URL"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        
        request_body = json.dumps({
            'name': 'Custom Model',
            'api_key': 'sk-test123',
            'provider': 'custom'
        })
        
        h = create_mock_handler(
            method='POST',
            headers={
                'Authorization': 'Bearer valid_token',
                'Content-Length': str(len(request_body))
            },
            body=request_body
        )
        h.do_POST()
        
        h.send_response.assert_called_with(400)
        response = get_response_from_handler(h)
        assert 'Base URL is required' in response['error']
    
    @patch('api.user_models.create_user_model')
    @patch('api.user_models.get_auth_user')
    def test_post_create_model_with_default_base_url(self, mock_get_auth_user, mock_create_user_model):
        """Test creating model uses default base_url for known providers"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_create_user_model.return_value = create_sample_user_model()
        
        request_body = json.dumps({
            'name': 'My GPT-4',
            'api_key': 'sk-test123',
            'provider': 'openai'
        })
        
        h = create_mock_handler(
            method='POST',
            headers={
                'Authorization': 'Bearer valid_token',
                'Content-Length': str(len(request_body))
            },
            body=request_body
        )
        h.do_POST()
        
        # Verify create_user_model was called with default base_url
        call_args = mock_create_user_model.call_args[0]
        assert call_args[4] == PROVIDERS['openai']['base_url']
    
    @patch('api.user_models.get_auth_user')
    def test_post_create_model_unauthenticated(self, mock_get_auth_user):
        """Test creating model without authentication"""
        mock_get_auth_user.return_value = None
        
        h = create_mock_handler(
            method='POST',
            headers={}
        )
        h.do_POST()
        
        h.send_response.assert_called_with(401)


# ──────────────────────────────────────────────────────────────
# PUT Request Tests - Update Model
# ──────────────────────────────────────────────────────────────

class TestHandlerPutUpdateModel:
    """Tests for PUT /api/user-models/:id (update model)"""
    
    @patch('api.user_models.update_user_model')
    @patch('api.user_models.get_auth_user')
    def test_put_update_model_success(self, mock_get_auth_user, mock_update_user_model):
        """Test updating a model successfully"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_update_user_model.return_value = create_sample_user_model()
        
        request_body = json.dumps({
            'name': 'Updated Model Name'
        })
        
        h = create_mock_handler(
            method='PUT',
            path='/api/user-models/1',
            headers={
                'Authorization': 'Bearer valid_token',
                'Content-Length': str(len(request_body))
            },
            body=request_body
        )
        h.do_PUT()
        
        h.send_response.assert_called_with(200)
        response = get_response_from_handler(h)
        assert response['success'] is True
    
    @patch('api.user_models.get_auth_user')
    def test_put_update_model_no_id_in_path(self, mock_get_auth_user):
        """Test updating model without ID in path"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        
        h = create_mock_handler(
            method='PUT',
            path='/api/user-models/',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_PUT()
        
        h.send_response.assert_called_with(400)
    
    @patch('api.user_models.get_auth_user')
    def test_put_update_model_invalid_provider(self, mock_get_auth_user):
        """Test updating model with invalid provider"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        
        request_body = json.dumps({
            'provider': 'invalid_provider'
        })
        
        h = create_mock_handler(
            method='PUT',
            path='/api/user-models/1',
            headers={
                'Authorization': 'Bearer valid_token',
                'Content-Length': str(len(request_body))
            },
            body=request_body
        )
        h.do_PUT()
        
        h.send_response.assert_called_with(400)
    
    @patch('api.user_models.update_user_model')
    @patch('api.user_models.get_auth_user')
    def test_put_update_model_not_found(self, mock_get_auth_user, mock_update_user_model):
        """Test updating non-existent model"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_update_user_model.return_value = None
        
        request_body = json.dumps({'name': 'New Name'})
        
        h = create_mock_handler(
            method='PUT',
            path='/api/user-models/999',
            headers={
                'Authorization': 'Bearer valid_token',
                'Content-Length': str(len(request_body))
            },
            body=request_body
        )
        h.do_PUT()
        
        h.send_response.assert_called_with(404)


# ──────────────────────────────────────────────────────────────
# DELETE Request Tests - Delete Model
# ──────────────────────────────────────────────────────────────

class TestHandlerDeleteModel:
    """Tests for DELETE /api/user-models/:id (delete model)"""
    
    @patch('api.user_models.delete_user_model')
    @patch('api.user_models.get_auth_user')
    def test_delete_model_success(self, mock_get_auth_user, mock_delete_user_model):
        """Test deleting a model successfully"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_delete_user_model.return_value = True
        
        h = create_mock_handler(
            method='DELETE',
            path='/api/user-models/1',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_DELETE()
        
        h.send_response.assert_called_with(200)
        response = get_response_from_handler(h)
        assert response['success'] is True
    
    @patch('api.user_models.delete_user_model')
    @patch('api.user_models.get_auth_user')
    def test_delete_model_not_found(self, mock_get_auth_user, mock_delete_user_model):
        """Test deleting non-existent model"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_delete_user_model.return_value = False
        
        h = create_mock_handler(
            method='DELETE',
            path='/api/user-models/999',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_DELETE()
        
        h.send_response.assert_called_with(404)
    
    @patch('api.user_models.get_auth_user')
    def test_delete_model_no_id_in_path(self, mock_get_auth_user):
        """Test deleting model without ID in path"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        
        h = create_mock_handler(
            method='DELETE',
            path='/api/user-models/',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_DELETE()
        
        h.send_response.assert_called_with(400)
    
    @patch('api.user_models.get_auth_user')
    def test_delete_model_unauthenticated(self, mock_get_auth_user):
        """Test deleting model without authentication"""
        mock_get_auth_user.return_value = None
        
        h = create_mock_handler(
            method='DELETE',
            path='/api/user-models/1',
            headers={}
        )
        h.do_DELETE()
        
        h.send_response.assert_called_with(401)


# ──────────────────────────────────────────────────────────────
# Path Parsing Tests
# ──────────────────────────────────────────────────────────────

class TestPathParsing:
    """Tests for path parsing in PUT and DELETE"""
    
    @patch('api.user_models.delete_user_model')
    @patch('api.user_models.get_auth_user')
    def test_parse_model_id_from_path(self, mock_get_auth_user, mock_delete_user_model):
        """Test parsing model ID from path"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_delete_user_model.return_value = True
        
        h = create_mock_handler(
            method='DELETE',
            path='/api/user-models/42',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_DELETE()
        
        # Verify delete_user_model was called with correct ID
        call_args = mock_delete_user_model.call_args[0]
        assert call_args[0] == 42
    
    @patch('api.user_models.delete_user_model')
    @patch('api.user_models.get_auth_user')
    def test_parse_model_id_with_trailing_slash(self, mock_get_auth_user, mock_delete_user_model):
        """Test parsing model ID with trailing slash"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_delete_user_model.return_value = True
        
        h = create_mock_handler(
            method='DELETE',
            path='/api/user-models/42/',
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_DELETE()
        
        # Verify delete_user_model was called with correct ID
        call_args = mock_delete_user_model.call_args[0]
        assert call_args[0] == 42


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
            'id': 1,
            'name': 'Test Model',
            'created_at': dt
        }
        
        result = h._serialize_dict(data)
        
        assert result['id'] == 1
        assert isinstance(result['created_at'], str)
        assert '2026-03-16' in result['created_at']
    
    def test_serialize_dict_without_datetime(self):
        """Test serializing dict without datetime objects"""
        h = create_mock_handler()
        
        data = {
            'id': 1,
            'name': 'Test Model',
            'provider': 'openai'
        }
        
        result = h._serialize_dict(data)
        
        assert result == data
    
    def test_serialize_dict_with_none(self):
        """Test serializing None"""
        h = create_mock_handler()
        result = h._serialize_dict(None)
        assert result is None


# ──────────────────────────────────────────────────────────────
# Error Handling Tests
# ──────────────────────────────────────────────────────────────

class TestErrorHandling:
    """Tests for error handling"""
    
    @patch('api.user_models.get_auth_user')
    def test_post_invalid_json(self, mock_get_auth_user):
        """Test POST with invalid JSON"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        
        h = create_mock_handler(
            method='POST',
            headers={
                'Authorization': 'Bearer valid_token',
                'Content-Length': '20'
            },
            body='{invalid json'
        )
        h.do_POST()
        
        h.send_response.assert_called_with(400)
        response = get_response_from_handler(h)
        assert 'Invalid JSON' in response['error']
    
    @patch('api.user_models.get_user_models')
    @patch('api.user_models.get_auth_user')
    def test_get_server_error(self, mock_get_auth_user, mock_get_user_models):
        """Test handling server errors in GET"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_models.side_effect = Exception("Database error")
        
        h = create_mock_handler(
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        h.send_response.assert_called_with(500)
        response = get_response_from_handler(h)
        assert 'error' in response


# ──────────────────────────────────────────────────────────────
# JSON Response Tests
# ──────────────────────────────────────────────────────────────

class TestJsonResponses:
    """Tests for JSON response formatting"""
    
    def test_send_json_sets_headers(self):
        """Test _send_json sets correct headers"""
        h = create_mock_handler()
        h._send_json({'test': 'data'})
        
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        assert header_dict['Content-Type'] == 'application/json'
        assert header_dict['Access-Control-Allow-Origin'] == '*'
    
    def test_send_json_default_status(self):
        """Test _send_json with default status 200"""
        h = create_mock_handler()
        h._send_json({'test': 'data'})
        
        h.send_response.assert_called_with(200)
    
    def test_send_json_custom_status(self):
        """Test _send_json with custom status"""
        h = create_mock_handler()
        h._send_json({'error': 'Not found'}, 404)
        
        h.send_response.assert_called_with(404)


# ──────────────────────────────────────────────────────────────
# Provider Validation Tests
# ──────────────────────────────────────────────────────────────

class TestProviderValidation:
    """Tests for provider validation"""
    
    def test_providers_constant_exists(self):
        """Test PROVIDERS constant is defined"""
        assert PROVIDERS is not None
        assert isinstance(PROVIDERS, dict)
    
    def test_openai_provider_has_required_fields(self):
        """Test OpenAI provider has required fields"""
        assert 'name' in PROVIDERS['openai']
        assert 'base_url' in PROVIDERS['openai']
        assert 'models' in PROVIDERS['openai']
    
    def test_all_providers_have_name(self):
        """Test all providers have a name"""
        for provider_key, provider_data in PROVIDERS.items():
            assert 'name' in provider_data
            assert isinstance(provider_data['name'], str)
    
    def test_all_providers_have_models_list(self):
        """Test all providers have models list"""
        for provider_key, provider_data in PROVIDERS.items():
            assert 'models' in provider_data
            assert isinstance(provider_data['models'], list)


# ──────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────

class TestIntegration:
    """Integration tests for user models workflow"""
    
    @patch('api.user_models.get_user_models')
    @patch('api.user_models.get_auth_user')
    def test_complete_get_workflow(self, mock_get_auth_user, mock_get_user_models):
        """Test complete GET workflow with models and providers"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_get_user_models.return_value = create_sample_user_models(2)
        
        h = create_mock_handler(
            headers={'Authorization': 'Bearer valid_token'}
        )
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        assert 'models' in response
        assert 'providers' in response
        assert len(response['models']) == 2
        assert len(response['providers']) > 0
    
    @patch('api.user_models.create_user_model')
    @patch('api.user_models.get_auth_user')
    def test_complete_post_workflow(self, mock_get_auth_user, mock_create_user_model):
        """Test complete POST workflow for creating model"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_create_user_model.return_value = create_sample_user_model()
        
        request_body = json.dumps({
            'name': 'My GPT-4',
            'api_key': 'sk-test123',
            'provider': 'openai'
        })
        
        h = create_mock_handler(
            method='POST',
            headers={
                'Authorization': 'Bearer valid_token',
                'Content-Length': str(len(request_body))
            },
            body=request_body
        )
        h.do_POST()
        
        response = get_response_from_handler(h)
        
        assert response['success'] is True
        assert 'message' in response
        assert 'model' in response


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
