"""
Vercel Serverless Function: /api/chats
Handles chat and message management
"""

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# Import database functions
try:
    from api.database import (
        create_chat, get_user_chats, get_chat, delete_chat,
        get_chat_messages, get_chat_logs
    )
    from api.auth import validate_token
except ImportError:
    from database import (
        create_chat, get_user_chats, get_chat, delete_chat,
        get_chat_messages, get_chat_logs
    )
    from auth import validate_token


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
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        """Get user's chats or a specific chat with messages"""
        try:
            user = get_auth_user(self.headers)
            if not user:
                self._send_json({'error': 'Authentication required'}, 401)
                return
            
            parsed = urlparse(self.path)
            path_parts = parsed.path.rstrip('/').split('/')
            query = parse_qs(parsed.query)
            
            # Check if requesting a specific chat
            chat_id = None
            if len(path_parts) >= 3 and path_parts[-1].isdigit():
                chat_id = int(path_parts[-1])
            
            if chat_id:
                # Get specific chat with messages
                chat = get_chat(chat_id, user['user_id'])
                
                if not chat:
                    self._send_json({'error': 'Chat not found'}, 404)
                    return
                
                messages = get_chat_messages(chat_id)
                
                response = {
                    'chat': self._serialize_dict(chat),
                    'messages': [self._serialize_dict(msg) for msg in messages]
                }
                
                # Include logs if requested
                if query.get('include_logs'):
                    logs = get_chat_logs(chat_id)
                    response['logs'] = [self._serialize_dict(log) for log in logs]
                
                self._send_json(response)
            else:
                # Get all user's chats
                chats = get_user_chats(user['user_id'])
                serialized_chats = [self._serialize_dict(chat) for chat in chats]
                self._send_json({'chats': serialized_chats})
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._send_json({'error': f'Server error: {str(e)}'}, 500)

    def do_POST(self):
        """Create a new chat"""
        try:
            user = get_auth_user(self.headers)
            if not user:
                self._send_json({'error': 'Authentication required'}, 401)
                return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            name = data.get('name', '').strip()
            original_prompt = data.get('original_prompt', '').strip()
            
            if not name:
                # Auto-generate name from prompt
                name = (original_prompt[:50] + '...') if len(original_prompt) > 50 else original_prompt
                if not name:
                    name = 'New Chat'
            
            chat = create_chat(user['user_id'], name, original_prompt)
            
            self._send_json({
                'success': True,
                'message': 'Chat created successfully',
                'chat': chat
            })
            
        except json.JSONDecodeError:
            self._send_json({'error': 'Invalid JSON'}, 400)
        except Exception as e:
            self._send_json({'error': f'Server error: {str(e)}'}, 500)

    def do_DELETE(self):
        """Delete a chat"""
        try:
            user = get_auth_user(self.headers)
            if not user:
                self._send_json({'error': 'Authentication required'}, 401)
                return
            
            # Extract chat ID from path
            parsed = urlparse(self.path)
            path_parts = parsed.path.rstrip('/').split('/')
            
            if len(path_parts) < 3 or not path_parts[-1].isdigit():
                self._send_json({'error': 'Chat ID required in path'}, 400)
                return
            
            chat_id = int(path_parts[-1])
            
            if delete_chat(chat_id, user['user_id']):
                self._send_json({'success': True, 'message': 'Chat deleted successfully'})
            else:
                self._send_json({'error': 'Chat not found'}, 404)
            
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
        self.wfile.write(json.dumps(data, default=str).encode())
