import React, { useRef, useEffect } from 'react';
import { Plus, X } from 'lucide-react';
import { useChat } from '../../context/ChatContext';
import MessageBubble from './MessageBubble';
import MessageInput from './MessageInput';
import TypingIndicator from './TypingIndicator';
import './ChatDock.css';

/**
 * Persistent chat panel docked to the right side of the app.
 * Visible on every tab. Collapsible via the topbar toggle.
 */
export function ChatDock() {
  const { messages, isLoading, sendMessage, clearChat } = useChat();
  const messagesEndRef = useRef(null);
  const messageListRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  return (
    <div className="chat-dock">
      {/* Header */}
      <div className="chat-dock-header">
        <h3 className="chat-dock-title">Chat</h3>
        <div className="chat-dock-actions">
          <button
            className="chat-dock-action-btn"
            onClick={clearChat}
            title="New chat"
            aria-label="Start new chat"
          >
            <Plus size={15} />
            <span>New</span>
          </button>
        </div>
      </div>

      {/* Message List */}
      <div className="chat-dock-messages" ref={messageListRef}>
        {messages.length === 0 ? (
          <div className="chat-dock-empty">
            <div className="chat-dock-empty-icon">🔱</div>
            <p className="chat-dock-empty-title">Welcome to Poseidon</p>
            <p className="chat-dock-empty-sub">
              Type a message to start a conversation with your agent.
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))
        )}

        {isLoading && <TypingIndicator />}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <MessageInput onSend={sendMessage} disabled={isLoading} />
    </div>
  );
}

export default ChatDock;
