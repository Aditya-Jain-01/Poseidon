import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Plus, Maximize2, Minimize2, ChevronsLeft, ChevronsRight, RotateCcw } from 'lucide-react';
import { useChat } from '../../context/ChatContext';
import MessageBubble from './MessageBubble';
import MessageInput from './MessageInput';
import TypingIndicator from './TypingIndicator';
import './ChatDock.css';

/**
 * Persistent chat panel docked to the right side of the app.
 * Supports interactive dragging resize, full width toggle, and state persistence.
 */
export function ChatDock() {
  const {
    messages,
    isLoading,
    sendMessage,
    clearChat,
    dockWidth,
    setDockWidth,
    isExpanded,
    toggleExpand,
    toggleDock
  } = useChat();

  const messagesEndRef = useRef(null);
  const messageListRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  // Handle Dragging Resize on the Left Handle
  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);

    const handleMouseMove = (moveEvent) => {
      const newWidth = window.innerWidth - moveEvent.clientX;
      setDockWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  }, [setDockWidth]);

  return (
    <div className={`chat-dock ${isDragging ? 'is-resizing' : ''}`}>
      {/* Left Resize Drag Handle */}
      <div
        className="chat-dock-resize-handle"
        onMouseDown={handleMouseDown}
        onDoubleClick={() => setDockWidth(dockWidth > 550 ? 420 : 650)}
        title="Drag to resize chat panel (Double-click to toggle width)"
      >
        <div className="resize-grip-line" />
      </div>

      {/* Header */}
      <div className="chat-dock-header">
        <div className="chat-dock-header-left">
          <h3 className="chat-dock-title">Chat</h3>
          <span className="chat-dock-size-indicator mono">
            {isExpanded ? 'Full' : `${Math.round(dockWidth)}px`}
          </span>
        </div>

        <div className="chat-dock-actions">
          {/* Quick Expand / Maximize Toggle */}
          <button
            className={`chat-dock-action-btn ${isExpanded ? 'active' : ''}`}
            onClick={toggleExpand}
            title={isExpanded ? 'Collapse to standard width' : 'Expand chat width'}
            aria-label="Expand chat"
          >
            {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            <span>{isExpanded ? 'Compact' : 'Expand'}</span>
          </button>

          {/* New Chat Button */}
          <button
            className="chat-dock-action-btn"
            onClick={clearChat}
            title="Start a new chat"
            aria-label="Start new chat"
          >
            <Plus size={14} />
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
              Type a message to start a conversation with your agent. Drag the left border to expand this panel.
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
