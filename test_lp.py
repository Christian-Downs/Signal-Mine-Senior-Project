from __future__ import annotations

import json
import os
from typing import List, Dict, Optional

from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI


# --- Define the structured output for linear programming problems ---
class LinearProgramSolution(BaseModel):
    problem_statement: str
    objective_function: str
    constraints: List[str]
    solution_method: str = Field(
        description="Method used to solve (e.g., Simplex, Graphical, Interior Point)"
    )
    optimal_solution: Dict[str, float] = Field(
        default_factory=dict,
        description="Variable values at optimum (keys are variable names, values are floats)",
    )
    optimal_value: Optional[float] = Field(
        default=None,
        description="Optimal objective function value (float or null if infeasible/unbounded)",
    )
    reasoning: str = Field(description="Step-by-step solution process")
    feasibility_status: str = Field(
        description='Feasible, Infeasible, or Unbounded (use exactly one of these words)'
    )
    sources: List[str] = Field(
        default_factory=list,
        description="List of reference titles/links used to solve or check the problem",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Model confidence between 0 and 1",
    )


def test_lp() -> None:
    print("Linear Programming Problem Solver")
    print("Example problems you can ask:")
    print("- Maximize 3x + 2y subject to x + y ≤ 4, 2x + y ≤ 6, x ≥ 0, y ≥ 0")

    user_question = input("Enter your linear programming problem: ").strip()
    if not user_question:
        print("No problem provided.")
        return

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.")
        return

    client = OpenAI(api_key=api_key)

    # Ask the model to solve the linear programming problem
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},  # always returns a single JSON object
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert in linear programming and optimization.\n\n"
                    "You MUST respond with a single JSON object ONLY, with EXACTLY the following keys and types:\n"
                    "{\n"
                    '  "problem_statement": string,\n'
                    '  "objective_function": string,\n'
                    '  "constraints": array of strings,\n'
                    '  "solution_method": string,\n'
                    '  "optimal_solution": object mapping variable name (string) -> numeric value (float),\n'
                    '  "optimal_value": number or null,\n'
                    '  "reasoning": string,\n'
                    '  "feasibility_status": string (one of "Feasible", "Infeasible", "Unbounded"),\n'
                    '  "sources": array of strings,\n'
                    '  "confidence": number between 0 and 1\n'
                    "}\n\n"
                    "Important formatting rules:\n"
                    "- Do NOT wrap the JSON in backticks.\n"
                    "- Do NOT include any text before or after the JSON.\n"
                    "- All numeric values must be valid JSON numbers, not strings.\n"
                    "- Make sure constraints is a JSON array of strings, not a single string.\n"
                    "- Make sure sources is a JSON array of strings.\n\n"
                    "Solve the given linear programming problem step by step and encode the full solution "
                    "in the JSON fields. Show complete mathematical reasoning in the 'reasoning' field."
                ),
            },
            {
                "role": "user",
                "content": f"Linear Programming Problem: {user_question}",
            },
        ],
        temperature=0.1,  # Lower temperature for more consistent mathematical solutions
    )

    # Parse JSON → Pydantic
    raw = resp.choices[0].message.content

    # Uncomment this if you want to always see what the model actually returned:
    # print("\n--- RAW MODEL OUTPUT ---\n", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print("Failed to decode JSON from model output:")
        print(e)
        print("\nRaw model output:\n", raw)
        return

    try:
        solution = LinearProgramSolution.model_validate(data)
    except ValidationError as e:
        print("JSON decoded, but failed to validate against LinearProgramSolution schema:")
        print(e)
        print("\nDecoded JSON object:\n", json.dumps(data, indent=2))
        return

    # Display the solution in a formatted way
    print("\n" + "=" * 60)
    print("LINEAR PROGRAMMING SOLUTION")
    print("=" * 60)

    print(f"\nPROBLEM: {solution.problem_statement}")
    print(f"\nOBJECTIVE: {solution.objective_function}")

    print("\nCONSTRAINTS:")
    for i, constraint in enumerate(solution.constraints, 1):
        print(f"  {i}. {constraint}")

    print(f"\nSOLUTION METHOD: {solution.solution_method}")
    print(f"FEASIBILITY: {solution.feasibility_status}")

    if solution.optimal_solution:
        print("\nOPTIMAL SOLUTION:")
        for var, value in solution.optimal_solution.items():
            print(f"  {var} = {value}")

    if solution.optimal_value is not None:
        print(f"\nOPTIMAL VALUE: {solution.optimal_value}")

    print(f"\nREASONING:\n{solution.reasoning}")

    if solution.sources:
        print("\nSOURCES:")
        for source in solution.sources:
            print(f"  - {source}")

    print(f"\nCONFIDENCE: {solution.confidence:.2%}")

    print("\n" + "=" * 60)
    print("RAW JSON OUTPUT (re-serialized from validated model):")
    print("=" * 60)
    print(solution.model_dump_json(indent=2))


if __name__ == "__main__":
    test_lp()