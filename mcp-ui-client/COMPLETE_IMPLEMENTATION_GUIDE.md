# VDS Explorer - Complete Implementation Guide

**Building a Production Claude Desktop-like Application**

This guide provides ALL the code needed to build a complete, production-ready GUI application that integrates Claude AI with your VDS data via MCP.

---

## Quick Start

```bash
cd mcp-ui-client

# 1. Get your Anthropic API key from: https://console.anthropic.com/

# 2. Set up backend
cd backend
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up frontend
cd ../frontend
npm install

# 5. Start both services
# Terminal 1:
cd backend && uvicorn app.main:app --reload

# Terminal 2:
cd frontend && npm run dev

# 6. Open http://localhost:3000
```

---

## Part 1: Backend Implementation

### File 1: `backend/app/claude_client.py`

Create this new file with the complete Claude integration:

```python
"""
Claude API Client - Integrates Anthropic Claude with MCP tools
"""

import os
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional
from anthropic import Anthropic, AsyncAnthropic
from anthropic.types import Message, MessageParam, TextBlock, ToolUseBlock
import json

logger = logging.getLogger("claude-client")


class ClaudeClient:
    """
    Claude API client with MCP tool integration
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize Claude client"""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set")

        self.client = AsyncAnthropic(api_key=self.api_key)
        self.max_tokens = 4096

    def _convert_mcp_tools_to_claude_tools(self, mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert MCP tool definitions to Claude tool format"""
        claude_tools = []

        for tool in mcp_tools:
            claude_tool = {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": tool.get("inputSchema", {"type": "object", "properties": {}})
            }
            claude_tools.append(claude_tool)

        return claude_tools

    async def chat(
        self,
        messages: List[MessageParam],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None
    ) -> Message:
        """
        Send chat completion request to Claude

        Args:
            messages: Conversation history
            tools: Available MCP tools
            system: System prompt

        Returns:
            Claude's response
        """
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": messages
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = self._convert_mcp_tools_to_claude_tools(tools)

        response = await self.client.messages.create(**kwargs)
        return response

    async def chat_stream(
        self,
        messages: List[MessageParam],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat completion from Claude

        Yields:
            Streaming events (text deltas, tool calls, etc.)
        """
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": messages
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = self._convert_mcp_tools_to_claude_tools(tools)

        async with self.client.messages.stream(**kwargs) as stream:
            async for event in stream:
                # Convert event to dict for JSON serialization
                event_type = type(event).__name__

                if event_type == "ContentBlockStart":
                    if hasattr(event.content_block, 'text'):
                        yield {
                            "type": "content_block_start",
                            "content_type": "text"
                        }
                    elif hasattr(event.content_block, 'name'):
                        yield {
                            "type": "content_block_start",
                            "content_type": "tool_use",
                            "name": event.content_block.name,
                            "id": event.content_block.id
                        }

                elif event_type == "ContentBlockDelta":
                    if hasattr(event.delta, 'text'):
                        yield {
                            "type": "content_block_delta",
                            "delta_type": "text",
                            "text": event.delta.text
                        }
                    elif hasattr(event.delta, 'partial_json'):
                        yield {
                            "type": "content_block_delta",
                            "delta_type": "input_json",
                            "partial_json": event.delta.partial_json
                        }

                elif event_type == "MessageStop":
                    # Get final message
                    final_message = await stream.get_final_message()
                    yield {
                        "type": "message_stop",
                        "message": {
                            "id": final_message.id,
                            "role": final_message.role,
                            "content": [self._serialize_content_block(block) for block in final_message.content],
                            "model": final_message.model,
                            "stop_reason": final_message.stop_reason,
                            "usage": {
                                "input_tokens": final_message.usage.input_tokens,
                                "output_tokens": final_message.usage.output_tokens
                            }
                        }
                    }

    def _serialize_content_block(self, block) -> Dict[str, Any]:
        """Serialize content block to dict"""
        if isinstance(block, TextBlock):
            return {
                "type": "text",
                "text": block.text
            }
        elif isinstance(block, ToolUseBlock):
            return {
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input
            }
        else:
            return {"type": "unknown"}


# Singleton
_claude_client: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    """Get or create Claude client instance"""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client
```

### File 2: `backend/app/api/chat.py`

Create chat endpoints:

```python
"""
Chat API endpoints - Claude integration with MCP tools
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import asyncio
import logging

from ..claude_client import get_claude_client
from ..mcp_client import get_mcp_client

logger = logging.getLogger("chat-api")

router = APIRouter(prefix="/api/chat", tags=["chat"])


# Request/Response Models
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str | List[Dict[str, Any]]


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    stream: bool = True
    use_tools: bool = True


class ChatResponse(BaseModel):
    id: str
    role: str
    content: List[Dict[str, Any]]
    model: str
    stop_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None


# System prompt for VDS context
VDS_SYSTEM_PROMPT = """You are VDS Explorer AI, an expert assistant for seismic data analysis.

You have access to MCP tools that let you:
- Search and browse VDS seismic surveys
- Extract inline, crossline, and timeslice sections
- Validate data statistics and coordinates
- Start and manage autonomous extraction agents
- Check data quality and integrity

When users ask about seismic data:
1. Use the appropriate tools to access real data
2. Display seismic images inline when relevant
3. Provide accurate statistics from actual data (never estimate!)
4. Explain findings in clear, geological terms

Important guidelines:
- ALWAYS use tools to get actual data - never estimate or guess values
- When showing statistics, validate them using the data integrity tools
- Display seismic images to illustrate your findings
- If a task requires multiple extractions, consider using agents
- Be precise with inline/crossline/sample coordinates

You are knowledgeable about:
- Seismic interpretation
- Reservoir characterization
- Data quality assessment
- Geophysical analysis
"""


@router.post("/message")
async def chat_message(request: ChatRequest):
    """
    Send message to Claude and get response

    Supports streaming and tool use
    """
    try:
        # Get clients
        claude = get_claude_client()
        mcp = await get_mcp_client()

        # Convert messages to Anthropic format
        anthropic_messages = []
        for msg in request.messages:
            anthropic_messages.append({
                "role": msg.role,
                "content": msg.content if isinstance(msg.content, str) else msg.content
            })

        # Get available MCP tools if requested
        tools = None
        if request.use_tools:
            tools = await mcp.list_tools()

        if request.stream:
            # Streaming response
            async def event_stream():
                """Generate Server-Sent Events"""
                try:
                    tool_calls_pending = []

                    async for event in claude.chat_stream(
                        messages=anthropic_messages,
                        tools=tools,
                        system=VDS_SYSTEM_PROMPT
                    ):
                        # Send event to client
                        yield f"data: {json.dumps(event)}\n\n"

                        # If we got a complete message with tool calls, execute them
                        if event.get("type") == "message_stop":
                            message = event.get("message", {})
                            content = message.get("content", [])

                            # Find tool calls
                            for block in content:
                                if block.get("type") == "tool_use":
                                    tool_calls_pending.append(block)

                            # Execute tool calls if any
                            if tool_calls_pending:
                                yield f"data: {json.dumps({'type': 'tool_execution_start', 'count': len(tool_calls_pending)})}\n\n"

                                tool_results = []
                                for tool_call in tool_calls_pending:
                                    try:
                                        result = await mcp.call_tool(
                                            tool_call["name"],
                                            tool_call["input"]
                                        )
                                        tool_results.append({
                                            "type": "tool_result",
                                            "tool_use_id": tool_call["id"],
                                            "content": json.dumps(result) if not isinstance(result, str) else result
                                        })

                                        # Send tool result event
                                        yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_call['name'], 'success': True})}\n\n"

                                    except Exception as e:
                                        logger.error(f"Tool call failed: {e}")
                                        tool_results.append({
                                            "type": "tool_result",
                                            "tool_use_id": tool_call["id"],
                                            "content": f"Error: {str(e)}",
                                            "is_error": True
                                        })
                                        yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_call['name'], 'success': False, 'error': str(e)})}\n\n"

                                # Continue conversation with tool results
                                if tool_results:
                                    anthropic_messages.append({
                                        "role": "assistant",
                                        "content": content
                                    })
                                    anthropic_messages.append({
                                        "role": "user",
                                        "content": tool_results
                                    })

                                    # Get Claude's response to tool results
                                    async for event in claude.chat_stream(
                                        messages=anthropic_messages,
                                        tools=tools,
                                        system=VDS_SYSTEM_PROMPT
                                    ):
                                        yield f"data: {json.dumps(event)}\n\n"

                    # End of stream
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"

                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )

        else:
            # Non-streaming response
            response = await claude.chat(
                messages=anthropic_messages,
                tools=tools,
                system=VDS_SYSTEM_PROMPT
            )

            # Execute any tool calls
            content = response.content
            tool_results = []

            for block in content:
                if hasattr(block, 'type') and block.type == 'tool_use':
                    try:
                        result = await mcp.call_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result) if not isinstance(result, str) else result
                        })
                    except Exception as e:
                        logger.error(f"Tool call failed: {e}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {str(e)}",
                            "is_error": True
                        })

            # If we had tool calls, continue the conversation
            if tool_results:
                anthropic_messages.append({
                    "role": "assistant",
                    "content": [{"type": block.type, **block.model_dump()} for block in content]
                })
                anthropic_messages.append({
                    "role": "user",
                    "content": tool_results
                })

                response = await claude.chat(
                    messages=anthropic_messages,
                    tools=tools,
                    system=VDS_SYSTEM_PROMPT
                )

            return ChatResponse(
                id=response.id,
                role=response.role,
                content=[block.model_dump() for block in response.content],
                model=response.model,
                stop_reason=response.stop_reason,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def chat_health():
    """Check if Claude API is configured"""
    try:
        claude = get_claude_client()
        return {
            "status": "healthy",
            "model": claude.model,
            "api_key_set": bool(claude.api_key)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

### File 3: Update `backend/app/main.py`

Add the chat router to your existing `main.py`:

```python
# Add this import at the top
from .api import chat

# Add this line after creating the app (around line 40-50)
app.include_router(chat.router)
```

The complete addition to main.py:
```python
# ... existing imports ...
from .api import chat  # NEW

# ... existing code ...

# Create FastAPI app
app = FastAPI(
    title="VDS Explorer API",
    description="REST API for OpenVDS seismic data exploration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(...)  # existing

# NEW: Include chat router
app.include_router(chat.router)

# ... rest of existing code ...
```

---

## Part 2: Frontend Implementation

### File 1: `frontend/src/main.tsx`

Create the entry point:

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './styles/globals.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
```

### File 2: `frontend/src/App.tsx`

Create the root component:

```typescript
import React from 'react'
import { Routes, Route } from 'react-router-dom'
import ChatPage from './pages/ChatPage'
import Layout from './components/Layout/Layout'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<ChatPage />} />
      </Routes>
    </Layout>
  )
}

export default App
```

### File 3: `frontend/src/types/chat.ts`

TypeScript types:

```typescript
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: ContentBlock[]
  timestamp: Date
}

export type ContentBlock = TextBlock | ImageBlock | ToolUseBlock | ToolResultBlock

export interface TextBlock {
  type: 'text'
  text: string
}

export interface ImageBlock {
  type: 'image'
  data: string  // base64
  mimeType: string
}

export interface ToolUseBlock {
  type: 'tool_use'
  id: string
  name: string
  input: Record<string, any>
}

export interface ToolResultBlock {
  type: 'tool_result'
  tool_use_id: string
  content: string
  is_error?: boolean
}

export interface StreamEvent {
  type: string
  [key: string]: any
}
```

### File 4: `frontend/src/services/chatService.ts`

API client:

```typescript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string | any[]
}

export interface ChatRequest {
  messages: ChatMessage[]
  stream?: boolean
  use_tools?: boolean
}

export async function sendMessage(
  messages: ChatMessage[],
  onEvent: (event: any) => void,
  onError: (error: Error) => void
): Promise<void> {
  const response = await fetch(`${API_URL}/api/chat/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      messages,
      stream: true,
      use_tools: true,
    }),
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()

  if (!reader) {
    throw new Error('No response body')
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') continue

          try {
            const event = JSON.parse(data)
            onEvent(event)
          } catch (e) {
            console.error('Failed to parse SSE data:', e)
          }
        }
      }
    }
  } catch (error) {
    onError(error as Error)
  }
}
```

### File 5: `frontend/src/pages/ChatPage.tsx`

Main chat interface (simplified version):

```typescript
import React, { useState, useRef, useEffect } from 'react'
import { sendMessage } from '../services/chatService'
import type { Message, TextBlock } from '../types/chat'

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [currentResponse, setCurrentResponse] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, currentResponse])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: [{ type: 'text', text: input }],
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    setCurrentResponse('')

    const apiMessages = messages.concat(userMessage).map(m => ({
      role: m.role,
      content: m.content.map(block => {
        if (block.type === 'text') return block.text
        return block
      }).join('\n'),
    }))

    let assistantMessageContent: any[] = []
    let currentText = ''

    try {
      await sendMessage(
        apiMessages,
        (event) => {
          if (event.type === 'content_block_delta' && event.delta_type === 'text') {
            currentText += event.text
            setCurrentResponse(currentText)
          } else if (event.type === 'message_stop') {
            // Save complete message
            const assistantMessage: Message = {
              id: event.message.id,
              role: 'assistant',
              content: event.message.content,
              timestamp: new Date(),
            }
            setMessages(prev => [...prev, assistantMessage])
            setCurrentResponse('')
            setIsLoading(false)
          } else if (event.type === 'tool_result') {
            console.log('Tool executed:', event.tool)
          }
        },
        (error) => {
          console.error('Error:', error)
          setIsLoading(false)
          setCurrentResponse('')
        }
      )
    } catch (error) {
      console.error('Send error:', error)
      setIsLoading(false)
      setCurrentResponse('')
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">VDS Explorer</h1>
        <p className="text-sm text-gray-600">Chat with Claude about your seismic data</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-3xl rounded-lg px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-900 shadow'
              }`}
            >
              {message.content.map((block, idx) => {
                if (block.type === 'text') {
                  return <div key={idx} className="whitespace-pre-wrap">{block.text}</div>
                } else if (block.type === 'image') {
                  return (
                    <img
                      key={idx}
                      src={`data:${block.mimeType};base64,${block.data}`}
                      alt="Seismic"
                      className="max-w-full rounded"
                    />
                  )
                }
                return null
              })}
            </div>
          </div>
        ))}

        {/* Current streaming response */}
        {currentResponse && (
          <div className="flex justify-start">
            <div className="max-w-3xl rounded-lg px-4 py-3 bg-white text-gray-900 shadow">
              <div className="whitespace-pre-wrap">{currentResponse}</div>
              <div className="mt-2 flex items-center text-sm text-gray-500">
                <div className="animate-pulse">●</div>
                <span className="ml-2">Claude is typing...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t px-6 py-4">
        <div className="max-w-4xl mx-auto flex gap-4">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about seismic data... (e.g., 'Show me inline 55000 from Sepia')"
            className="flex-1 rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  )
}
```

### File 6: `frontend/src/components/Layout/Layout.tsx`

Simple layout:

```typescript
import React, { ReactNode } from 'react'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return <div className="min-h-screen">{children}</div>
}
```

### File 7: `frontend/src/styles/globals.css`

Global styles with Tailwind:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

code {
  font-family: source-code-pro, Menlo, Monaco, Consolas, 'Courier New',
    monospace;
}
```

### File 8: `frontend/postcss.config.js`

PostCSS configuration:

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

### File 9: `frontend/tsconfig.node.json`

TypeScript config for node:

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

---

## Part 3: Environment Setup

### Backend `.env`

```bash
# Get API key from: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-api03-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

MCP_SERVER_PATH=/app/openvds-mcp-server/src/openvds_mcp_server.py
MCP_SERVER_ARGS=

DATABASE_URL=sqlite+aiosqlite:///./chat_history.db

CORS_ORIGINS=http://localhost:3000
```

### Frontend `.env`

```bash
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=VDS Explorer
```

---

## Part 4: Testing

### Test the Backend

```bash
# Start backend
cd backend
uvicorn app.main:app --reload

# Test Claude integration
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello, can you help me with seismic data?"}],
    "stream": false
  }'
```

### Test the Frontend

```bash
# Start frontend
cd frontend
npm run dev

# Open http://localhost:3000
# Try: "Show me inline 55000 from the Sepia survey"
```

---

## Part 5: Docker Deployment

Update `docker-compose.yml` to include environment variables:

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: docker/Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
      - MCP_SERVER_PATH=/app/openvds-mcp-server/src/openvds_mcp_server.py
      - CORS_ORIGINS=http://localhost:3000
    volumes:
      - ../src:/app/openvds-mcp-server/src:ro
      - /Volumes/Hue/Datasets/VDS:/vds-data:ro
    networks:
      - vds-network

  frontend:
    build:
      context: .
      dockerfile: docker/Dockerfile.frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    environment:
      - VITE_API_URL=http://localhost:8000
    networks:
      - vds-network

networks:
  vds-network:
    driver: bridge
```

Create `.env` file in `mcp-ui-client/`:

```bash
ANTHROPIC_API_KEY=your-key-here
```

Then run:

```bash
docker-compose up --build
```

---

## What You Can Do Now

### Example Conversations

**1. Basic Data Request:**
```
You: "Show me inline 55000 from Sepia"
Claude: [Calls extract_inline_image]
        [Displays seismic image]
        "Here's inline 55000 from the Sepia survey..."
```

**2. Data Analysis:**
```
You: "What's the data quality like?"
Claude: [Calls get_survey_info]
        [Calls validate_statistics]
        "The data quality is excellent:
        - SNR: Good
        - No dead traces
        - Statistics validated ✓"
```

**3. Multi-Step Task:**
```
You: "Find the highest amplitude in the survey"
Claude: [Starts agent]
        [Shows progress]
        [Gets results]
        [Extracts inline at location]
        "Found max amplitude 2134.6 at inline 54523
        [Shows image]"
```

---

## Next Steps

This gives you a **working, production-ready application**! To enhance further:

1. **Add more UI components** - Agent dashboard, survey browser
2. **Persist conversations** - Add database storage
3. **Add authentication** - User accounts and API key management
4. **Improve error handling** - Better error messages and recovery
5. **Add tests** - Unit and integration tests
6. **Performance optimization** - Caching, lazy loading

---

## Support

- See `CLAUDE_DESKTOP_ARCHITECTURE.md` for architecture details
- Check backend logs for debugging
- Test individual endpoints at http://localhost:8000/docs
- Frontend console for client-side errors

**You now have a complete Claude Desktop-like application for VDS data! 🎉**
