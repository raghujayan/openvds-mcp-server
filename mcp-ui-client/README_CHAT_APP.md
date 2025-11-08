# VDS Explorer Chat Application

**Production-Grade GUI for Seismic Data Exploration with Claude AI**

A complete chat application similar to Claude Desktop that enables natural language interaction with seismic data through the OpenVDS MCP Server.

---

## Overview

VDS Explorer Chat Application provides:

- 💬 **Claude Desktop-like Interface** - Professional chat UI with streaming responses
- 🔧 **MCP Tool Integration** - Claude can autonomously call seismic data tools
- 🖼️ **Inline Visualizations** - Seismic images display directly in chat
- ✅ **Data Validation** - Built-in integrity checking to prevent hallucinations
- 🤖 **Agent Support** - Monitor and manage autonomous extraction agents
- ⚡ **Real-time Updates** - Server-sent events for instant feedback

---

## Key Features

### Chat Interface
- Real-time streaming responses from Claude 3.5 Sonnet
- Message history with context awareness
- Tool call visualization (see what Claude is doing)
- Rich content rendering (text, images, tool results)
- Responsive design with Tailwind CSS

### Claude AI Integration
- Anthropic API with latest Claude models
- Tool use capability for MCP functions
- Multi-turn conversations with full context
- Automatic tool calling and result handling
- Error handling and retry logic

### MCP Tool Access
Claude can call any MCP tool:
- `search_surveys` - Find available seismic surveys
- `get_survey_info` - Get survey metadata and dimensions
- `extract_inline_image` - Extract and visualize inline sections
- `extract_crossline_image` - Extract crossline sections
- `extract_timeslice` - Extract time slices (map views)
- `validate_extracted_statistics` - Verify data integrity
- `verify_spatial_coordinates` - Check coordinate validity
- `check_statistical_consistency` - Validate mathematical consistency
- `agent_start_extraction` - Start autonomous data extraction
- `agent_get_status` - Check agent progress
- `agent_get_results` - Retrieve agent results

### Data Integrity
- All extracted values are verified against raw data
- Statistics are re-computed to prevent hallucinations
- SHA256 provenance tracking for data verification
- Automatic validation of claimed vs. actual values

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Browser (React UI)                      │
│  ┌────────────────────────────────────────────────────┐  │
│  │            ChatPage Component                       │  │
│  │  - Message display                                  │  │
│  │  - Input handling                                   │  │
│  │  - Streaming renderer                               │  │
│  │  - Tool call visualization                          │  │
│  └────────────────┬───────────────────────────────────┘  │
└───────────────────┼──────────────────────────────────────┘
                    │ HTTP REST + Server-Sent Events
┌───────────────────▼──────────────────────────────────────┐
│              FastAPI Backend (Python)                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │         Claude API Client                          │  │
│  │  - Streaming chat completions                      │  │
│  │  - Tool use coordination                           │  │
│  └─────────────┬──────────────────────────────────────┘  │
│                │                                          │
│  ┌─────────────▼──────────────────────────────────────┐  │
│  │      Tool Calling Orchestrator                     │  │
│  │  - Parse tool calls from Claude                    │  │
│  │  - Execute via MCP client                          │  │
│  │  - Return results to Claude                        │  │
│  │  - Handle multi-step sequences                     │  │
│  └─────────────┬──────────────────────────────────────┘  │
│                │                                          │
│  ┌─────────────▼──────────────────────────────────────┐  │
│  │         MCP Client Bridge                          │  │
│  │  - stdio communication                             │  │
│  │  - JSON-RPC protocol                               │  │
│  └─────────────┬──────────────────────────────────────┘  │
└────────────────┼─────────────────────────────────────────┘
                 │ JSON-RPC over stdin/stdout
┌────────────────▼─────────────────────────────────────────┐
│              OpenVDS MCP Server                          │
│  - VDS file access                                       │
│  - Data extraction                                       │
│  - Integrity validation                                  │
│  - Autonomous agents                                     │
└──────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Backend
- **FastAPI** - Modern async web framework
- **Anthropic SDK** - Claude API client with streaming
- **MCP SDK** - Model Context Protocol implementation
- **SSE-Starlette** - Server-sent events for streaming
- **Pydantic** - Data validation and serialization
- **Python 3.10+** - Async/await support

### Frontend
- **React 18** - UI framework with hooks
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **EventSource** - SSE client for streaming
- **React Query** - Data fetching (optional enhancement)

---

## Quick Start

See **[CHAT_APP_QUICKSTART.md](./CHAT_APP_QUICKSTART.md)** for detailed setup instructions.

**TL;DR:**
```bash
# 1. Setup environment (creates venv)
./setup_env.sh

# 2. Add your Anthropic API key to backend/.env
nano backend/.env  # Add: ANTHROPIC_API_KEY=sk-ant-...

# 3. Install dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt
cd ../frontend && npm install

# 4. Start backend (with venv activated)
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# 5. Start frontend (new terminal)
cd frontend && npm run dev

# 6. Open browser
# http://localhost:3000
```

---

## Usage Examples

### Example 1: Basic Data Extraction
```
User: Show me inline 55000 from the Sepia survey

Claude: [Uses search_surveys to find Sepia]
        [Uses extract_inline_image to get the data]

        Here's inline 55000 from the Sepia survey:

        [Displays seismic image inline]

        Statistics:
        - Max amplitude: 2487.3
        - Mean amplitude: 12.4
        - Standard deviation: 487.2
```

### Example 2: Multi-Step Analysis
```
User: Find the highest amplitude in Sepia and show me that location

Claude: [Uses search_surveys]
        [Uses get_survey_info to understand dimensions]
        [Uses agent_start_extraction to scan the volume]
        [Monitors agent progress]
        [Uses agent_get_results to find max location]
        [Uses extract_inline_image at max location]

        I found the highest amplitude at inline 54523,
        crossline 8287 with amplitude 2134.6

        [Shows seismic image at that location]
```

### Example 3: Data Validation
```
User: Verify the statistics for inline 55000 in Sepia

Claude: [Uses validate_extracted_statistics]

        The statistics are verified:
        - ✓ Max amplitude: 2487.3 (validated)
        - ✓ Mean amplitude: 12.4 (validated)
        - ✓ All values mathematically consistent
        - ✓ SHA256 hash: a3f2e1...
```

---

## API Reference

### Chat Endpoints

#### POST /api/chat/message
Send a chat message and get streaming response.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Show me inline 55000 from Sepia"}
  ],
  "stream": true,
  "use_tools": true,
  "system": "Optional system prompt"
}
```

**Response:** Server-Sent Events stream
```
event: claude_event
data: {"type": "content_block_delta", "delta_type": "text", "text": "I'll extract..."}

event: tool_call
data: {"id": "toolu_123", "name": "extract_inline_image", "input": {...}}

event: tool_result
data: {"id": "toolu_123", "success": true, "preview": "..."}

event: done
data: {"message": "Stream complete"}
```

#### GET /api/chat/health
Check Claude API status.

**Response:**
```json
{
  "status": "healthy",
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 4096
}
```

### Existing API Endpoints

All existing REST endpoints remain available:
- Survey operations: `/api/surveys/*`
- Data extraction: `/api/extract/*`
- Validation: `/api/validate/*`
- Agents: `/api/agents/*`

See http://localhost:8000/docs for full API documentation.

---

## Configuration

### Environment Variables

**Backend (`backend/.env`):**
```bash
ANTHROPIC_API_KEY=sk-ant-...           # Required: Your API key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
MCP_SERVER_PATH=/path/to/openvds_mcp_server.py
MCP_SERVER_ARGS=
CORS_ORIGINS=http://localhost:3000
MAX_CONVERSATION_LENGTH=50
STREAMING_ENABLED=true
LOG_LEVEL=INFO
```

**Frontend (`frontend/.env`):**
```bash
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=VDS Explorer
VITE_ENABLE_STREAMING=true
```

---

## File Structure

```
mcp-ui-client/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── mcp_client.py        # MCP bridge
│   │   ├── claude_client.py     # Claude API client
│   │   ├── api/
│   │   │   └── chat.py          # Chat endpoints
│   │   └── models/
│   │       └── chat.py          # Data models
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.tsx             # Entry point
│   │   ├── App.tsx              # Root component
│   │   ├── pages/
│   │   │   └── ChatPage.tsx     # Chat UI
│   │   ├── services/
│   │   │   └── chatService.ts   # API client
│   │   └── types/
│   │       └── chat.ts          # TypeScript types
│   └── package.json
├── docker-compose.yml
├── setup_env.sh
├── CHAT_APP_QUICKSTART.md       # Quick start guide
├── CLAUDE_DESKTOP_ARCHITECTURE.md  # Architecture details
└── README_CHAT_APP.md           # This file
```

---

## Development

### Backend Development
```bash
cd backend

# Activate virtual environment
source venv/bin/activate

# Run with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests (if implemented)
pytest

# Type checking
mypy app/
```

### Frontend Development
```bash
cd frontend

# Start dev server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type checking
npm run type-check
```

### Docker Development
```bash
# Build and start all services
docker-compose up --build

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart a service
docker-compose restart backend

# Stop all services
docker-compose down
```

---

## Production Deployment

### Option 1: Docker Deployment
```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d

# Scale if needed
docker-compose scale backend=3
```

### Option 2: Cloud Deployment
- **Backend:** Deploy to AWS/GCP/Azure using FastAPI container
- **Frontend:** Deploy to Vercel/Netlify from `frontend/dist`
- **Environment:** Use secret management for API keys
- **Database:** Add PostgreSQL for conversation persistence (optional)

---

## Security Considerations

1. **API Key Management**
   - Never commit `.env` files
   - Use environment variables in production
   - Rotate keys regularly

2. **CORS Configuration**
   - Update `CORS_ORIGINS` for production domains
   - Never use `allow_origins=["*"]` in production

3. **Rate Limiting**
   - Add rate limiting middleware
   - Implement per-user quotas
   - Monitor API usage

4. **Data Privacy**
   - Conversations stored locally by default
   - Add encryption for sensitive data
   - Implement user authentication if sharing

---

## Troubleshooting

See **[CHAT_APP_QUICKSTART.md](./CHAT_APP_QUICKSTART.md#troubleshooting)** for detailed troubleshooting steps.

Common issues:
- API key not set → Check `backend/.env`
- MCP connection failed → Verify `MCP_SERVER_PATH`
- Streaming not working → Check CORS and SSE support
- TypeScript errors → Run `npm install` and restart dev server

---

## Contributing

To add new features:

1. **Backend:** Add endpoints in `backend/app/api/`
2. **Frontend:** Add components in `frontend/src/components/`
3. **Types:** Update `frontend/src/types/chat.ts`
4. **Docs:** Update this README

---

## Resources

- **Anthropic API Docs:** https://docs.anthropic.com/
- **MCP Protocol:** https://modelcontextprotocol.io/
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **React Docs:** https://react.dev/

---

## License

[Your License Here]

---

## Support

For issues or questions:
1. Check the [troubleshooting guide](./CHAT_APP_QUICKSTART.md#troubleshooting)
2. Review API docs at http://localhost:8000/docs
3. Check browser console for errors (F12)
4. Review backend logs

---

**Built with ❤️ for seismic data exploration**

Ready to start? See **[CHAT_APP_QUICKSTART.md](./CHAT_APP_QUICKSTART.md)**
