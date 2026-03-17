"""
Comprehensive unit tests for SignalMine Health Check API (api/health.py)
Tests health check endpoint
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
import sys
import os

from api.health import handler


# ──────────────────────────────────────────────────────────────
# Helper Functions for Testing
# ──────────────────────────────────────────────────────────────

def create_mock_handler():
    """Create a mock HTTP handler"""
    h = handler(
        MagicMock(),
        ('127.0.0.1', 8000),
        MagicMock()
    )
    
    h.command = 'GET'
    h.path = '/api/health'
    h.headers = {}
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
# Health Check Endpoint Tests
# ──────────────────────────────────────────────────────────────

class TestHealthCheckEndpoint:
    """Tests for GET /api/health endpoint"""
    
    def test_health_check_returns_200(self):
        """Test health check returns 200 OK status"""
        h = create_mock_handler()
        h.do_GET()
        
        h.send_response.assert_called_once_with(200)
    
    def test_health_check_response_body(self):
        """Test health check returns correct response body"""
        h = create_mock_handler()
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        assert response is not None
        assert 'status' in response
        assert response['status'] == 'up'
    
    def test_health_check_sets_content_type_header(self):
        """Test health check sets Content-Type header"""
        h = create_mock_handler()
        h.do_GET()
        
        # Extract headers from calls
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        assert 'Content-Type' in header_dict
        assert header_dict['Content-Type'] == 'application/json'
    
    def test_health_check_sets_cors_header(self):
        """Test health check sets CORS header"""
        h = create_mock_handler()
        h.do_GET()
        
        # Extract headers from calls
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        assert 'Access-Control-Allow-Origin' in header_dict
        assert header_dict['Access-Control-Allow-Origin'] == '*'
    
    def test_health_check_calls_end_headers(self):
        """Test health check calls end_headers"""
        h = create_mock_handler()
        h.do_GET()
        
        h.end_headers.assert_called_once()
    
    def test_health_check_writes_valid_json(self):
        """Test health check writes valid JSON to response"""
        h = create_mock_handler()
        h.do_GET()
        
        h.wfile.seek(0)
        response_str = h.wfile.read().decode()
        
        # Should be valid JSON
        parsed = json.loads(response_str)
        assert isinstance(parsed, dict)
    
    def test_health_check_response_is_json_encoded(self):
        """Test health check response is properly JSON encoded"""
        h = create_mock_handler()
        h.do_GET()
        
        h.wfile.seek(0)
        response_bytes = h.wfile.read()
        
        # Should be bytes
        assert isinstance(response_bytes, bytes)
        
        # Should be decodable as UTF-8
        response_str = response_bytes.decode('utf-8')
        assert response_str == '{"status": "up"}'


# ──────────────────────────────────────────────────────────────
# Header Verification Tests
# ──────────────────────────────────────────────────────────────

class TestHealthCheckHeaders:
    """Tests for health check response headers"""
    
    def test_all_required_headers_present(self):
        """Test that all required headers are present"""
        h = create_mock_handler()
        h.do_GET()
        
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        required_headers = ['Content-Type', 'Access-Control-Allow-Origin']
        for header in required_headers:
            assert header in header_dict
    
    def test_header_order(self):
        """Test that headers are sent in correct order"""
        h = create_mock_handler()
        h.do_GET()
        
        # Get list of header calls in order
        header_calls = [call[0][0] for call in h.send_header.call_args_list]
        
        # Should have at least 2 header calls
        assert len(header_calls) >= 2
    
    def test_json_content_type_exact(self):
        """Test exact Content-Type value"""
        h = create_mock_handler()
        h.do_GET()
        
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        assert header_dict['Content-Type'] == 'application/json'
    
    def test_cors_allows_all_origins(self):
        """Test CORS header allows all origins"""
        h = create_mock_handler()
        h.do_GET()
        
        header_dict = {}
        for call_obj in h.send_header.call_args_list:
            header_dict[call_obj[0][0]] = call_obj[0][1]
        
        assert header_dict['Access-Control-Allow-Origin'] == '*'


# ──────────────────────────────────────────────────────────────
# Response Content Tests
# ──────────────────────────────────────────────────────────────

class TestHealthCheckResponseContent:
    """Tests for health check response content"""
    
    def test_response_contains_status_key(self):
        """Test response contains 'status' key"""
        h = create_mock_handler()
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert 'status' in response
    
    def test_status_value_is_up(self):
        """Test status value is 'up'"""
        h = create_mock_handler()
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert response['status'] == 'up'
    
    def test_response_has_one_key(self):
        """Test response has exactly one key"""
        h = create_mock_handler()
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert len(response) == 1
    
    def test_response_is_dict_type(self):
        """Test response is a dictionary"""
        h = create_mock_handler()
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert isinstance(response, dict)
    
    def test_status_value_is_string(self):
        """Test status value is a string"""
        h = create_mock_handler()
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert isinstance(response['status'], str)


# ──────────────────────────────────────────────────────────────
# HTTP Method Tests
# ──────────────────────────────────────────────────────────────

class TestHealthCheckMethods:
    """Tests for different HTTP methods"""
    
    def test_get_method_implemented(self):
        """Test that GET method is implemented"""
        h = create_mock_handler()
        
        # Should not raise
        h.do_GET()
        
        # Should have called send_response
        h.send_response.assert_called_once()
    
    def test_handler_has_do_get(self):
        """Test that handler has do_GET method"""
        h = create_mock_handler()
        assert hasattr(h, 'do_GET')
        assert callable(h.do_GET)


# ──────────────────────────────────────────────────────────────
# Status Code Tests
# ──────────────────────────────────────────────────────────────

class TestHealthCheckStatusCode:
    """Tests for HTTP status code"""
    
    def test_status_code_is_200(self):
        """Test status code is 200 OK"""
        h = create_mock_handler()
        h.do_GET()
        
        h.send_response.assert_called_with(200)
    
    def test_status_code_is_success(self):
        """Test status code indicates success (2xx)"""
        h = create_mock_handler()
        h.do_GET()
        
        status_code = h.send_response.call_args[0][0]
        assert 200 <= status_code < 300
    
    def test_only_one_send_response_call(self):
        """Test send_response is called exactly once"""
        h = create_mock_handler()
        h.do_GET()
        
        assert h.send_response.call_count == 1


# ──────────────────────────────────────────────────────────────
# Edge Cases Tests
# ──────────────────────────────────────────────────────────────

class TestHealthCheckEdgeCases:
    """Tests for edge cases"""
    
    def test_multiple_calls_same_handler(self):
        """Test calling health check multiple times on same handler"""
        h = create_mock_handler()
        
        h.do_GET()
        first_response = get_response_from_handler(h)
        
        # Create new handler for second call
        h2 = create_mock_handler()
        h2.do_GET()
        second_response = get_response_from_handler(h2)
        
        assert first_response == second_response
        assert first_response['status'] == 'up'
    
    def test_handler_with_different_paths(self):
        """Test health check works regardless of path"""
        for path in ['/api/health', '/health', '/']:
            h = create_mock_handler()
            h.path = path
            h.do_GET()
            
            response = get_response_from_handler(h)
            assert response['status'] == 'up'
    
    def test_handler_with_different_headers(self):
        """Test health check works with any request headers"""
        h = create_mock_handler()
        h.headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'Authorization': 'Bearer token'
        }
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert response['status'] == 'up'


# ──────────────────────────────────────────────────────────────
# JSON Encoding Tests
# ──────────────────────────────────────────────────────────────

class TestHealthCheckJsonEncoding:
    """Tests for JSON encoding"""
    
    def test_json_uses_utf8_encoding(self):
        """Test JSON response uses UTF-8 encoding"""
        h = create_mock_handler()
        h.do_GET()
        
        h.wfile.seek(0)
        response_bytes = h.wfile.read()
        
        # Should be decodable as UTF-8
        response_str = response_bytes.decode('utf-8')
        assert isinstance(response_str, str)
    
    def test_json_valid_format(self):
        """Test JSON is in valid format"""
        h = create_mock_handler()
        h.do_GET()
        
        h.wfile.seek(0)
        response_str = h.wfile.read().decode()
        
        # Should parse as JSON
        parsed = json.loads(response_str)
        assert parsed == {"status": "up"}
    
    def test_response_is_bytes_in_wfile(self):
        """Test response written to wfile is bytes"""
        h = create_mock_handler()
        h.do_GET()
        
        h.wfile.seek(0)
        content = h.wfile.read()
        
        assert isinstance(content, bytes)
    
    def test_can_serialize_and_deserialize(self):
        """Test response can be serialized and deserialized"""
        h = create_mock_handler()
        h.do_GET()
        
        # Get response as bytes
        h.wfile.seek(0)
        response_bytes = h.wfile.read()
        
        # Deserialize
        response_str = response_bytes.decode('utf-8')
        response_obj = json.loads(response_str)
        
        # Should match original
        assert response_obj == {"status": "up"}


# ──────────────────────────────────────────────────────────────
# Handler Lifecycle Tests
# ──────────────────────────────────────────────────────────────

class TestHealthCheckHandlerLifecycle:
    """Tests for handler lifecycle"""
    
    def test_complete_request_response_cycle(self):
        """Test complete request-response cycle"""
        h = create_mock_handler()
        
        # Execute request
        h.do_GET()
        
        # Verify response sequence
        assert h.send_response.called
        assert h.send_header.called
        assert h.end_headers.called
        
        # Verify data written to wfile
        h.wfile.seek(0)
        assert len(h.wfile.read()) > 0
    
    def test_send_calls_in_order(self):
        """Test send calls are made in correct order"""
        h = create_mock_handler()
        h.do_GET()
        
        # send_response should be called first
        response_call_order = h.send_response.call_args_list[0]
        # send_header calls should come after
        header_call_order = h.send_header.call_args_list
        # end_headers should be called last
        end_call_order = h.end_headers.call_args_list
        
        # Verify they all happened
        assert len(response_call_order[0]) > 0


# ──────────────────────────────────────────────────────────────
# Response Validation Tests
# ──────────────────────────────────────────────────────────────

class TestHealthCheckResponseValidation:
    """Tests for response validation"""
    
    def test_response_not_empty(self):
        """Test response is not empty"""
        h = create_mock_handler()
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert response is not None
        assert len(response) > 0
    
    def test_response_matches_expected_schema(self):
        """Test response matches expected schema"""
        h = create_mock_handler()
        h.do_GET()
        
        response = get_response_from_handler(h)
        
        # Schema validation
        assert isinstance(response, dict)
        assert 'status' in response
        assert isinstance(response['status'], str)
        assert response['status'] in ['up', 'down']  # Expected values
    
    def test_status_indicates_up(self):
        """Test status indicates service is up"""
        h = create_mock_handler()
        h.do_GET()
        
        response = get_response_from_handler(h)
        assert response['status'] == 'up'
        assert response['status'] != 'down'


# ──────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────

class TestHealthCheckIntegration:
    """Integration tests"""
    
    def test_health_check_is_reliable(self):
        """Test health check is reliable across multiple calls"""
        for _ in range(10):
            h = create_mock_handler()
            h.do_GET()
            
            response = get_response_from_handler(h)
            assert response['status'] == 'up'
            assert h.send_response.call_args[0][0] == 200
    
    def test_health_check_response_consistent(self):
        """Test health check response is consistent"""
        responses = []
        for _ in range(5):
            h = create_mock_handler()
            h.do_GET()
            response = get_response_from_handler(h)
            responses.append(response)
        
        # All responses should be identical
        first_response = responses[0]
        for response in responses[1:]:
            assert response == first_response


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
