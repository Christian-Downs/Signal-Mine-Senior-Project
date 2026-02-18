"""
SignalMine Test Client
- Function to send chat messages to the Flask backend API
- Can be used for testing the LP generation pipeline
"""

from __future__ import annotations
import json
import os
from typing import List, Dict, Optional
import requests
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI


# ─────────────────────────────────────────────────────────────
# Pydantic Models (matching backend)
# ─────────────────────────────────────────────────────────────

class LinearProgram(BaseModel):
    """Validated Linear Program structure"""
    problem_description: str
    objective_type: str
    objective_function: str
    decision_variables: List[str]
    constraints: List[str]
    variable_bounds: Dict[str, str] = {}
    latex_formulation: Optional[str] = None
    python_code: Optional[str] = None


class LPResponse(BaseModel):
    """Full response from LP agent"""
    linear_program: LinearProgram
    explanation: str
    assumptions: List[str] = []
    suggestions: List[str] = []


class AnswerCard(BaseModel):
    """Generic answer structure"""
    question: str
    answer: str
    reasoning: str
    sources: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


# ─────────────────────────────────────────────────────────────
# API Chat Function
# ─────────────────────────────────────────────────────────────

def chat(
    message: str,
    base_url: str = "http://localhost:5000",
    model: str = "gpt-4o-mini",
    conversation_id: Optional[str] = None,
    token: Optional[str] = None
) -> dict:
    """
    Send a chat message to the SignalMine Flask backend.
    
    Args:
        message: The prompt/message to send
        base_url: Backend URL (default: http://localhost:5000)
        model: Model to use (gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo)
        conversation_id: Optional conversation ID for multi-turn chat
        token: Optional bearer token for authentication
    
    Returns:
        dict with keys: message, linear_program, was_healed, conversation_id, model_used
        or dict with key: error
    """
    endpoint = f"{base_url.rstrip('/')}/api/chat"
    
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    payload = {
        "prompt": message,
        "model": model,
    }
    if conversation_id:
        payload["conversation_id"] = conversation_id
    
    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=120)
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {endpoint}. Is the Flask server running?"}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out"}
    except Exception as e:
        return {"error": str(e)}


def get_available_models(base_url: str = "http://localhost:5000") -> dict:
    """Get list of available models from the backend."""
    endpoint = f"{base_url.rstrip('/')}/api/models"
    try:
        response = requests.get(endpoint, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# Interactive CLI
# ─────────────────────────────────────────────────────────────

def interactive_chat():
    """Interactive chat session with the LP backend."""
    print("=" * 60)
    print("SignalMine LP Chat - Interactive Mode")
    print("=" * 60)
    print("Commands: /models, /clear, /quit")
    print("=" * 60)
    
    base_url = os.environ.get("BACKEND_URL", "http://localhost:5000")
    conversation_id = None
    model = "gpt-4o-mini"
    
    # Check connection
    models_resp = get_available_models(base_url)
    if "error" in models_resp:
        print(f"\n⚠️  Warning: {models_resp['error']}")
        print("Make sure to start the Flask server with: python frontend.py\n")
    else:
        print(f"\nConnected to: {base_url}")
        print(f"Available models: {', '.join(models_resp['models'].keys())}")
        print(f"Using model: {model}\n")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        
        if not user_input:
            continue
        
        # Handle commands
        if user_input.lower() == "/quit":
            print("Goodbye!")
            break
        elif user_input.lower() == "/clear":
            conversation_id = None
            print("Conversation cleared.")
            continue
        elif user_input.lower() == "/models":
            resp = get_available_models(base_url)
            if "error" in resp:
                print(f"Error: {resp['error']}")
            else:
                print("Available models:")
                for mid, name in resp["models"].items():
                    marker = " (current)" if mid == model else ""
                    print(f"  - {mid}: {name}{marker}")
            continue
        elif user_input.lower().startswith("/model "):
            new_model = user_input[7:].strip()
            model = new_model
            print(f"Switched to model: {model}")
            continue
        
        # Send message
        print("\nAssistant: ", end="", flush=True)
        
        response = chat(
            message=user_input,
            base_url=base_url,
            model=model,
            conversation_id=conversation_id
        )
        
        if "error" in response:
            print(f"❌ Error: {response['error']}")
        else:
            conversation_id = response.get("conversation_id")
            was_healed = response.get("was_healed", False)
            
            if was_healed:
                print("⚠️ [Self-healing applied]\n")
            
            # Print the message (simplified for terminal)
            message = response.get("message", "No response")
            # Strip markdown for cleaner terminal output
            print(message)
            
            # Show LP details if available
            lp_data = response.get("linear_program")
            if lp_data:
                lp = lp_data.get("linear_program", {})
                print("\n" + "-" * 40)
                print("LP SUMMARY:")
                print(f"  Objective: {lp.get('objective_type', 'N/A')} {lp.get('objective_function', 'N/A')}")
                print(f"  Variables: {', '.join(lp.get('decision_variables', []))}")
                print(f"  Constraints: {len(lp.get('constraints', []))} total")


def main():
    """Legacy main function for backward compatibility."""
    user_question = input("Ask a question: ").strip()
    if not user_question:
        print("No question provided.")
        return

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": (
                "You are a careful assistant. "
                "Return a single JSON object with keys: question, answer, reasoning, sources, confidence."
            )},
            {"role": "user", "content": f"Question: {user_question}"}
        ],
        temperature=0.2,
    )

    raw = resp.choices[0].message.content
    try:
        data = json.loads(raw)
        card = AnswerCard.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        print("Failed to parse/validate JSON:", e)
        print("Raw model output:\n", raw)
        return

    print("\n=== Parsed & Validated ===")
    print(card.model_dump_json(indent=2))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_chat()
    else:
        # Default to interactive chat now
        interactive_chat()