import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '../types';

interface ChatPanelProps {
  messages: Message[];
  onSendMessage: (message: string) => Promise<void>;
  isLoading?: boolean;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ messages, onSendMessage, isLoading }) => {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const message = inputValue.trim();
    setInputValue('');
    await onSendMessage(message);
  };

  return (
    <>
      <div className="chat-container">
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">💬</div>
              <div className="empty-state-text">开始提问吧</div>
              <div className="empty-state-text" style={{ marginTop: '8px', fontSize: '12px' }}>
                上传文档后，您可以针对文档内容提问
              </div>
            </div>
          ) : (
            messages.map(message => (
              <div key={message.id} className={`message ${message.role}`}>
                <div className="message-avatar">
                  {message.role === 'user' ? '👤' : '🤖'}
                </div>
                <div>
                  <div className="message-sender">
                    {message.role === 'user' ? '您' : 'AI助手'}
                  </div>
                  <div className="message-content">
                    {message.role === 'assistant' ? (
                      <div className="message-text markdown-content">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            // 标题样式
                            h1: ({ children }) => <h1 className="md-h1">{children}</h1>,
                            h2: ({ children }) => <h2 className="md-h2">{children}</h2>,
                            h3: ({ children }) => <h3 className="md-h3">{children}</h3>,
                            h4: ({ children }) => <h4 className="md-h4">{children}</h4>,
                            h5: ({ children }) => <h5 className="md-h5">{children}</h5>,
                            h6: ({ children }) => <h6 className="md-h6">{children}</h6>,
                            // 加粗
                            strong: ({ children }) => <strong className="md-strong">{children}</strong>,
                            // 斜体
                            em: ({ children }) => <em className="md-em">{children}</em>,
                            // 代码
                            code: ({ className, children }) => (
                              <code className={className ? `md-code-block ${className}` : 'md-inline-code'}>
                                {children}
                              </code>
                            ),
                            // 代码块
                            pre: ({ children }) => <pre className="md-pre">{children}</pre>,
                            // 列表
                            ul: ({ children }) => <ul className="md-ul">{children}</ul>,
                            ol: ({ children }) => <ol className="md-ol">{children}</ol>,
                            li: ({ children }) => <li className="md-li">{children}</li>,
                            // 引用
                            blockquote: ({ children }) => <blockquote className="md-blockquote">{children}</blockquote>,
                            // 分隔线
                            hr: () => <hr className="md-hr" />,
                            // 链接
                            a: ({ href, children }) => (
                              <a href={href} className="md-a" target="_blank" rel="noopener noreferrer">
                                {children}
                              </a>
                            ),
                            // 表格
                            table: ({ children }) => <div className="md-table-wrapper"><table className="md-table">{children}</table></div>,
                            thead: ({ children }) => <thead className="md-thead">{children}</thead>,
                            tbody: ({ children }) => <tbody className="md-tbody">{children}</tbody>,
                            tr: ({ children }) => <tr className="md-tr">{children}</tr>,
                            th: ({ children }) => <th className="md-th">{children}</th>,
                            td: ({ children }) => <td className="md-td">{children}</td>,
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <div className="message-text">{message.content}</div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}

          {isLoading && (
            <div className="message assistant">
              <div className="message-avatar">🤖</div>
              <div>
                <div className="message-sender">AI助手</div>
                <div className="message-content">
                  <div className="typing-indicator">
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="input-container">
        <form className="input-wrapper" onSubmit={handleSubmit}>
          <textarea
            className="message-input"
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            placeholder="输入您的问题..."
            rows={1}
            disabled={isLoading}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <button type="submit" className="send-button" disabled={!inputValue.trim() || isLoading}>
            发送
          </button>
        </form>
      </div>
    </>
  );
};
