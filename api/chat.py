"""
Vercel Serverless Function: /api/chat
Handles LP generation with Pydantic validation and self-healing
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import uuid
from typing import List, Dict, Optional

from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI

import psycopg
from dotenv import load_dotenv


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

def get_openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)


def generate_lp(prompt: str, model: str, history: List[dict]) -> tuple:
    client = get_openai_client()
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
    return json.loads(raw_content), raw_content


def fix_lp(broken_json: str, error_message: str, model: str) -> dict:
    client = get_openai_client()
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


def validate_and_heal(raw_data: dict, raw_content: str, model: str) -> tuple:
    try:
        validated = LPResponse.model_validate(raw_data)
        return validated, False
    except ValidationError as e:
        fixed_data = fix_lp(raw_content, str(e), model)
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


def create_neon_cursor() -> psycopg.Cursor:

    load_dotenv()
    conn_string = os.getenv("DATABASE_URL")
    try:
        with psycopg.connect(conn_string) as conn:
            print("Connection established")
            # Open a cursor to perform database operations
            with conn.cursor() as cur:
                print("Cursor created")
                return cur
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise



# ──────────────────────────────────────────────────────────────
# Vercel Handler
# ──────────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            cursor = create_neon_cursor()
            print("Database cursor created successfully")
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            prompt = data.get("prompt", "").strip()
            model = data.get("model", DEFAULT_MODEL)
            history = data.get("history", [])
            
            if not prompt:
                self._send_json({"error": "Missing prompt"}, 400)
                return
            
            if model not in AVAILABLE_MODELS:
                model = DEFAULT_MODEL
            
            # Generate LP
            raw_data, raw_content = generate_lp(prompt, model, history)
            validated_response, was_healed = validate_and_heal(raw_data, raw_content, model)
            
            lp = validated_response.linear_program
            message = build_response_message(lp, validated_response, was_healed)
            
            self._send_json({
                "message": message,
                "linear_program": validated_response.model_dump(),
                "was_healed": was_healed,
                "conversation_id": str(uuid.uuid4()),
                "model_used": model
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

