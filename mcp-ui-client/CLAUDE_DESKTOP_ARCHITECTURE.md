# VDS Explorer - Production GUI Application Architecture

## Overview

Build a production-grade GUI application similar to Claude Desktop that:
- Provides a chat interface with Claude AI
- Integrates with OpenVDS MCP server for seismic data access
- Enables Claude to call MCP tools (data extraction, validation, agents)
- Displays seismic visualizations inline in chat
- Manages autonomous agents
- Provides real-time updates

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Browser (React + TypeScript)                      │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │              Chat Interface (Claude Desktop-like)               │ │
│  │  - Message history                                              │ │
│  │  - Claude AI responses                                          │ │
│  │  - Inline seismic images                                        │ │
│  │  - Tool call visualizations                                     │ │
│  │  - Agent status widgets                                         │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    UI Components                                │ │
│  │  - Survey Browser  - Data Viewer  - Agent Dashboard            │ │
│  └────────────────────────────────────────────────────────────────┘ │
└────────────────────┬──────────────────────────────────────────────┘
                     │ HTTP REST API + Server-Sent Events (SSE)
┌────────────────────▼──────────────────────────────────────────────┐
│              FastAPI Backend (Python)                              │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │           Claude API Integration                              │ │
│  │  - Chat completions                                           │ │
│  │  - Tool use (MCP tools)                                       │ │
│  │  - Streaming responses                                        │ │
│  │  - Conversation history                                       │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │           Tool Calling Orchestrator                           │ │
│  │  - Receives tool calls from Claude                            │ │
│  │  - Routes to MCP client                                       │ │
│  │  - Returns results to Claude                                  │ │
│  │  - Handles multi-step tool sequences                          │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │           MCP Client Bridge (Existing)                        │ │
│  │  - stdio communication                                        │ │
│  │  - All VDS operations                                         │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────┬────────────────────────────────────────────────┘
                     │ JSON-RPC (stdio)
┌────────────────────▼────────────────────────────────────────────────┐
│              OpenVDS MCP Server                                      │
│  - VDS Data Access  - Data Integrity  - Autonomous Agents           │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Chat Interface
- **Claude Desktop-like UI** - Professional chat interface
- **Streaming responses** - Real-time text generation
- **Message history** - Persistent conversation
- **Rich content** - Inline images, tables, formatted text
- **Tool call visibility** - Show when Claude uses tools
- **Regenerate** - Re-run responses
- **Copy/export** - Save conversations

### 2. Claude AI Integration
- **Anthropic API** - Claude 3.5 Sonnet
- **Tool use** - Claude can call MCP tools
- **Context awareness** - Remembers conversation
- **Multi-turn** - Complex multi-step tasks
- **Error handling** - Graceful failures

### 3. MCP Tool Access
Claude can call any MCP tool:
- Search surveys
- Extract seismic data
- Validate statistics
- Start/manage agents
- Verify coordinates
- Check data quality

### 4. Seismic Visualization
- **Inline images** - Show seismic sections in chat
- **Interactive viewer** - Pan, zoom, adjust colormap
- **Metadata display** - Statistics, coordinates
- **Comparison** - Side-by-side views
- **Export** - Download images

### 5. Agent Monitoring
- **Status dashboard** - Real-time agent progress
- **Results viewer** - Browse completed extractions
- **Control panel** - Pause/resume/cancel
- **Notifications** - Agent completion alerts

## Technology Stack

### Backend (Python)
```
- FastAPI              # Web framework
- Anthropic SDK        # Claude API
- MCP SDK              # MCP protocol
- Server-Sent Events   # Streaming responses
- WebSocket            # Real-time updates
- SQLite               # Conversation storage
```

### Frontend (React + TypeScript)
```
- React 18             # UI framework
- TypeScript           # Type safety
- Tailwind CSS         # Styling
- React Query          # Data fetching
- Zustand              # State management
- React Markdown       # Message formatting
- EventSource          # SSE client
- Recharts             # Data visualization
```

## User Workflows

### Workflow 1: Basic Chat with Data Access
```
User: "Show me inline 55000 from the Sepia survey"

Claude: [Uses extract_inline_image tool]
        "Here's inline 55000 from Sepia:

        [Seismic image displayed inline]

        Statistics:
        - Max amplitude: 2487.3
        - Mean amplitude: 12.4
        - Standard deviation: 487.2"
```

### Workflow 2: Multi-Step Analysis
```
User: "Find the highest amplitude anomaly in Sepia"

Claude: 1. [Uses search_surveys to confirm Sepia exists]
        2. [Uses get_survey_info to understand dimensions]
        3. [Uses agent_start_extraction to scan volume]
        4. [Shows agent progress widget]
        5. [Uses agent_get_results to find max location]
        6. [Uses extract_inline_image at max location]

        "I found the highest amplitude at inline 54523,
         crossline 8287 with amplitude 2134.6

         [Shows inline image at that location]"
```

### Workflow 3: Data Quality Check
```
User: "Is this data good quality?"

Claude: [Uses validate_statistics on current section]
        [Uses check_consistency on reported stats]

        "The data quality looks excellent:
        - ✓ All statistics are consistent
        - ✓ No dead traces
        - ✓ Good SNR
        - ✓ Clear reflectors visible"
```

## Implementation Plan

### Phase 1: Backend Enhancement (Week 1)
**Files to create/modify:**
- `backend/app/claude_client.py` - Anthropic API integration
- `backend/app/chat.py` - Chat endpoint with tool calling
- `backend/app/models/chat.py` - Chat data models
- `backend/app/database.py` - SQLite for conversations
- Update `backend/requirements.txt` - Add anthropic SDK

**Features:**
- Claude API integration
- Tool calling orchestration
- Streaming responses (SSE)
- Conversation persistence

### Phase 2: Complete React Frontend (Week 2)
**Files to create:**
- `frontend/src/main.tsx` - App entry point
- `frontend/src/App.tsx` - Root component
- `frontend/src/pages/ChatPage.tsx` - Main chat interface
- `frontend/src/components/Chat/` - Chat components
  - `MessageList.tsx`
  - `MessageInput.tsx`
  - `Message.tsx`
  - `ToolCallDisplay.tsx`
  - `SeismicImageDisplay.tsx`
- `frontend/src/services/chatService.ts` - Chat API client
- `frontend/src/store/chatStore.ts` - Chat state management

**Features:**
- Complete chat UI
- Message rendering
- Tool call visualization
- Image display
- Streaming support

### Phase 3: Advanced Features (Week 3)
**Features:**
- Agent monitoring dashboard
- Data comparison tools
- Export functionality
- Settings panel
- Keyboard shortcuts
- Dark mode

### Phase 4: Production Polish (Week 4)
**Features:**
- Error boundaries
- Loading states
- Offline support
- Performance optimization
- Comprehensive testing
- Documentation

## File Structure

```
mcp-ui-client/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app (existing)
│   │   ├── mcp_client.py              # MCP bridge (existing)
│   │   ├── claude_client.py           # NEW: Claude API client
│   │   ├── chat.py                    # NEW: Chat endpoints
│   │   ├── database.py                # NEW: SQLite for chats
│   │   └── models/
│   │       ├── chat.py                # NEW: Chat models
│   │       └── tools.py               # NEW: Tool definitions
│   └── requirements.txt               # Updated
├── frontend/
│   ├── src/
│   │   ├── main.tsx                   # NEW: Entry point
│   │   ├── App.tsx                    # NEW: Root component
│   │   ├── pages/
│   │   │   └── ChatPage.tsx           # NEW: Main chat UI
│   │   ├── components/
│   │   │   ├── Chat/                  # NEW: Chat components
│   │   │   │   ├── MessageList.tsx
│   │   │   │   ├── MessageInput.tsx
│   │   │   │   ├── Message.tsx
│   │   │   │   ├── ToolCallDisplay.tsx
│   │   │   │   └── SeismicImageDisplay.tsx
│   │   │   ├── Layout/                # NEW: Layout components
│   │   │   │   ├── Header.tsx
│   │   │   │   └── Sidebar.tsx
│   │   │   └── Agent/                 # NEW: Agent components
│   │   │       └── AgentMonitor.tsx
│   │   ├── services/
│   │   │   └── chatService.ts         # NEW: Chat API
│   │   ├── store/
│   │   │   └── chatStore.ts           # NEW: State management
│   │   ├── types/
│   │   │   └── chat.ts                # NEW: TypeScript types
│   │   └── styles/
│   │       └── globals.css            # NEW: Global styles
│   └── package.json                   # Updated
└── docs/
    └── CLAUDE_INTEGRATION.md          # Integration guide
```

## API Endpoints (New)

### Chat
- `POST /api/chat/message` - Send message, get Claude response (SSE)
- `GET /api/chat/conversations` - List conversations
- `GET /api/chat/conversations/{id}` - Get conversation history
- `DELETE /api/chat/conversations/{id}` - Delete conversation
- `POST /api/chat/regenerate` - Regenerate last response

### Server-Sent Events
- `GET /api/chat/stream/{conversation_id}` - Stream Claude responses

## Configuration

### Environment Variables

**Backend (.env):**
```bash
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# MCP Server
MCP_SERVER_PATH=/path/to/openvds_mcp_server.py

# Database
DATABASE_URL=sqlite:///./chat_history.db

# CORS
CORS_ORIGINS=http://localhost:3000
```

**Frontend (.env):**
```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_APP_NAME=VDS Explorer
```

## Security Considerations

1. **API Key Management**
   - Store Anthropic API key securely
   - Never expose in frontend
   - Use environment variables

2. **CORS Configuration**
   - Restrict allowed origins
   - Validate all inputs

3. **Rate Limiting**
   - Limit requests per user
   - Prevent API abuse

4. **Data Privacy**
   - Conversations stored locally
   - Optional encryption
   - Clear data deletion

## Performance Optimizations

1. **Frontend**
   - Virtual scrolling for long chats
   - Image lazy loading
   - Code splitting
   - Debounced inputs

2. **Backend**
   - Streaming responses
   - Connection pooling
   - Caching frequent queries
   - Async operations

3. **Network**
   - HTTP/2
   - Compression
   - CDN for static assets

## Deployment

### Development
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm start
```

### Production (Docker)
```bash
docker-compose up --build
```

### Production (Cloud)
- Backend: Deploy to AWS/GCP/Azure
- Frontend: Deploy to Vercel/Netlify
- Database: Managed PostgreSQL
- MCP Server: Same instance as backend

## Success Metrics

- ✅ Chat interface identical to Claude Desktop
- ✅ Claude can use all MCP tools seamlessly
- ✅ Seismic images display inline in chat
- ✅ Agent monitoring works in real-time
- ✅ Streaming responses feel natural
- ✅ Production-ready code quality
- ✅ Comprehensive documentation

## Timeline

- **Week 1:** Backend with Claude integration ✅
- **Week 2:** Complete React frontend
- **Week 3:** Advanced features
- **Week 4:** Production polish

**Total: 4 weeks to production-ready application**

---

Ready to start implementation? The backend already has MCP integration - we just need to add Claude API and build the frontend!
