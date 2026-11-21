import React, { useState } from 'react';
import { Wrench, ChevronDown, ChevronRight, CheckCircle2, AlertCircle, Shield } from 'lucide-react';
import { CappedOutput } from './CappedOutput';
import './ExecutionReceipt.css';

export function ExecutionReceipt({ toolCall, toolResult, riskLevel = 'auto' }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!toolCall) return null;

  const toolName = toolCall.name || toolCall.tool || 'tool_call';
  const args = toolCall.arguments || toolCall.args || {};
  const resultStatus = String(toolResult?.status || '').toLowerCase();
  const isSuccess = !toolResult?.error && !['error', 'failed', 'denied'].includes(resultStatus);
  const isAuto = riskLevel === 'auto' || riskLevel === 'low';

  // Format short argument preview
  const argKeys = Object.keys(args);
  let shortArgPreview = '';
  if (argKeys.length > 0) {
    const firstVal = typeof args[argKeys[0]] === 'object' ? JSON.stringify(args[argKeys[0]]) : String(args[argKeys[0]]);
    shortArgPreview = `${argKeys[0]}: ${firstVal.length > 30 ? firstVal.slice(0, 30) + '...' : firstVal}`;
    if (argKeys.length > 1) shortArgPreview += `, +${argKeys.length - 1}`;
  }

  return (
    <div className={`execution-receipt-root ${isAuto ? 'is-auto' : 'is-approval'} ${isExpanded ? 'is-expanded' : ''}`}>
      <div
        className="execution-receipt-bar"
        role="button"
        tabIndex={0}
        onClick={() => setIsExpanded(!isExpanded)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            setIsExpanded((value) => !value);
          }
        }}
        aria-expanded={isExpanded}
      >
        <div className="receipt-left">
          <div className="receipt-icon-wrap">
            <Wrench size={13} className="receipt-icon" />
          </div>
          <span className="receipt-tool-name">{toolName}</span>
          {shortArgPreview && (
            <span className="receipt-arg-preview" title={JSON.stringify(args, null, 2)}>
              ({shortArgPreview})
            </span>
          )}
        </div>

        <div className="receipt-right">
          <span className={`receipt-risk-badge ${isAuto ? 'risk-auto' : 'risk-approval'}`}>
            <Shield size={10} />
            <span>{isAuto ? 'Auto-run' : 'Approval'}</span>
          </span>

          {isSuccess ? (
            <span className="receipt-status-pill success">
              <CheckCircle2 size={12} />
              <span>Done</span>
            </span>
          ) : (
            <span className="receipt-status-pill error">
              <AlertCircle size={12} />
              <span>Failed</span>
            </span>
          )}

          <span className="receipt-expand-btn" aria-hidden="true">
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </span>
        </div>
      </div>

      {isExpanded && (
        <div className="receipt-body animate-fade-in">
          <div className="receipt-details-grid">
            <div className="receipt-detail-block">
              <div className="receipt-detail-label">Arguments</div>
              <CappedOutput value={args} />
            </div>
            {toolResult && (
              <div className="receipt-detail-block">
                <div className="receipt-detail-label">Observation / Result</div>
                <CappedOutput value={toolResult} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default ExecutionReceipt;
