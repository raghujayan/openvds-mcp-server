/**
 * ChatPage - Main chat interface for VDS Explorer
 */

import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message, ChatMessage, ContentBlock, TextContent, ToolUseContent, ToolResultContent, ImageContent } from '../types/chat';
import { sendMessage } from '../services/chatService';
import { CollapsibleToolCall, CollapsibleImage } from '../components';

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
          <div key={index} className="prose prose-sm" style={{ maxWidth: 'none', marginLeft: 0, marginRight: 0 }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {textBlock.text}
            </ReactMarkdown>
          </div>
        );
      } else if (block.type === 'image') {
        const imageBlock = block as ImageContent;
        return (
          <CollapsibleImage
            key={index}
            src={`data:${imageBlock.source.media_type};base64,${imageBlock.source.data}`}
            alt="Seismic visualization"
            title="Seismic Data Visualization"
          />
        );
      } else if (block.type === 'tool_use') {
        const toolBlock = block as ToolUseContent;
        return (
          <CollapsibleToolCall
            key={index}
            name={toolBlock.name}
            input={toolBlock.input}
            status="completed"
          />
        );
      } else if (block.type === 'tool_result') {
        const resultBlock = block as ToolResultContent;

        // Check if content is an array of content blocks (could include images)
        if (Array.isArray(resultBlock.content)) {
          return (
            <div key={index} style={{ margin: '8px 0' }}>
              {resultBlock.content.map((item: any, i: number) => {
                if (item.type === 'image') {
                  return (
                    <CollapsibleImage
                      key={i}
                      src={`data:${item.source?.media_type || 'image/jpeg'};base64,${item.source?.data}`}
                      alt="Tool result image"
                      title="Tool Result - Seismic Data"
                    />
                  );
                } else if (item.type === 'text') {
                  return (
                    <div key={i} style={{
                      backgroundColor: '#3a4149',
                      border: '1px solid rgba(206, 223, 231, 0.3)',
                      borderRadius: '8px',
                      padding: '12px',
                      margin: '8px 0'
                    }}>
                      <div style={{ fontSize: '14px', fontWeight: 500, color: '#cedfe7' }}>✓ Tool result</div>
                      <pre style={{
                        fontSize: '11px',
                        color: '#9ca3af',
                        marginTop: '4px',
                        overflowX: 'auto',
                        maxHeight: '160px',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word'
                      }}>
                        {item.text?.slice(0, 500)}
                        {item.text && item.text.length > 500 && '...'}
                      </pre>
                    </div>
                  );
                } else {
                  return (
                    <div key={i} style={{
                      backgroundColor: '#3a4149',
                      border: '1px solid rgba(206, 223, 231, 0.3)',
                      borderRadius: '8px',
                      padding: '12px',
                      margin: '8px 0'
                    }}>
                      <div style={{ fontSize: '14px', fontWeight: 500, color: '#cedfe7' }}>✓ Tool result</div>
                      <pre style={{
                        fontSize: '11px',
                        color: '#9ca3af',
                        marginTop: '4px',
                        overflowX: 'auto',
                        maxHeight: '160px',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word'
                      }}>
                        {JSON.stringify(item, null, 2).slice(0, 500)}
                      </pre>
                    </div>
                  );
                }
              })}
            </div>
          );
        }

        // Original string/simple content handling
        return (
          <div key={index} style={{
            backgroundColor: '#3a4149',
            border: '1px solid rgba(206, 223, 231, 0.3)',
            borderRadius: '8px',
            padding: '12px',
            margin: '8px 0'
          }}>
            <div style={{ fontSize: '14px', fontWeight: 500, color: '#cedfe7' }}>✓ Tool result</div>
            <pre style={{
              fontSize: '11px',
              color: '#9ca3af',
              marginTop: '4px',
              overflowX: 'auto',
              maxHeight: '160px',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}>
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
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      width: '100%',
      height: '100vh',
      backgroundColor: '#2c323a',
      overflow: 'hidden'
    }}>
      {/* Header - Bluware Dark Theme */}
      <header
        style={{
          height: '64px',
          backgroundColor: '#2c323a',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <img
            src="/datahub-logo.png"
            alt="Bluware DataHub"
            className="object-contain"
            style={{
              width: '40px',
              height: '40px',
              filter: 'drop-shadow(1px 1px 2px rgba(0,0,0,0.5))'
            }}
          />
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <h1 style={{ color: '#cedfe7', fontSize: '18px', fontWeight: 'bold', margin: 0 }}>VDS Copilot</h1>
            <p style={{ color: '#9ca3af', fontSize: '10px', margin: 0 }}>AI-Powered Seismic Data Exploration</p>
          </div>
        </div>
      </header>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        overflowX: 'hidden',
        padding: '16px 24px'
      }}>
        <div style={{ maxWidth: '896px', margin: '0 auto' }}>
          {messages.map((message) => (
            <div
              key={message.id}
              style={{
                display: 'flex',
                justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                marginBottom: '16px'
              }}
            >
              <div
                style={{
                  maxWidth: '768px',
                  borderRadius: '8px',
                  padding: '12px 16px',
                  ...(message.role === 'user'
                    ? {
                        backgroundColor: '#1976d2',
                        color: '#fff'
                      }
                    : {
                        backgroundColor: '#3a4149',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        color: '#f4f4f4'
                      })
                }}
              >
                {renderContent(message.content)}
                {message.usage && (
                  <div style={{
                    fontSize: '11px',
                    marginTop: '12px',
                    paddingTop: '8px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    borderTop: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#9ca3af'
                  }}>
                    <span>Tokens: {message.usage.input_tokens} in / {message.usage.output_tokens} out</span>
                    {message.usage.time_taken && (
                      <span style={{ fontWeight: 500, color: '#cedfe7' }}>
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
            <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: '16px' }}>
              <div style={{
                maxWidth: '768px',
                borderRadius: '8px',
                padding: '16px 24px',
                backgroundColor: '#3a4149',
                border: '1px solid rgba(255, 255, 255, 0.1)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    <div style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      backgroundColor: '#cedfe7',
                      animation: 'bounce 1s infinite',
                      animationDelay: '0ms'
                    }}></div>
                    <div style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      backgroundColor: '#cedfe7',
                      animation: 'bounce 1s infinite',
                      animationDelay: '150ms'
                    }}></div>
                    <div style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      backgroundColor: '#cedfe7',
                      animation: 'bounce 1s infinite',
                      animationDelay: '300ms'
                    }}></div>
                  </div>
                  <span style={{ fontSize: '14px', fontWeight: 500, color: '#9ca3af' }}>
                    VDS Copilot is thinking... {(elapsedTime / 1000).toFixed(1)}s
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Tool execution status */}
          {toolCalls.length > 0 && (
            <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: '16px' }}>
              <div style={{
                maxWidth: '768px',
                borderRadius: '8px',
                padding: '12px 16px',
                backgroundColor: '#3a4149',
                border: '1px solid rgba(206, 223, 231, 0.3)'
              }}>
                <div style={{ fontSize: '14px', fontWeight: 500, marginBottom: '8px', color: '#cedfe7' }}>
                  Executing tools...
                </div>
                {toolCalls.map((tc, i) => (
                  <div key={i} style={{ fontSize: '12px', color: '#9ca3af' }}>
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
      <div style={{
        backgroundColor: '#2c323a',
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        padding: '16px 24px',
        flexShrink: 0
      }}>
        <div style={{ maxWidth: '1024px', margin: '0 auto', width: '100%' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about seismic data... (Press Enter to send, Shift+Enter for new line)"
              style={{
                flex: 1,
                borderRadius: '8px',
                padding: '12px 16px',
                backgroundColor: '#3a4149',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                color: '#f4f4f4',
                fontSize: '14px',
                resize: 'none',
                outline: 'none',
                fontFamily: 'inherit'
              }}
              onFocus={(e) => e.currentTarget.style.borderColor = '#cedfe7'}
              onBlur={(e) => e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)'}
              rows={3}
              disabled={isLoading}
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              style={{
                padding: '12px 24px',
                backgroundColor: isLoading || !input.trim() ? '#6b7280' : '#1976d2',
                color: '#fff',
                borderRadius: '8px',
                border: 'none',
                fontWeight: 500,
                fontSize: '14px',
                cursor: isLoading || !input.trim() ? 'not-allowed' : 'pointer',
                transition: 'background-color 0.2s',
                whiteSpace: 'nowrap'
              }}
              onMouseEnter={(e) => {
                if (!isLoading && input.trim()) {
                  e.currentTarget.style.backgroundColor = '#1565c0';
                }
              }}
              onMouseLeave={(e) => {
                if (!isLoading && input.trim()) {
                  e.currentTarget.style.backgroundColor = '#1976d2';
                }
              }}
            >
              {isLoading ? 'Sending...' : 'Send'}
            </button>
          </div>
          <div style={{ fontSize: '12px', marginTop: '8px', color: '#9ca3af' }}>
            Try: "Show me inline 55000 from the Sepia survey" or "What surveys are available?"
          </div>
        </div>
      </div>
    </div>
  );
}
