# SignalMine – Self-Healing LP Chat

A multi-agent system that converts natural language optimization problems into validated Linear Programs using Pydantic AI agents with self-healing capabilities.

## Features

- 🤖 **Pydantic AI Agents** - Generate Linear Programs from natural language
- 🔧 **Self-Healing** - If LP validation fails, a fixer agent automatically corrects it
- 🎨 **ChatGPT-style UI** - Clean HTML/CSS/JS frontend
- 🔄 **Model Selection** - Switch between GPT-4o, GPT-4o-mini, GPT-4-turbo, GPT-3.5-turbo
- 📝 **LaTeX & Python Output** - Get mathematical formulations and working code
- ☁️ **Vercel Ready** - Deploy to Vercel with serverless functions

---

## Deploy to Vercel (Recommended)

### 1. Push to GitHub
```bash
git add .
git commit -m "Add Vercel support"
git push
```

### 2. Deploy on Vercel
1. Go to [vercel.com](https://vercel.com) and import your GitHub repo
2. Add environment variable:
   - Name: `OPENAI_API_KEY`
   - Value: `sk-your-key-here`
3. Click **Deploy**

That's it! Your app will be live at `https://your-project.vercel.app`

---

## Local Development

### 1. Clone the repository
```bash
git clone https://github.com/Christian-Downs/Signal-Mine-Senior-Project
cd Signal-Mine-Senior-Project
```

### 2. Set up environment variables
```bash
cp .env.example .env
```
Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-key-here
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Flask backend
```bash
python frontend.py
```

### 5. Open in browser
Navigate to [http://localhost:5000](http://localhost:5000)

---

## Project Structure

```
├── api/                  # Vercel serverless functions
│   ├── chat.py          # Main chat endpoint
│   ├── models.py        # Available models
│   └── health.py        # Health check
├── public/              # Static frontend files
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── frontend.py          # Flask backend (local dev)
├── vercel.json          # Vercel configuration
└── requirements.txt
```

---

## Using the API from Python

```python
from test import chat

# Send a message to the LP chatbot
response = chat("Maximize 3x + 2y subject to x + y <= 4")

print(response["message"])  # Formatted LP output
print(response["linear_program"])  # Structured LP data
print(response["was_healed"])  # True if self-healing was applied
```

## Interactive CLI Mode

```bash
python test.py
```

Commands:
- `/models` - List available models
- `/model gpt-4o` - Switch model
- `/clear` - Clear conversation
- `/quit` - Exit

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│  Vercel/Flask   │────▶│  OpenAI API     │
│  (HTML/JS/CSS)  │     │   API Routes    │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                        ┌────────▼────────┐
                        │  Pydantic       │
                        │  Validation     │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │  Self-Healing   │
                        │  Fixer Agent    │
                        └─────────────────┘
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve frontend |
| `/api/chat` | POST | Send LP prompt |
| `/api/models` | GET | List available models |
| `/api/conversations/<id>` | DELETE | Clear conversation |
| `/health` | GET | Health check |