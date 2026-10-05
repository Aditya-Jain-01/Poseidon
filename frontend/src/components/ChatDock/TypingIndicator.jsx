import React from 'react';
import './TypingIndicator.css';

/**
 * Minimal typing indicator — three pulsing dots matching the conversational bubble layout.
 */
export function TypingIndicator() {
  return (
    <div className="typing-indicator-row animate-fade-in">
      <div className="typing-bubble">
        <span className="typing-dot" style={{ animationDelay: '0ms' }} />
        <span className="typing-dot" style={{ animationDelay: '160ms' }} />
        <span className="typing-dot" style={{ animationDelay: '320ms' }} />
      </div>
    </div>
  );
}

export default TypingIndicator;
