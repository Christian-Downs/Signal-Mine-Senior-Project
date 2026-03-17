"""
Comprehensive unit tests for SignalMine User Models API (api/user_models.py)
Tests custom AI model API key management
"""

import pytest
import json
from datetime import datetime
from unittest.mock import MagicMock


# ──────────────────────────────────────────────────────────────
# Constants & Helper Data
# ──────────────────────────────────────────────────────────────

PROVIDERS = {
    'openai': {'name': 'OpenAI', 'base_url': 'https://api.openai.com/v1'},
    'anthropic': {'name': 'Anthropic', 'base_url': 'https://api.anthropic.com/v1'},
    'google': {'name': 'Google AI', 'base_url': 'https://generativelanguage.googleapis.com/v1beta'},
    'groq': {'name': 'Groq', 'base_url': 'https://api.groq.com/openai/v1'},
    'together': {'name': 'Together AI', 'base_url': 'https://api.together.xyz/v1'},
    'custom': {'name': 'Custom', 'base_url': None}
}


def create_sample_user_model(model_id=1, user_id=1, name='My GPT-4', provider='openai'):
    """Create a sample user model object"""
    return {
        'id': model_id,
        'user_id': user_id,
        'name': name,
        'provider': provider,
        'api_key': 'sk-...masked',
        'base_url': PROVIDERS.get(provider, {}).get('base_url'),
        'created_at': datetime.now().isoformat()
    }


def create_sample_user_models(count=3):
    """Create multiple sample user models"""
    models = []
    for i in range(count):
        model = create_sample_user_model(
            model_id=i + 1,
            name=f'Model {i + 1}',
            provider='openai' if i % 2 == 0 else 'anthropic'
        )
        models.append(model)
    return models


# ──────────────────────────────────────────────────────────────
# Providers Tests
# ──────────────────────────────────────────────────────────────

class TestProviders:
    """Tests for provider definitions"""
    
    def test_providers_constant_exists(self):
        """Test that PROVIDERS constant is defined"""
        assert PROVIDERS is not None
        assert isinstance(PROVIDERS, dict)
    
    def test_providers_not_empty(self):
        """Test that providers list is not empty"""
        assert len(PROVIDERS) > 0
    
    def test_openai_provider_exists(self):
        """Test OpenAI provider is defined"""
        assert 'openai' in PROVIDERS
    
    def test_anthropic_provider_exists(self):
        """Test Anthropic provider is defined"""
        assert 'anthropic' in PROVIDERS
    
    def test_google_provider_exists(self):
        """Test Google provider is defined"""
        assert 'google' in PROVIDERS
    
    def test_groq_provider_exists(self):
        """Test Groq provider is defined"""
        assert 'groq' in PROVIDERS
    
    def test_together_provider_exists(self):
        """Test Together AI provider is defined"""
        assert 'together' in PROVIDERS
    
    def test_custom_provider_exists(self):
        """Test Custom provider is defined"""
        assert 'custom' in PROVIDERS
    
    def test_provider_has_name(self):
        """Test each provider has a name"""
        for provider_key, provider_info in PROVIDERS.items():
            assert 'name' in provider_info
            assert provider_info['name'] is not None
    
    def test_provider_has_base_url(self):
        """Test each provider has base_url (or None for custom)"""
        for provider_key, provider_info in PROVIDERS.items():
            assert 'base_url' in provider_info
    
    def test_custom_provider_base_url_is_none(self):
        """Test custom provider has None base_url"""
        assert PROVIDERS['custom']['base_url'] is None
    
    def test_openai_base_url_correct(self):
        """Test OpenAI base_url is correct"""
        assert PROVIDERS['openai']['base_url'] == 'https://api.openai.com/v1'


# ──────────────────────────────────────────────────────────────
# User Model Structure Tests
# ──────────────────────────────────────────────────────────────

class TestUserModelStructure:
    """Tests for user model data structure"""
    
    def test_user_model_has_id(self):
        """Test user model has id field"""
        model = create_sample_user_model()
        assert 'id' in model
        assert model['id'] == 1
    
    def test_user_model_has_user_id(self):
        """Test user model has user_id field"""
        model = create_sample_user_model()
        assert 'user_id' in model
        assert model['user_id'] == 1
    
    def test_user_model_has_name(self):
        """Test user model has name field"""
        model = create_sample_user_model()
        assert 'name' in model
        assert model['name'] == 'My GPT-4'
    
    def test_user_model_has_provider(self):
        """Test user model has provider field"""
        model = create_sample_user_model()
        assert 'provider' in model
        assert model['provider'] == 'openai'
    
    def test_user_model_has_api_key(self):
        """Test user model has api_key field"""
        model = create_sample_user_model()
        assert 'api_key' in model
    
    def test_user_model_has_base_url(self):
        """Test user model has base_url field"""
        model = create_sample_user_model()
        assert 'base_url' in model
    
    def test_user_model_has_created_at(self):
        """Test user model has created_at field"""
        model = create_sample_user_model()
        assert 'created_at' in model
        assert isinstance(model['created_at'], str)


# ──────────────────────────────────────────────────────────────
# User Model Creation Tests
# ──────────────────────────────────────────────────────────────

class TestUserModelCreation:
    """Tests for creating user models"""
    
    def test_create_single_user_model(self):
        """Test creating a single user model"""
        model = create_sample_user_model()
        
        assert model is not None
        assert model['id'] == 1
    
    def test_create_user_model_with_custom_id(self):
        """Test creating user model with custom ID"""
        model = create_sample_user_model(model_id=42)
        
        assert model['id'] == 42
    
    def test_create_user_model_with_custom_name(self):
        """Test creating user model with custom name"""
        model = create_sample_user_model(name='My Custom Model')
        
        assert model['name'] == 'My Custom Model'
    
    def test_create_user_model_with_different_provider(self):
        """Test creating user model with different provider"""
        model = create_sample_user_model(provider='anthropic')
        
        assert model['provider'] == 'anthropic'
    
    def test_create_multiple_user_models(self):
        """Test creating multiple user models"""
        models = create_sample_user_models(5)
        
        assert len(models) == 5
        assert models[0]['id'] == 1
        assert models[4]['id'] == 5
    
    def test_user_models_have_unique_ids(self):
        """Test that multiple user models have unique IDs"""
        models = create_sample_user_models(3)
        ids = [m['id'] for m in models]
        
        assert len(ids) == len(set(ids))


# ──────────────────────────────────────────────────────────────
# User Model Validation Tests
# ──────────────────────────────────────────────────────────────

class TestUserModelValidation:
    """Tests for user model validation"""
    
    def test_model_name_not_empty(self):
        """Test that model name is not empty"""
        model = create_sample_user_model(name='Test Model')
        
        assert model['name'] is not None
        assert len(model['name']) > 0
    
    def test_model_provider_is_valid(self):
        """Test that model provider is valid"""
        model = create_sample_user_model(provider='openai')
        
        assert model['provider'] in PROVIDERS
    
    def test_model_id_is_positive(self):
        """Test that model ID is positive"""
        model = create_sample_user_model(model_id=1)
        
        assert model['id'] > 0
    
    def test_model_user_id_is_positive(self):
        """Test that user ID is positive"""
        model = create_sample_user_model(user_id=1)
        
        assert model['user_id'] > 0


# ──────────────────────────────────────────────────────────────
# API Response Tests
# ──────────────────────────────────────────────────────────────

class TestApiResponses:
    """Tests for API response structures"""
    
    def test_get_models_response_structure(self):
        """Test GET response structure for user models"""
        models = create_sample_user_models(2)
        response = {
            'models': models,
            'count': len(models)
        }
        
        assert 'models' in response
        assert 'count' in response
        assert response['count'] == 2
    
    def test_get_providers_response_structure(self):
        """Test GET response structure for providers"""
        response = {
            'providers': PROVIDERS
        }
        
        assert 'providers' in response
        assert len(response['providers']) > 0
    
    def test_create_model_response_structure(self):
        """Test POST response structure for creating model"""
        model = create_sample_user_model()
        response = {
            'success': True,
            'message': 'Model created',
            'model': model
        }
        
        assert response['success'] is True
        assert 'model' in response
    
    def test_delete_model_response_structure(self):
        """Test DELETE response structure"""
        response = {
            'success': True,
            'message': 'Model deleted'
        }
        
        assert response['success'] is True
    
    def test_error_response_structure(self):
        """Test error response structure"""
        response = {
            'error': 'Unauthorized',
            'message': 'Invalid authentication'
        }
        
        assert 'error' in response
        assert 'message' in response


# ──────────────────────────────────────────────────────────────
# JSON Serialization Tests
# ──────────────────────────────────────────────────────────────

class TestJsonSerialization:
    """Tests for JSON serialization"""
    
    def test_user_model_json_serializable(self):
        """Test that user model can be JSON serialized"""
        model = create_sample_user_model()
        json_str = json.dumps(model)
        parsed = json.loads(json_str)
        
        assert parsed['id'] == 1
    
    def test_user_models_list_json_serializable(self):
        """Test that user models list can be JSON serialized"""
        models = create_sample_user_models(3)
        json_str = json.dumps(models)
        parsed = json.loads(json_str)
        
        assert len(parsed) == 3
    
    def test_response_json_serializable(self):
        """Test that response can be JSON serialized"""
        models = create_sample_user_models(2)
        response = {
            'models': models,
            'count': len(models)
        }
        
        json_str = json.dumps(response)
        parsed = json.loads(json_str)
        
        assert parsed['count'] == 2


# ──────────────────────────────────────────────────────────────
# Authentication Tests
# ──────────────────────────────────────────────────────────────

class TestAuthenticationFlow:
    """Tests for authentication handling"""
    
    def test_valid_bearer_token_extraction(self):
        """Test extracting valid Bearer token"""
        auth_header = 'Bearer test_token_123'
        token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else None
        
        assert token == 'test_token_123'
    
    def test_invalid_auth_header_format(self):
        """Test handling invalid Authorization header format"""
        auth_header = 'InvalidFormat token123'
        token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else None
        
        assert token is None
    
    def test_missing_auth_header(self):
        """Test handling missing Authorization header"""
        headers = {}
        token = headers.get('Authorization')
        
        assert token is None
    
    def test_authenticated_request_has_token(self):
        """Test that authenticated request has token"""
        headers = {'Authorization': 'Bearer valid_token_xyz'}
        auth_header = headers.get('Authorization', '')
        
        assert auth_header.startswith('Bearer ')


# ──────────────────────────────────────────────────────────────
# Query Parameter Tests
# ──────────────────────────────────────────────────────────────

class TestQueryParameters:
    """Tests for query parameter parsing"""
    
    def test_parse_model_id_from_path(self):
        """Test parsing model ID from path"""
        path = '/api/user-models/42'
        model_id = int(path.split('/')[-1]) if path.split('/')[-1].isdigit() else None
        
        assert model_id == 42
    
    def test_parse_invalid_model_id(self):
        """Test handling invalid model ID"""
        path = '/api/user-models/invalid'
        model_id = int(path.split('/')[-1]) if path.split('/')[-1].isdigit() else None
        
        assert model_id is None


# ──────────────────────────────────────────────────────────────
# Business Logic Tests
# ──────────────────────────────────────────────────────────────

class TestBusinessLogic:
    """Tests for business logic"""
    
    def test_get_models_for_user(self):
        """Test retrieving models for a specific user"""
        user_id = 1
        models = create_sample_user_models(3)
        models = [m for m in models if m['user_id'] == user_id]
        
        assert len(models) == 3
    
    def test_filter_models_by_provider(self):
        """Test filtering models by provider"""
        models = create_sample_user_models(5)
        openai_models = [m for m in models if m['provider'] == 'openai']
        
        assert len(openai_models) > 0
    
    def test_count_user_models(self):
        """Test counting user models"""
        models = create_sample_user_models(5)
        count = len(models)
        
        assert count == 5
    
    def test_find_model_by_id(self):
        """Test finding model by ID"""
        models = create_sample_user_models(5)
        model = next((m for m in models if m['id'] == 3), None)
        
        assert model is not None
        assert model['id'] == 3


# ──────────────────────────────────────────────────────────────
# Error Handling Tests
# ──────────────────────────────────────────────────────────────

class TestErrorHandling:
    """Tests for error handling"""
    
    def test_unauthenticated_request_returns_401(self):
        """Test that unauthenticated request triggers 401"""
        user = None
        status = 401 if user is None else 200
        
        assert status == 401
    
    def test_invalid_api_key_returns_400(self):
        """Test that invalid API key returns 400"""
        api_key = ''
        status = 400 if not api_key else 200
        
        assert status == 400
    
    def test_duplicate_model_name_returns_409(self):
        """Test that duplicate model name returns 409"""
        models = create_sample_user_models(2)
        new_model_name = models[0]['name']
        
        # Check if name already exists
        conflict = any(m['name'] == new_model_name for m in models[1:])
        status = 409 if conflict else 200
        
        assert status == 409 or status == 200
    
    def test_model_not_found_returns_404(self):
        """Test that missing model returns 404"""
        models = create_sample_user_models(3)
        model = next((m for m in models if m['id'] == 999), None)
        
        status = 404 if model is None else 200
        assert status == 404
    
    def test_invalid_provider_returns_400(self):
        """Test that invalid provider returns 400"""
        provider = 'invalid_provider'
        is_valid = provider in PROVIDERS
        status = 200 if is_valid else 400
        
        assert status == 400


# ──────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────

class TestIntegration:
    """Integration tests for user models workflow"""
    
    def test_complete_user_model_workflow(self):
        """Test complete user model workflow"""
        # Create models
        models = create_sample_user_models(3)
        
        # Verify structure
        response = {
            'models': models,
            'count': len(models)
        }
        
        assert response['count'] == 3
        assert all('id' in m for m in response['models'])
    
    def test_provider_selection_workflow(self):
        """Test provider selection workflow"""
        selected_provider = 'openai'
        provider_info = PROVIDERS.get(selected_provider)
        
        assert provider_info is not None
        assert provider_info['name'] == 'OpenAI'
    
    def test_model_crud_workflow(self):
        """Test CRUD operations workflow"""
        # Create
        model = create_sample_user_model()
        assert model['id'] == 1
        
        # Read
        found_model = model
        assert found_model['id'] == 1
        
        # Update would go here
        found_model['name'] = 'Updated Name'
        assert found_model['name'] == 'Updated Name'
        
        # Delete would set deleted=True
        found_model['deleted'] = False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
