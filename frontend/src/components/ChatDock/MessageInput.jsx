import React, { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import './MessageInput.css';

/**
 * Auto-resizing textarea with Enter-to-send and Shift+Enter for newlines.
 */
export function MessageInput({ onSend, disabled = false }) {
  const [value, setValue] = useState('');
  const textareaRef = useRef(null);

  // Auto-resize the textarea based on content
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, [value]);

  const handleSubmit = () => {
    if (!value.trim() || disabled) return;
    onSend(value);
    setValue('');

    // Reset height after clearing
    requestAnimationFrame(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    });
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="message-input-container">
      <textarea
        ref={textareaRef}
        className="message-input"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type a message..."
        disabled={disabled}
        rows={1}
        aria-label="Chat message input"
      />
      <button
        className="message-send-btn"
        onClick={handleSubmit}
        disabled={!value.trim() || disabled}
        title="Send message"
        aria-label="Send message"
      >
        <Send size={16} />
      </button>
    </div>
  );
}

export default MessageInput;
