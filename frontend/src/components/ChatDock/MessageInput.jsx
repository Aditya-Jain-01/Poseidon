import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp, Plus, Shield, ChevronDown } from 'lucide-react';
import { useHealth } from '../../context/HealthContext';
import './MessageInput.css';

/**
 * Modern Developer Prompt Box (DeepSeek Harness / Clean Workspace Style)
 */
export function MessageInput({ onSend, disabled = false, isHero = false }) {
  const { modelName, isConnected } = useHealth();
  const dynamicModel = modelName || (isConnected ? 'Poseidon Agent' : 'Connecting...');

  const [value, setValue] = useState('');
  const textareaRef = useRef(null);

  // Auto-resize the textarea based on content
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const handleSubmit = () => {
    if (!value.trim() || disabled) return;
    onSend(value);
    setValue('');

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
    <div className={`message-input-dock ${isHero ? 'is-hero-input' : ''}`}>
      <div className="message-command-box">
        {/* Text Area */}
        <textarea
          ref={textareaRef}
          className="command-textarea"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe what you want to build"
          disabled={disabled}
          rows={1}
          aria-label="Agent command execution input"
        />

        {/* Bottom Control Bar */}
        <div className="command-bar-bottom">
          {/* Left Actions */}
          <div className="command-bottom-left">
            <button 
              type="button" 
              className="input-circle-add-btn" 
              title="Add attachment or files"
            >
              <Plus size={14} />
            </button>

            <button 
              type="button" 
              className="input-permission-pill" 
              title="Workspace Execution Permissions"
            >
              <Shield size={13} className="pill-shield-icon" />
              <span>Workspace Write</span>
              <ChevronDown size={11} className="pill-chevron-icon" />
            </button>
          </div>

          {/* Right Actions */}
          <div className="command-bottom-right">
            <button 
              type="button" 
              className="input-model-selector-btn" 
              title={`Active Model: ${dynamicModel}`}
            >
              <span className="model-selector-name">{dynamicModel}</span>
              <ChevronDown size={11} className="pill-chevron-icon" />
            </button>

            <button
              className={`command-send-btn ${value.trim() ? 'active' : ''}`}
              onClick={handleSubmit}
              disabled={!value.trim() || disabled}
              title="Send (Enter ↵)"
              aria-label="Send message"
            >
              <ArrowUp size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default MessageInput;
