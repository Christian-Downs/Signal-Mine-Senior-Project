from http.server import BaseHTTPRequestHandler
import json
import os
from typing import Optional

import psycopg
from dotenv import load_dotenv

load_dotenv()

# Global connection cache - reused across requests
_conn: Optional[psycopg.Connection] = None

def get_neon_connection() -> psycopg.Connection:
    """Get or create a database connection"""
    global _conn
    
    try:
        if _conn is None or _conn.closed:
            conn_string = os.getenv("DATABASE_URL")
            _conn = psycopg.connect(conn_string)
            print("New connection established")
        else:
            print("Reusing existing connection")
        return _conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        _conn = None
        raise

class handler(BaseHTTPRequestHandler):
 
    def do_POST(self):
        try:
            conn = get_neon_connection()
            with conn.cursor() as cur:
                # Do your database operations here
                pass
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'success'}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))