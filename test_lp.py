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
    solution_method: str = Field(description="Method used to solve (e.g., Simplex, Graphical, Interior Point)")
    optimal_solution: Dict[str, float] = Field(default_factory=dict, description="Variable values at optimum")
    optimal_value: Optional[float] = Field(default=None, description="Optimal objective function value")
    reasoning: str = Field(description="Step-by-step solution process")
    feasibility_status: str = Field(description="Feasible, Infeasible, or Unbounded")
    sources: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

def test_lp():
    print("Linear Programming Problem Solver")
    print("Example problems you can ask:")
    print("- Maximize 3x + 2y subject to x + y ≤ 4, 2x + y ≤ 6, x ≥ 0, y ≥ 0")
    print("- Minimize cost for production planning problem")
    print("- Diet problem with nutritional constraints")
    print("- Transportation problem optimization")
    print()
    
    user_question = input("Enter your linear programming problem: ").strip()
    if not user_question:
        print("No problem provided.")
        return

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    # Ask the model to solve the linear programming problem
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},  # always returns a single JSON object
        messages=[
            {"role": "system", "content": (
                "You are an expert in linear programming and optimization. "
                "Solve the given linear programming problem step by step. "
                "Return a single JSON object with keys: problem_statement, objective_function, "
                "constraints, solution_method, optimal_solution, optimal_value, reasoning, "
                "feasibility_status, sources, confidence. "
                "For optimal_solution, use variable names as keys and their optimal values as values. "
                "Show complete mathematical reasoning in the reasoning field."
            )},
            {"role": "user", "content": f"Linear Programming Problem: {user_question}"}
        ],
        temperature=0.1,  # Lower temperature for more consistent mathematical solutions
    )

    # Parse JSON → Pydantic
    raw = resp.choices[0].message.content
    try:
        data = json.loads(raw)
        solution = LinearProgramSolution.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        print("Failed to parse/validate JSON:", e)
        print("Raw model output:\n", raw)
        return

    # Display the solution in a formatted way
    print("\n" + "="*60)
    print("LINEAR PROGRAMMING SOLUTION")
    print("="*60)
    
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
    
    print("\n" + "="*60)
    print("RAW JSON OUTPUT:")
    print("="*60)
    print(solution.model_dump_json(indent=2))
