import React from 'react';
import './TypingIndicator.css';

/**
 * Three pulsing dots that show while the agent is thinking.
 */
export function TypingIndicator() {
  return (
    <div className="typing-indicator">
      <div className="typing-bubble">
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-dot" />
      </div>
    </div>
  );
}

export default TypingIndicator;
