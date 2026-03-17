"""
Comprehensive unit tests for SignalMine Chat API (api/chat.py)
Tests LP generation, validation, healing, and HTTP request handling
"""

import pytest
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from io import BytesIO
import sys
import os
from pydantic import ValidationError

# Mock database and auth before importing chat
sys.modules['api.database'] = MagicMock()
sys.modules['api.auth'] = MagicMock()

from api.chat import (
    LinearProgram, LPResponse, AVAILABLE_MODELS, DEFAULT_MODEL,
    LP_GENERATOR_SYSTEM_PROMPT, LP_FIXER_SYSTEM_PROMPT,
    get_openai_client, get_auth_user, generate_lp, fix_lp,
    validate_and_heal, build_response_message, handler
)


# ──────────────────────────────────────────────────────────────
# Helper Functions for Testing
# ──────────────────────────────────────────────────────────────

def create_mock_handler(method='POST', body=None, headers=None):
    """Create a mock HTTP handler"""
    h = handler(
        MagicMock(),
        ('127.0.0.1', 8000),
        MagicMock()
    )
    
    h.command = method
    h.path = '/api/chat'
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


def create_sample_lp_response():
    """Create a valid LP response for testing"""
    return {
        'linear_program': {
            'problem_description': 'Maximize profit from production',
            'objective_type': 'maximize',
            'objective_function': '3x + 2y',
            'decision_variables': ['x', 'y'],
            'constraints': ['x + y <= 10', '2x + y <= 15'],
            'variable_bounds': {'x': '>= 0', 'y': '>= 0'},
            'latex_formulation': '\\max 3x + 2y',
            'python_code': 'from scipy.optimize import linprog'
        },
        'explanation': 'This is a simple LP problem',
        'assumptions': ['All coefficients are positive'],
        'suggestions': ['Consider sensitivity analysis']
    }


# ──────────────────────────────────────────────────────────────
# Pydantic Model Tests
# ──────────────────────────────────────────────────────────────

class TestLinearProgramModel:
    """Tests for LinearProgram Pydantic model"""
    
    def test_linear_program_valid(self):
        """Test valid LinearProgram creation"""
        data = {
            'problem_description': 'Test problem',
            'objective_type': 'maximize',
            'objective_function': '3x + 2y',
            'decision_variables': ['x', 'y'],
            'constraints': ['x + y <= 10'],
            'variable_bounds': {'x': '>= 0', 'y': '>= 0'}
        }
        
        lp = LinearProgram(**data)
        assert lp.problem_description == 'Test problem'
        assert lp.objective_type == 'maximize'
        assert lp.objective_function == '3x + 2y'
    
    def test_linear_program_missing_required_field(self):
        """Test LinearProgram validation with missing field"""
        data = {
            'objective_type': 'maximize',
            'objective_function': '3x + 2y',
            'decision_variables': ['x', 'y'],
            'constraints': ['x + y <= 10']
        }
        
        with pytest.raises(ValidationError):
            LinearProgram(**data)
    
    def test_linear_program_with_latex_and_python(self):
        """Test LinearProgram with optional fields"""
        data = {
            'problem_description': 'Test',
            'objective_type': 'minimize',
            'objective_function': 'x + y',
            'decision_variables': ['x', 'y'],
            'constraints': [],
            'latex_formulation': '\\min x + y',
            'python_code': 'print("test")'
        }
        
        lp = LinearProgram(**data)
        assert lp.latex_formulation == '\\min x + y'
        assert lp.python_code == 'print("test")'


class TestLPResponseModel:
    """Tests for LPResponse Pydantic model"""
    
    def test_lp_response_valid(self):
        """Test valid LPResponse creation"""
        lp_data = {
            'problem_description': 'Test',
            'objective_type': 'maximize',
            'objective_function': 'x',
            'decision_variables': ['x'],
            'constraints': []
        }
        
        response_data = {
            'linear_program': lp_data,
            'explanation': 'Test explanation',
            'assumptions': ['Test assumption'],
            'suggestions': ['Test suggestion']
        }
        
        response = LPResponse(**response_data)
        assert response.explanation == 'Test explanation'
        assert len(response.assumptions) == 1
    
    def test_lp_response_default_empty_lists(self):
        """Test LPResponse with default empty lists"""
        lp_data = {
            'problem_description': 'Test',
            'objective_type': 'maximize',
            'objective_function': 'x',
            'decision_variables': ['x'],
            'constraints': []
        }
        
        response_data = {
            'linear_program': lp_data,
            'explanation': 'Test'
        }
        
        response = LPResponse(**response_data)
        assert response.assumptions == []
        assert response.suggestions == []


# ──────────────────────────────────────────────────────────────
# OpenAI Client Tests
# ──────────────────────────────────────────────────────────────

class TestOpenAIClient:
    """Tests for OpenAI client initialization"""
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test-123'})
    def test_get_openai_client_default(self):
        """Test OpenAI client initialization with default key"""
        with patch('api.chat.OpenAI') as mock_openai:
            get_openai_client()
            mock_openai.assert_called_once()
            call_kwargs = mock_openai.call_args[1]
            assert call_kwargs['api_key'] == 'sk-test-123'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_openai_client_no_key(self):
        """Test OpenAI client raises when no API key"""
        with pytest.raises(ValueError, match="OPENAI_API_KEY not set"):
            get_openai_client()
    
    def test_get_openai_client_custom_key(self):
        """Test OpenAI client with custom API key"""
        with patch('api.chat.OpenAI') as mock_openai:
            get_openai_client(api_key='sk-custom-456')
            call_kwargs = mock_openai.call_args[1]
            assert call_kwargs['api_key'] == 'sk-custom-456'
    
    def test_get_openai_client_custom_base_url(self):
        """Test OpenAI client with custom base URL"""
        with patch('api.chat.OpenAI') as mock_openai:
            get_openai_client(api_key='sk-test', base_url='https://custom.api.com/v1')
            call_kwargs = mock_openai.call_args[1]
            assert call_kwargs['base_url'] == 'https://custom.api.com/v1'


# ──────────────────────────────────────────────────────────────
# Auth User Tests
# ──────────────────────────────────────────────────────────────

class TestGetAuthUser:
    """Tests for extracting authenticated user from headers"""
    
    @patch('api.chat.validate_token')
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
    
    @patch('api.chat.validate_token')
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
# LP Generation Tests
# ──────────────────────────────────────────────────────────────

class TestGenerateLP:
    """Tests for LP generation from OpenAI"""
    
    @patch('api.chat.OpenAI')
    def test_generate_lp_success(self, mock_openai_class):
        """Test successful LP generation"""
        # Mock the OpenAI response
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        response_data = create_sample_lp_response()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(response_data)
        mock_response.usage.total_tokens = 150
        
        mock_client.chat.completions.create.return_value = mock_response
        
        result, raw_content, tokens = generate_lp('Test prompt', 'gpt-4o-mini', [])
        
        assert result['linear_program']['objective_type'] == 'maximize'
        assert tokens == 150
        assert raw_content is not None
    
    @patch('api.chat.OpenAI')
    def test_generate_lp_with_history(self, mock_openai_class):
        """Test LP generation with conversation history"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        response_data = create_sample_lp_response()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(response_data)
        mock_response.usage.total_tokens = 200
        
        mock_client.chat.completions.create.return_value = mock_response
        
        history = [
            {'role': 'user', 'content': 'Previous message'},
            {'role': 'assistant', 'content': 'Previous response'}
        ]
        
        result, raw_content, tokens = generate_lp('New prompt', 'gpt-4o', history)
        
        # Verify history was included
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        assert len(messages) >= 3  # system + history + new prompt
    
    @patch('api.chat.OpenAI')
    def test_generate_lp_with_custom_credentials(self, mock_openai_class):
        """Test LP generation with custom API credentials"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        response_data = create_sample_lp_response()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(response_data)
        mock_response.usage = None
        
        mock_client.chat.completions.create.return_value = mock_response
        
        result, raw_content, tokens = generate_lp(
            'Test',
            'model-x',
            [],
            api_key='sk-custom-123',
            base_url='https://custom.api.com/v1'
        )
        
        # Verify custom credentials were used
        openai_call_kwargs = mock_openai_class.call_args[1]
        assert openai_call_kwargs['api_key'] == 'sk-custom-123'
        assert openai_call_kwargs['base_url'] == 'https://custom.api.com/v1'
    
    @patch('api.chat.OpenAI')
    def test_generate_lp_no_tokens_info(self, mock_openai_class):
        """Test LP generation when usage info is not available"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        response_data = create_sample_lp_response()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(response_data)
        mock_response.usage = None
        
        mock_client.chat.completions.create.return_value = mock_response
        
        result, raw_content, tokens = generate_lp('Test', 'gpt-4o-mini', [])
        
        assert tokens is None


# ──────────────────────────────────────────────────────────────
# LP Fixing Tests
# ──────────────────────────────────────────────────────────────

class TestFixLP:
    """Tests for LP JSON fixing"""
    
    @patch('api.chat.OpenAI')
    def test_fix_lp_success(self, mock_openai_class):
        """Test successful LP fixing"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        fixed_data = create_sample_lp_response()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(fixed_data)
        
        mock_client.chat.completions.create.return_value = mock_response
        
        result = fix_lp('broken json {', 'Invalid JSON structure', 'gpt-4o-mini')
        
        assert result['linear_program']['objective_type'] == 'maximize'
    
    @patch('api.chat.OpenAI')
    def test_fix_lp_with_custom_credentials(self, mock_openai_class):
        """Test LP fixing with custom credentials"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        fixed_data = create_sample_lp_response()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(fixed_data)
        
        mock_client.chat.completions.create.return_value = mock_response
        
        result = fix_lp(
            'broken',
            'Error',
            'custom-model',
            api_key='sk-custom',
            base_url='https://custom.api.com/v1'
        )
        
        openai_call_kwargs = mock_openai_class.call_args[1]
        assert openai_call_kwargs['api_key'] == 'sk-custom'


# ──────────────────────────────────────────────────────────────
# Validation and Healing Tests
# ──────────────────────────────────────────────────────────────

class TestValidateAndHeal:
    """Tests for LP validation and self-healing"""
    
    @patch('api.chat.OpenAI')
    def test_validate_and_heal_valid_response(self, mock_openai_class):
        """Test validation with valid response (no healing needed)"""
        valid_data = create_sample_lp_response()
        
        response, was_healed = validate_and_heal(valid_data, json.dumps(valid_data), 'gpt-4o-mini')
        
        assert isinstance(response, LPResponse)
        assert was_healed is False
    
    @patch('api.chat.fix_lp')
    def test_validate_and_heal_invalid_response(self, mock_fix_lp):
        """Test validation with invalid response (healing applied)"""
        invalid_data = {'linear_program': {}}  # Missing required fields
        fixed_data = create_sample_lp_response()
        
        mock_fix_lp.return_value = fixed_data
        
        response, was_healed = validate_and_heal(
            invalid_data,
            json.dumps(invalid_data),
            'gpt-4o-mini'
        )
        
        assert isinstance(response, LPResponse)
        assert was_healed is True
        mock_fix_lp.assert_called_once()


# ──────────────────────────────────────────────────────────────
# Response Building Tests
# ──────────────────────────────────────────────────────────────

class TestBuildResponseMessage:
    """Tests for building formatted response messages"""
    
    def test_build_response_message_format(self):
        """Test response message includes all components"""
        lp = LinearProgram(
            problem_description='Test problem',
            objective_type='maximize',
            objective_function='3x + 2y',
            decision_variables=['x', 'y'],
            constraints=['x + y <= 10'],
            variable_bounds={'x': '>= 0'},
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
        assert 'Assumption 1' in message
        assert 'Suggestion 1' in message
    
    def test_build_response_message_with_healing_flag(self):
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
        assert '⚠️' in message
    
    def test_build_response_message_no_healing(self):
        """Test response message without healing flag"""
        lp = LinearProgram(
            problem_description='Test',
            objective_type='maximize',
            objective_function='x',
            decision_variables=['x'],
            constraints=[]
        )
        
        response = LPResponse(linear_program=lp, explanation='Test')
        message = build_response_message(lp, response, False)
        
        assert 'Self-healing' not in message


# ──────────────────────────────────────────────────────────────
# HTTP Handler: OPTIONS Tests
# ──────────────────────────────────────────────────────────────

class TestHandlerOptions:
    """Tests for OPTIONS request handling"""
    
    def test_options_returns_204(self):
        """Test OPTIONS returns 204 No Content"""
        h = create_mock_handler(method='OPTIONS')
        h.do_OPTIONS()
        
        h.send_response.assert_called_with(204)
    
    def test_options_sets_cors_headers(self):
        """Test OPTIONS sets CORS headers"""
        h = create_mock_handler(method='OPTIONS')
        h.do_OPTIONS()
        
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        assert 'Access-Control-Allow-Origin' in header_dict
        assert 'Access-Control-Allow-Methods' in header_dict
        assert 'POST' in header_dict.get('Access-Control-Allow-Methods', '')


# ──────────────────────────────────────────────────────────────
# HTTP Handler: POST Tests
# ──────────────────────────────────────────────────────────────

class TestHandlerPost:
    """Tests for POST request handling"""
    
    @patch('api.chat.validate_and_heal')
    @patch('api.chat.generate_lp')
    def test_post_basic_request(self, mock_generate_lp, mock_validate_and_heal):
        """Test basic POST request"""
        response_data = create_sample_lp_response()
        mock_generate_lp.return_value = (response_data, json.dumps(response_data), 100)
        mock_validate_and_heal.return_value = (LPResponse(**response_data), False)
        
        body = json.dumps({
            'prompt': 'Maximize 3x + 2y subject to x + y <= 10',
            'model': 'gpt-4o-mini'
        })
        
        h = create_mock_handler(body=body, headers={'Content-Length': str(len(body))})
        h.headers['Content-Length'] = str(len(body))
        h.do_POST()
        
        h.send_response.assert_called_with(200)
        response = get_response_from_handler(h)
        
        assert 'message' in response
        assert 'linear_program' in response
        assert response['was_healed'] is False
    
    @patch('api.chat.validate_and_heal')
    @patch('api.chat.generate_lp')
    def test_post_with_history(self, mock_generate_lp, mock_validate_and_heal):
        """Test POST with conversation history"""
        response_data = create_sample_lp_response()
        mock_generate_lp.return_value = (response_data, json.dumps(response_data), 100)
        mock_validate_and_heal.return_value = (LPResponse(**response_data), False)
        
        history = [
            {'role': 'user', 'content': 'Previous'},
            {'role': 'assistant', 'content': 'Response'}
        ]
        
        body = json.dumps({
            'prompt': 'New prompt',
            'model': 'gpt-4o-mini',
            'history': history
        })
        
        h = create_mock_handler(body=body, headers={'Content-Length': str(len(body))})
        h.headers['Content-Length'] = str(len(body))
        h.do_POST()
        
        # Verify generate_lp was called with history
        call_args = mock_generate_lp.call_args[0]
        assert call_args[2] == history  # history parameter
    
    def test_post_missing_prompt(self):
        """Test POST without prompt"""
        body = json.dumps({'model': 'gpt-4o-mini'})
        
        h = create_mock_handler(body=body, headers={'Content-Length': str(len(body))})
        h.headers['Content-Length'] = str(len(body))
        h.do_POST()
        
        h.send_response.assert_called_with(400)
        response = get_response_from_handler(h)
        assert 'error' in response
    
    @patch('api.chat.validate_and_heal')
    @patch('api.chat.generate_lp')
    def test_post_invalid_model_defaults(self, mock_generate_lp, mock_validate_and_heal):
        """Test invalid model defaults to DEFAULT_MODEL"""
        response_data = create_sample_lp_response()
        mock_generate_lp.return_value = (response_data, json.dumps(response_data), 100)
        mock_validate_and_heal.return_value = (LPResponse(**response_data), False)
        
        body = json.dumps({
            'prompt': 'Test',
            'model': 'invalid-model-xyz'
        })
        
        h = create_mock_handler(body=body, headers={'Content-Length': str(len(body))})
        h.headers['Content-Length'] = str(len(body))
        h.do_POST()
        
        # Verify DEFAULT_MODEL was used
        call_args = mock_generate_lp.call_args[0]
        assert call_args[1] == DEFAULT_MODEL
    
    def test_post_invalid_json(self):
        """Test POST with invalid JSON"""
        body = 'invalid json {'
        
        h = create_mock_handler(body=body, headers={'Content-Length': str(len(body))})
        h.headers['Content-Length'] = str(len(body))
        h.do_POST()
        
        h.send_response.assert_called_with(500)
        response = get_response_from_handler(h)
        assert 'error' in response
    
    @patch('api.chat.validate_and_heal')
    @patch('api.chat.generate_lp')
    def test_post_response_includes_metadata(self, mock_generate_lp, mock_validate_and_heal):
        """Test POST response includes timing and token info"""
        response_data = create_sample_lp_response()
        mock_generate_lp.return_value = (response_data, json.dumps(response_data), 250)
        mock_validate_and_heal.return_value = (LPResponse(**response_data), False)
        
        body = json.dumps({'prompt': 'Test'})
        
        h = create_mock_handler(body=body, headers={'Content-Length': str(len(body))})
        h.headers['Content-Length'] = str(len(body))
        h.do_POST()
        
        response = get_response_from_handler(h)
        
        assert 'response_time_ms' in response
        assert 'tokens_used' in response
        assert response['tokens_used'] == 250
        assert response['model_used'] == DEFAULT_MODEL


# ──────────────────────────────────────────────────────────────
# Database Integration Tests
# ──────────────────────────────────────────────────────────────

class TestDatabaseIntegration:
    """Tests for database operations in chat handler"""
    
    @patch('api.chat.get_next_message_order')
    @patch('api.chat.create_message')
    @patch('api.chat.create_log')
    @patch('api.chat.create_chat')
    @patch('api.chat.validate_and_heal')
    @patch('api.chat.generate_lp')
    @patch('api.chat.get_auth_user')
    def test_post_creates_chat_for_authenticated_user(
        self, mock_get_auth_user, mock_generate_lp, mock_validate_and_heal,
        mock_create_chat, mock_create_log, mock_create_message, mock_get_next_order
    ):
        """Test that authenticated users' chats are created"""
        mock_get_auth_user.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_create_chat.return_value = {'ID': 123}
        mock_get_next_order.return_value = 1
        mock_create_message.return_value = {'ID': 1}
        
        response_data = create_sample_lp_response()
        mock_generate_lp.return_value = (response_data, json.dumps(response_data), 100)
        mock_validate_and_heal.return_value = (LPResponse(**response_data), False)
        
        body = json.dumps({'prompt': 'Test prompt'})
        
        h = create_mock_handler(
            body=body,
            headers={
                'Content-Length': str(len(body)),
                'Authorization': 'Bearer valid_token'
            }
        )
        h.headers['Content-Length'] = str(len(body))
        h.headers['Authorization'] = 'Bearer valid_token'
        h.do_POST()
        
        mock_create_chat.assert_called_once()
        call_args = mock_create_chat.call_args[0]
        assert call_args[0] == 1  # user_id


# ──────────────────────────────────────────────────────────────
# Error Handling Tests
# ──────────────────────────────────────────────────────────────

class TestErrorHandling:
    """Tests for error handling"""
    
    @patch('api.chat.get_openai_client')
    @patch('api.chat.generate_lp')
    def test_post_value_error_returns_422(self, mock_generate_lp, mock_get_client):
        """Test ValueError returns 422"""
        mock_generate_lp.side_effect = ValueError("API Error")
        
        body = json.dumps({'prompt': 'Test'})
        
        h = create_mock_handler(body=body, headers={'Content-Length': str(len(body))})
        h.headers['Content-Length'] = str(len(body))
        h.do_POST()
        
        h.send_response.assert_called_with(422)
    
    @patch('api.chat.validate_and_heal')
    @patch('api.chat.generate_lp')
    def test_post_generic_error_returns_500(self, mock_generate_lp, mock_validate):
        """Test generic error returns 500"""
        mock_generate_lp.side_effect = RuntimeError("Unexpected error")
        
        body = json.dumps({'prompt': 'Test'})
        
        h = create_mock_handler(body=body, headers={'Content-Length': str(len(body))})
        h.headers['Content-Length'] = str(len(body))
        h.do_POST()
        
        h.send_response.assert_called_with(500)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
