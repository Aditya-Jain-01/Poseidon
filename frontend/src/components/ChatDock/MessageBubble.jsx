import React, { useState } from 'react';
import Markdown from 'react-markdown';
import { 
  Copy, 
  Check,
  ThumbsUp,
  ThumbsDown,
  RotateCw,
  BrainCircuit,
  ChevronDown,
  ChevronRight,
  FileText
} from 'lucide-react';
import { useChat } from '../../context/ChatContext';
import { useHealth } from '../../context/HealthContext';
import { useAgents } from '../../context/AgentContext';
import ExecutionReceipt from './ExecutionReceipt';
import ApprovalCard from '../ApprovalCard/ApprovalCard';
import './MessageBubble.css';

/**
 * Grok-style Message Renderer
 */
export function MessageBubble({ message }) {
  const { handleApprovalDecision, inspectTurn, sendMessage, messages } = useChat();
  const { modelName, isConnected } = useHealth();
  const { agents } = useAgents();
  const [copied, setCopied] = useState(false);
  const [liked, setLiked] = useState(null);
  const [isThinkExpanded, setIsThinkExpanded] = useState(false);

  const isUser = message.role === 'user';
  const isError = message.isError;
  const approval = message.approvalRequest;

  const dynamicModel = message.model || modelName || (isConnected ? 'Poseidon' : 'Connecting...');
  const timeStr = formatClockTime(message.timestamp);

  const handleCopy = () => {
    if (!message.content) return;
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRetry = () => {
    const messageIndex = messages.findIndex((item) => item.id === message.id);
    const previousUserMessage = messageIndex > 0
      ? messages.slice(0, messageIndex).reverse().find((item) => item.role === 'user')
      : null;
    if (previousUserMessage?.content) sendMessage(previousUserMessage.content);
  };

  /* ── User Message ── */
  if (isUser) {
    return (
      <div className="user-message-row animate-slide-up">
        <div className="user-message-bubble">
          <p>{message.content}</p>
        </div>
        {timeStr && (
          <div className="user-message-meta">
            <span className="user-time">{timeStr}</span>
          </div>
        )}
      </div>
    );
  }

  /* ── Agent Message ── */
  const agentId = (message.activeAgent || 'poseidon').toLowerCase();
  const agentInfo = agents?.find((a) => a.id === agentId) || {
    id: agentId,
    display_name: 'Poseidon',
    avatar: 'P',
    color: '#2dd4bf',
  };

  // Tool calls from trajectory
  const executedTools = (message.trajectory || [])
    .filter((step) => step.step_type === 'tool_executed')
    .map((step) => ({
      name: step.tool_name,
      arguments: step.tool_args || {},
      result: step.tool_result || { status: 'executed' },
      risk: step.risk_level || 'auto',
    }));

  // A mentioned filename is not a generated file. Render file chips only
  // when a file-producing tool explicitly returns a path in its result.
  const producedFiles = [];
  (message.trajectory || []).forEach((step) => {
    const toolName = String(step.tool_name || '');
    const isFileProducer = /(write|create|export|save|generate)/i.test(toolName);
    if (!isFileProducer || !step.tool_result || typeof step.tool_result !== 'object') return;

    const candidates = [
      step.tool_result.file_path,
      step.tool_result.path,
      step.tool_result.filename,
      step.tool_result.created?.file_path,
      step.tool_result.created?.path,
      step.tool_result.created?.filename,
    ].filter((value) => typeof value === 'string' && value.trim());

    candidates.forEach((file) => {
      if (!producedFiles.includes(file)) producedFiles.push(file);
    });
  });

  const reasoningTokens = message.telemetry?.reasoning_tokens || null;

  return (
    <div className={`ai-message-row animate-slide-up ${isError ? 'is-error' : ''}`}>
      {/* Content */}
      <div className="ai-message-content">
        {/* Header */}
        <div className="ai-message-header">
          <span className="ai-agent-name">{agentInfo.display_name}</span>
          <span className="ai-model-tag">{dynamicModel}</span>
          {message.runId && (
            <button
              type="button"
              className="ai-run-tag"
              title="Inspect this turn"
              onClick={() => inspectTurn(message)}
            >
              {message.runId.slice(0, 8)}
            </button>
          )}
        </div>

        {/* Thinking Accordion */}
        {reasoningTokens && (
          <div className={`thinking-section ${isThinkExpanded ? 'is-open' : ''}`}>
            <button
              type="button"
              className="thinking-toggle"
              onClick={() => setIsThinkExpanded(!isThinkExpanded)}
              aria-expanded={isThinkExpanded}
            >
              <BrainCircuit size={14} className="thinking-icon" />
              <span>Thinking · ~{reasoningTokens} tokens</span>
              {isThinkExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>
            {isThinkExpanded && (
              <div className="thinking-body animate-fade-in">
                <p>
                  Evaluated working memory context, verified sandbox boundaries, and synthesized response.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Tool Execution Receipts */}
        {executedTools.length > 0 && (
          <div className="tool-receipts">
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

        {/* AI Message Bubble */}
        {message.content && (
          <div className="ai-message-bubble">
            <div className="ai-message-body">
              <Markdown
                components={{
                  code({ className = '', children, ...props }) {
                    return <code className={`inline-code ${className}`.trim()} {...props}>{children}</code>;
                  },
                  pre({ children, ...props }) {
                    return <pre className="code-block" {...props}>{children}</pre>;
                  },
                  a({ children, ...props }) {
                    return <a target="_blank" rel="noopener noreferrer" {...props}>{children}</a>;
                  },
                }}
              >
                {message.content}
              </Markdown>
            </div>
          </div>
        )}

        {/* Produced Files */}
        {producedFiles.length > 0 && (
          <div className="produced-files">
            {producedFiles.map((file, idx) => (
              <span key={idx} className="file-chip">
                <FileText size={12} />
                <span>{file}</span>
              </span>
            ))}
          </div>
        )}

        {/* Action Bar (hover reveal) */}
        <div className="ai-message-actions">
          <button
            type="button"
            className="msg-action-btn"
            onClick={handleCopy}
            title={copied ? "Copied" : "Copy"}
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
          </button>
          <button
            type="button"
            className={`msg-action-btn ${liked === true ? 'liked' : ''}`}
            onClick={() => setLiked(liked === true ? null : true)}
            title="Good response"
          >
            <ThumbsUp size={14} />
          </button>
          <button
            type="button"
            className={`msg-action-btn ${liked === false ? 'disliked' : ''}`}
            onClick={() => setLiked(liked === false ? null : false)}
            title="Poor response"
          >
            <ThumbsDown size={14} />
          </button>
          <button
            type="button"
            className="msg-action-btn"
            onClick={handleRetry}
            title="Retry"
          >
            <RotateCw size={14} />
          </button>

          {timeStr && <span className="msg-action-time">{timeStr}</span>}
        </div>

        {/* Approval Card */}
        {approval && (
          <div className="approval-card-wrap">
            <ApprovalCard
              approvalId={approval.id || 'gate-1'}
              toolName={approval.tool_name || approval.tool || 'Unknown tool'}
              arguments={approval.args || approval.arguments || {}}
              diff={approval.diff || {}}
              dangerousParams={approval.dangerous_params || []}
              warnings={approval.warnings || ['Tool invocation requires authorization.']}
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

function formatClockTime(timestamp) {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
}

export default MessageBubble;
