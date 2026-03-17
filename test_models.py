"""
Comprehensive unit tests for SignalMine Models API (api/models.py)
Tests available AI models endpoint
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
import sys

from api.models import (
    handler, AVAILABLE_MODELS, DEFAULT_MODEL
)


# ──────────────────────────────────────────────────────────────
# Helper Functions for Testing
# ──────────────────────────────────────────────────────────────

def create_mock_handler(method='GET', path='/api/models', headers=None):
    """Create a mock HTTP handler for testing"""
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


# ──────────────────────────────────────────────────────────────
# Constants Tests
# ──────────────────────────────────────────────────────────────

class TestModelsConstants:
    """Tests for models constants"""
    
    def test_available_models_exists(self):
        """Test that AVAILABLE_MODELS constant is defined"""
        assert AVAILABLE_MODELS is not None
        assert isinstance(AVAILABLE_MODELS, dict)
    
    def test_available_models_not_empty(self):
        """Test that AVAILABLE_MODELS contains models"""
        assert len(AVAILABLE_MODELS) > 0
    
    def test_available_models_contains_gpt4o(self):
        """Test that gpt-4o model is available"""
        assert 'gpt-4o' in AVAILABLE_MODELS
    
    def test_available_models_contains_gpt4o_mini(self):
        """Test that gpt-4o-mini model is available"""
        assert 'gpt-4o-mini' in AVAILABLE_MODELS
    
    def test_available_models_contains_gpt4_turbo(self):
        """Test that gpt-4-turbo model is available"""
        assert 'gpt-4-turbo' in AVAILABLE_MODELS
    
    def test_available_models_contains_gpt35_turbo(self):
        """Test that gpt-3.5-turbo model is available"""
        assert 'gpt-3.5-turbo' in AVAILABLE_MODELS
    
    def test_available_models_descriptions(self):
        """Test that each model has a description"""
        for model_name, description in AVAILABLE_MODELS.items():
            assert isinstance(description, str)
            assert len(description) > 0
    
    def test_default_model_exists(self):
        """Test that DEFAULT_MODEL constant is defined"""
        assert DEFAULT_MODEL is not None
        assert isinstance(DEFAULT_MODEL, str)
    
    def test_default_model_is_valid(self):
        """Test that DEFAULT_MODEL is in AVAILABLE_MODELS"""
        assert DEFAULT_MODEL in AVAILABLE_MODELS
    
    def test_default_model_is_gpt4o_mini(self):
        """Test that default model is gpt-4o-mini"""
        assert DEFAULT_MODEL == 'gpt-4o-mini'


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
    
    def test_options_ends_headers(self):
        """Test OPTIONS request calls end_headers"""
        h = create_mock_handler(method='OPTIONS')
        h.do_OPTIONS()
        
        h.end_headers.assert_called_once()
    
    def test_options_sets_cors_origin_header(self):
        """Test OPTIONS request sets CORS origin header"""
        h = create_mock_handler(method='OPTIONS')
        h.do_OPTIONS()
        
        # Extract headers from mock calls
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        assert 'Access-Control-Allow-Origin' in header_dict
        assert header_dict['Access-Control-Allow-Origin'] == '*'
    
    def test_options_sets_allowed_methods(self):
        """Test OPTIONS request sets allowed methods"""
        h = create_mock_handler(method='OPTIONS')
        h.do_OPTIONS()
        
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        assert 'Access-Control-Allow-Methods' in header_dict
        assert 'GET' in header_dict['Access-Control-Allow-Methods']
        assert 'OPTIONS' in header_dict['Access-Control-Allow-Methods']
    
    def test_options_sets_allowed_headers(self):
        """Test OPTIONS request sets allowed headers"""
        h = create_mock_handler(method='OPTIONS')
        h.do_OPTIONS()
        
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        assert 'Access-Control-Allow-Headers' in header_dict
        assert 'Content-Type' in header_dict['Access-Control-Allow-Headers']


# ──────────────────────────────────────────────────────────────
# GET Request Tests - Basic Response
# ──────────────────────────────────────────────────────────────

class TestHandlerGetBasic:
    """Tests for basic GET request handling"""
    
    def test_get_returns_200(self):
        """Test GET request returns 200 OK"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        h.send_response.assert_called_once_with(200)
    
    def test_get_ends_headers(self):
        """Test GET request calls end_headers"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        h.end_headers.assert_called_once()
    
    def test_get_writes_response(self):
        """Test GET request writes response"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        h.wfile.seek(0)
        response = h.wfile.read()
        assert len(response) > 0


# ──────────────────────────────────────────────────────────────
# GET Request Tests - Headers
# ──────────────────────────────────────────────────────────────

class TestHandlerGetHeaders:
    """Tests for GET request response headers"""
    
    def test_get_sets_content_type_header(self):
        """Test GET request sets Content-Type header"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        assert 'Content-Type' in header_dict
        assert header_dict['Content-Type'] == 'application/json'
    
    def test_get_sets_cors_header(self):
        """Test GET request sets CORS header"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        assert 'Access-Control-Allow-Origin' in header_dict
        assert header_dict['Access-Control-Allow-Origin'] == '*'
    
    def test_get_header_count(self):
        """Test GET request sends exactly 2 headers"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        # Should be Content-Type and Access-Control-Allow-Origin
        assert h.send_header.call_count == 2


# ──────────────────────────────────────────────────────────────
# GET Request Tests - Response Structure
# ──────────────────────────────────────────────────────────────

class TestHandlerGetResponseStructure:
    """Tests for GET response JSON structure"""
    
    def test_get_response_is_valid_json(self):
        """Test GET response is valid JSON"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert response is not None
        assert isinstance(response, dict)
    
    def test_get_response_contains_models_key(self):
        """Test GET response contains 'models' key"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'models' in response
    
    def test_get_response_contains_default_key(self):
        """Test GET response contains 'default' key"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'default' in response
    
    def test_get_response_models_is_dict(self):
        """Test GET response 'models' is a dict"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert isinstance(response['models'], dict)
    
    def test_get_response_default_is_string(self):
        """Test GET response 'default' is a string"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert isinstance(response['default'], str)


# ──────────────────────────────────────────────────────────────
# GET Request Tests - Response Content
# ──────────────────────────────────────────────────────────────

class TestHandlerGetResponseContent:
    """Tests for GET response content validation"""
    
    def test_get_response_contains_all_models(self):
        """Test GET response contains all available models"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        for model_name in AVAILABLE_MODELS.keys():
            assert model_name in response['models']
    
    def test_get_response_model_count(self):
        """Test GET response contains correct number of models"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert len(response['models']) == len(AVAILABLE_MODELS)
    
    def test_get_response_models_match_constant(self):
        """Test GET response models match AVAILABLE_MODELS constant"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert response['models'] == AVAILABLE_MODELS
    
    def test_get_response_default_matches_constant(self):
        """Test GET response default matches DEFAULT_MODEL constant"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert response['default'] == DEFAULT_MODEL
    
    def test_get_response_models_descriptions(self):
        """Test each model in response has a description"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        for model_name, description in response['models'].items():
            assert isinstance(description, str)
            assert len(description) > 0


# ──────────────────────────────────────────────────────────────
# Model Specification Tests
# ──────────────────────────────────────────────────────────────

class TestModelSpecifications:
    """Tests for specific model information"""
    
    def test_gpt4o_model_exists(self):
        """Test gpt-4o model is in response"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'gpt-4o' in response['models']
    
    def test_gpt4o_mini_model_exists(self):
        """Test gpt-4o-mini model is in response"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'gpt-4o-mini' in response['models']
    
    def test_gpt4_turbo_model_exists(self):
        """Test gpt-4-turbo model is in response"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'gpt-4-turbo' in response['models']
    
    def test_gpt35_turbo_model_exists(self):
        """Test gpt-3.5-turbo model is in response"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'gpt-3.5-turbo' in response['models']
    
    def test_gpt4o_has_description(self):
        """Test gpt-4o has a meaningful description"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        gpt4o_desc = response['models']['gpt-4o']
        assert 'quality' in gpt4o_desc.lower() or 'gpt-4o' in gpt4o_desc
    
    def test_gpt4o_mini_has_description(self):
        """Test gpt-4o-mini has a meaningful description"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        gpt4o_mini_desc = response['models']['gpt-4o-mini']
        assert 'fast' in gpt4o_mini_desc.lower() or 'cheap' in gpt4o_mini_desc.lower() or 'mini' in gpt4o_mini_desc.lower()


# ──────────────────────────────────────────────────────────────
# JSON Encoding Tests
# ──────────────────────────────────────────────────────────────

class TestJsonEncoding:
    """Tests for JSON encoding"""
    
    def test_get_response_is_utf8_encoded(self):
        """Test GET response is UTF-8 encoded"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        h.wfile.seek(0)
        response_bytes = h.wfile.read()
        # Should not raise UnicodeDecodeError
        response_str = response_bytes.decode('utf-8')
        assert isinstance(response_str, str)
    
    def test_get_response_is_valid_json_string(self):
        """Test GET response can be parsed as JSON"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        # If this works without exception, JSON is valid
        assert response is not None
    
    def test_get_response_serializable(self):
        """Test GET response is properly serialized"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        h.wfile.seek(0)
        response_str = h.wfile.read().decode('utf-8')
        
        # Should be able to re-parse
        reparsed = json.loads(response_str)
        assert 'models' in reparsed
        assert 'default' in reparsed


# ──────────────────────────────────────────────────────────────
# Request Path Tests
# ──────────────────────────────────────────────────────────────

class TestRequestPaths:
    """Tests for different request paths"""
    
    def test_get_root_path(self):
        """Test GET request on root path"""
        h = create_mock_handler(path='/api/models')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'models' in response
    
    def test_get_with_trailing_slash(self):
        """Test GET request with trailing slash"""
        h = create_mock_handler(path='/api/models/')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'models' in response
    
    def test_get_with_query_string(self):
        """Test GET request with query string (should be ignored)"""
        h = create_mock_handler(path='/api/models?param=value')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'models' in response


# ──────────────────────────────────────────────────────────────
# Response Consistency Tests
# ──────────────────────────────────────────────────────────────

class TestResponseConsistency:
    """Tests for response consistency across multiple requests"""
    
    def test_multiple_requests_return_same_response(self):
        """Test multiple GET requests return identical response"""
        h1 = create_mock_handler(method='GET')
        h1.do_GET()
        response1 = get_response_from_handler(h1)
        
        h2 = create_mock_handler(method='GET')
        h2.do_GET()
        response2 = get_response_from_handler(h2)
        
        assert response1 == response2
    
    def test_response_contains_only_expected_keys(self):
        """Test response contains only 'models' and 'default' keys"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        expected_keys = {'models', 'default'}
        actual_keys = set(response.keys())
        
        assert actual_keys == expected_keys
    
    def test_models_dict_contains_only_expected_keys(self):
        """Test models dict contains only model names as keys"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        expected_models = set(AVAILABLE_MODELS.keys())
        actual_models = set(response['models'].keys())
        
        assert actual_models == expected_models


# ──────────────────────────────────────────────────────────────
# Status Code Tests
# ──────────────────────────────────────────────────────────────

class TestStatusCodes:
    """Tests for HTTP status codes"""
    
    def test_options_status_code_204(self):
        """Test OPTIONS returns 204 No Content"""
        h = create_mock_handler(method='OPTIONS')
        h.do_OPTIONS()
        
        h.send_response.assert_called_with(204)
    
    def test_get_status_code_200(self):
        """Test GET returns 200 OK"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        h.send_response.assert_called_with(200)


# ──────────────────────────────────────────────────────────────
# CORS Tests
# ──────────────────────────────────────────────────────────────

class TestCorsConfiguration:
    """Tests for CORS configuration"""
    
    def test_cors_allows_any_origin(self):
        """Test CORS allows any origin"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        assert header_dict['Access-Control-Allow-Origin'] == '*'
    
    def test_cors_consistent_across_methods(self):
        """Test CORS is consistent across OPTIONS and GET"""
        h_options = create_mock_handler(method='OPTIONS')
        h_options.do_OPTIONS()
        
        options_headers = {}
        for call_obj in h_options.send_header.call_args_list:
            options_headers[call_obj[0][0]] = call_obj[0][1]
        
        h_get = create_mock_handler(method='GET')
        h_get.do_GET()
        
        get_headers = {}
        for call_obj in h_get.send_header.call_args_list:
            get_headers[call_obj[0][0]] = call_obj[0][1]
        
        assert options_headers['Access-Control-Allow-Origin'] == get_headers['Access-Control-Allow-Origin']


# ──────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────

class TestIntegration:
    """Integration tests for models endpoint"""
    
    def test_complete_models_workflow(self):
        """Test complete models retrieval workflow"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        # Verify status
        h.send_response.assert_called_with(200)
        
        # Verify headers
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        assert header_dict['Content-Type'] == 'application/json'
        assert header_dict['Access-Control-Allow-Origin'] == '*'
        
        # Verify response content
        response = get_response_from_handler(h)
        assert 'models' in response
        assert 'default' in response
        assert len(response['models']) == 4
        assert response['default'] == 'gpt-4o-mini'
    
    def test_models_endpoint_availability(self):
        """Test models endpoint is always available"""
        for _ in range(5):
            h = create_mock_handler(method='GET')
            h.do_GET()
            
            response = get_response_from_handler(h)
            assert 'models' in response
            assert len(response['models']) == len(AVAILABLE_MODELS)
    
    def test_cors_preflight_workflow(self):
        """Test CORS preflight workflow"""
        # Send OPTIONS request
        h_options = create_mock_handler(method='OPTIONS')
        h_options.do_OPTIONS()
        
        assert h_options.send_response.call_args[0][0] == 204
        
        # Send actual GET request
        h_get = create_mock_handler(method='GET')
        h_get.do_GET()
        
        response = get_response_from_handler(h_get)
        assert 'models' in response


# ──────────────────────────────────────────────────────────────
# Edge Case Tests
# ──────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Tests for edge cases"""
    
    def test_empty_headers_dict(self):
        """Test handler works with empty headers dict"""
        h = create_mock_handler(headers={})
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert response is not None
    
    def test_response_not_none(self):
        """Test response is never None"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert response is not None
    
    def test_models_not_empty(self):
        """Test models dict is never empty"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert len(response['models']) > 0
    
    def test_default_model_not_empty_string(self):
        """Test default model is not empty string"""
        h = create_mock_handler(method='GET')
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert len(response['default']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
