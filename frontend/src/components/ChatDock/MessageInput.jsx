import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ArrowUp, 
  Plus, 
  Terminal, 
  Brain, 
  Trash2, 
  Cpu, 
  FileText, 
  Square
} from 'lucide-react';
import { useChat } from '../../context/ChatContext';
import './MessageInput.css';

const SLASH_COMMANDS = [
  { cmd: '/memory', label: 'Inspect Memory', desc: 'View semantic facts and episodic state', icon: Brain },
  { cmd: '/clear', label: 'Clear Session', desc: 'Reset conversation context', icon: Trash2 },
  { cmd: '/skills', label: 'List Skills', desc: 'Inspect procedural playbooks', icon: FileText },
  { cmd: '/status', label: 'System Status', desc: 'Connectivity and model health', icon: Cpu },
  { cmd: '/model', label: 'Switch Model', desc: 'Configure models in Settings', icon: Terminal },
];

/**
 * Floating Pill Input Bar
 */
export function MessageInput({ onSend, onStop, disabled = false, isHero = false }) {
  const navigate = useNavigate();
  const { clearChat, openOverview } = useChat();

  const [value, setValue] = useState('');
  const [slashIndex, setSlashIndex] = useState(0);
  const textareaRef = useRef(null);

  const isSlashMode = value.startsWith('/') && !value.includes(' ');
  const matchingCommands = isSlashMode
    ? SLASH_COMMANDS.filter((c) => c.cmd.toLowerCase().startsWith(value.toLowerCase()))
    : [];

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const executeCommand = (cmdObj) => {
    setValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    if (cmdObj.cmd === '/clear') {
      clearChat();
    } else if (cmdObj.cmd === '/memory' || cmdObj.cmd === '/skills') {
      openOverview('turn');
    } else if (cmdObj.cmd === '/status') {
      openOverview('telemetry');
    } else if (cmdObj.cmd === '/model') {
      navigate('/settings');
    } else {
      onSend(cmdObj.cmd);
    }
  };

  const handleStop = (e) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (onStop) {
      onStop();
    }
  };

  const handleSubmit = () => {
    if (disabled) {
      handleStop();
      return;
    }

    if (!value.trim()) return;

    if (value.trim() === '/clear') {
      executeCommand(SLASH_COMMANDS[1]);
      return;
    }

    if (isSlashMode && matchingCommands.length > 0) {
      executeCommand(matchingCommands[slashIndex] || matchingCommands[0]);
      return;
    }

    onSend(value);
    setValue('');

    requestAnimationFrame(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    });
  };

  const handleKeyDown = (e) => {
    if (isSlashMode && matchingCommands.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSlashIndex((prev) => (prev + 1) % matchingCommands.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSlashIndex((prev) => (prev - 1 + matchingCommands.length) % matchingCommands.length);
        return;
      }
      if (e.key === 'Tab' || (e.key === 'Enter' && !e.shiftKey)) {
        e.preventDefault();
        executeCommand(matchingCommands[slashIndex] || matchingCommands[0]);
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setValue('');
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className={`input-container ${isHero ? 'is-hero' : ''}`}>
      {/* Slash Command Overlay */}
      {isSlashMode && matchingCommands.length > 0 && (
        <div className="slash-dropdown animate-slide-up">
          <div className="slash-dropdown-header">
            <Terminal size={12} />
            <span>Commands</span>
          </div>
          <div className="slash-dropdown-list">
            {matchingCommands.map((item, idx) => {
              const Icon = item.icon;
              const isSelected = idx === slashIndex;
              return (
                <div
                  key={item.cmd}
                  className={`slash-item ${isSelected ? 'selected' : ''}`}
                  onClick={() => executeCommand(item)}
                  onMouseEnter={() => setSlashIndex(idx)}
                >
                  <Icon size={16} className="slash-item-icon" />
                  <div className="slash-item-content">
                    <span className="slash-item-cmd">{item.cmd}</span>
                    <span className="slash-item-desc">{item.desc}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Floating Pill */}
      <div className="input-pill">
        <button
          type="button"
          className="input-plus-btn"
          title="Attachments are not enabled yet"
          aria-label="Attachments are not enabled yet"
          disabled
        >
          <Plus size={18} />
        </button>

        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setSlashIndex(0);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Message Poseidon..."
          disabled={disabled}
          rows={1}
          aria-label="Message input"
        />

        <button
          type="button"
          className={`input-send-btn ${value.trim() ? 'active' : ''} ${disabled ? 'loading is-stop' : ''}`}
          onClick={disabled ? handleStop : handleSubmit}
          disabled={!value.trim() && !disabled}
          title={disabled ? 'Stop generating' : 'Send'}
          aria-label={disabled ? 'Stop generating' : 'Send message'}
        >
          {disabled ? <Square size={13} fill="currentColor" /> : <ArrowUp size={18} />}
        </button>
      </div>
    </div>
  );
}

export default MessageInput;
