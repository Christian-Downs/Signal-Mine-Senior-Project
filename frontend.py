"""
SignalMine Flask Backend
- User authentication with database
- Chat persistence and history
- Custom model management
- Model communication logging
- LP generation with self-healing
"""

from __future__ import annotations
import json
import os
import uuid
import time
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI

load_dotenv()

# Try to import database functions
try:
    from api.database import (
        init_database, create_user, verify_user,
        create_chat, get_user_chats, get_chat, delete_chat,
        create_message, get_chat_messages, get_next_message_order,
        create_user_model, get_user_models, get_user_model, delete_user_model, update_user_model,
        create_log, get_user_logs, get_chat_logs
    )
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("Warning: Database module not available. Running in memory-only mode.")

app = Flask(__name__, static_folder="public", static_url_path="")
CORS(app)

# ──────────────────────────────────────────────────────────────
# Pydantic Models for Linear Programming
# ──────────────────────────────────────────────────────────────

class LinearProgram(BaseModel):
    """Validated Linear Program structure"""
    problem_description: str = Field(description="Natural language description of the problem")
    objective_type: str = Field(description="'maximize' or 'minimize'")
    objective_function: str = Field(description="The objective function, e.g., '3x + 2y'")
    decision_variables: List[str] = Field(description="List of decision variable names")
    constraints: List[str] = Field(description="List of constraint expressions")
    variable_bounds: Dict[str, str] = Field(
        default_factory=dict,
        description="Bounds for variables, e.g., {'x': '>= 0', 'y': '>= 0'}"
    )
    latex_formulation: Optional[str] = Field(default=None)
    python_code: Optional[str] = Field(default=None)


class LPResponse(BaseModel):
    """Full response from LP agent"""
    linear_program: LinearProgram
    explanation: str = Field(description="Explanation of the formulation")
    assumptions: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────
# In-Memory Storage (fallback when DB unavailable)
# ──────────────────────────────────────────────────────────────

memory_users: Dict[str, Dict] = {}
memory_sessions: Dict[str, Dict] = {}
memory_conversations: Dict[str, List[dict]] = {}

# ──────────────────────────────────────────────────────────────
# Session Management
# ──────────────────────────────────────────────────────────────

SESSION_EXPIRY_HOURS = 24

def generate_token(user_id: int, username: str) -> str:
    """Generate a session token"""
    token = secrets.token_urlsafe(32)
    memory_sessions[token] = {
        'user_id': user_id,
        'username': username,
        'created_at': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(hours=SESSION_EXPIRY_HOURS)).isoformat()
    }
    return token


def validate_token(token: str) -> Optional[Dict]:
    """Validate a session token"""
    if not token or token not in memory_sessions:
        return None
    
    session = memory_sessions[token]
    if datetime.fromisoformat(session['expires_at']) < datetime.now():
        del memory_sessions[token]
        return None
    
    return session


def get_current_user():
    """Get current user from Authorization header"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:]
    return validate_token(token)


# ──────────────────────────────────────────────────────────────
# Available Models
# ──────────────────────────────────────────────────────────────

AVAILABLE_MODELS = {
    "gpt-4o": "GPT-4o (Best quality)",
    "gpt-4o-mini": "GPT-4o Mini (Fast & cheap)",
    "gpt-4-turbo": "GPT-4 Turbo",
    "gpt-3.5-turbo": "GPT-3.5 Turbo (Fastest)",
}

DEFAULT_MODEL = "gpt-4o-mini"

PROVIDERS = {
    'openai': {'name': 'OpenAI', 'base_url': 'https://api.openai.com/v1'},
    'anthropic': {'name': 'Anthropic', 'base_url': 'https://api.anthropic.com/v1'},
    'google': {'name': 'Google AI', 'base_url': 'https://generativelanguage.googleapis.com/v1beta'},
    'groq': {'name': 'Groq', 'base_url': 'https://api.groq.com/openai/v1'},
    'together': {'name': 'Together AI', 'base_url': 'https://api.together.xyz/v1'},
    'custom': {'name': 'Custom', 'base_url': None}
}

# ──────────────────────────────────────────────────────────────
# System Prompts
# ──────────────────────────────────────────────────────────────

LP_GENERATOR_SYSTEM_PROMPT = """You are an expert in linear programming and mathematical optimization.

Your task is to convert natural language descriptions into formal Linear Programs.

You MUST respond with a single JSON object with EXACTLY this structure:
{
  "linear_program": {
    "problem_description": "string",
    "objective_type": "maximize" or "minimize",
    "objective_function": "string - e.g., '3x + 2y'",
    "decision_variables": ["x", "y", ...],
    "constraints": ["x + y <= 10", ...],
    "variable_bounds": {"x": ">= 0", "y": ">= 0"},
    "latex_formulation": "LaTeX string",
    "python_code": "Python code using scipy or PuLP"
  },
  "explanation": "string",
  "assumptions": ["assumption 1", ...],
  "suggestions": ["suggestion 1", ...]
}

Do NOT include text outside the JSON."""

LP_FIXER_SYSTEM_PROMPT = """Fix the malformed Linear Program JSON to match this structure:
{
  "linear_program": {
    "problem_description": "string",
    "objective_type": "maximize" or "minimize",
    "objective_function": "string",
    "decision_variables": ["array"],
    "constraints": ["array"],
    "variable_bounds": {"var": "bound"},
    "latex_formulation": "string or null",
    "python_code": "string or null"
  },
  "explanation": "string",
  "assumptions": ["array"],
  "suggestions": ["array"]
}
Return ONLY valid JSON."""


# ──────────────────────────────────────────────────────────────
# AI Functions
# ──────────────────────────────────────────────────────────────

def get_openai_client(api_key: str = None, base_url: str = None) -> OpenAI:
    """Get OpenAI client with optional custom credentials"""
    if api_key is None:
        api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    
    kwargs = {'api_key': api_key}
    if base_url:
        kwargs['base_url'] = base_url
    
    return OpenAI(**kwargs)


def generate_lp(prompt: str, model: str, history: List[dict], api_key: str = None, base_url: str = None) -> tuple:
    """Generate LP from prompt"""
    client = get_openai_client(api_key, base_url)
    
    messages = [{"role": "system", "content": LP_GENERATOR_SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": prompt})
    
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=messages,
        temperature=0.2,
    )
    
    raw_content = response.choices[0].message.content
    tokens_used = response.usage.total_tokens if response.usage else None
    return json.loads(raw_content), raw_content, tokens_used


def fix_lp(broken_json: str, error_message: str, model: str, api_key: str = None, base_url: str = None) -> dict:
    """Attempt to fix malformed LP JSON"""
    client = get_openai_client(api_key, base_url)
    
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": LP_FIXER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Error: {error_message}\n\nBroken JSON:\n{broken_json}"}
        ],
        temperature=0.1,
    )
    
    return json.loads(response.choices[0].message.content)


def validate_and_heal(raw_data: dict, raw_content: str, model: str, api_key: str = None, base_url: str = None) -> tuple:
    """Validate and optionally heal LP response"""
    try:
        validated = LPResponse.model_validate(raw_data)
        return validated, False
    except ValidationError as e:
        fixed_data = fix_lp(raw_content, str(e), model, api_key, base_url)
        validated = LPResponse.model_validate(fixed_data)
        return validated, True


def build_response_message(lp: LinearProgram, response: LPResponse, was_healed: bool) -> str:
    """Build formatted response message"""
    msg = f"""## Linear Program Formulation

**Problem:** {lp.problem_description}

**Objective ({lp.objective_type}):**
$$\\text{{{lp.objective_type}}} \\quad {lp.objective_function}$$

**Decision Variables:** {', '.join(lp.decision_variables)}

**Constraints:**
{chr(10).join(f'- ${c}$' for c in lp.constraints)}

**Variable Bounds:**
{chr(10).join(f'- ${v} {b}$' for v, b in lp.variable_bounds.items())}

---

### LaTeX Formulation
```latex
{lp.latex_formulation or 'Not provided'}
```

### Python Code
```python
{lp.python_code or 'Not provided'}
```

---

**Explanation:** {response.explanation}

**Assumptions:** {', '.join(response.assumptions) if response.assumptions else 'None'}

**Suggestions:** {', '.join(response.suggestions) if response.suggestions else 'None'}
"""
    if was_healed:
        msg = "⚠️ *Self-healing was applied to fix the LP format.*\n\n" + msg
    return msg


# ──────────────────────────────────────────────────────────────
# Flask Routes - Static Files
# ──────────────────────────────────────────────────────────────

@app.route("/")
def serve_index():
    return send_from_directory("public", "index.html")


@app.route("/health")
def health():
    return jsonify({"status": "up", "db_available": DB_AVAILABLE})


# ──────────────────────────────────────────────────────────────
# Flask Routes - Authentication
# ──────────────────────────────────────────────────────────────

@app.route("/api/auth", methods=["GET", "POST", "DELETE"])
def auth():
    if request.method == "GET":
        # Validate token
        user = get_current_user()
        if user:
            return jsonify({
                'authenticated': True,
                'user': {'id': user['user_id'], 'username': user['username']}
            })
        return jsonify({'error': 'Invalid or expired token'}), 401
    
    elif request.method == "POST":
        data = request.get_json(force=True)
        action = data.get('action', 'login')
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        if len(username) < 3:
            return jsonify({'error': 'Username must be at least 3 characters'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        if action == 'register':
            if DB_AVAILABLE:
                user = create_user(username, password)
            else:
                # Memory fallback
                if username in memory_users:
                    return jsonify({'error': 'Username already exists'}), 409
                user_id = len(memory_users) + 1
                memory_users[username] = {'ID': user_id, 'username': username, 'password': password}
                user = memory_users[username]
            
            if user:
                token = generate_token(user['ID'], user['username'])
                return jsonify({
                    'success': True,
                    'message': 'Account created',
                    'token': token,
                    'user': {'id': user['ID'], 'username': user['username']}
                })
            return jsonify({'error': 'Username already exists'}), 409
        
        else:  # login
            if DB_AVAILABLE:
                user = verify_user(username, password)
            else:
                # Memory fallback
                stored = memory_users.get(username)
                user = stored if stored and stored['password'] == password else None
            
            if user:
                token = generate_token(user['ID'], user['username'])
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'token': token,
                    'user': {'id': user['ID'], 'username': user['username']}
                })
            return jsonify({'error': 'Invalid username or password'}), 401
    
    else:  # DELETE - logout
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if token in memory_sessions:
                del memory_sessions[token]
        return jsonify({'success': True, 'message': 'Logged out'})


# ──────────────────────────────────────────────────────────────
# Flask Routes - Models
# ──────────────────────────────────────────────────────────────

@app.route("/api/models", methods=["GET"])
def get_models():
    return jsonify({"models": AVAILABLE_MODELS, "default": DEFAULT_MODEL})


@app.route("/api/user-models", methods=["GET", "POST"])
@app.route("/api/user-models/<int:model_id>", methods=["PUT", "DELETE"])
def user_models(model_id=None):
    user = get_current_user()
    
    if request.method == "GET":
        # Get providers without auth
        if request.args.get('providers'):
            return jsonify({'providers': PROVIDERS})
        
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        if DB_AVAILABLE:
            models = get_user_models(user['user_id'])
        else:
            models = []
        
        return jsonify({'models': models, 'providers': PROVIDERS})
    
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    if request.method == "POST":
        data = request.get_json(force=True)
        name = data.get('name', '').strip()
        api_key = data.get('api_key', '').strip()
        provider = data.get('provider', 'openai')
        base_url = data.get('base_url', '').strip() or None
        
        if not name or not api_key:
            return jsonify({'error': 'Name and API key are required'}), 400
        
        if provider not in PROVIDERS:
            return jsonify({'error': 'Invalid provider'}), 400
        
        if not base_url and provider != 'custom':
            base_url = PROVIDERS[provider]['base_url']
        
        if DB_AVAILABLE:
            model = create_user_model(user['user_id'], name, api_key, provider, base_url)
            return jsonify({'success': True, 'model': model})
        
        return jsonify({'error': 'Database not available'}), 500
    
    elif request.method == "PUT":
        data = request.get_json(force=True)
        if DB_AVAILABLE:
            model = update_user_model(
                model_id, user['user_id'],
                name=data.get('name'),
                api_key=data.get('api_key'),
                provider=data.get('provider'),
                base_url=data.get('base_url')
            )
            if model:
                return jsonify({'success': True, 'model': model})
        return jsonify({'error': 'Model not found'}), 404
    
    else:  # DELETE
        if DB_AVAILABLE and delete_user_model(model_id, user['user_id']):
            return jsonify({'success': True})
        return jsonify({'error': 'Model not found'}), 404


# ──────────────────────────────────────────────────────────────
# Flask Routes - Chats
# ──────────────────────────────────────────────────────────────

@app.route("/api/chats", methods=["GET", "POST"])
@app.route("/api/chats/<int:chat_id>", methods=["GET", "DELETE"])
def chats(chat_id=None):
    user = get_current_user()
    
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    if request.method == "GET":
        if chat_id:
            if DB_AVAILABLE:
                chat = get_chat(chat_id, user['user_id'])
                if chat:
                    messages = get_chat_messages(chat_id)
                    return jsonify({'chat': chat, 'messages': messages})
            return jsonify({'error': 'Chat not found'}), 404
        else:
            if DB_AVAILABLE:
                user_chats = get_user_chats(user['user_id'])
                return jsonify({'chats': user_chats})
            return jsonify({'chats': []})
    
    elif request.method == "POST":
        data = request.get_json(force=True)
        name = data.get('name', '').strip()
        original_prompt = data.get('original_prompt', '').strip()
        
        if not name:
            name = (original_prompt[:50] + '...') if len(original_prompt) > 50 else original_prompt or 'New Chat'
        
        if DB_AVAILABLE:
            chat = create_chat(user['user_id'], name, original_prompt)
            return jsonify({'success': True, 'chat': chat})
        
        return jsonify({'error': 'Database not available'}), 500
    
    else:  # DELETE
        if DB_AVAILABLE and delete_chat(chat_id, user['user_id']):
            return jsonify({'success': True})
        return jsonify({'error': 'Chat not found'}), 404


# ──────────────────────────────────────────────────────────────
# Flask Routes - Logs
# ──────────────────────────────────────────────────────────────

@app.route("/api/logs", methods=["GET"])
def logs():
    user = get_current_user()
    
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    chat_id = request.args.get('chat_id')
    limit = int(request.args.get('limit', 100))
    
    if DB_AVAILABLE:
        if chat_id:
            log_data = get_chat_logs(int(chat_id))
        else:
            log_data = get_user_logs(user['user_id'], limit)
        
        # Calculate summary
        total_tokens = sum(log.get('tokens_used', 0) or 0 for log in log_data)
        response_times = [log.get('response_time_ms', 0) for log in log_data if log.get('response_time_ms')]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        healed_count = sum(1 for log in log_data if log.get('was_healed'))
        
        return jsonify({
            'logs': log_data,
            'summary': {
                'total_requests': len(log_data),
                'total_tokens': total_tokens,
                'avg_response_time_ms': round(avg_response_time, 2),
                'healed_count': healed_count
            }
        })
    
    return jsonify({'logs': [], 'summary': {}})


# ──────────────────────────────────────────────────────────────
# Flask Routes - Chat (LP Generation)
# ──────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def chat():
    start_time = time.time()
    
    data = request.get_json(force=True)
    prompt = data.get("prompt", "").strip()
    model = data.get("model", DEFAULT_MODEL)
    history = data.get("history", [])
    chat_id = data.get("chat_id")
    custom_model_id = data.get("custom_model_id")
    
    if not prompt:
        return jsonify({"error": "Missing prompt"}), 400
    
    user = get_current_user()
    
    # Get custom API credentials
    api_key = None
    base_url = None
    
    if custom_model_id and user and DB_AVAILABLE:
        custom_model = get_user_model(custom_model_id, user['user_id'])
        if custom_model:
            api_key = custom_model.get('API-key')
            base_url = custom_model.get('base_url')
            model = custom_model.get('Name', model)
    
    # Validate model for default API
    if not api_key and model not in AVAILABLE_MODELS:
        model = DEFAULT_MODEL
    
    # Create chat if authenticated and no chat_id
    db_chat_id = chat_id
    if user and not chat_id and DB_AVAILABLE:
        try:
            chat_obj = create_chat(user['user_id'], prompt[:50] + '...' if len(prompt) > 50 else prompt, prompt)
            if chat_obj:
                db_chat_id = chat_obj['ID']
        except Exception:
            pass
    
    try:
        # Generate LP
        raw_data, raw_content, tokens_used = generate_lp(prompt, model, history, api_key, base_url)
        validated_response, was_healed = validate_and_heal(raw_data, raw_content, model, api_key, base_url)
        
        lp = validated_response.linear_program
        message = build_response_message(lp, validated_response, was_healed)
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Save to database if authenticated
        if user and db_chat_id and DB_AVAILABLE:
            try:
                order = get_next_message_order(db_chat_id)
                create_message(db_chat_id, prompt, order, 'user')
                
                order = get_next_message_order(db_chat_id)
                assistant_msg = create_message(db_chat_id, message, order, 'assistant')
                
                if assistant_msg:
                    log_content = json.dumps({
                        'request': {'prompt': prompt[:500], 'model': model},
                        'response': {'was_healed': was_healed}
                    })
                    create_log(
                        message_id=assistant_msg['ID'],
                        log=log_content,
                        model_used=model,
                        tokens_used=tokens_used,
                        response_time_ms=response_time_ms,
                        was_healed=was_healed
                    )
            except Exception as e:
                print(f"Database logging error: {e}")
        
        return jsonify({
            "message": message,
            "linear_program": validated_response.model_dump(),
            "was_healed": was_healed,
            "conversation_id": str(db_chat_id) if db_chat_id else str(uuid.uuid4()),
            "model_used": model,
            "response_time_ms": response_time_ms,
            "tokens_used": tokens_used
        })
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Initialize database on startup
    if DB_AVAILABLE:
        try:
            init_database()
            print("Database initialized successfully!")
        except Exception as e:
            print(f"Database initialization failed: {e}")
            DB_AVAILABLE = False
    
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting SignalMine LP Backend on port {port}")
    print(f"Database available: {DB_AVAILABLE}")
    print(f"Available models: {list(AVAILABLE_MODELS.keys())}")
    app.run(debug=True, port=port)
