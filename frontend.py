"""
SignalMine Flask Backend
- Pydantic AI agents for Linear Program generation
- Self-healing: if LP validation fails, a fixer agent corrects it
"""

from __future__ import annotations
import json
import os
import uuid
from typing import List, Dict, Optional

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI

load_dotenv()

app = Flask(__name__, static_folder=".", static_url_path="")
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
    latex_formulation: Optional[str] = Field(
        default=None,
        description="LaTeX formatted LP formulation"
    )
    python_code: Optional[str] = Field(
        default=None,
        description="Python code using scipy or PuLP to solve this LP"
    )


class LPResponse(BaseModel):
    """Full response from LP agent"""
    linear_program: LinearProgram
    explanation: str = Field(description="Explanation of the formulation")
    assumptions: List[str] = Field(default_factory=list, description="Assumptions made")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")


# ──────────────────────────────────────────────────────────────
# Conversation Storage (in-memory for demo)
# ──────────────────────────────────────────────────────────────

conversations: Dict[str, List[dict]] = {}

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

# ──────────────────────────────────────────────────────────────
# System Prompts
# ──────────────────────────────────────────────────────────────

LP_GENERATOR_SYSTEM_PROMPT = """You are an expert in linear programming and mathematical optimization.

Your task is to convert natural language descriptions of scheduling, assignment, or optimization problems into formal Linear Programs.

You MUST respond with a single JSON object with EXACTLY this structure:
{
  "linear_program": {
    "problem_description": "string - natural language summary",
    "objective_type": "maximize" or "minimize",
    "objective_function": "string - e.g., '3x + 2y'",
    "decision_variables": ["x", "y", ...],
    "constraints": ["x + y <= 10", "2x + 3y <= 20", ...],
    "variable_bounds": {"x": ">= 0", "y": ">= 0"},
    "latex_formulation": "LaTeX string for the complete LP formulation",
    "python_code": "Python code using scipy.optimize.linprog or PuLP to solve"
  },
  "explanation": "string - explain how you formulated this",
  "assumptions": ["assumption 1", ...],
  "suggestions": ["suggestion 1", ...]
}

Rules:
- Use standard LP notation
- Include ALL constraints explicitly
- Provide working Python code
- Make reasonable assumptions and list them
- Do NOT include text outside the JSON"""

LP_FIXER_SYSTEM_PROMPT = """You are an expert at fixing malformed Linear Program JSON structures.

You will receive a JSON object that failed validation. Your job is to fix it to match this EXACT structure:
{
  "linear_program": {
    "problem_description": "string",
    "objective_type": "maximize" or "minimize",
    "objective_function": "string",
    "decision_variables": ["array", "of", "strings"],
    "constraints": ["array", "of", "constraint strings"],
    "variable_bounds": {"var": "bound expression"},
    "latex_formulation": "string or null",
    "python_code": "string or null"
  },
  "explanation": "string",
  "assumptions": ["array of strings"],
  "suggestions": ["array of strings"]
}

Fix any issues:
- Missing fields: add with sensible defaults
- Wrong types: convert to correct types
- Malformed JSON: fix syntax
- Return ONLY valid JSON, no other text"""

# ──────────────────────────────────────────────────────────────
# AI Agent Functions
# ──────────────────────────────────────────────────────────────

def get_openai_client() -> OpenAI:
    """Get OpenAI client with API key from environment"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return OpenAI(api_key=api_key)


def generate_lp(prompt: str, model: str, conversation_history: List[dict]) -> tuple:
    """
    Generate a Linear Program from natural language.
    Returns (parsed_data, raw_content) tuple.
    """
    client = get_openai_client()
    
    messages = [{"role": "system", "content": LP_GENERATOR_SYSTEM_PROMPT}]
    messages.extend(conversation_history)
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
    """
    Attempt to fix a malformed LP JSON using the fixer agent.
    """
    client = get_openai_client()
    
    fix_prompt = f"""The following JSON failed validation with this error:
{error_message}

Broken JSON:
{broken_json}

Please fix it and return ONLY valid JSON matching the required schema."""
    
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": LP_FIXER_SYSTEM_PROMPT},
            {"role": "user", "content": fix_prompt}
        ],
        temperature=0.1,
    )
    
    return json.loads(response.choices[0].message.content)


def validate_and_heal(raw_data: dict, raw_content: str, model: str) -> tuple:
    """
    Validate LP response. If invalid, attempt self-healing with fixer agent.
    Returns (validated_response, was_healed)
    """
    was_healed = False
    
    try:
        validated = LPResponse.model_validate(raw_data)
        return validated, was_healed
    except ValidationError as e:
        # Self-healing: send to fixer agent
        error_msg = str(e)
        print(f"[SELF-HEAL] Validation failed, attempting fix: {error_msg[:200]}")
        
        try:
            fixed_data = fix_lp(raw_content, error_msg, model)
            validated = LPResponse.model_validate(fixed_data)
            was_healed = True
            print("[SELF-HEAL] Fix successful!")
            return validated, was_healed
        except Exception as fix_error:
            print(f"[SELF-HEAL] Fix failed: {fix_error}")
            raise ValueError(f"LP validation failed and self-healing unsuccessful: {error_msg}")


# ──────────────────────────────────────────────────────────────
# Flask Routes
# ──────────────────────────────────────────────────────────────

@app.route("/")
def serve_index():
    """Serve the main HTML page"""
    return send_from_directory(".", "index.html")


@app.route("/api/models", methods=["GET"])
def get_models():
    """Return available models for the frontend dropdown"""
    return jsonify({
        "models": AVAILABLE_MODELS,
        "default": DEFAULT_MODEL
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint.
    Accepts: { prompt, model?, conversation_id? }
    Returns: { message, linear_program?, was_healed, conversation_id }
    """
    data = request.get_json(force=True)
    prompt = data.get("prompt", "").strip()
    model = data.get("model", DEFAULT_MODEL)
    conversation_id = data.get("conversation_id")
    
    if not prompt:
        return jsonify({"error": "Missing prompt"}), 400
    
    if model not in AVAILABLE_MODELS:
        model = DEFAULT_MODEL
    
    # Get or create conversation
    if not conversation_id or conversation_id not in conversations:
        conversation_id = str(uuid.uuid4())
        conversations[conversation_id] = []
    
    history = conversations[conversation_id]
    
    try:
        # Generate LP
        raw_data, raw_content = generate_lp(prompt, model, history)
        
        # Validate with self-healing
        validated_response, was_healed = validate_and_heal(raw_data, raw_content, model)
        
        # Update conversation history
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": validated_response.model_dump_json()})
        
        # Build response
        lp = validated_response.linear_program
        
        response_message = f"""## Linear Program Formulation

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

**Explanation:** {validated_response.explanation}

**Assumptions:** {', '.join(validated_response.assumptions) if validated_response.assumptions else 'None'}

**Suggestions:** {', '.join(validated_response.suggestions) if validated_response.suggestions else 'None'}
"""
        
        if was_healed:
            response_message = "⚠️ *Self-healing was applied to fix the LP format.*\n\n" + response_message
        
        return jsonify({
            "message": response_message,
            "linear_program": validated_response.model_dump(),
            "was_healed": was_healed,
            "conversation_id": conversation_id,
            "model_used": model
        })
        
    except ValueError as e:
        return jsonify({
            "error": str(e),
            "conversation_id": conversation_id
        }), 422
    except Exception as e:
        return jsonify({
            "error": f"Server error: {str(e)}",
            "conversation_id": conversation_id
        }), 500


@app.route("/api/conversations/<conv_id>", methods=["DELETE"])
def delete_conversation(conv_id):
    """Clear a conversation"""
    if conv_id in conversations:
        del conversations[conv_id]
    return jsonify({"ok": True})


@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({"status": "up"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting SignalMine LP Backend on port {port}")
    print(f"Available models: {list(AVAILABLE_MODELS.keys())}")
    app.run(debug=True, port=port)
