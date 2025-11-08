/**
 * ChatPage - Main chat interface for VDS Explorer
 */

import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message, ChatMessage, ContentBlock, TextContent, ToolUseContent, ToolResultContent, ImageContent } from '../types/chat';
import { sendMessage } from '../services/chatService';

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const [toolCalls, setToolCalls] = useState<Array<{ id: string; name: string; input: any; status: string }>>([]);
  const [responseStartTime, setResponseStartTime] = useState<number | null>(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentResponse]);

  // Timer effect for elapsed time
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;

    if (isLoading && responseStartTime) {
      interval = setInterval(() => {
        setElapsedTime(Date.now() - responseStartTime);
      }, 100); // Update every 100ms
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isLoading, responseStartTime]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: [{ type: 'text', text: input }],
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setCurrentResponse('');
    setToolCalls([]);

    // Start timer
    const startTime = Date.now();
    setResponseStartTime(startTime);
    setElapsedTime(0);

    try {
      // Convert messages to API format
      const apiMessages: ChatMessage[] = messages.concat(userMessage).map((msg) => {
        // For user messages, send simple text (filter out tool_result blocks)
        if (msg.role === 'user') {
          const textContent = msg.content.find((c) => c.type === 'text') as TextContent;
          return {
            role: msg.role,
            content: textContent ? textContent.text : '',
          };
        }
        // For assistant messages, only send text blocks (exclude tool_use/tool_result)
        // Tool execution happens on the backend, we just show results in UI
        const textBlocks = msg.content.filter(c => c.type === 'text');
        if (textBlocks.length > 0) {
          // Join all text blocks
          const combinedText = textBlocks.map(b => (b as TextContent).text).join('\n\n');
          return {
            role: msg.role,
            content: combinedText,
          };
        }
        // If no text blocks, return empty (shouldn't happen)
        return {
          role: msg.role,
          content: '',
        };
      });

      let currentText = '';
      let assistantMessageId = '';
      let assistantContent: ContentBlock[] = [];

      await sendMessage(apiMessages, (event) => {
        console.log('Received event:', JSON.stringify(event));

        // Parse nested claude_event if present
        if (event.event === 'claude_event' && event.data) {
          const claudeEvent = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
          console.log('Claude event type:', claudeEvent.type);

          if (claudeEvent.type === 'message_start') {
            assistantMessageId = claudeEvent.message?.id || Date.now().toString();
            console.log('Message started:', assistantMessageId);
          } else if (claudeEvent.type === 'content_block_delta' && claudeEvent.delta_type === 'text') {
            // Accumulate text silently (don't display incrementally)
            currentText += claudeEvent.text;
          } else if (claudeEvent.type === 'message_stop') {
            const messageContent = claudeEvent.message?.content || [];
            assistantContent = messageContent;

            // Calculate elapsed time
            const endTime = Date.now();
            const timeTaken = startTime ? (endTime - startTime) / 1000 : 0;

            // Create final message with time taken
            const assistantMessage: Message = {
              id: assistantMessageId || Date.now().toString(),
              role: 'assistant',
              content: messageContent,
              timestamp: new Date(),
              model: claudeEvent.message?.model,
              usage: {
                ...claudeEvent.message?.usage,
                time_taken: timeTaken,
              },
            };

            setMessages((prev) => [...prev, assistantMessage]);
            setCurrentResponse('');
          }
        }

        // Handle tool execution events
        if (event.event === 'tool_call' && event.data) {
          const toolData = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
          setToolCalls((prev) => [...prev, { ...toolData, status: 'executing' }]);
        } else if (event.event === 'tool_result' && event.data) {
          const resultData = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
          setToolCalls((prev) =>
            prev.map((tc) => (tc.id === resultData.id ? { ...tc, status: 'completed' } : tc))
          );
        } else if (event.event === 'tool_error' && event.data) {
          const errorData = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
          setToolCalls((prev) =>
            prev.map((tc) => (tc.id === errorData.id ? { ...tc, status: 'error' } : tc))
          );
        } else if (event.event === 'done') {
          console.log('Done event received');
          setIsLoading(false);
        }
      });

      console.log('sendMessage completed');
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: [{ type: 'text', text: `Error: ${error instanceof Error ? error.message : 'Unknown error'}` }],
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setCurrentResponse('');
      setToolCalls([]);
      setResponseStartTime(null);
      setElapsedTime(0);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const renderContent = (content: ContentBlock[]) => {
    return content.map((block, index) => {
      if (block.type === 'text') {
        const textBlock = block as TextContent;
        return (
          <div key={index} className="prose prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {textBlock.text}
            </ReactMarkdown>
          </div>
        );
      } else if (block.type === 'image') {
        const imageBlock = block as ImageContent;
        return (
          <img
            key={index}
            src={`data:${imageBlock.source.media_type};base64,${imageBlock.source.data}`}
            alt="Seismic visualization"
            className="max-w-full rounded-lg my-2"
          />
        );
      } else if (block.type === 'tool_use') {
        const toolBlock = block as ToolUseContent;
        return (
          <div key={index} className="bg-blue-50 border border-blue-200 rounded-lg p-3 my-2">
            <div className="text-sm font-medium text-blue-900">🔧 Using tool: {toolBlock.name}</div>
            <pre className="text-xs text-blue-700 mt-1 overflow-x-auto">
              {JSON.stringify(toolBlock.input, null, 2)}
            </pre>
          </div>
        );
      } else if (block.type === 'tool_result') {
        const resultBlock = block as ToolResultContent;

        // Check if content is an array of content blocks (could include images)
        if (Array.isArray(resultBlock.content)) {
          return (
            <div key={index} className="bg-green-50 border border-green-200 rounded-lg p-3 my-2">
              <div className="text-sm font-medium text-green-900">✓ Tool result</div>
              {resultBlock.content.map((item: any, i: number) => {
                if (item.type === 'image') {
                  return (
                    <img
                      key={i}
                      src={`data:${item.source?.media_type || 'image/jpeg'};base64,${item.source?.data}`}
                      alt="Tool result image"
                      className="max-w-full rounded-lg my-2"
                    />
                  );
                } else if (item.type === 'text') {
                  return (
                    <pre key={i} className="text-xs text-green-700 mt-1 overflow-x-auto max-h-40">
                      {item.text?.slice(0, 500)}
                      {item.text && item.text.length > 500 && '...'}
                    </pre>
                  );
                } else {
                  return (
                    <pre key={i} className="text-xs text-green-700 mt-1 overflow-x-auto max-h-40">
                      {JSON.stringify(item, null, 2).slice(0, 500)}
                    </pre>
                  );
                }
              })}
            </div>
          );
        }

        // Original string/simple content handling
        return (
          <div key={index} className="bg-green-50 border border-green-200 rounded-lg p-3 my-2">
            <div className="text-sm font-medium text-green-900">✓ Tool result</div>
            <pre className="text-xs text-green-700 mt-1 overflow-x-auto max-h-40">
              {typeof resultBlock.content === 'string'
                ? resultBlock.content.slice(0, 500)
                : JSON.stringify(resultBlock.content, null, 2).slice(0, 500)}
              {(typeof resultBlock.content === 'string' ? resultBlock.content.length : JSON.stringify(resultBlock.content).length) > 500 && '...'}
            </pre>
          </div>
        );
      }
      return null;
    });
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">VDS Copilot</h1>
        <p className="text-sm text-gray-600">Your AI partner for seismic data exploration</p>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-3xl rounded-lg px-4 py-3 ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white border border-gray-200 text-gray-900'
                }`}
              >
                {renderContent(message.content)}
                {message.usage && (
                  <div className="text-xs text-gray-500 mt-3 pt-2 border-t border-gray-200 flex justify-between items-center">
                    <span>Tokens: {message.usage.input_tokens} in / {message.usage.output_tokens} out</span>
                    {message.usage.time_taken && (
                      <span className="font-medium text-gray-700">
                        ⏱️ {message.usage.time_taken.toFixed(2)}s
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Loading indicator with elapsed time */}
          {isLoading && !currentResponse && (
            <div className="flex justify-start">
              <div className="max-w-3xl rounded-lg px-6 py-4 bg-white border border-gray-200 text-gray-900">
                <div className="flex items-center space-x-3">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                  <span className="text-sm text-gray-600 font-medium">
                    VDS Copilot is thinking... {(elapsedTime / 1000).toFixed(1)}s
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Tool execution status */}
          {toolCalls.length > 0 && (
            <div className="flex justify-start">
              <div className="max-w-3xl rounded-lg px-4 py-3 bg-yellow-50 border border-yellow-200">
                <div className="text-sm font-medium text-yellow-900 mb-2">Executing tools...</div>
                {toolCalls.map((tc, i) => (
                  <div key={i} className="text-xs text-yellow-700">
                    {tc.status === 'executing' && '⏳ '}
                    {tc.status === 'completed' && '✓ '}
                    {tc.status === 'error' && '❌ '}
                    {tc.name}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="bg-white border-t border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about seismic data... (Press Enter to send, Shift+Enter for new line)"
              className="flex-1 rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              rows={3}
              disabled={isLoading}
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-medium"
            >
              {isLoading ? 'Sending...' : 'Send'}
            </button>
          </div>
          <div className="text-xs text-gray-500 mt-2">
            Try: "Show me inline 55000 from the Sepia survey" or "What surveys are available?"
          </div>
        </div>
      </div>
    </div>
  );
}
