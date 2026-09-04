import React, { useState } from 'react';
import { BrainCircuit, ChevronDown, ChevronRight } from 'lucide-react';
import './TypingIndicator.css';

/**
 * Real-time Agent Thinking & Execution State (DeepSeek Harness alignment)
 */
export function TypingIndicator() {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="dsh-thinking-container animate-fade-in">
      <div className={`deepseek-think-container ${isExpanded ? 'is-open' : ''}`}>
        <button
          type="button"
          className="deepseek-think-header-btn"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <div className="think-header-left">
            <BrainCircuit size={13} className="think-brain-icon" />
            <span className="think-label">Think · ~5436</span>
          </div>
          <div className="think-header-right">
            {isExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          </div>
        </button>
        {isExpanded && (
          <div className="deepseek-think-body animate-fade-in">
            <p className="think-body-text">
              Tracing episodic memories, evaluating sandbox paths, and formulating verification contract...
            </p>
          </div>
        )}
      </div>

      <div className="nothing-instrument-loading">
        <div className="loading-header-row">
          <div className="loading-left">
            <span className="diving-pulse-dot" />
            <span className="loading-tag nothing-label">[ INFERENCE IN PROGRESS ]</span>
          </div>
          <span className="loading-status-val nothing-label">RUNNING</span>
        </div>
        <div className="segmented-progress-bar">
          <div className="segmented-block filled pulse-seq-1" />
          <div className="segmented-block filled pulse-seq-2" />
          <div className="segmented-block filled pulse-seq-3" />
          <div className="segmented-block filled pulse-seq-4" />
          <div className="segmented-block pulse-seq-5" />
          <div className="segmented-block pulse-seq-6" />
          <div className="segmented-block" />
          <div className="segmented-block" />
        </div>
      </div>
    </div>
  );
}

export default TypingIndicator;
