# AI Collaboration for Linear Programming

This program enables OpenAI (GPT-4) and Google Gemini to communicate and collaborate with each other to solve linear programming problems through structured conversation.

## Features

- **Collaborative Problem Solving**: Two AI models work together through multiple rounds of discussion
- **Structured Approach**:
  1. OpenAI formulates the problem
  2. Gemini proposes a solution approach
  3. OpenAI computes the solution
  4. Gemini verifies the solution
  5. OpenAI provides final summary
- **Conversation Logging**: Track the complete dialogue between the AIs
- **JSON Export**: Save conversations for later analysis

## Setup

### Prerequisites

You need API keys for both OpenAI and Google Gemini:

1. **OpenAI API Key**: Get from [platform.openai.com](https://platform.openai.com)
2. **Google Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY = "your-openai-api-key"
$env:GOOGLE_API_KEY = "your-gemini-api-key"
```

**Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=your-openai-api-key
set GOOGLE_API_KEY=your-gemini-api-key
```

**Linux/Mac:**
```bash
export OPENAI_API_KEY="your-openai-api-key"
export GOOGLE_API_KEY="your-gemini-api-key"
```

## Usage

Run the program:
```bash
python ai_collaboration_lp.py
```

### Example Problems

1. **Maximization Problem**:
   ```
   Maximize 3x + 2y subject to x + y ≤ 4, 2x + y ≤ 6, x ≥ 0, y ≥ 0
   ```

2. **Minimization Problem**:
   ```
   Minimize 2x + 3y subject to x + y ≥ 5, 2x + y ≥ 8, x ≥ 0, y ≥ 0
   ```

3. **Complex Problem**:
   ```
   Maximize 5x + 4y subject to x + y ≤ 5, 10x + 6y ≤ 45, x ≥ 0, y ≥ 0
   ```

## How It Works

The program orchestrates a conversation between two AI models:

1. **OpenAI (GPT-4-mini)** starts by analyzing and formulating the problem
2. **Gemini** reviews the formulation and proposes a solution method
3. **OpenAI** implements the solution with detailed calculations
4. **Gemini** verifies the solution and checks for errors
5. **OpenAI** provides a final summary addressing any issues

Each AI has access to the conversation history, allowing for true collaboration.

## Output

The program displays:
- Real-time conversation between the AIs
- Problem formulation and constraints
- Solution methodology
- Step-by-step calculations
- Verification results
- Final optimal solution

You can optionally:
- View the complete conversation log
- Save the conversation to a JSON file

## Code Structure

- `AICollaborationLP`: Main class managing the collaboration
- `ask_openai()`: Interface to OpenAI API
- `ask_gemini()`: Interface to Google Gemini API
- `solve_lp_collaboratively()`: Orchestrates the 5-round conversation
- `save_conversation()`: Exports conversation to JSON

## Notes

- The program uses temperature=0.3 for more consistent mathematical reasoning
- Conversation context is limited to the last 5 messages to manage token usage
- Both models are prompted to be thorough but concise
- The verification phase helps catch calculation errors

## Troubleshooting

**Error: API key not set**
- Make sure you've set the environment variables correctly
- Restart your terminal after setting environment variables

**Rate limit errors**
- Add delays between API calls if needed
- Consider upgrading your API plan

**Inconsistent results**
- The models may occasionally disagree or make errors
- Run multiple times to compare results
- Use the verification phase to catch issues

## License

This is a demonstration project for educational purposes.
