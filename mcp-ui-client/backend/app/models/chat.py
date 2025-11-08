"""
Chat data models for VDS Explorer

Pydantic models for chat conversations, messages, and API requests/responses
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# Message content types
class TextContent(BaseModel):
    """Text content block"""
    type: Literal["text"] = "text"
    text: str


class ImageContent(BaseModel):
    """Image content block (base64 encoded)"""
    type: Literal["image"] = "image"
    source: Dict[str, str]  # {"type": "base64", "media_type": "image/png", "data": "..."}


class ToolUseContent(BaseModel):
    """Tool use request from Claude"""
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: Dict[str, Any]


class ToolResultContent(BaseModel):
    """Tool result from execution"""
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str | List[Dict[str, Any]]
    is_error: bool = False


# Message models
class ChatMessage(BaseModel):
    """A single message in a conversation"""
    role: Literal["user", "assistant"]
    content: str | List[TextContent | ImageContent | ToolUseContent | ToolResultContent]


class Message(BaseModel):
    """Internal message representation with metadata"""
    id: str
    role: Literal["user", "assistant"]
    content: List[TextContent | ImageContent | ToolUseContent | ToolResultContent]
    timestamp: datetime
    model: Optional[str] = None
    usage: Optional[Dict[str, int]] = None  # {"input_tokens": 100, "output_tokens": 50}


# Chat requests
class ChatRequest(BaseModel):
    """Request to send a chat message"""
    messages: List[ChatMessage]
    stream: bool = True
    use_tools: bool = True
    system: Optional[str] = None
    conversation_id: Optional[str] = None


class RegenerateRequest(BaseModel):
    """Request to regenerate last assistant response"""
    conversation_id: str
    use_tools: bool = True


# Chat responses
class ChatResponse(BaseModel):
    """Response from chat endpoint (non-streaming)"""
    message: Message
    conversation_id: str
    tool_calls: Optional[List[Dict[str, Any]]] = None


class StreamEvent(BaseModel):
    """Server-sent event during streaming"""
    type: str
    data: Dict[str, Any]


# Conversation models
class Conversation(BaseModel):
    """A conversation with message history"""
    id: str
    title: str
    messages: List[Message]
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class ConversationSummary(BaseModel):
    """Summary of a conversation (without full messages)"""
    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime
    last_message_preview: Optional[str] = None


class ConversationListResponse(BaseModel):
    """Response for list conversations endpoint"""
    conversations: List[ConversationSummary]
    total: int
    page: int = 1
    page_size: int = 20


# Database models (for SQLAlchemy)
class ConversationDB(BaseModel):
    """Database model for conversations"""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    metadata: Optional[str] = None  # JSON string

    class Config:
        from_attributes = True


class MessageDB(BaseModel):
    """Database model for messages"""
    id: str
    conversation_id: str
    role: str
    content: str  # JSON string of content blocks
    model: Optional[str] = None
    usage_input_tokens: Optional[int] = None
    usage_output_tokens: Optional[int] = None
    timestamp: datetime

    class Config:
        from_attributes = True
