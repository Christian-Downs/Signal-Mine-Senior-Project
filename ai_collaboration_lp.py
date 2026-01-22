"""
AI Collaboration for Linear Programming
This program allows OpenAI and Gemini to communicate with each other to solve linear programming problems.
"""

import os
import json
from typing import List, Dict, Optional
from openai import OpenAI
import google.generativeai as genai


class AICollaborationLP:
    """Manages collaboration between OpenAI and Gemini to solve LP problems."""
    
    def __init__(self):
        # Initialize OpenAI client
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.openai_client = OpenAI(api_key=self.openai_key)
        
        # Initialize Gemini client (using free tier model)
        self.gemini_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not self.gemini_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable is not set")
        genai.configure(api_key=self.gemini_key)
        # Using gemini-pro which is available on the free tier
        self.gemini_model = genai.GenerativeModel('gemini-3-flash-preview')
        
        # Conversation history
        self.conversation_history: List[Dict[str, str]] = []
        
    def add_to_history(self, speaker: str, message: str):
        """Add a message to the conversation history."""
        self.conversation_history.append({
            "speaker": speaker,
            "message": message
        })
        
    def get_conversation_context(self) -> str:
        """Get formatted conversation history."""
        context = "Previous conversation:\n"
        for entry in self.conversation_history[-5:]:  # Last 5 messages for context
            context += f"{entry['speaker']}: {entry['message']}\n\n"
        return context
    
    def ask_openai(self, prompt: str, role: str = "solver") -> str:
        """Query OpenAI with the given prompt."""
        system_prompts = {
            "solver": (
                "You are an expert in linear programming and optimization. "
                "You are collaborating with another AI (Gemini) to solve linear programming problems. "
                "Engage in a collaborative discussion, propose solutions, verify calculations, "
                "and work together to find the optimal solution. Be thorough but concise."
            ),
            "verifier": (
                "You are an expert in linear programming verification. "
                "You are collaborating with another AI (Gemini) to verify linear programming solutions. "
                "Carefully check the solution, identify any errors, and suggest improvements. "
                "Be constructive and specific in your feedback."
            )
        }
        
        context = self.get_conversation_context()
        full_prompt = f"{context}\nCurrent task: {prompt}"
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompts.get(role, system_prompts["solver"])},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        return response.choices[0].message.content.strip()
    
    def ask_gemini(self, prompt: str, role: str = "solver") -> str:
        """Query Gemini with the given prompt."""
        system_prompts = {
            "solver": (
                "You are an expert in linear programming and optimization. "
                "You are collaborating with another AI (OpenAI) to solve linear programming problems. "
                "Engage in a collaborative discussion, propose solutions, verify calculations, "
                "and work together to find the optimal solution. Be thorough but concise."
            ),
            "verifier": (
                "You are an expert in linear programming verification. "
                "You are collaborating with another AI (OpenAI) to verify linear programming solutions. "
                "Carefully check the solution, identify any errors, and suggest improvements. "
                "Be constructive and specific in your feedback."
            )
        }
        
        context = self.get_conversation_context()
        full_prompt = (
            f"{system_prompts.get(role, system_prompts['solver'])}\n\n"
            f"{context}\n"
            f"Current task: {prompt}"
        )
        
        response = self.gemini_model.generate_content(full_prompt)
        return response.text.strip()
    
    def solve_lp_collaboratively(self, problem: str, max_iterations: int = 5) -> Dict:
        """
        Have OpenAI and Gemini collaborate to solve a linear programming problem.
        
        Args:
            problem: The linear programming problem statement
            max_iterations: Maximum number of conversation rounds
            
        Returns:
            Dictionary containing the solution and conversation log
        """
        print("=" * 80)
        print("AI COLLABORATION: Linear Programming Problem Solver")
        print("=" * 80)
        print(f"\nProblem: {problem}\n")
        print("=" * 80)
        
        # Phase 1: Initial problem formulation by OpenAI
        print("\n[Round 1] OpenAI - Problem Formulation")
        print("-" * 80)
        openai_formulation = self.ask_openai(
            f"Analyze this linear programming problem and provide a clear formulation "
            f"including the objective function and constraints: {problem}",
            role="solver"
        )
        print(openai_formulation)
        self.add_to_history("OpenAI", openai_formulation)
        
        # Phase 2: Gemini reviews and proposes solution approach
        print("\n[Round 2] Gemini - Solution Approach")
        print("-" * 80)
        gemini_approach = self.ask_gemini(
            f"Review the problem formulation from OpenAI and propose a solution approach. "
            f"What method should we use to solve this problem?",
            role="solver"
        )
        print(gemini_approach)
        self.add_to_history("Gemini", gemini_approach)
        
        # Phase 3: OpenAI solves using the proposed approach
        print("\n[Round 3] OpenAI - Solution Computation")
        print("-" * 80)
        openai_solution = self.ask_openai(
            f"Based on Gemini's approach, compute the actual solution. "
            f"Show all steps and calculations. Provide the optimal values for all variables "
            f"and the optimal objective function value.",
            role="solver"
        )
        print(openai_solution)
        self.add_to_history("OpenAI", openai_solution)
        
        # Phase 4: Gemini verifies the solution
        print("\n[Round 4] Gemini - Solution Verification")
        print("-" * 80)
        gemini_verification = self.ask_gemini(
            f"Verify the solution provided by OpenAI. Check if all constraints are satisfied "
            f"and if the objective function value is correctly calculated. "
            f"Point out any errors or confirm correctness.",
            role="verifier"
        )
        print(gemini_verification)
        self.add_to_history("Gemini", gemini_verification)
        
        # Phase 5: OpenAI provides final summary
        print("\n[Round 5] OpenAI - Final Summary")
        print("-" * 80)
        openai_final = self.ask_openai(
            f"Provide a final summary of the solution. If Gemini found any issues, "
            f"address them. Give the final answer in a clear, structured format.",
            role="verifier"
        )
        print(openai_final)
        self.add_to_history("OpenAI", openai_final)
        
        print("\n" + "=" * 80)
        print("COLLABORATION COMPLETE")
        print("=" * 80)
        
        return {
            "problem": problem,
            "conversation": self.conversation_history,
            "final_summary": openai_final
        }
    
    def print_conversation_log(self):
        """Print the complete conversation log."""
        print("\n" + "=" * 80)
        print("COMPLETE CONVERSATION LOG")
        print("=" * 80)
        for i, entry in enumerate(self.conversation_history, 1):
            print(f"\n[Message {i}] {entry['speaker']}:")
            print("-" * 80)
            print(entry['message'])
    
    def save_conversation(self, filename: str = "lp_collaboration_log.json"):
        """Save the conversation to a JSON file."""
        result = {
            "conversation": self.conversation_history,
            "total_messages": len(self.conversation_history)
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nConversation saved to {filename}")


def main():
    """Main function to run the AI collaboration."""
    print("AI Collaboration for Linear Programming")
    print("This program uses OpenAI and Gemini to collaboratively solve LP problems.\n")
    
    # Check for API keys
    try:
        collaborator = AICollaborationLP()
    except ValueError as e:
        print(f"Error: {e}")
        print("\nPlease set the following environment variables:")
        print("  - OPENAI_API_KEY")
        print("  - GOOGLE_API_KEY or GEMINI_API_KEY")
        return
    
    # Example problems
    print("Example Linear Programming Problems:")
    print("1. Maximize 3x + 2y subject to x + y ≤ 4, 2x + y ≤ 6, x ≥ 0, y ≥ 0")
    print("2. Minimize 2x + 3y subject to x + y ≥ 5, 2x + y ≥ 8, x ≥ 0, y ≥ 0")
    print("3. Maximize 5x + 4y subject to x + y ≤ 5, 10x + 6y ≤ 45, x ≥ 0, y ≥ 0")
    print()
    
    # Get problem from user
    problem = input("Enter your linear programming problem (or press Enter for example 1): ").strip()
    if not problem:
        problem = "Maximize 3x + 2y subject to x + y ≤ 4, 2x + y ≤ 6, x ≥ 0, y ≥ 0"
        print(f"Using example problem: {problem}\n")
    
    # Solve collaboratively
    try:
        result = collaborator.solve_lp_collaboratively(problem)
        
        # Ask if user wants to see full conversation log
        print("\n")
        show_log = input("Show complete conversation log? (y/n): ").strip().lower()
        if show_log == 'y':
            collaborator.print_conversation_log()
        
        # Ask if user wants to save the conversation
        save = input("\nSave conversation to file? (y/n): ").strip().lower()
        if save == 'y':
            filename = input("Enter filename (default: lp_collaboration_log.json): ").strip()
            if not filename:
                filename = "lp_collaboration_log.json"
            collaborator.save_conversation(filename)
            
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
