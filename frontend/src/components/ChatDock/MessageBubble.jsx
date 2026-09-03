import React, { useState } from 'react';
import Markdown from 'react-markdown';
import { 
  ShieldAlert, 
  Sparkles, 
  Terminal, 
  FileEdit, 
  CheckCircle2, 
  Copy, 
  Check
} from 'lucide-react';
import { useChat } from '../../context/ChatContext';
import { useHealth } from '../../context/HealthContext';
import { useAgents } from '../../context/AgentContext';
import './MessageBubble.css';

/**
 * Poseidon Message Renderer
 */
export function MessageBubble({ message }) {
  const { openOverview } = useChat();
  const { modelName, isConnected } = useHealth();
  const { agents } = useAgents();
  const [copied, setCopied] = useState(false);

  const isUser = message.role === 'user';
  const isError = message.isError;
  const approval = message.approvalRequest;

  const dynamicModel = message.model || modelName || (isConnected ? 'Poseidon Agent' : 'Connecting...');
  const timeStr = formatRelativeTime(message.timestamp);

  const handleCopy = () => {
    if (!message.content) return;
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleOpenSecurity = () => {
    openOverview('security');
  };

  if (isUser) {
    return (
      <div className="user-message-row animate-fade-in">
        <div className="user-message-container">
          <div className="user-pill-card">
            <p className="user-text-content">{message.content}</p>
          </div>
          <div className="user-action-bar">
            <button 
              className="user-copy-btn" 
              onClick={handleCopy}
              title={copied ? "Copied!" : "Copy message"}
              aria-label="Copy message"
            >
              {copied ? <Check size={12} /> : <Copy size={12} />}
            </button>
          </div>
        </div>
      </div>
    );
  }

  const agentId = (message.activeAgent || 'octavious').toLowerCase();
  const agentInfo = agents?.find((a) => a.id === agentId) || {
    id: agentId,
    display_name: agentId === 'octavious' ? 'Octavious' : agentId === 'nereus' ? 'Nereus' : agentId === 'kraken' ? 'Kraken' : (agentId.charAt(0).toUpperCase() + agentId.slice(1)),
    avatar: agentId === 'octavious' ? 'O' : agentId === 'nereus' ? 'N' : agentId === 'kraken' ? 'K' : (agentId[0]?.toUpperCase() || 'A'),
    color: agentId === 'octavious' ? '#39ff14' : agentId === 'nereus' ? '#00bfff' : agentId === 'kraken' ? '#ff4500' : '#a855f7',
  };

  return (
    <div className={`agent-message-row animate-fade-in ${isError ? 'is-error' : ''}`}>
      <div className="agent-message-container">
        {/* Model & Meta Tag Row */}
        <div className="agent-model-meta-row">
          {/* Agent Identity Badge */}
          <div 
            className="agent-identity-badge-pill"
            style={{
              borderColor: `${agentInfo.color}55`,
              backgroundColor: `${agentInfo.color}18`,
              boxShadow: `0 0 12px ${agentInfo.color}22`
            }}
            title={`Handled by Agent: ${agentInfo.display_name}`}
          >
            <span 
              className="agent-badge-avatar"
              style={{ backgroundColor: agentInfo.color }}
            >
              {agentInfo.avatar || agentInfo.display_name?.[0] || 'A'}
            </span>
            <span className="agent-badge-name" style={{ color: agentInfo.color }}>
              {agentInfo.display_name}
            </span>
          </div>

          <div className="gemini-model-badge" title={`Active Model: ${dynamicModel}`}>
            <Sparkles size={12} className="sparkle-icon" />
            <span className="gemini-model-name">{dynamicModel}</span>
          </div>

          <div className="agent-meta-tags">
            {message.runId && (
              <span className="message-run-tag" title={`Run ID: ${message.runId}`}>
                run:{message.runId.slice(0, 8)}
              </span>
            )}
            {timeStr && <span className="message-time-tag">{timeStr}</span>}
          </div>
        </div>

        {/* Agent Markdown Content */}
        {message.content && (
          <div className="agent-markdown-body">
            <Markdown
              components={{
                code({ className = '', children, ...props }) {
                  return <code className={`inline-code ${className}`.trim()} {...props}>{children}</code>;
                },
                pre({ children, ...props }) {
                  return (
                    <pre className="code-block" {...props}>
                      {children}
                    </pre>
                  );
                },
                a({ children, ...props }) {
                  return <a target="_blank" rel="noopener noreferrer" {...props}>{children}</a>;
                },
              }}
            >
              {message.content}
            </Markdown>
          </div>
        )}

        {/* Structured Tool Call Execution Cards */}
        {message.toolCalls && message.toolCalls.map((tc, idx) => (
          <div key={idx} className="tool-execution-block">
            <div className="tool-block-header">
              <div className="tool-block-title">
                {tc.name === 'bash' ? (
                  <Terminal size={13} className="tool-block-icon" />
                ) : (
                  <FileEdit size={13} className="tool-block-icon" />
                )}
                <span className="tool-name-label">{tc.name}</span>
              </div>
              <span className={`tool-status-pill ${tc.status?.toLowerCase() || 'completed'}`}>
                <CheckCircle2 size={11} />
                <span>{tc.status || 'Executed'}</span>
              </span>
            </div>
            <div className="tool-block-body">
              {tc.command && <div className="tool-command-line"><code>{tc.command}</code></div>}
              {tc.details && <div className="tool-desc-text">{tc.details}</div>}
              {tc.meta && <div className="tool-meta-text">{tc.meta}</div>}
            </div>
          </div>
        ))}

        {/* Inline Tool Approval Gate Callout */}
        {approval && (
          <div className={`inline-approval-callout risk-${approval.risk_level || 'medium'}`}>
            <div className="callout-header">
              <ShieldAlert size={14} className="callout-icon" />
              <span className="callout-title">Tool Approval Required: <strong>{approval.tool}</strong></span>
              <span className={`callout-risk-tag ${approval.risk_level || 'medium'}`}>
                {approval.risk_level?.toUpperCase()} RISK
              </span>
            </div>
            <div className="callout-details">
              <p className="callout-sub">
                Operator verification required before executing side-effect tool action.
              </p>
              <button className="callout-review-btn" onClick={handleOpenSecurity}>
                Inspect Diff &amp; Review in Security Gate →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Format a timestamp into a short relative string.
 */
function formatRelativeTime(timestamp) {
  if (!timestamp) return '';
  const now = Date.now();
  const then = new Date(timestamp).getTime();
  const diffSec = Math.floor((now - then) / 1000);

  if (diffSec < 10) return 'just now';
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return new Date(timestamp).toLocaleDateString();
}

export default MessageBubble;
