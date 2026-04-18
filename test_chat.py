"""
Comprehensive unit tests for SignalMine Chat API (api/chat.py)
Tests LP generation, validation, healing, and business logic
"""

import pytest
import json
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from pydantic import ValidationError

# Mock database and auth before importing chat
import sys
sys.modules['api.database'] = MagicMock()
sys.modules['api.auth'] = MagicMock()

from api.chat import (
    LinearProgram, LPResponse, AVAILABLE_MODELS, DEFAULT_MODEL,
    LP_GENERATOR_SYSTEM_PROMPT, LP_FIXER_SYSTEM_PROMPT,
    get_openai_client, get_auth_user, generate_lp, fix_lp,
    validate_and_heal, build_response_message, build_questionnaire_fallback
)


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
    
    def test_linear_program_empty_constraints(self):
        """Test LinearProgram with empty constraints"""
        data = {
            'problem_description': 'Unbounded problem',
            'objective_type': 'maximize',
            'objective_function': 'x',
            'decision_variables': ['x'],
            'constraints': []
        }
        
        lp = LinearProgram(**data)
        assert lp.constraints == []


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
    @patch('api.chat.OpenAI')
    def test_get_openai_client_default(self, mock_openai_class):
        """Test OpenAI client initialization with default key"""
        mock_openai_class.return_value = MagicMock()
        
        get_openai_client()
        
        mock_openai_class.assert_called_once()
        call_kwargs = mock_openai_class.call_args[1]
        assert call_kwargs['api_key'] == 'sk-test-123'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_openai_client_no_key(self):
        """Test OpenAI client raises when no API key"""
        with pytest.raises(ValueError, match="OPENAI_API_KEY not set"):
            get_openai_client()
    
    @patch('api.chat.OpenAI')
    def test_get_openai_client_custom_key(self, mock_openai_class):
        """Test OpenAI client with custom API key"""
        mock_openai_class.return_value = MagicMock()
        
        get_openai_client(api_key='sk-custom-456')
        
        call_kwargs = mock_openai_class.call_args[1]
        assert call_kwargs['api_key'] == 'sk-custom-456'
    
    @patch('api.chat.OpenAI')
    def test_get_openai_client_custom_base_url(self, mock_openai_class):
        """Test OpenAI client with custom base URL"""
        mock_openai_class.return_value = MagicMock()
        
        get_openai_client(api_key='sk-test', base_url='https://custom.api.com/v1')
        
        call_kwargs = mock_openai_class.call_args[1]
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
    
    @patch('api.chat.get_openai_client')
    def test_generate_lp_success(self, mock_get_client):
        """Test successful LP generation"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        response_data = create_sample_lp_response()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(response_data)
        mock_response.usage.total_tokens = 150
        
        mock_client.chat.completions.create.return_value = mock_response
        
        result, raw_content, tokens = generate_lp('Test prompt', 'gpt-4o-mini', [])
        
        assert result['linear_program']['objective_type'] == 'maximize'
        assert tokens == 150
        assert raw_content is not None
    
    @patch('api.chat.get_openai_client')
    def test_generate_lp_with_history(self, mock_get_client):
        """Test LP generation with conversation history"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
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
        
        # Verify history was included in API call
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        assert len(messages) >= 3  # system + history items + new prompt
    
    @patch('api.chat.get_openai_client')
    def test_generate_lp_with_custom_credentials(self, mock_get_client):
        """Test LP generation with custom API credentials"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
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
        
        # Verify custom credentials were passed to get_openai_client
        mock_get_client.assert_called_once_with('sk-custom-123', 'https://custom.api.com/v1')
    
    @patch('api.chat.get_openai_client')
    def test_generate_lp_no_tokens_info(self, mock_get_client):
        """Test LP generation when usage info is not available"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        response_data = create_sample_lp_response()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(response_data)
        mock_response.usage = None
        
        mock_client.chat.completions.create.return_value = mock_response
        
        result, raw_content, tokens = generate_lp('Test', 'gpt-4o-mini', [])
        
        assert tokens is None

    @patch('api.chat.recover_lp_or_questions')
    @patch('api.chat.fix_lp')
    @patch('api.chat.get_openai_client')
    def test_generate_lp_invalid_json_uses_recovery_agent(self, mock_get_client, mock_fix_lp, mock_recover):
        """Test malformed JSON falls through to the recovery agent."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_fix_lp.side_effect = ValueError('still broken')
        mock_recover.return_value = create_sample_lp_response()

        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"linear_program": {"broken": true'
        mock_response.usage.total_tokens = 77
        mock_client.chat.completions.create.return_value = mock_response

        result, raw_content, tokens = generate_lp('Need a nurse schedule', 'gpt-4o-mini', [])

        assert result['linear_program']['objective_type'] == 'maximize'
        assert tokens == 77
        mock_recover.assert_called_once()


# ──────────────────────────────────────────────────────────────
# LP Fixing Tests
# ──────────────────────────────────────────────────────────────

class TestFixLP:
    """Tests for LP JSON fixing"""
    
    @patch('api.chat.get_openai_client')
    def test_fix_lp_success(self, mock_get_client):
        """Test successful LP fixing"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        fixed_data = create_sample_lp_response()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(fixed_data)
        
        mock_client.chat.completions.create.return_value = mock_response
        
        result = fix_lp('broken json {', 'Invalid JSON structure', 'gpt-4o-mini')
        
        assert result['linear_program']['objective_type'] == 'maximize'
    
    @patch('api.chat.get_openai_client')
    def test_fix_lp_with_custom_credentials(self, mock_get_client):
        """Test LP fixing with custom credentials"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
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
        
        mock_get_client.assert_called_once_with('sk-custom', 'https://custom.api.com/v1')


# ──────────────────────────────────────────────────────────────
# Validation and Healing Tests
# ──────────────────────────────────────────────────────────────

class TestValidateAndHeal:
    """Tests for LP validation and self-healing"""
    
    def test_validate_and_heal_valid_response(self):
        """Test validation with valid response (no healing needed)"""
        valid_data = create_sample_lp_response()

        response, was_healed, validation_details = validate_and_heal(valid_data, json.dumps(valid_data), 'gpt-4o-mini')

        assert isinstance(response, LPResponse)
        assert was_healed is False
        assert validation_details['schema_validation']['passed'] is True
        assert validation_details['math_validation']['passed'] is True

    @patch('api.chat.fix_lp')
    def test_validate_and_heal_invalid_response(self, mock_fix_lp):
        """Test validation with invalid response (healing applied)"""
        invalid_data = {'linear_program': {}}  # Missing required fields
        fixed_data = create_sample_lp_response()

        mock_fix_lp.return_value = fixed_data

        response, was_healed, validation_details = validate_and_heal(
            invalid_data,
            json.dumps(invalid_data),
            'gpt-4o-mini'
        )

        assert isinstance(response, LPResponse)
        assert was_healed is True
        assert validation_details['healing']['attempted'] is True
        assert validation_details['healing']['successful'] is True
        mock_fix_lp.assert_called_once()

    @patch('api.chat.recover_lp_or_questions')
    @patch('api.chat.fix_lp')
    def test_validate_and_heal_schema_failure_uses_recovery_agent(self, mock_fix_lp, mock_recover):
        """Test recovery agent is used when the fixer still fails."""
        invalid_data = {'linear_program': {}}
        mock_fix_lp.side_effect = ValueError('fixer failed')
        mock_recover.return_value = build_questionnaire_fallback('Prompt text', 'fixer failed')

        response, was_healed, validation_details = validate_and_heal(
            invalid_data,
            json.dumps(invalid_data),
            'gpt-4o-mini',
            user_prompt='Prompt text'
        )

        assert isinstance(response, LPResponse)
        assert was_healed is True
        assert validation_details['healing']['attempted'] is True
        assert validation_details['healing']['successful'] is True
        mock_recover.assert_called_once()


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

    def test_build_response_message_formats_grouped_subscripts(self):
        """Test grouped subscripts render differently from multiplication."""
        lp = LinearProgram(
            problem_description='Indexed test',
            objective_type='minimize',
            objective_function='x_ij + x_i*j',
            decision_variables=['x_ij', 'x_i*j'],
            constraints=['x_ij >= 0', 'x_i*j <= 3'],
            variable_bounds={'x_ij': '>= 0'}
        )

        response = LPResponse(linear_program=lp, explanation='Test')
        message = build_response_message(lp, response, False)

        assert '$x_{ij}$' in message
        assert '$x_{i} \\cdot j$' in message
        assert 'x_{ij} \\geq 0' in message
        assert 'x_{i} \\cdot j \\leq 3' in message
    
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

    def test_build_response_message_renders_clarification_questions(self):
        """Test clarification questions are shown in their own section."""
        lp = LinearProgram(
            problem_description='Clarification needed',
            objective_type='minimize',
            objective_function='0',
            decision_variables=['x_placeholder'],
            constraints=[]
        )

        response = LPResponse(
            linear_program=lp,
            explanation='Need more data',
            suggestions=['What is the objective?', 'Add data after clarification']
        )
        message = build_response_message(lp, response, False)

        assert 'Questions for Clarification' in message
        assert 'What is the objective?' in message
        assert 'Add data after clarification' in message


# ──────────────────────────────────────────────────────────────
# Authentication Logic Tests
# ──────────────────────────────────────────────────────────────

class TestAuthenticationLogic:
    """Tests for authentication in chat handler"""
    
    @patch('api.chat.validate_token')
    def test_auth_user_extraction_from_bearer_token(self, mock_validate_token):
        """Test extracting user from Bearer token"""
        mock_validate_token.return_value = {'user_id': 42, 'username': 'alice'}
        
        headers = {'Authorization': 'Bearer xyz123'}
        user = get_auth_user(headers)
        
        assert user is not None
        assert user['user_id'] == 42
    
    @patch('api.chat.validate_token')
    def test_auth_user_none_on_invalid_token(self, mock_validate_token):
        """Test user is None for invalid token"""
        mock_validate_token.return_value = None
        
        headers = {'Authorization': 'Bearer invalid'}
        user = get_auth_user(headers)
        
        assert user is None
    
    def test_auth_missing_bearer_keyword(self):
        """Test header without Bearer keyword"""
        headers = {'Authorization': 'xyz123'}
        user = get_auth_user(headers)
        
        assert user is None


# ──────────────────────────────────────────────────────────────
# Input Validation Tests
# ──────────────────────────────────────────────────────────────

class TestInputValidation:
    """Tests for input validation"""
    
    def test_json_parsing_valid(self):
        """Test valid JSON parsing"""
        body = '{"action": "generate", "prompt": "test"}'
        data = json.loads(body)
        assert data['action'] == 'generate'
        assert data['prompt'] == 'test'
    
    def test_json_parsing_invalid(self):
        """Test invalid JSON raises error"""
        body = 'invalid json {'
        with pytest.raises(json.JSONDecodeError):
            json.loads(body)
    
    def test_prompt_required(self):
        """Test that prompt field is required"""
        data = {'model': 'gpt-4o'}
        prompt = data.get('prompt', '').strip()
        assert not prompt
    
    def test_prompt_present(self):
        """Test prompt field validation"""
        data = {'prompt': 'Test prompt', 'model': 'gpt-4o'}
        assert data.get('prompt', '').strip() != ''


# ──────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────

class TestLPGenerationFlow:
    """Integration tests for LP generation flow"""
    
    @patch('api.chat.get_openai_client')
    def test_prompt_to_lp_response_flow(self, mock_get_client):
        """Test complete flow from prompt to LP response"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        response_data = create_sample_lp_response()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(response_data)
        mock_response.usage.total_tokens = 100
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Generate LP
        result, raw_content, tokens = generate_lp('Test prompt', DEFAULT_MODEL, [])
        assert result is not None
        
        # Validate LP
        validated_response, was_healed = validate_and_heal(result, raw_content, DEFAULT_MODEL)
        assert isinstance(validated_response, LPResponse)
        assert was_healed is False
    
    @patch('api.chat.fix_lp')
    @patch('api.chat.get_openai_client')
    def test_healing_flow_on_invalid_response(self, mock_get_client, mock_fix_lp):
        """Test healing flow for invalid LP response"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # First response is invalid
        invalid_response = {'error': 'malformed'}
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(invalid_response)
        mock_response.usage.total_tokens = 50
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Generate LP (gets invalid response)
        result, raw_content, tokens = generate_lp('Test', DEFAULT_MODEL, [])
        
        # Setup healing
        fixed_data = create_sample_lp_response()
        mock_fix_lp.return_value = fixed_data
        
        # Validate and heal
        validated_response, was_healed = validate_and_heal(result, raw_content, DEFAULT_MODEL)
        
        assert was_healed is True
        assert isinstance(validated_response, LPResponse)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
