"""
Vercel Serverless Function: /api/user-models
Handles custom model API key management
"""

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# Import database functions
try:
    from api.database import (
        create_user_model, get_user_models, get_user_model, 
        delete_user_model, update_user_model
    )
    from api.auth import validate_token
except ImportError:
    from database import (
        create_user_model, get_user_models, get_user_model, 
        delete_user_model, update_user_model
    )
    from auth import validate_token

# Available model providers
PROVIDERS = {
    'openai': {
        'name': 'OpenAI',
        'base_url': 'https://api.openai.com/v1',
        'models': ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo', 'o1', 'o1-mini']
    },
    'anthropic': {
        'name': 'Anthropic',
        'base_url': 'https://api.anthropic.com/v1',
        'models': ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229']
    },
    'google': {
        'name': 'Google AI',
        'base_url': 'https://generativelanguage.googleapis.com/v1beta',
        'models': ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash']
    },
    'groq': {
        'name': 'Groq',
        'base_url': 'https://api.groq.com/openai/v1',
        'models': ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768']
    },
    'together': {
        'name': 'Together AI',
        'base_url': 'https://api.together.xyz/v1',
        'models': ['meta-llama/Llama-3.3-70B-Instruct-Turbo', 'mistralai/Mixtral-8x7B-Instruct-v0.1']
    },
    'custom': {
        'name': 'Custom/Self-hosted',
        'base_url': None,  # User provides
        'models': []
    }
}


def get_auth_user(headers):
    """Extract and validate user from Authorization header"""
    auth_header = headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:]
    session = validate_token(token)
    return session


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        """Get user's custom models or available providers"""
        try:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            
            # Get available providers (no auth required)
            if query.get('providers'):
                self._send_json({'providers': PROVIDERS})
                return
            
            # Get user's models (auth required)
            user = get_auth_user(self.headers)
            if not user:
                self._send_json({'error': 'Authentication required'}, 401)
                return
            
            models = get_user_models(user['user_id'])
            serialized_models = [self._serialize_dict(model) for model in models]
            self._send_json({
                'models': serialized_models,
                'providers': PROVIDERS
            })
            
        except Exception as e:
            self._send_json({'error': f'Server error: {str(e)}'}, 500)

    def do_POST(self):
        """Add a new custom model"""
        try:
            user = get_auth_user(self.headers)
            if not user:
                self._send_json({'error': 'Authentication required'}, 401)
                return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            name = data.get('name', '').strip()
            api_key = data.get('api_key', '').strip()
            provider = data.get('provider', 'openai')
            base_url = data.get('base_url', '').strip() or None
            
            if not name:
                self._send_json({'error': 'Model name is required'}, 400)
                return
            
            if not api_key:
                self._send_json({'error': 'API key is required'}, 400)
                return
            
            if provider not in PROVIDERS:
                self._send_json({'error': f'Invalid provider. Choose from: {", ".join(PROVIDERS.keys())}'}, 400)
                return
            
            if provider == 'custom' and not base_url:
                self._send_json({'error': 'Base URL is required for custom providers'}, 400)
                return
            
            # Use default base_url for known providers
            if not base_url and provider != 'custom':
                base_url = PROVIDERS[provider]['base_url']
            
            model = create_user_model(user['user_id'], name, api_key, provider, base_url)
            
            self._send_json({
                'success': True,
                'message': 'Model added successfully',
                'model': model
            })
            
        except json.JSONDecodeError:
            self._send_json({'error': 'Invalid JSON'}, 400)
        except Exception as e:
            self._send_json({'error': f'Server error: {str(e)}'}, 500)

    def do_PUT(self):
        """Update a custom model"""
        try:
            user = get_auth_user(self.headers)
            if not user:
                self._send_json({'error': 'Authentication required'}, 401)
                return
            
            # Extract model ID from path
            parsed = urlparse(self.path)
            path_parts = parsed.path.rstrip('/').split('/')
            
            if len(path_parts) < 3 or not path_parts[-1].isdigit():
                self._send_json({'error': 'Model ID required in path'}, 400)
                return
            
            model_id = int(path_parts[-1])
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            name = data.get('name', '').strip() or None
            api_key = data.get('api_key', '').strip() or None
            provider = data.get('provider', '').strip() or None
            base_url = data.get('base_url', '')
            
            if provider and provider not in PROVIDERS:
                self._send_json({'error': f'Invalid provider. Choose from: {", ".join(PROVIDERS.keys())}'}, 400)
                return
            
            model = update_user_model(model_id, user['user_id'], name, api_key, provider, base_url if base_url else None)
            
            if model:
                self._send_json({
                    'success': True,
                    'message': 'Model updated successfully',
                    'model': model
                })
            else:
                self._send_json({'error': 'Model not found or no changes made'}, 404)
            
        except json.JSONDecodeError:
            self._send_json({'error': 'Invalid JSON'}, 400)
        except Exception as e:
            self._send_json({'error': f'Server error: {str(e)}'}, 500)

    def do_DELETE(self):
        """Delete a custom model"""
        try:
            user = get_auth_user(self.headers)
            if not user:
                self._send_json({'error': 'Authentication required'}, 401)
                return
            
            # Extract model ID from path
            parsed = urlparse(self.path)
            path_parts = parsed.path.rstrip('/').split('/')
            
            if len(path_parts) < 3 or not path_parts[-1].isdigit():
                self._send_json({'error': 'Model ID required in path'}, 400)
                return
            
            model_id = int(path_parts[-1])
            
            if delete_user_model(model_id, user['user_id']):
                self._send_json({'success': True, 'message': 'Model deleted successfully'})
            else:
                self._send_json({'error': 'Model not found'}, 404)
            
        except Exception as e:
            self._send_json({'error': f'Server error: {str(e)}'}, 500)

    def _serialize_dict(self, data):
        """Convert datetime objects to ISO strings for JSON serialization"""
        if not data:
            return data
        result = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
