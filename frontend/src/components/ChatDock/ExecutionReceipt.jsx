import React, { useState } from 'react';
import { Wrench, ChevronDown, ChevronRight, CheckCircle2, AlertCircle, Clock, Shield } from 'lucide-react';
import './ExecutionReceipt.css';

export function ExecutionReceipt({ toolCall, toolResult, riskLevel = 'auto' }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!toolCall) return null;

  const toolName = toolCall.name || toolCall.tool || 'tool_call';
  const args = toolCall.arguments || toolCall.args || {};
  const isSuccess = !toolResult?.error;
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
      <div className="execution-receipt-bar" onClick={() => setIsExpanded(!isExpanded)}>
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

          <button type="button" className="receipt-expand-btn" aria-label="Toggle details">
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="receipt-body animate-fade-in">
          <div className="receipt-details-grid">
            <div className="receipt-detail-block">
              <div className="receipt-detail-label">Arguments</div>
              <pre className="receipt-json-code">{JSON.stringify(args, null, 2)}</pre>
            </div>
            {toolResult && (
              <div className="receipt-detail-block">
                <div className="receipt-detail-label">Observation / Result</div>
                <pre className="receipt-json-code">{JSON.stringify(toolResult, null, 2)}</pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default ExecutionReceipt;
