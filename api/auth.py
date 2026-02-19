"""  
Vercel Serverless Function: /api/auth
Handles user authentication (login, register, session management)
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict

# Import database functions
try:
    from api.database import create_user, verify_user, init_database, create_session, get_session, delete_session
except ImportError:
    from database import create_user, verify_user, init_database, create_session, get_session, delete_session

# Session configuration
SESSION_EXPIRY_HOURS = 24
SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))


def generate_token(user_id: int, username: str) -> str:
    """Generate a session token and store in database"""
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(hours=SESSION_EXPIRY_HOURS)).isoformat()
    
    try:
        create_session(token, user_id, username, expires_at)
    except Exception as e:
        print(f"Failed to create session: {e}")
        raise
    
    return token


def validate_token(token: str) -> Optional[Dict]:
    """Validate a session token from database"""
    if not token:
        return None
    
    try:
        session = get_session(token)
        
        if not session:
            return None
        
        # Check if expired - handle both datetime and string
        expires_at = session['expires_at']
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        
        if expires_at < datetime.now():
            delete_session(token)
            return None
        
        return session
    except Exception as e:
        print(f"Token validation error: {e}")
        return None


def invalidate_token(token: str):
    """Invalidate a session token"""
    if token:
        try:
            delete_session(token)
        except Exception as e:
            print(f"Token invalidation error: {e}")


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_POST(self):
        """Handle login and register"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            action = data.get('action', 'login')
            username = data.get('username', '').strip()
            password = data.get('password', '')
            
            if not username or not password:
                self._send_json({'error': 'Username and password are required'}, 400)
                return
            
            if len(username) < 3:
                self._send_json({'error': 'Username must be at least 3 characters'}, 400)
                return
            
            if len(password) < 6:
                self._send_json({'error': 'Password must be at least 6 characters'}, 400)
                return
            
            if action == 'register':
                # Create new user
                user = create_user(username, password)
                if user:
                    token = generate_token(user['ID'], user['username'])
                    self._send_json({
                        'success': True,
                        'message': 'Account created successfully',
                        'token': token,
                        'user': {
                            'id': user['ID'],
                            'username': user['username']
                        }
                    })
                else:
                    self._send_json({'error': 'Username already exists'}, 409)
            
            elif action == 'login':
                # Verify credentials
                user = verify_user(username, password)
                if user:
                    token = generate_token(user['ID'], user['username'])
                    self._send_json({
                        'success': True,
                        'message': 'Login successful',
                        'token': token,
                        'user': {
                            'id': user['ID'],
                            'username': user['username']
                        }
                    })
                else:
                    self._send_json({'error': 'Invalid username or password'}, 401)
            
            else:
                self._send_json({'error': 'Invalid action. Use "login" or "register"'}, 400)
                
        except json.JSONDecodeError:
            self._send_json({'error': 'Invalid JSON'}, 400)
        except Exception as e:
            self._send_json({'error': f'Server error: {str(e)}'}, 500)

    def do_GET(self):
        """Validate token and get user info"""
        try:
            auth_header = self.headers.get('Authorization', '')
            
            if not auth_header.startswith('Bearer '):
                self._send_json({'error': 'Missing or invalid Authorization header'}, 401)
                return
            
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            session = validate_token(token)
            
            if session:
                self._send_json({
                    'authenticated': True,
                    'user': {
                        'id': session['user_id'],
                        'username': session['username']
                    }
                })
            else:
                self._send_json({'error': 'Invalid or expired token'}, 401)
                
        except Exception as e:
            self._send_json({'error': f'Server error: {str(e)}'}, 500)

    def do_DELETE(self):
        """Logout - invalidate token"""
        try:
            auth_header = self.headers.get('Authorization', '')
            
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                invalidate_token(token)
            
            self._send_json({'success': True, 'message': 'Logged out successfully'})
            
        except Exception as e:
            self._send_json({'error': f'Server error: {str(e)}'}, 500)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
