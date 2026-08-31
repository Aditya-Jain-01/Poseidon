import React from 'react';
import './TypingIndicator.css';

/**
 * Real-time Agent Thinking & Execution State
 */
export function TypingIndicator() {
  return (
    <div className="dsh-thinking-container animate-fade-in">
      <div className="dsh-deep-diving-status">
        <span>Agent synthesizing response...</span>
        <span className="diving-pulse-dot" />
      </div>
    </div>
  );
}

export default TypingIndicator;
