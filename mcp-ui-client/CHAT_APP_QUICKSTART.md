# VDS Explorer Chat Application - Quick Start Guide

🎉 **Claude Desktop-like Chat Interface for Seismic Data Exploration**

This guide will help you get the complete VDS Explorer chat application running with Claude AI integration.

---

## What's Been Built

✅ **Backend (Python/FastAPI):**
- Claude API integration with streaming responses
- MCP tool calling orchestration
- Chat API endpoints with Server-Sent Events (SSE)
- Tool execution and result handling

✅ **Frontend (React/TypeScript):**
- Chat interface similar to Claude Desktop
- Real-time streaming responses
- Tool call visualization
- Seismic image display
- Message history

---

## Prerequisites

1. **Anthropic API Key** - Get from https://console.anthropic.com/
2. **Python 3.10+** installed
3. **Node.js 18+** and npm installed
4. **Docker** (optional, for containerized deployment)

---

## Quick Start (5 Minutes)

### Step 1: Environment Setup

Run the setup script:

```bash
cd /Users/raghu/code/openvds-mcp-server/mcp-ui-client
./setup_env.sh
```

This creates:
- `backend/.env` - Backend configuration
- `frontend/.env` - Frontend configuration

### Step 2: Add Your Anthropic API Key

Edit `backend/.env` and add your API key:

```bash
# Open in your editor
nano backend/.env

# Or use sed to replace
sed -i '' 's/your-api-key-here/sk-ant-YOUR-ACTUAL-KEY/' backend/.env
```

**IMPORTANT:** Replace `sk-ant-YOUR-ACTUAL-KEY` with your actual Anthropic API key!

### Step 3: Install Dependencies

**Backend (with virtual environment):**
```bash
cd backend

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Frontend:**
```bash
cd ../frontend
npm install
```

### Step 4: Start the Application

**Option A: Development Mode (Recommended)**

Terminal 1 - Backend:
```bash
cd backend

# Activate virtual environment (if not already activated)
source venv/bin/activate

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

**Option B: Docker (Production-like)**
```bash
# From mcp-ui-client directory
docker-compose up --build
```

### Step 5: Open the Application

Open your browser to:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000/docs

---

## Usage

### Basic Chat

Try these example queries:

1. **List Surveys:**
   ```
   What surveys are available?
   ```

2. **Extract Seismic Data:**
   ```
   Show me inline 55000 from the Sepia survey
   ```

3. **Multi-step Analysis:**
   ```
   Find the highest amplitude in the Sepia survey and show me that section
   ```

4. **Data Validation:**
   ```
   Validate the statistics for inline 55000 in Sepia
   ```

### Features You'll See

- 🔄 **Real-time streaming** - Claude's responses appear as they're generated
- 🔧 **Tool calling** - Watch Claude use MCP tools to access seismic data
- 🖼️ **Inline images** - Seismic visualizations display directly in chat
- ✅ **Tool results** - See results from data extraction and validation
- 💬 **Message history** - Full conversation context maintained

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  Browser (http://localhost:3000)            │
│  - React Chat Interface                     │
│  - Streaming SSE Client                     │
└─────────────┬───────────────────────────────┘
              │ HTTP + SSE
┌─────────────▼───────────────────────────────┐
│  FastAPI Backend (http://localhost:8000)    │
│  - Claude API Client                        │
│  - Tool Calling Orchestrator                │
│  - MCP Client Bridge                        │
└─────────────┬───────────────────────────────┘
              │ JSON-RPC (stdio)
┌─────────────▼───────────────────────────────┐
│  OpenVDS MCP Server                         │
│  - VDS Data Access                          │
│  - Data Integrity Validation                │
│  - Autonomous Agents                        │
└─────────────────────────────────────────────┘
```

---

## API Endpoints

### Chat Endpoints

- `POST /api/chat/message` - Send message, get streaming response
- `GET /api/chat/health` - Check Claude API status

### Existing Endpoints (Still Available)

- `POST /api/surveys/search` - Search surveys
- `GET /api/surveys/{id}` - Get survey details
- `POST /api/extract/inline` - Extract inline section
- `POST /api/validate/statistics` - Validate data
- `POST /api/agents/start` - Start autonomous agent

---

## Configuration

### Backend Environment Variables

Edit `backend/.env`:

```bash
# Anthropic API (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# MCP Server Path (update if needed)
MCP_SERVER_PATH=/app/openvds-mcp-server/src/openvds_mcp_server.py
MCP_SERVER_ARGS=

# CORS (allow frontend origins)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Application Settings
MAX_CONVERSATION_LENGTH=50
STREAMING_ENABLED=true
LOG_LEVEL=INFO
```

### Frontend Environment Variables

Edit `frontend/.env`:

```bash
# API URL (must match backend)
VITE_API_URL=http://localhost:8000

# App Configuration
VITE_APP_NAME=VDS Explorer
VITE_ENABLE_STREAMING=true
```

---

## Troubleshooting

### Backend Issues

**Problem: "ANTHROPIC_API_KEY must be set"**
```bash
# Check backend/.env exists and has your key
cat backend/.env | grep ANTHROPIC_API_KEY

# If missing, add it:
echo "ANTHROPIC_API_KEY=sk-ant-YOUR-KEY" >> backend/.env
```

**Problem: "MCP client connection failed"**
```bash
# Check MCP server path in backend/.env
# Update if your MCP server is in a different location
MCP_SERVER_PATH=/path/to/your/openvds_mcp_server.py
```

**Problem: "Module not found" errors**
```bash
# Reinstall dependencies in virtual environment
cd backend
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

### Frontend Issues

**Problem: "Cannot connect to backend"**
```bash
# Check frontend/.env has correct API URL
cat frontend/.env | grep VITE_API_URL

# Should be: VITE_API_URL=http://localhost:8000

# Restart frontend dev server
npm run dev
```

**Problem: TypeScript errors**
```bash
# Clear cache and rebuild
rm -rf node_modules dist
npm install
npm run dev
```

**Problem: Streaming not working**
```bash
# Check browser console for errors
# Verify backend is streaming SSE events:
curl -N http://localhost:8000/api/chat/health
```

### Docker Issues

**Problem: Container won't start**
```bash
# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

**Problem: Environment variables not loaded**
```bash
# Make sure .env files exist
ls -la backend/.env frontend/.env

# Pass env vars to docker-compose
docker-compose --env-file backend/.env up
```

---

## Development Workflow

### Making Backend Changes

1. Ensure virtual environment is activated: `source backend/venv/bin/activate`
2. Edit Python files in `backend/app/`
3. Backend auto-reloads (if using `--reload` flag)
4. Test in browser or with curl

### Making Frontend Changes

1. Edit React files in `frontend/src/`
2. Vite hot-reloads automatically
3. See changes instantly in browser

### Testing Tool Calling

1. Open browser console (F12)
2. Send a message that requires tools
3. Watch SSE events in Network tab
4. See tool execution in UI

---

## File Structure

```
mcp-ui-client/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app with all endpoints
│   │   ├── mcp_client.py        # MCP bridge (existing)
│   │   ├── claude_client.py     # NEW: Claude API client
│   │   ├── api/
│   │   │   ├── __init__.py      # NEW: API package
│   │   │   └── chat.py          # NEW: Chat endpoints
│   │   └── models/
│   │       └── chat.py          # NEW: Chat data models
│   ├── requirements.txt         # Updated with Claude deps
│   ├── .env.example
│   └── .env                     # Your config (create from example)
├── frontend/
│   ├── src/
│   │   ├── main.tsx             # NEW: Entry point
│   │   ├── App.tsx              # NEW: Root component
│   │   ├── pages/
│   │   │   └── ChatPage.tsx     # NEW: Main chat interface
│   │   ├── services/
│   │   │   └── chatService.ts   # NEW: API client
│   │   ├── types/
│   │   │   └── chat.ts          # NEW: TypeScript types
│   │   └── index.css            # NEW: Global styles
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── .env.example
│   └── .env                     # Your config (create from example)
├── setup_env.sh                 # NEW: Environment setup script
└── CHAT_APP_QUICKSTART.md       # This file
```

---

## Next Steps

### Phase 1: Basic Usage ✅ (You are here!)
- Chat with Claude
- Extract seismic data
- View visualizations
- Validate data

### Phase 2: Advanced Features (Optional)
- Conversation persistence (save/load chats)
- Agent monitoring dashboard
- Data comparison tools
- Export functionality
- Settings panel
- Dark mode

### Phase 3: Production Deployment (Optional)
- Deploy backend to cloud (AWS/GCP/Azure)
- Deploy frontend to Vercel/Netlify
- Add authentication
- Set up monitoring
- Configure CDN

---

## Resources

- **API Documentation:** http://localhost:8000/docs
- **Architecture Details:** See `CLAUDE_DESKTOP_ARCHITECTURE.md`
- **Complete Implementation:** See `COMPLETE_IMPLEMENTATION_GUIDE.md`
- **Anthropic Docs:** https://docs.anthropic.com/

---

## Success Checklist

- [ ] Backend running on http://localhost:8000
- [ ] Frontend running on http://localhost:3000
- [ ] Anthropic API key configured
- [ ] MCP server connected
- [ ] Can send messages and get responses
- [ ] Can see Claude using tools
- [ ] Seismic images display in chat
- [ ] Streaming responses work

---

**🎉 You're ready to explore seismic data with Claude AI!**

Open http://localhost:3000 and start chatting!

For help, see the troubleshooting section above or check the logs:
- Backend: Terminal running uvicorn
- Frontend: Browser console (F12)
- Docker: `docker-compose logs -f`
