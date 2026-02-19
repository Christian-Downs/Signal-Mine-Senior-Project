# SignalMine – Self-Healing LP Chat

A multi-agent system that converts natural language optimization problems into validated Linear Programs using Pydantic AI agents with self-healing capabilities.

## Features

- 🤖 **Pydantic AI Agents** - Generate Linear Programs from natural language
- 🔧 **Self-Healing** - If LP validation fails, a fixer agent automatically corrects it
- 🎨 **ChatGPT-style UI** - Clean HTML/CSS/JS frontend with Bootstrap modals
- 🔄 **Model Selection** - Switch between GPT-4o, GPT-4o-mini, GPT-4-turbo, GPT-3.5-turbo
- 📝 **LaTeX & Python Output** - Get mathematical formulations and working code
- 🔐 **User Authentication** - Register/login with persistent sessions
- 💬 **Chat History** - Save and load previous conversations
- 🔑 **Custom API Keys** - Add your own API keys for OpenAI, Anthropic, Google, Groq, and more
- 📊 **Usage Logging** - Track model communication, tokens used, and response times
- 🗄️ **PostgreSQL Database** - Neon PostgreSQL for data persistence
- ☁️ **Vercel Ready** - Deploy to Vercel with serverless functions

---

## Database Schema (ERD)

The application uses PostgreSQL with the following tables:

- **Users** - User accounts (ID, username, password)
- **Chat** - Chat conversations (ID, userId, Name, originalPrompt, lastMessageId)
- **Messages** - Chat messages (ID, chatID, message, order, origin)
- **Models** - User's custom API keys (ID, userId, Name, API-key, provider, base_url)
- **Logs** - Model communication logs (ID, messageId, log, model_used, tokens_used, response_time_ms, was_healed)

---

## Deploy to Vercel

### 1. Push to GitHub
```bash
git add .
git commit -m "Add database and auth support"
git push
```

### 2. Set up Vercel Environment Variables
Add these environment variables in Vercel dashboard:
```
OPENAI_API_KEY=sk-your-key-here
PGHOST=your-neon-host.neon.tech
PGDATABASE=neondb
PGUSER=neondb_owner
PGPASSWORD=your-password
PGSSLMODE=require
SECRET_KEY=your-secret-key
```

### 3. Deploy on Vercel
1. Go to [vercel.com](https://vercel.com) and import your GitHub repo
2. Add the environment variables above
3. Click **Deploy**

---

## Local Development

### 1. Clone the repository
```bash
git clone https://github.com/Christian-Downs/Signal-Mine-Senior-Project
cd Signal-Mine-Senior-Project
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
Create a `.env` file:
```env
# OpenAI API Key
OPENAI_API_KEY=sk-your-key-here

# Database (Neon PostgreSQL)
PGHOST=ep-solitary-math-aijp7w88-pooler.c-4.us-east-1.aws.neon.tech
PGDATABASE=neondb
PGUSER=neondb_owner
PGPASSWORD=your-password
PGSSLMODE=require

# Session Secret
SECRET_KEY=your-secret-key
```

### 4. Initialize the database
```bash
python init_db.py
```

### 5. Run the server
```bash
python main.py
```

Open http://localhost:5000 in your browser.

---

## API Endpoints

### Authentication
- `POST /api/auth` - Login or register (`action: 'login'` or `'register'`)
- `GET /api/auth` - Validate token and get user info
- `DELETE /api/auth` - Logout

### Chat
- `POST /api/chat` - Generate LP from prompt
- `GET /api/chats` - Get user's chat history
- `GET /api/chats/:id` - Get specific chat with messages
- `POST /api/chats` - Create new chat
- `DELETE /api/chats/:id` - Delete chat

### Models
- `GET /api/models` - Get available default models
- `GET /api/user-models` - Get user's custom models
- `POST /api/user-models` - Add custom model/API key
- `PUT /api/user-models/:id` - Update custom model
- `DELETE /api/user-models/:id` - Delete custom model

### Logs
- `GET /api/logs` - Get user's usage logs with summary

---

## Custom API Keys

Users can add their own API keys for various providers:

| Provider | Base URL |
|----------|----------|
| OpenAI | https://api.openai.com/v1 |
| Anthropic | https://api.anthropic.com/v1 |
| Google AI | https://generativelanguage.googleapis.com/v1beta |
| Groq | https://api.groq.com/openai/v1 |
| Together AI | https://api.together.xyz/v1 |
| Custom | User-provided |

---

## Project Structure

```
Signal-Mine-Senior-Project/
├── api/
│   ├── auth.py         # Authentication API
│   ├── chat.py         # LP generation API
│   ├── chats.py        # Chat management API
│   ├── database.py     # Database connection & models
│   ├── health.py       # Health check API
│   ├── logs.py         # Usage logs API
│   ├── models.py       # Available models API
│   ├── user_models.py  # Custom API keys API
│   └── requirements.txt
├── public/
│   ├── app.js          # Frontend JavaScript
│   ├── index.html      # Main HTML page
│   └── styles.css      # Styles
├── .env                # Environment variables
├── frontend.py         # Flask server (local development)
├── init_db.py          # Database initialization script
├── main.py             # Main entry point
├── requirements.txt    # Python dependencies
└── vercel.json         # Vercel configuration
```

---

## License

MIT
