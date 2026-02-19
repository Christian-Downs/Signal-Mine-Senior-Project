"""
Vercel Serverless Function: /api/chat
Handles LP generation with Pydantic validation and self-healing
Supports database logging and custom user models
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import uuid
import time
from typing import List, Dict, Optional

from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI

# Import database functions
try:
    from api.database import (
        create_chat, create_message, create_log, 
        get_chat_messages, get_next_message_order, get_user_model
    )
    from api.auth import validate_token
except ImportError:
    try:
        from database import (
            create_chat, create_message, create_log, 
            get_chat_messages, get_next_message_order, get_user_model
        )
        from auth import validate_token
    except ImportError:
        # Fallback for when DB is not available
        def create_chat(*args, **kwargs): return None
        def create_message(*args, **kwargs): return None
        def create_log(*args, **kwargs): return None
        def get_chat_messages(*args, **kwargs): return []
        def get_next_message_order(*args, **kwargs): return 1
        def get_user_model(*args, **kwargs): return None
        def validate_token(*args, **kwargs): return None


# ──────────────────────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────────────────────

class LinearProgram(BaseModel):
    problem_description: str = Field(description="Natural language description")
    objective_type: str = Field(description="'maximize' or 'minimize'")
    objective_function: str = Field(description="e.g., '3x + 2y'")
    decision_variables: List[str] = Field(description="Variable names")
    constraints: List[str] = Field(description="Constraint expressions")
    variable_bounds: Dict[str, str] = Field(default_factory=dict)
    latex_formulation: Optional[str] = Field(default=None)
    python_code: Optional[str] = Field(default=None)


class LPResponse(BaseModel):
    linear_program: LinearProgram
    explanation: str
    assumptions: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────

AVAILABLE_MODELS = {
    "gpt-4o": "GPT-4o (Best quality)",
    "gpt-4o-mini": "GPT-4o Mini (Fast & cheap)",
    "gpt-4-turbo": "GPT-4 Turbo",
    "gpt-3.5-turbo": "GPT-3.5 Turbo (Fastest)",
}

DEFAULT_MODEL = "gpt-4o-mini"

LP_GENERATOR_SYSTEM_PROMPT = """You are an expert in linear programming and mathematical optimization.

Convert natural language descriptions into formal Linear Programs.

Respond with a single JSON object with EXACTLY this structure:
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
    """Get OpenAI client with optional custom API key"""
    if api_key is None:
        api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    
    kwargs = {'api_key': api_key}
    if base_url:
        kwargs['base_url'] = base_url
    
    return OpenAI(**kwargs)


def get_auth_user(headers):
    """Extract and validate user from Authorization header"""
    auth_header = headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:]
    return validate_token(token)


def generate_lp(prompt: str, model: str, history: List[dict], api_key: str = None, base_url: str = None) -> tuple:
    """Generate LP with optional custom API credentials"""
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
    """Fix malformed LP JSON with optional custom API credentials"""
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
    """Validate and optionally heal the LP response"""
    try:
        validated = LPResponse.model_validate(raw_data)
        return validated, False
    except ValidationError as e:
        fixed_data = fix_lp(raw_content, str(e), model, api_key, base_url)
        validated = LPResponse.model_validate(fixed_data)
        return validated, True


def build_response_message(lp: LinearProgram, response: LPResponse, was_healed: bool) -> str:
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
# Vercel Handler
# ──────────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_POST(self):
        try:
            start_time = time.time()
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            prompt = data.get("prompt", "").strip()
            model = data.get("model", DEFAULT_MODEL)
            history = data.get("history", [])
            chat_id = data.get("chat_id")  # Optional: for persistent chats
            custom_model_id = data.get("custom_model_id")  # Optional: for user's custom model
            
            # Convert chat_id to integer if it's a numeric string
            if chat_id:
                try:
                    chat_id = int(chat_id)
                except (ValueError, TypeError):
                    chat_id = None
            
            if not prompt:
                self._send_json({"error": "Missing prompt"}, 400)
                return
            
            # Get authenticated user (optional)
            user = get_auth_user(self.headers)
            
            # Get custom API credentials if using user's model
            api_key = None
            base_url = None
            
            if custom_model_id and user:
                custom_model = get_user_model(custom_model_id, user['user_id'])
                if custom_model:
                    api_key = custom_model.get('API-key')
                    base_url = custom_model.get('base_url')
                    model = custom_model.get('Name', model)
            
            # Validate model for default API
            if not api_key and model not in AVAILABLE_MODELS:
                model = DEFAULT_MODEL
            
            # Create chat if user is authenticated and no chat_id provided
            db_chat_id = chat_id
            if user and not chat_id:
                try:
                    # Use the user's first message as the chat title
                    chat_title = prompt[:100] + '...' if len(prompt) > 100 else prompt
                    chat = create_chat(user['user_id'], chat_title, prompt)
                    if chat:
                        db_chat_id = chat['ID']
                        print(f"Created new chat {db_chat_id} for user {user['user_id']}: {chat_title}")
                except Exception as e:
                    import traceback
                    print(f"Chat creation error: {e}")
                    traceback.print_exc()
            
            # Generate LP
            raw_data, raw_content, tokens_used = generate_lp(prompt, model, history, api_key, base_url)
            validated_response, was_healed = validate_and_heal(raw_data, raw_content, model, api_key, base_url)
            
            lp = validated_response.linear_program
            message = build_response_message(lp, validated_response, was_healed)
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Save messages and create log if user is authenticated
            user_message_id = None
            assistant_message_id = None
            
            if user and db_chat_id:
                try:
                    # Save user message
                    order = get_next_message_order(db_chat_id)
                    user_msg = create_message(db_chat_id, prompt, order, 'user')
                    if user_msg:
                        user_message_id = user_msg['ID']
                    
                    # Save assistant message
                    order = get_next_message_order(db_chat_id)
                    assistant_msg = create_message(db_chat_id, message, order, 'assistant')
                    if assistant_msg:
                        assistant_message_id = assistant_msg['ID']
                        
                        # Create log entry for model communication
                        log_content = json.dumps({
                            'request': {
                                'prompt': prompt,
                                'model': model,
                                'history_length': len(history)
                            },
                            'response': {
                                'raw': raw_content[:1000] + '...' if len(raw_content) > 1000 else raw_content,
                                'was_healed': was_healed
                            }
                        })
                        
                        create_log(
                            message_id=assistant_message_id,
                            log=log_content,
                            model_used=model,
                            tokens_used=tokens_used,
                            response_time_ms=response_time_ms,
                            was_healed=was_healed
                        )
                except Exception as e:
                    print(f"Database logging error: {e}")  # Log but don't fail
            
            self._send_json({
                "message": message,
                "linear_program": validated_response.model_dump(),
                "was_healed": was_healed,
                "conversation_id": db_chat_id if db_chat_id else None,
                "model_used": model,
                "response_time_ms": response_time_ms,
                "tokens_used": tokens_used
            })
            
        except ValueError as e:
            self._send_json({"error": str(e)}, 422)
        except Exception as e:
            self._send_json({"error": f"Server error: {str(e)}"}, 500)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
