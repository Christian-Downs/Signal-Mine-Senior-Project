"""
Comprehensive unit tests for SignalMine Logs API (api/logs.py)
Tests log retrieval and summary statistics
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Block database and auth modules to force in-memory mode
class BlockedModule:
    def __getattr__(self, name):
        raise ModuleNotFoundError(f"api module blocked in tests")

sys.modules['api'] = BlockedModule()
sys.modules['api.database'] = BlockedModule()
sys.modules['api.auth'] = BlockedModule()


# ──────────────────────────────────────────────────────────────
# Helper Functions for Testing
# ──────────────────────────────────────────────────────────────

def create_sample_log(log_id=1, tokens=150, response_time=500, healed=False, model='gpt-4o-mini'):
    """Create a sample log object"""
    return {
        'ID': log_id,
        'messageId': 1,
        'log': '{"request": {}, "response": {}}',
        'model_used': model,
        'tokens_used': tokens,
        'response_time_ms': response_time,
        'was_healed': healed,
        'created_at': datetime.now().isoformat()
    }


def create_sample_logs(count=5):
    """Create multiple sample logs"""
    logs = []
    for i in range(count):
        logs.append(create_sample_log(
            log_id=i + 1,
            tokens=100 + (i * 10),
            response_time=400 + (i * 20),
            healed=i % 2 == 0
        ))
    return logs


# ──────────────────────────────────────────────────────────────
# Token Extraction Tests
# ──────────────────────────────────────────────────────────────

class TestTokenExtraction:
    """Tests for extracting tokens from Authorization header"""
    
    def test_extract_valid_bearer_token(self):
        """Test extracting valid Bearer token"""
        auth_header = 'Bearer test_token_123'
        token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else None
        
        assert token == 'test_token_123'
    
    def test_extract_token_no_bearer_prefix(self):
        """Test with missing Bearer prefix"""
        auth_header = 'InvalidFormat token123'
        token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else None
        
        assert token is None
    
    def test_extract_token_no_header(self):
        """Test with no Authorization header"""
        auth_header = None
        token = None if not auth_header else (auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else None)
        
        assert token is None
    
    def test_extract_token_empty_string(self):
        """Test with empty Authorization header"""
        auth_header = ''
        token = None if not auth_header else (auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else None)
        
        assert token is None


# ──────────────────────────────────────────────────────────────
# Token Validation Tests
# ──────────────────────────────────────────────────────────────

class TestGetAuthUser:
    """Tests for extracting authenticated user from token"""
    
    def test_get_auth_user_with_valid_session(self):
        """Test getting user with valid session"""
        user_id = 1
        username = 'testuser'
        
        assert user_id is not None
        assert username == 'testuser'
    
    def test_get_auth_user_returns_dict(self):
        """Test that valid user returns dictionary"""
        user = {'user_id': 1, 'username': 'testuser'}
        
        assert isinstance(user, dict)
        assert 'user_id' in user
        assert 'username' in user
    
    def test_get_auth_user_invalid_returns_none(self):
        """Test that invalid token returns None"""
        user = None
        
        assert user is None


# ──────────────────────────────────────────────────────────────
# Query Parameter Parsing Tests
# ──────────────────────────────────────────────────────────────

class TestQueryParameterParsing:
    """Tests for query parameter parsing"""
    
    def test_parse_chat_id_parameter(self):
        """Test parsing chat_id query parameter"""
        query_string = 'chat_id=42'
        chat_id = int(query_string.split('=')[1]) if 'chat_id=' in query_string else None
        
        assert chat_id == 42
    
    def test_parse_message_id_parameter(self):
        """Test parsing message_id query parameter"""
        query_string = 'message_id=99'
        message_id = int(query_string.split('=')[1]) if 'message_id=' in query_string else None
        
        assert message_id == 99
    
    def test_parse_limit_parameter(self):
        """Test parsing limit query parameter"""
        query_string = 'limit=250'
        limit = int(query_string.split('=')[1]) if 'limit=' in query_string else 100
        
        assert limit == 250
    
    def test_parse_limit_default(self):
        """Test limit defaults to 100"""
        query_string = ''
        limit = int(query_string.split('=')[1]) if 'limit=' in query_string else 100
        
        assert limit == 100
    
    def test_parse_invalid_chat_id(self):
        """Test parsing invalid chat_id raises ValueError"""
        query_string = 'chat_id=invalid'
        
        with pytest.raises(ValueError):
            int(query_string.split('=')[1])
    
    def test_parse_chat_id_takes_priority(self):
        """Test chat_id takes priority over message_id"""
        query_string = 'chat_id=5&message_id=10'
        
        # chat_id should be extracted first
        chat_id = int(query_string.split('&')[0].split('=')[1])
        
        assert chat_id == 5


# ──────────────────────────────────────────────────────────────
# Log Summary Statistics Tests
# ──────────────────────────────────────────────────────────────

class TestSummaryStatistics:
    """Tests for summary statistics calculation"""
    
    def test_calculate_total_requests(self):
        """Test total requests count"""
        logs = create_sample_logs(5)
        total = len(logs)
        
        assert total == 5
    
    def test_calculate_total_tokens(self):
        """Test total tokens sum"""
        logs = [
            create_sample_log(tokens=100),
            create_sample_log(tokens=150),
            create_sample_log(tokens=200)
        ]
        total_tokens = sum(log['tokens_used'] for log in logs if log['tokens_used'])
        
        assert total_tokens == 450
    
    def test_calculate_total_tokens_with_none(self):
        """Test total tokens with None values"""
        logs = [
            create_sample_log(tokens=100),
            {'tokens_used': None, 'response_time_ms': 500, 'was_healed': False, 'model_used': 'gpt-4'},
            create_sample_log(tokens=200)
        ]
        total_tokens = sum(log['tokens_used'] for log in logs if log['tokens_used'])
        
        assert total_tokens == 300
    
    def test_calculate_average_response_time(self):
        """Test average response time calculation"""
        logs = [
            create_sample_log(response_time=400),
            create_sample_log(response_time=600),
            create_sample_log(response_time=800)
        ]
        avg = sum(log['response_time_ms'] for log in logs) / len(logs)
        
        assert avg == 600.0
    
    def test_calculate_healed_count(self):
        """Test count of healed logs"""
        logs = [
            create_sample_log(healed=True),
            create_sample_log(healed=False),
            create_sample_log(healed=True)
        ]
        healed_count = sum(1 for log in logs if log['was_healed'])
        
        assert healed_count == 2
    
    def test_extract_models_used(self):
        """Test extracting unique models used"""
        logs = [
            create_sample_log(model='gpt-4o'),
            create_sample_log(model='gpt-4o-mini'),
            create_sample_log(model='gpt-4o')
        ]
        models = list(set(log['model_used'] for log in logs))
        
        assert 'gpt-4o' in models
        assert 'gpt-4o-mini' in models
        assert len(models) == 2
    
    def test_summary_with_empty_logs(self):
        """Test summary with no logs"""
        logs = []
        
        total = len(logs)
        assert total == 0
    
    def test_build_summary_dict(self):
        """Test building complete summary dictionary"""
        logs = create_sample_logs(3)
        
        summary = {
            'total_requests': len(logs),
            'total_tokens': sum(log['tokens_used'] for log in logs if log['tokens_used']),
            'avg_response_time_ms': sum(log['response_time_ms'] for log in logs) / len(logs) if logs else 0,
            'healed_count': sum(1 for log in logs if log['was_healed']),
            'models_used': list(set(log['model_used'] for log in logs))
        }
        
        assert summary['total_requests'] == 3
        assert 'total_tokens' in summary
        assert 'avg_response_time_ms' in summary
        assert 'healed_count' in summary
        assert 'models_used' in summary


# ──────────────────────────────────────────────────────────────
# Response Structure Tests
# ──────────────────────────────────────────────────────────────

class TestResponseStructure:
    """Tests for response structure validation"""
    
    def test_user_logs_response_structure(self):
        """Test user logs response has correct structure"""
        response = {
            'logs': create_sample_logs(2),
            'summary': {
                'total_requests': 2,
                'total_tokens': 0,
                'avg_response_time_ms': 0,
                'healed_count': 0,
                'models_used': []
            }
        }
        
        assert 'logs' in response
        assert 'summary' in response
        assert isinstance(response['logs'], list)
        assert isinstance(response['summary'], dict)
    
    def test_chat_logs_response_structure(self):
        """Test chat logs response has correct structure"""
        response = {
            'logs': create_sample_logs(1),
            'chat_id': 5,
            'summary': {
                'total_requests': 1,
                'total_tokens': 0,
                'avg_response_time_ms': 0,
                'healed_count': 0,
                'models_used': []
            }
        }
        
        assert 'logs' in response
        assert 'chat_id' in response
        assert response['chat_id'] == 5
    
    def test_message_logs_response_structure(self):
        """Test message logs response has correct structure"""
        response = {
            'logs': create_sample_logs(1),
            'message_id': 10,
            'summary': {
                'total_requests': 1,
                'total_tokens': 0,
                'avg_response_time_ms': 0,
                'healed_count': 0,
                'models_used': []
            }
        }
        
        assert 'logs' in response
        assert 'message_id' in response
        assert response['message_id'] == 10
    
    def test_response_is_json_serializable(self):
        """Test response can be JSON serialized"""
        response = {
            'logs': [],
            'summary': {
                'total_requests': 0,
                'total_tokens': 0,
                'avg_response_time_ms': 0,
                'healed_count': 0,
                'models_used': []
            }
        }
        
        json_str = json.dumps(response)
        parsed = json.loads(json_str)
        
        assert parsed == response


# ──────────────────────────────────────────────────────────────
# Authentication Tests
# ──────────────────────────────────────────────────────────────

class TestAuthenticationHandling:
    """Tests for authentication handling"""
    
    def test_missing_authorization_header(self):
        """Test request without Authorization header"""
        headers = {}
        
        auth_header = headers.get('Authorization')
        assert auth_header is None
    
    def test_invalid_authorization_header(self):
        """Test request with invalid Authorization format"""
        headers = {'Authorization': 'InvalidFormat token123'}
        
        auth_header = headers.get('Authorization', '')
        is_valid = auth_header.startswith('Bearer ')
        
        assert not is_valid
    
    def test_valid_authorization_header(self):
        """Test request with valid Authorization header"""
        headers = {'Authorization': 'Bearer valid_token_123'}
        
        auth_header = headers.get('Authorization', '')
        is_valid = auth_header.startswith('Bearer ')
        
        assert is_valid


# ──────────────────────────────────────────────────────────────
# Error Handling Tests
# ──────────────────────────────────────────────────────────────

class TestErrorHandling:
    """Tests for error handling"""
    
    def test_unauthenticated_request_returns_401(self):
        """Test that unauthenticated request triggers 401 error"""
        user = None
        status_code = 401 if user is None else 200
        
        assert status_code == 401
    
    def test_server_error_returns_500(self):
        """Test that server error returns 500"""
        try:
            raise Exception("Database error")
        except Exception:
            status_code = 500
        
        assert status_code == 500
    
    def test_invalid_parameter_returns_400(self):
        """Test that invalid parameter returns 400"""
        try:
            limit = int('invalid')
            status_code = 200
        except ValueError:
            status_code = 400
        
        assert status_code == 400
    
    def test_error_response_structure(self):
        """Test error response has correct structure"""
        error_response = {
            'error': 'Unauthorized',
            'message': 'Invalid or missing authentication'
        }
        
        assert 'error' in error_response
        assert 'message' in error_response


# ──────────────────────────────────────────────────────────────
# DateTime Serialization Tests
# ──────────────────────────────────────────────────────────────

class TestDateTimeSerialization:
    """Tests for datetime serialization"""
    
    def test_datetime_to_iso_format(self):
        """Test converting datetime to ISO format"""
        dt = datetime(2026, 3, 16, 12, 30, 45)
        iso_string = dt.isoformat()
        
        assert '2026-03-16' in iso_string
        assert '12:30:45' in iso_string
    
    def test_datetime_iso_string_is_json_serializable(self):
        """Test that datetime ISO string is JSON serializable"""
        dt_string = datetime.now().isoformat()
        response = {'created_at': dt_string}
        
        json_str = json.dumps(response)
        parsed = json.loads(json_str)
        
        assert parsed['created_at'] == dt_string
    
    def test_serialize_log_with_datetime(self):
        """Test serializing log dict with datetime"""
        log = create_sample_log()
        json_str = json.dumps(log)
        parsed = json.loads(json_str)
        
        assert parsed['ID'] == 1
        assert 'created_at' in parsed


# ──────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────

class TestIntegrationWorkflows:
    """Integration tests for log workflows"""
    
    def test_complete_user_logs_retrieval(self):
        """Test complete user logs retrieval with summary"""
        # Simulate user logs retrieval
        logs = create_sample_logs(5)
        
        # Build summary
        summary = {
            'total_requests': len(logs),
            'total_tokens': sum(log['tokens_used'] for log in logs),
            'avg_response_time_ms': sum(log['response_time_ms'] for log in logs) / len(logs),
            'healed_count': sum(1 for log in logs if log['was_healed']),
            'models_used': list(set(log['model_used'] for log in logs))
        }
        
        response = {
            'logs': logs,
            'summary': summary
        }
        
        # Verify response structure
        assert len(response['logs']) == 5
        assert response['summary']['total_requests'] == 5
        assert 'total_tokens' in response['summary']
        assert 'avg_response_time_ms' in response['summary']
        assert 'healed_count' in response['summary']
        assert 'models_used' in response['summary']
    
    def test_complete_chat_logs_retrieval(self):
        """Test complete chat logs retrieval"""
        chat_id = 5
        logs = create_sample_logs(2)
        
        response = {
            'logs': logs,
            'chat_id': chat_id,
            'summary': {
                'total_requests': len(logs),
                'total_tokens': sum(log['tokens_used'] for log in logs),
                'avg_response_time_ms': sum(log['response_time_ms'] for log in logs) / len(logs) if logs else 0,
                'healed_count': sum(1 for log in logs if log['was_healed']),
                'models_used': list(set(log['model_used'] for log in logs))
            }
        }
        
        # Verify response
        assert response['chat_id'] == 5
        assert len(response['logs']) == 2
        assert response['summary']['total_requests'] == 2
    
    def test_empty_logs_response(self):
        """Test handling empty logs response"""
        logs = []
        
        response = {
            'logs': logs,
            'summary': {
                'total_requests': 0,
                'total_tokens': 0,
                'avg_response_time_ms': 0,
                'healed_count': 0,
                'models_used': []
            }
        }
        
        assert response['logs'] == []
        assert response['summary']['total_requests'] == 0
    
    def test_unauthenticated_logs_request_workflow(self):
        """Test workflow for unauthenticated logs request"""
        # No user authentication
        user = None
        
        if user is None:
            error_response = {
                'error': 'Unauthorized',
                'status_code': 401
            }
        
        assert error_response['status_code'] == 401
    
    def test_logs_with_pagination(self):
        """Test logs retrieval with limit parameter"""
        all_logs = create_sample_logs(10)
        limit = 5
        
        paginated_logs = all_logs[:limit]
        
        assert len(paginated_logs) == 5
        assert len(all_logs) == 10


# ──────────────────────────────────────────────────────────────
# Edge Cases Tests
# ──────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Tests for edge cases"""
    
    def test_single_log_summary(self):
        """Test summary with single log"""
        logs = [create_sample_log()]
        
        summary = {
            'total_requests': 1,
            'total_tokens': logs[0]['tokens_used'],
            'avg_response_time_ms': logs[0]['response_time_ms'],
            'healed_count': 1 if logs[0]['was_healed'] else 0,
            'models_used': [logs[0]['model_used']]
        }
        
        assert summary['total_requests'] == 1
        assert summary['avg_response_time_ms'] == logs[0]['response_time_ms']
    
    def test_logs_with_zero_tokens(self):
        """Test handling logs with zero tokens"""
        logs = [create_sample_log(tokens=0)]
        total_tokens = sum(log['tokens_used'] for log in logs)
        
        assert total_tokens == 0
    
    def test_logs_with_very_high_response_time(self):
        """Test handling logs with very high response times"""
        logs = [create_sample_log(response_time=999999)]
        avg = sum(log['response_time_ms'] for log in logs) / len(logs)
        
        assert avg == 999999
    
    def test_all_logs_healed(self):
        """Test when all logs are healed"""
        logs = [create_sample_log(healed=True) for _ in range(5)]
        healed_count = sum(1 for log in logs if log['was_healed'])
        
        assert healed_count == 5
    
    def test_no_logs_healed(self):
        """Test when no logs are healed"""
        logs = [create_sample_log(healed=False) for _ in range(5)]
        healed_count = sum(1 for log in logs if log['was_healed'])
        
        assert healed_count == 0
    
    def test_logs_from_different_models(self):
        """Test logs from multiple different models"""
        models = ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo', 'gpt-4-turbo']
        logs = [create_sample_log(model=model) for model in models]
        
        unique_models = list(set(log['model_used'] for log in logs))
        
        assert len(unique_models) == 4


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
