"""
Chat API endpoints for VDS Explorer

Handles chat conversations with Claude, including:
- Streaming responses
- Tool calling (MCP tools)
- Conversation management
"""

import json
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from ..claude_client import get_claude_client
from ..mcp_client import get_mcp_client

logger = logging.getLogger("chat-api")
from ..models.chat import (
    ChatRequest,
    ChatResponse,
    ChatMessage,
    Message,
    TextContent,
    ToolUseContent,
    ToolResultContent,
)


router = APIRouter(prefix="/api/chat", tags=["chat"])


def convert_to_anthropic_messages(messages: List[ChatMessage]) -> List[Dict[str, Any]]:
    """
    Convert our ChatMessage format to Anthropic's message format

    Args:
        messages: List of ChatMessage objects

    Returns:
        List of message dicts in Anthropic format
    """
    anthropic_messages = []

    for msg in messages:
        # Convert content to Anthropic format
        if isinstance(msg.content, str):
            # Simple string content
            content = msg.content
        elif isinstance(msg.content, list):
            # List of content blocks
            content = []
            for block in msg.content:
                if isinstance(block, dict):
                    content.append(block)
                else:
                    # Pydantic model - convert to dict
                    content.append(block.model_dump(exclude_none=True))
        else:
            content = str(msg.content)

        anthropic_messages.append({
            "role": msg.role,
            "content": content
        })

    return anthropic_messages


async def get_mcp_tools() -> List[Dict[str, Any]]:
    """
    Get list of MCP tools in Anthropic tool format

    Returns:
        List of tool definitions
    """
    mcp = await get_mcp_client()
    tools = await mcp.list_tools()

    # Convert MCP tool format to Anthropic tool format
    anthropic_tools = []
    for tool in tools:
        anthropic_tools.append({
            "name": tool["name"],
            "description": tool.get("description", ""),
            "input_schema": tool.get("inputSchema", {
                "type": "object",
                "properties": {},
                "required": []
            })
        })

    return anthropic_tools


@router.post("/message")
async def chat_message(request: ChatRequest):
    """
    Send a chat message and get Claude's response

    Supports streaming and tool calling:
    - If stream=True: Returns Server-Sent Events stream
    - If stream=False: Returns complete response
    - If use_tools=True: Claude can call MCP tools

    Tool calling flow:
    1. User sends message
    2. Claude responds (may include tool_use blocks)
    3. Backend executes tools and adds tool_result blocks
    4. Backend sends continuation to Claude with tool results
    5. Claude responds with final answer
    6. Repeat 2-5 if Claude needs more tools
    """
    try:
        claude = get_claude_client()
        mcp = await get_mcp_client()

        # Convert messages to Anthropic format
        anthropic_messages = convert_to_anthropic_messages(request.messages)

        # Get available tools if requested
        tools = None
        if request.use_tools:
            tools = await get_mcp_tools()

        # System prompt for VDS Explorer context
        system_prompt = request.system or """You are VDS Explorer Assistant, an AI assistant that helps users explore and analyze seismic data.

You have access to tools for:
- Searching seismic surveys
- Extracting seismic sections (inline, crossline, timeslice)
- Validating data integrity and statistics
- Managing autonomous extraction agents

When users ask to see seismic data:
1. Use search_surveys to find available surveys
2. Use extract_inline_image, extract_crossline_image, or extract_timeslice to get seismic sections
3. Display the images inline in the chat
4. Use validation tools to verify data quality when appropriate
5. Use agents for large-scale extraction tasks

Always provide context about what you're doing and explain the seismic data you show."""

        if request.stream:
            # Streaming response with tool calling
            async def event_generator():
                """Generate SSE events from Claude's streaming response"""
                conversation_messages = anthropic_messages.copy()
                max_tool_iterations = 10  # Prevent infinite loops
                iteration = 0

                # Track images from tool results to include in final response
                tool_result_images: List[Dict[str, Any]] = []

                while iteration < max_tool_iterations:
                    iteration += 1

                    # Reset tracking for this iteration
                    tool_calls_pending: List[Dict[str, Any]] = []
                    assistant_message_content: List[Dict[str, Any]] = []

                    # Stream Claude's response
                    async for event in claude.chat_stream(
                        messages=conversation_messages,
                        tools=tools,
                        system=system_prompt
                    ):
                        # Check if this is the final message with tool calls
                        if event.get("type") == "message_stop":
                            message_data = event.get("message", {})
                            content = message_data.get("content", [])

                            # If this is the final iteration (no tool calls), append images from tool results
                            has_tool_calls = any(block.get("type") == "tool_use" for block in content)
                            if not has_tool_calls and tool_result_images:
                                # Inject images into the message content
                                logger.info(f"Appending {len(tool_result_images)} images to final response")
                                event["message"]["content"] = list(content) + tool_result_images

                        # Forward event to client
                        yield {
                            "event": "claude_event",
                            "data": json.dumps(event)
                        }

                        if event.get("type") == "message_stop":
                            message_data = event.get("message", {})
                            content = message_data.get("content", [])

                            # Extract tool calls and text
                            for block in content:
                                if block.get("type") == "tool_use":
                                    tool_calls_pending.append(block)
                                assistant_message_content.append(block)

                            # If no tool calls, we're done
                            if not tool_calls_pending:
                                yield {
                                    "event": "done",
                                    "data": json.dumps({
                                        "message": "Stream complete",
                                        "iterations": iteration
                                    })
                                }
                                return

                            # Execute tool calls
                            yield {
                                "event": "tool_execution_start",
                                "data": json.dumps({
                                    "tool_count": len(tool_calls_pending)
                                })
                            }

                            # Add assistant message to conversation
                            conversation_messages.append({
                                "role": "assistant",
                                "content": assistant_message_content
                            })

                            # Execute each tool and collect results
                            tool_results = []
                            for tool_call in tool_calls_pending:
                                tool_name = tool_call["name"]
                                tool_input = tool_call["input"]
                                tool_id = tool_call["id"]

                                yield {
                                    "event": "tool_call",
                                    "data": json.dumps({
                                        "id": tool_id,
                                        "name": tool_name,
                                        "input": tool_input
                                    })
                                }

                                try:
                                    # Call MCP tool
                                    logger.info(f"[BEFORE] About to call MCP tool: {tool_name}")
                                    result = await mcp.call_tool(tool_name, tool_input)
                                    logger.info(f"[AFTER] MCP tool {tool_name} returned result type: {type(result)}, length: {len(result) if isinstance(result, (list, dict, str)) else 'N/A'}")

                                    # Handle different result types
                                    # Check if result is a list of MCP content blocks (ImageContent, TextContent)
                                    if isinstance(result, list) and len(result) > 0:
                                        # Check if first item looks like MCP content (has 'type' and 'data'/'text')
                                        first_item = result[0]
                                        if isinstance(first_item, dict) and 'type' in first_item:
                                            # Convert MCP content blocks to Claude API format
                                            content_blocks = []
                                            for item in result:
                                                if item.get('type') == 'image':
                                                    # Image content - convert to Claude API format
                                                    content_blocks.append({
                                                        "type": "image",
                                                        "source": {
                                                            "type": "base64",
                                                            "media_type": item.get('mimeType', 'image/jpeg'),
                                                            "data": item.get('data', '')
                                                        }
                                                    })
                                                elif item.get('type') == 'text':
                                                    # Text content
                                                    content_blocks.append({
                                                        "type": "text",
                                                        "text": item.get('text', str(item))
                                                    })
                                                else:
                                                    # Unknown type - convert to text
                                                    content_blocks.append({
                                                        "type": "text",
                                                        "text": json.dumps(item, indent=2)
                                                    })

                                            # Use content blocks directly
                                            result_content = content_blocks
                                        else:
                                            # Regular list - stringify
                                            result_content = json.dumps(result, indent=2)
                                    elif isinstance(result, dict):
                                        result_content = json.dumps(result, indent=2)
                                    else:
                                        result_content = str(result)

                                    # Log what we're sending to Claude
                                    if isinstance(result_content, list):
                                        logger.info(f"Sending {len(result_content)} content blocks to Claude: {[b.get('type') for b in result_content if isinstance(b, dict)]}")
                                        # Store any images for final response
                                        for block in result_content:
                                            if isinstance(block, dict) and block.get('type') == 'image':
                                                tool_result_images.append(block)
                                    else:
                                        logger.info(f"Sending text result to Claude: {result_content[:100]}...")

                                    tool_results.append({
                                        "type": "tool_result",
                                        "tool_use_id": tool_id,
                                        "content": result_content
                                    })

                                    # Generate preview for SSE event
                                    if isinstance(result_content, list):
                                        # Content blocks - create summary
                                        preview_parts = []
                                        for block in result_content:
                                            if isinstance(block, dict):
                                                if block.get('type') == 'image':
                                                    preview_parts.append(f"[Image: {block.get('source', {}).get('media_type', 'unknown')}]")
                                                elif block.get('type') == 'text':
                                                    text = block.get('text', '')
                                                    preview_parts.append(text[:100] + "..." if len(text) > 100 else text)
                                        preview = " | ".join(preview_parts)
                                    else:
                                        # String result
                                        preview = result_content[:200] + "..." if len(result_content) > 200 else result_content

                                    yield {
                                        "event": "tool_result",
                                        "data": json.dumps({
                                            "id": tool_id,
                                            "success": True,
                                            "preview": preview
                                        })
                                    }

                                except Exception as e:
                                    error_msg = f"Error calling tool {tool_name}: {str(e)}"
                                    logger.error(f"Tool execution error: {error_msg}", exc_info=True)
                                    tool_results.append({
                                        "type": "tool_result",
                                        "tool_use_id": tool_id,
                                        "content": error_msg,
                                        "is_error": True
                                    })

                                    yield {
                                        "event": "tool_error",
                                        "data": json.dumps({
                                            "id": tool_id,
                                            "error": error_msg
                                        })
                                    }

                            # Add tool results to conversation
                            conversation_messages.append({
                                "role": "user",
                                "content": tool_results
                            })

                            yield {
                                "event": "tool_execution_complete",
                                "data": json.dumps({
                                    "result_count": len(tool_results)
                                })
                            }

                            # Continue loop to get Claude's response with tool results

                # Max iterations reached
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": "Maximum tool calling iterations reached"
                    })
                }

            return EventSourceResponse(event_generator())

        else:
            # Non-streaming response
            response = await claude.chat(
                messages=anthropic_messages,
                tools=tools,
                system=system_prompt
            )

            # Convert response to our format
            content_blocks = []
            for block in response.content:
                if block.type == "text":
                    content_blocks.append(TextContent(text=block.text))
                elif block.type == "tool_use":
                    content_blocks.append(ToolUseContent(
                        id=block.id,
                        name=block.name,
                        input=block.input
                    ))

            message = Message(
                id=response.id,
                role="assistant",
                content=content_blocks,
                timestamp=datetime.now(),
                model=response.model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            )

            # Extract tool calls if any
            tool_calls = [
                {"id": block.id, "name": block.name, "input": block.input}
                for block in content_blocks
                if isinstance(block, ToolUseContent)
            ]

            return ChatResponse(
                message=message,
                conversation_id=request.conversation_id or str(uuid.uuid4()),
                tool_calls=tool_calls if tool_calls else None
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.get("/health")
async def chat_health():
    """Check if Claude API is configured"""
    try:
        claude = get_claude_client()
        return {
            "status": "healthy",
            "model": claude.model,
            "max_tokens": claude.max_tokens
        }
    except ValueError as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
