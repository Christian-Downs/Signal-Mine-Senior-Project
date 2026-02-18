"""
SignalMine Login - Vercel Serverless Function
"""

import json
import secrets
from http.server import BaseHTTPRequestHandler

# Demo users (in production, use a real database with hashed passwords)
DEMO_USERS = {
    "admin": "password123",
    "user": "user123",
    "demo": "demo"
}

# Store active tokens (in production, use Redis or a database)
# This is in-memory and will reset on serverless function restart
active_tokens = {}


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        """Handle login request"""
        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}

            username = data.get("username", "").strip()
            password = data.get("password", "").strip()

            # Validate credentials
            if not username or not password:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"error": "Username and password required"}).encode()
                )
                return

            if username not in DEMO_USERS:
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid credentials"}).encode())
                return

            if DEMO_USERS[username] != password:
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid credentials"}).encode())
                return

            # Generate token
            token = secrets.token_urlsafe(32)
            active_tokens[token] = username

            # Success response
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"token": token}).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(
                json.dumps({"error": f"Login failed: {str(e)}"}).encode()
            )
