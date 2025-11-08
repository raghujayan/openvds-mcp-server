/**
 * Chat service for communicating with VDS Explorer API
 */

import { ChatMessage, StreamEvent } from '../types/chat';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Send a chat message and receive streaming response
 *
 * @param messages - Array of messages in the conversation
 * @param onEvent - Callback for each SSE event
 * @param options - Additional options
 */
export async function sendMessage(
  messages: ChatMessage[],
  onEvent: (event: StreamEvent) => void,
  options: {
    useTools?: boolean;
    system?: string;
    conversationId?: string;
  } = {}
): Promise<void> {
  const { useTools = true, system, conversationId } = options;

  const response = await fetch(`${API_URL}/api/chat/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      messages,
      stream: true,
      use_tools: useTools,
      system,
      conversation_id: conversationId,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  if (!response.body) {
    throw new Error('No response body');
  }

  // Read the stream
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      // Decode the chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE events (events are separated by double newlines)
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          // Event type line
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          const data = line.slice(6); // Remove 'data: ' prefix

          if (data === '[DONE]') {
            continue;
          }

          try {
            const eventData = JSON.parse(data);
            // Pass event with type
            onEvent({
              event: currentEvent || 'message',
              data: eventData,
              ...eventData  // Also spread the data for backward compatibility
            });
            currentEvent = ''; // Reset for next event
          } catch (e) {
            console.error('Failed to parse SSE event:', e, data);
          }
        } else if (line === '') {
          // Empty line marks end of event
          currentEvent = '';
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Check if Claude API is healthy
 */
export async function checkChatHealth(): Promise<{
  status: string;
  model?: string;
  error?: string;
}> {
  const response = await fetch(`${API_URL}/api/chat/health`);
  return response.json();
}
