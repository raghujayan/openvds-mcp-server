"""
Claude API Client for VDS Explorer

Handles interactions with Anthropic's Claude API including:
- Chat completions
- Tool use (MCP tools)
- Streaming responses
- Message history management
"""

import os
from typing import List, Dict, Any, Optional, AsyncIterator
import anthropic
from anthropic.types import Message, MessageParam, ContentBlock


class ClaudeClient:
    """Client for interacting with Claude API"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
    ):
        """
        Initialize Claude client

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model name (defaults to ANTHROPIC_MODEL env var or claude-sonnet-4-5-20250929)
            max_tokens: Maximum tokens in response
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set")

        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        self.max_tokens = max_tokens
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)

    async def chat(
        self,
        messages: List[MessageParam],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
    ) -> Message:
        """
        Send a chat message and get response (non-streaming)

        Args:
            messages: List of messages in conversation
            tools: Optional list of tools Claude can use
            system: Optional system prompt

        Returns:
            Claude's response message
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": messages,
        }

        if tools:
            kwargs["tools"] = tools

        if system:
            kwargs["system"] = system

        response = await self.client.messages.create(**kwargs)
        return response

    async def chat_stream(
        self,
        messages: List[MessageParam],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream chat completion from Claude

        Yields events as they occur:
        - message_start: Initial message metadata
        - content_block_start: Start of text or tool use block
        - content_block_delta: Incremental text updates
        - content_block_stop: End of content block
        - message_delta: Message-level updates (usage, etc.)
        - message_stop: Message complete

        Args:
            messages: List of messages in conversation
            tools: Optional list of tools Claude can use
            system: Optional system prompt

        Yields:
            Event dictionaries with type and data
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": messages,
        }

        if tools:
            kwargs["tools"] = tools

        if system:
            kwargs["system"] = system

        async with self.client.messages.stream(**kwargs) as stream:
            # Track content blocks to build full message
            content_blocks: List[Dict[str, Any]] = []
            current_block: Optional[Dict[str, Any]] = None

            async for event in stream:
                event_type = event.type

                if event_type == "message_start":
                    yield {
                        "type": "message_start",
                        "message": {
                            "id": event.message.id,
                            "model": event.message.model,
                            "role": event.message.role,
                        }
                    }

                elif event_type == "content_block_start":
                    block_index = event.index
                    content_block = event.content_block

                    if content_block.type == "text":
                        current_block = {
                            "type": "text",
                            "text": "",
                            "index": block_index
                        }
                        yield {
                            "type": "content_block_start",
                            "index": block_index,
                            "content_type": "text"
                        }

                    elif content_block.type == "tool_use":
                        current_block = {
                            "type": "tool_use",
                            "id": content_block.id,
                            "name": content_block.name,
                            "input": {},
                            "index": block_index
                        }
                        yield {
                            "type": "content_block_start",
                            "index": block_index,
                            "content_type": "tool_use",
                            "tool_use": {
                                "id": content_block.id,
                                "name": content_block.name
                            }
                        }

                elif event_type == "content_block_delta":
                    delta = event.delta

                    if hasattr(delta, 'text'):
                        # Text delta
                        if current_block and current_block["type"] == "text":
                            current_block["text"] += delta.text

                        yield {
                            "type": "content_block_delta",
                            "index": event.index,
                            "delta_type": "text",
                            "text": delta.text
                        }

                    elif hasattr(delta, 'partial_json'):
                        # Tool input delta
                        if current_block and current_block["type"] == "tool_use":
                            # partial_json is incremental - we'll parse full JSON at block_stop
                            pass

                        yield {
                            "type": "content_block_delta",
                            "index": event.index,
                            "delta_type": "input_json_delta",
                            "partial_json": delta.partial_json
                        }

                elif event_type == "content_block_stop":
                    if current_block:
                        content_blocks.append(current_block)

                    yield {
                        "type": "content_block_stop",
                        "index": event.index
                    }

                    current_block = None

                elif event_type == "message_delta":
                    delta = event.delta
                    yield {
                        "type": "message_delta",
                        "delta": {
                            "stop_reason": getattr(delta, 'stop_reason', None),
                            "stop_sequence": getattr(delta, 'stop_sequence', None),
                        },
                        "usage": {
                            "output_tokens": event.usage.output_tokens if hasattr(event, 'usage') else 0
                        }
                    }

                elif event_type == "message_stop":
                    # Get the final message
                    final_message = await stream.get_final_message()

                    # Extract all content blocks from final message
                    final_content = []
                    for block in final_message.content:
                        if block.type == "text":
                            final_content.append({
                                "type": "text",
                                "text": block.text
                            })
                        elif block.type == "tool_use":
                            final_content.append({
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input
                            })

                    yield {
                        "type": "message_stop",
                        "message": {
                            "id": final_message.id,
                            "model": final_message.model,
                            "role": final_message.role,
                            "content": final_content,
                            "stop_reason": final_message.stop_reason,
                            "usage": {
                                "input_tokens": final_message.usage.input_tokens,
                                "output_tokens": final_message.usage.output_tokens
                            }
                        }
                    }


# Global client instance
_claude_client: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    """Get or create the global Claude client instance"""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client
