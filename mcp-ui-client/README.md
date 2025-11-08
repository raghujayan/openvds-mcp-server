# VDS Explorer - MCP UI Client

A polished web-based UI client for exploring OpenVDS seismic data through the MCP server.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (React UI)                        │
│  - Survey Explorer  - Data Viewer  - Validation Dashboard   │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/WebSocket
┌────────────────────▼────────────────────────────────────────┐
│              FastAPI Backend (Python)                        │
│  - REST API  - MCP Client Bridge  - Session Management      │
└────────────────────┬────────────────────────────────────────┘
                     │ stdio MCP protocol
┌────────────────────▼────────────────────────────────────────┐
│              OpenVDS MCP Server                              │
│  - VDS Access  - Data Integrity  - Agent Manager            │
└─────────────────────────────────────────────────────────────┘
```

## Features

- **Survey Explorer** - Browse and search available VDS surveys
- **Data Extraction** - Extract inlines, crosslines, and timeslices
- **Visualization Viewer** - View seismic images with interactive controls
- **Data Integrity** - Validate statistics and coordinates
- **Agent Dashboard** - Monitor autonomous extraction jobs
- **Real-time Updates** - WebSocket support for live progress

## Tech Stack

**Backend:**
- Python 3.10+
- FastAPI (async web framework)
- MCP SDK (MCP client)
- WebSockets for real-time communication

**Frontend:**
- React 18+ with TypeScript
- Tailwind CSS for styling
- React Query for data fetching
- Recharts for data visualization
- WebSocket client for updates

## Quick Start

### Docker (Recommended)

```bash
cd mcp-ui-client
docker-compose up
```

Access at: http://localhost:3000

### Manual Setup

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm start
```

## Project Structure

```
mcp-ui-client/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── mcp_client.py        # MCP client bridge
│   │   ├── api/
│   │   │   ├── surveys.py       # Survey endpoints
│   │   │   ├── extraction.py   # Data extraction endpoints
│   │   │   ├── validation.py   # Data integrity endpoints
│   │   │   └── agents.py        # Agent management endpoints
│   │   └── models/              # Pydantic models
│   ├── requirements.txt
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   │   ├── SurveyList.tsx
│   │   │   ├── DataViewer.tsx
│   │   │   ├── ValidationPanel.tsx
│   │   │   └── AgentDashboard.tsx
│   │   ├── pages/               # Page components
│   │   ├── services/            # API clients
│   │   ├── types/               # TypeScript types
│   │   └── styles/              # CSS/Tailwind
│   ├── package.json
│   └── tsconfig.json
├── docker/
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── docker-compose.yml
└── docs/
    ├── API.md                   # API documentation
    └── DEVELOPMENT.md           # Development guide
```

## API Endpoints

### Surveys
- `GET /api/surveys` - List all surveys
- `GET /api/surveys/search?q={query}` - Search surveys
- `GET /api/surveys/{id}` - Get survey details
- `GET /api/surveys/{id}/stats` - Get survey statistics

### Data Extraction
- `POST /api/extract/inline` - Extract inline slice
- `POST /api/extract/crossline` - Extract crossline slice
- `POST /api/extract/timeslice` - Extract timeslice
- `GET /api/extract/{job_id}` - Get extraction result

### Data Integrity
- `POST /api/validate/statistics` - Validate statistics
- `POST /api/validate/coordinates` - Verify coordinates
- `POST /api/validate/consistency` - Check consistency

### Agents
- `POST /api/agents/start` - Start extraction agent
- `GET /api/agents/{session_id}` - Get agent status
- `POST /api/agents/{session_id}/pause` - Pause agent
- `POST /api/agents/{session_id}/resume` - Resume agent
- `GET /api/agents/{session_id}/results` - Get results

### WebSocket
- `WS /ws/agents/{session_id}` - Real-time agent updates

## Configuration

**Backend** (`backend/.env`):
```env
MCP_SERVER_PATH=/path/to/openvds-mcp-server/src/openvds_mcp_server.py
MCP_SERVER_ARGS=
CORS_ORIGINS=http://localhost:3000
```

**Frontend** (`frontend/.env`):
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
```

## Development

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed development instructions.

## License

Same as parent project (openvds-mcp-server)
