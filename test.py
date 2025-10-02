from __future__ import annotations
import json
import os
from typing import List
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI

# --- Define the structured output you want ---
class AnswerCard(BaseModel):
    question: str
    answer: str
    reasoning: str
    sources: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

def main():
    user_question = input("Ask a question: ").strip()
    if not user_question:
        print("No question provided.")
        return

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    # Ask the model to respond as a JSON object
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},  # always returns a single JSON object
        messages=[
            {"role": "system", "content": (
                "You are a careful assistant. "
                "Return a single JSON object with keys: question, answer, reasoning, sources, confidence."
            )},
            {"role": "user", "content": f"Question: {user_question}"}
        ],
        temperature=0.2,
    )

    # Parse JSON → Pydantic
    raw = resp.choices[0].message.content
    try:
        data = json.loads(raw)
        card = AnswerCard.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        print("Failed to parse/validate JSON:", e)
        print("Raw model output:\n", raw)
        return

    # Use your validated object
    print("\n=== Parsed & Validated ===")
    print(card.model_dump_json(indent=2))

if __name__ == "__main__":
    main()