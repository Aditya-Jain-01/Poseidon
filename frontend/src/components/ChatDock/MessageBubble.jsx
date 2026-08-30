import React from 'react';
import Markdown from 'react-markdown';
import { ApprovalCard } from '../ApprovalCard/ApprovalCard';
import './MessageBubble.css';

/**
 * Renders a single chat message — user or agent.
 * Agent messages render markdown; user messages are plain text.
 * Also renders inline tool approval requests with risk analysis.
 */
export function MessageBubble({ message, onApprove, onDeny }) {
  const isUser = message.role === 'user';
  const isError = message.isError;
  const approval = message.approvalRequest;

  const timeStr = formatRelativeTime(message.timestamp);

  return (
    <div className={`message-bubble ${isUser ? 'message-user' : 'message-agent'} ${isError ? 'message-error' : ''}`}>
      <div className="message-content">
        {isUser ? (
          <p>{message.content}</p>
        ) : (
          <>
            {message.content && (
              <Markdown
                components={{
                  // Custom code styling
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
                  // Open links in new tab
                  a({ children, ...props }) {
                    return <a target="_blank" rel="noopener noreferrer" {...props}>{children}</a>;
                  },
                }}
              >
                {message.content}
              </Markdown>
            )}

            {/* Inline Tool Approval Card */}
            {approval && (
              <ApprovalCard
                approvalId={approval.id || message.runId}
                toolName={approval.tool}
                arguments={approval.arguments}
                diff={approval.diff}
                dangerousParams={approval.dangerous_params}
                warnings={approval.warnings}
                riskLevel={approval.risk_level}
                isTainted={approval.is_tainted}
                onApprove={onApprove}
                onDeny={onDeny}
              />
            )}
          </>
        )}
      </div>

      <div className="message-meta">
        <span className="message-time">{timeStr}</span>
        {message.runId && (
          <span className="message-run-id" title={`Run ID: ${message.runId}`}>
            {message.runId.slice(0, 8)}
          </span>
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
