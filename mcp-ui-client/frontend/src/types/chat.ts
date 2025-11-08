/**
 * TypeScript types for chat functionality
 */

export type MessageRole = 'user' | 'assistant';

export type ContentType = 'text' | 'image' | 'tool_use' | 'tool_result';

export interface TextContent {
  type: 'text';
  text: string;
}

export interface ImageContent {
  type: 'image';
  source: {
    type: 'base64';
    media_type: string;
    data: string;
  };
}

export interface ToolUseContent {
  type: 'tool_use';
  id: string;
  name: string;
  input: Record<string, any>;
}

export interface ToolResultContent {
  type: 'tool_result';
  tool_use_id: string;
  content: string | Array<Record<string, any>>;
  is_error?: boolean;
}

export type ContentBlock = TextContent | ImageContent | ToolUseContent | ToolResultContent;

export interface Message {
  id: string;
  role: MessageRole;
  content: ContentBlock[];
  timestamp: Date;
  model?: string;
  usage?: {
    input_tokens: number;
    output_tokens: number;
    time_taken?: number;
  };
}

export interface ChatMessage {
  role: MessageRole;
  content: string | ContentBlock[];
}

export interface ChatRequest {
  messages: ChatMessage[];
  stream?: boolean;
  use_tools?: boolean;
  system?: string;
  conversation_id?: string;
}

export interface StreamEvent {
  type: string;
  data: any;
}

export interface ClaudeEvent {
  type: 'message_start' | 'content_block_start' | 'content_block_delta' | 'content_block_stop' | 'message_delta' | 'message_stop';
  [key: string]: any;
}

export interface ToolCall {
  id: string;
  name: string;
  input: Record<string, any>;
}

export interface ToolResult {
  id: string;
  success: boolean;
  preview?: string;
  error?: string;
}
