"""
Vercel Serverless Function: /api/logs
Handles model communication logs for end users
"""

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# Import database functions
try:
    from api.database import get_user_logs, get_chat_logs, get_message_logs
    from api.auth import validate_token
except ImportError:
    from database import get_user_logs, get_chat_logs, get_message_logs
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
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        """Get logs for user, chat, or message"""
        try:
            user = get_auth_user(self.headers)
            if not user:
                self._send_json({'error': 'Authentication required'}, 401)
                return
            
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            
            # Get chat logs
            chat_id = query.get('chat_id', [None])[0]
            if chat_id:
                logs = get_chat_logs(int(chat_id))
                self._send_json({
                    'logs': logs,
                    'chat_id': int(chat_id)
                })
                return
            
            # Get message logs
            message_id = query.get('message_id', [None])[0]
            if message_id:
                logs = get_message_logs(int(message_id))
                self._send_json({
                    'logs': logs,
                    'message_id': int(message_id)
                })
                return
            
            # Get user's recent logs
            limit = int(query.get('limit', [100])[0])
            logs = get_user_logs(user['user_id'], limit)
            serialized_logs = [self.serialize_dict(log) if log else log for log in logs]
            
            # Calculate summary stats
            total_tokens = sum(log.get('tokens_used', 0) or 0 for log in logs)
            avg_response_time = 0
            response_times = [log.get('response_time_ms', 0) for log in logs if log.get('response_time_ms')]
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
            
            healed_count = sum(1 for log in logs if log.get('was_healed'))
            
            self._send_json({
                'logs': logs,
                'summary': {
                    'total_requests': len(logs),
                    'total_tokens': total_tokens,
                    'avg_response_time_ms': round(avg_response_time, 2),
                    'healed_count': healed_count,
                    'models_used': list(set(log.get('model_used', 'unknown') for log in logs if log.get('model_used')))
                }
            })
            
        except Exception as e:
            self._send_json({'error': f'Server error: {str(e)}'}, 500)

    def serialize_dict(self, data):
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
