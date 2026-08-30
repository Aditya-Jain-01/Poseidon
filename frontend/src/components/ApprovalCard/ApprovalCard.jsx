import React, { useState } from 'react';
import { AlertTriangle, ShieldAlert, CheckCircle, XCircle, ChevronDown, ChevronUp, ArrowRight } from 'lucide-react';
import './ApprovalCard.css';

/**
 * ApprovalCard — Renders pending tool approval requests with:
 * 1. Visual risk level badges (High / Medium / Low).
 * 2. Tainted context warning banner when invoked from untrusted origins.
 * 3. Parameter diffing with red-highlighted dangerous / modified fields.
 * 4. Approve / Deny action controls.
 */
export function ApprovalCard({
  approvalId,
  toolName,
  arguments: args = {},
  diff = {},
  dangerousParams = [],
  warnings = [],
  riskLevel = 'medium', // 'high' | 'medium' | 'low'
  isTainted = false,
  onApprove,
  onDeny,
}) {
  const [expanded, setExpanded] = useState(true);
  const [decided, setDecided] = useState(null); // 'approved' | 'denied' | null

  const handleApprove = () => {
    setDecided('approved');
    if (onApprove) onApprove(approvalId);
  };

  const handleDeny = () => {
    setDecided('denied');
    if (onDeny) onDeny(approvalId);
  };

  const dangerousParamKeys = new Set(dangerousParams.map((p) => (typeof p === 'string' ? p : p.param)));
  const diffKeys = Object.keys(diff || {});

  return (
    <div className={`approval-card risk-${riskLevel} ${isTainted ? 'is-tainted' : ''}`}>
      {/* Top Banner / Risk Badge */}
      <div className="approval-header">
        <div className="approval-title-row">
          <span className="approval-icon">
            {riskLevel === 'high' ? (
              <ShieldAlert size={18} className="icon-high-risk" />
            ) : (
              <AlertTriangle size={18} className="icon-med-risk" />
            )}
          </span>
          <div className="approval-title">
            <span className="tool-tag">TOOL APPROVAL</span>
            <h4>{toolName}</h4>
          </div>
        </div>

        <div className="approval-header-right">
          <span className={`risk-pill pill-${riskLevel}`}>
            {riskLevel.toUpperCase()} RISK
          </span>
          <button
            type="button"
            className="btn-toggle-expand"
            onClick={() => setExpanded(!expanded)}
            aria-label="Toggle details"
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {/* Taint Provenance Warning */}
      {isTainted && (
        <div className="taint-warning-banner">
          <AlertTriangle size={14} />
          <span>Context is <strong>UNTRUSTED (Tainted)</strong> — data originated from an external channel.</span>
        </div>
      )}

      {/* Warnings List */}
      {warnings.length > 0 && (
        <div className="approval-warnings">
          {warnings.map((w, idx) => (
            <div key={idx} className="warning-item">
              <span className="warning-dot">●</span>
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* Expandable Parameters & Diff Section */}
      {expanded && (
        <div className="approval-body">
          {/* Parameter Diffs if present */}
          {diffKeys.length > 0 && (
            <div className="diff-section">
              <span className="section-subtitle">Parameter Modifications (Diff):</span>
              <div className="diff-list">
                {diffKeys.map((key) => {
                  const isDangerous = dangerousParamKeys.has(key);
                  const entry = diff[key];
                  return (
                    <div key={key} className={`diff-row ${isDangerous ? 'dangerous-diff' : ''}`}>
                      <span className="diff-param-name">{key}:</span>
                      <div className="diff-values">
                        <span className="diff-old">{String(entry.old ?? '(empty)')}</span>
                        <ArrowRight size={12} className="diff-arrow" />
                        <span className="diff-new">{String(entry.new)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Full Parameter Inspector */}
          <div className="params-section">
            <span className="section-subtitle">Invocation Arguments:</span>
            <div className="params-grid">
              {Object.entries(args).map(([key, val]) => {
                const isDangerous = dangerousParamKeys.has(key);
                return (
                  <div key={key} className={`param-item ${isDangerous ? 'dangerous-param' : ''}`}>
                    <span className="param-label">{key}</span>
                    <span className="param-value">{typeof val === 'object' ? JSON.stringify(val) : String(val)}</span>
                    {isDangerous && <span className="param-danger-flag">⚠️ Sensitive / Risky</span>}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Decision Footer */}
      <div className="approval-footer">
        {decided === null ? (
          <div className="approval-actions">
            <button
              type="button"
              className="btn-deny"
              onClick={handleDeny}
            >
              <XCircle size={15} />
              <span>Deny</span>
            </button>
            <button
              type="button"
              className="btn-approve"
              onClick={handleApprove}
            >
              <CheckCircle size={15} />
              <span>Approve Action</span>
            </button>
          </div>
        ) : (
          <div className={`decision-status status-${decided}`}>
            {decided === 'approved' ? (
              <>
                <CheckCircle size={16} />
                <span>Action Approved by Operator</span>
              </>
            ) : (
              <>
                <XCircle size={16} />
                <span>Action Denied & Blocked</span>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default ApprovalCard;
