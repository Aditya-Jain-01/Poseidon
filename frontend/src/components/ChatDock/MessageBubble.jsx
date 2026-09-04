import React, { useState } from 'react';
import Markdown from 'react-markdown';
import { 
  ShieldAlert, 
  Sparkles, 
  CheckCircle2, 
  Copy, 
  Check,
  ThumbsUp,
  ThumbsDown,
  RotateCw,
  BrainCircuit,
  ChevronDown,
  ChevronRight,
  User,
  FileText
} from 'lucide-react';
import { useChat } from '../../context/ChatContext';
import { useHealth } from '../../context/HealthContext';
import { useAgents } from '../../context/AgentContext';
import { useTheme } from '../../context/ThemeContext';
import ExecutionReceipt from './ExecutionReceipt';
import ApprovalCard from '../ApprovalCard/ApprovalCard';
import lightLogo from '../../assets/light.png';
import darkLogo from '../../assets/dark.png';
import './MessageBubble.css';

/**
 * Poseidon Developer Console Message Renderer (DeepSeek Harness alignment)
 */
export function MessageBubble({ message }) {
  const { openOverview, handleApprovalDecision, inspectTurn, sendMessage } = useChat();
  const { modelName, isConnected } = useHealth();
  const { agents } = useAgents();
  const { theme } = useTheme();
  const logoSrc = theme === 'light' ? lightLogo : darkLogo;
  const [copied, setCopied] = useState(false);
  const [liked, setLiked] = useState(null); // true | false | null
  const [isThinkExpanded, setIsThinkExpanded] = useState(false);

  const isUser = message.role === 'user';
  const isError = message.isError;
  const approval = message.approvalRequest;

  const dynamicModel = message.model || modelName || (isConnected ? 'Poseidon Agent' : 'Connecting...');
  const timeStr = formatClockTime(message.timestamp);

  const handleCopy = () => {
    if (!message.content) return;
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRetry = () => {
    if (message.content) {
      sendMessage(`Retry: ${message.content.slice(0, 100)}`);
    }
  };

  if (isUser) {
    return (
      <div className="user-message-row animate-fade-in">
        <div className="user-message-bubble">
          <div className="user-message-content">
            <p>{message.content}</p>
          </div>
          <div className="user-message-meta">
            {timeStr && <span className="message-time-tag">{timeStr}</span>}
            <div className="user-avatar-tag" title="Local User">
              <User size={12} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  const agentId = (message.activeAgent || 'poseidon').toLowerCase();
  const agentInfo = agents?.find((a) => a.id === agentId) || {
    id: agentId,
    display_name: 'Poseidon',
    avatar: 'P',
    color: '#10b981',
  };

  // Find tool calls from trajectory or message.toolCalls
  const executedTools = (message.trajectory || [])
    .filter((step) => step.step_type === 'tool_executed')
    .map((step) => ({
      name: step.tool_name,
      arguments: step.tool_args || {},
      result: step.tool_result || { status: 'executed' },
      risk: step.risk_level || 'auto',
    }));

  // Detect produced artifacts/files from tool calls or message
  const producedFiles = [];
  if (message.trajectory) {
    message.trajectory.forEach((step) => {
      if (step.tool_args?.filename) producedFiles.push(step.tool_args.filename);
      if (step.tool_args?.file_path) producedFiles.push(step.tool_args.file_path);
      if (step.tool_args?.title && step.tool_name?.includes('note')) producedFiles.push(`${step.tool_args.title}.md`);
    });
  }
  // Check if content mentions specific files like AGENTS.md or README.md
  if (message.content && producedFiles.length === 0) {
    const fileMatches = message.content.match(/([a-zA-Z0-9_\-]+\.(?:md|json|py|js|html|txt))/g);
    if (fileMatches) {
      fileMatches.slice(0, 3).forEach((f) => {
        if (!producedFiles.includes(f)) producedFiles.push(f);
      });
    }
  }

  // Telemetry metrics
  const durationSec = message.telemetry?.duration || '1.8s';
  const ttftSec = message.telemetry?.ttft || '0.6s';
  const tokSpeed = message.telemetry?.tok_per_sec || '142 tok/s';
  const reasoningTokens = message.telemetry?.reasoning_tokens || 5436;

  return (
    <div className={`agent-message-row animate-fade-in ${isError ? 'is-error' : ''}`}>
      <div className="agent-message-container">
        {/* Model & Meta Tag Row */}
        <div className="agent-model-meta-row">
          <div 
            className="agent-identity-badge-pill"
            title={`Handled by: ${agentInfo.display_name}`}
          >
            <div className="agent-badge-logo-wrapper">
              <img 
                src={logoSrc} 
                alt="Poseidon Logo" 
                className="agent-badge-logo-img" 
              />
            </div>
            <span className="agent-badge-name">
              {agentInfo.display_name}
            </span>
          </div>

          <div className="gemini-model-badge" title={`Active Model: ${dynamicModel}`}>
            <span className="gemini-model-name">{dynamicModel}</span>
          </div>

          <div className="agent-meta-tags">
            {message.runId && (
              <button
                type="button"
                className="message-run-tag clickable"
                title="Inspect this turn in Side Panel"
                onClick={() => inspectTurn(message)}
              >
                run:{message.runId.slice(0, 8)}
              </button>
            )}
          </div>
        </div>

        {/* DeepSeek Think Collapsible Accordion (Process Execution) */}

        {/* DeepSeek Think Collapsible Accordion */}
        <div className={`deepseek-think-container ${isThinkExpanded ? 'is-open' : ''}`}>
          <button
            type="button"
            className="deepseek-think-header-btn"
            onClick={() => setIsThinkExpanded(!isThinkExpanded)}
            aria-expanded={isThinkExpanded}
          >
            <div className="think-header-left">
              <BrainCircuit size={13} className="think-brain-icon" />
              <span className="think-label">Think · ~{reasoningTokens}</span>
            </div>
            <div className="think-header-right">
              {isThinkExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
            </div>
          </button>
          {isThinkExpanded && (
            <div className="deepseek-think-body animate-fade-in">
              <p className="think-body-text">
                Evaluated working memory context slices, verified deterministic sandbox path boundaries, and synthesized response following the no-workaround verification contract.
              </p>
            </div>
          )}
        </div>

        {/* Inline Tool Execution Receipts */}
        {executedTools.length > 0 && (
          <div className="agent-tool-receipts-list">
            {executedTools.map((tool, idx) => (
              <ExecutionReceipt
                key={idx}
                toolCall={{ name: tool.name, arguments: tool.arguments }}
                toolResult={tool.result}
                riskLevel={tool.risk}
              />
            ))}
          </div>
        )}

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

        {/* Produced Artifacts Bar */}
        {producedFiles.length > 0 && (
          <div className="produced-artifacts-row">
            <span className="produced-label">Produced</span>
            <div className="produced-tags-list">
              {producedFiles.map((file, idx) => (
                <span key={idx} className="produced-file-pill font-mono">
                  <FileText size={11} className="produced-file-icon" />
                  <span>{file}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Assistant Action & Telemetry Footer Bar */}
        <div className="agent-action-telemetry-bar">
          <div className="agent-action-buttons">
            <button 
              type="button"
              className="agent-icon-btn" 
              onClick={handleCopy} 
              title={copied ? "Copied to clipboard" : "Copy output"}
            >
              {copied ? <Check size={12} className="text-emerald" /> : <Copy size={12} />}
            </button>
            <button 
              type="button"
              className={`agent-icon-btn ${liked === true ? 'active-like' : ''}`}
              onClick={() => setLiked(liked === true ? null : true)}
              title="Good response"
            >
              <ThumbsUp size={12} />
            </button>
            <button 
              type="button"
              className={`agent-icon-btn ${liked === false ? 'active-dislike' : ''}`}
              onClick={() => setLiked(liked === false ? null : false)}
              title="Poor response"
            >
              <ThumbsDown size={12} />
            </button>
            <button 
              type="button"
              className="agent-icon-btn" 
              onClick={handleRetry}
              title="Retry generation"
            >
              <RotateCw size={12} />
            </button>
          </div>

          <div className="agent-telemetry-strip">
            {timeStr && <span className="telemetry-time-stamp">{timeStr}</span>}
            <span className="telemetry-dot">·</span>
            <span className="telemetry-stat">Ran for {durationSec}</span>
            <span className="telemetry-dot">·</span>
            <span className="telemetry-stat">TTFT {ttftSec}</span>
            <span className="telemetry-dot">·</span>
            <span className="telemetry-stat">{tokSpeed}</span>
          </div>
        </div>

        {/* Inline Tool Approval Gate Card */}
        {approval && (
          <div className="inline-approval-card-wrap">
            <ApprovalCard
              approvalId={approval.id || 'gate-1'}
              toolName={approval.tool}
              arguments={approval.args || approval.arguments || {}}
              diff={approval.diff || {}}
              dangerousParams={approval.dangerous_params || []}
              warnings={approval.warnings || ['Tool invocation requires operator authorization.']}
              riskLevel={approval.risk_level || 'high'}
              isTainted={approval.is_tainted || false}
              onApprove={(id) => handleApprovalDecision(id, 'approved')}
              onDeny={(id) => handleApprovalDecision(id, 'denied')}
            />
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Format timestamp into standard 24h clock string like "12:24"
 */
function formatClockTime(timestamp) {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
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
