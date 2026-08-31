import React from 'react';
import ArchitectureMap from '../../components/ArchitectureMap/ArchitectureMap';
import ApprovalCard from '../../components/ApprovalCard/ApprovalCard';
import { useHealth } from '../../context/HealthContext';
import { useChat } from '../../context/ChatContext';
import { Cpu, Activity, MessageSquare, ShieldCheck, X } from 'lucide-react';
import './Overview.css';

export function Overview() {
  const { isConnected, modelName } = useHealth();
  const { messages, overviewTab, setOverviewTab, closeOverview } = useChat();

  const totalMessagesCount = messages.length;
  const liveApprovalMsg = messages.slice().reverse().find((m) => m.approvalRequest);
  const liveApproval = liveApprovalMsg?.approvalRequest;

  return (
    <div className="overview-drawer-content">
      {/* Drawer Header */}
      <div className="overview-header">
        <div className="overview-header-top">
          <h2 className="overview-title">Diagnostics</h2>
          <button className="overview-close-btn" onClick={closeOverview} title="Close (ESC)">
            <X size={20} />
          </button>
        </div>

        {/* 2x2 Telemetry Grid */}
        <div className="telemetry-compact-grid">
          <div className="telemetry-mini-card">
            <Cpu size={14} className="accent" />
            <div className="telemetry-mini-info">
              <span className="mini-label">Model</span>
              <span className="mini-val">{modelName ? modelName.replace('google/', '') : (isConnected ? 'Poseidon Agent' : 'Offline')}</span>
            </div>
          </div>
          <div className="telemetry-mini-card">
            <Activity size={14} className="teal" />
            <div className="telemetry-mini-info">
              <span className="mini-label">Backend</span>
              <span className="mini-val">{isConnected ? 'Active' : 'Down'}</span>
            </div>
          </div>
          <div className="telemetry-mini-card">
            <MessageSquare size={14} className="amber" />
            <div className="telemetry-mini-info">
              <span className="mini-label">Session</span>
              <span className="mini-val">{totalMessagesCount} msgs</span>
            </div>
          </div>
          <div className="telemetry-mini-card">
            <ShieldCheck size={14} className="success" />
            <div className="telemetry-mini-info">
              <span className="mini-label">Defenses</span>
              <span className="mini-val success-text">{isConnected ? 'Armed' : 'Offline'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="overview-tabs">
        <button 
          className={`overview-tab ${overviewTab === 'topology' ? 'active' : ''}`}
          onClick={() => setOverviewTab('topology')}
        >
          Topology
        </button>
        <button 
          className={`overview-tab ${overviewTab === 'security' ? 'active' : ''}`}
          onClick={() => setOverviewTab('security')}
        >
          Security Gate
        </button>
      </div>

      {/* Tab Content */}
      <div className="overview-tab-content">
        {overviewTab === 'topology' && (
          <div className="topology-tab animate-fade-in">
            <p className="tab-description">
              Live view of the Poseidon system architecture, tracing the path from gateway to memory stores.
            </p>
            <div className="architecture-wrapper">
              <ArchitectureMap activeNodes={isConnected ? ['gateway', 'harness', 'agent'] : []} />
            </div>
          </div>
        )}

        {overviewTab === 'security' && (
          <div className="security-tab animate-fade-in">
            {liveApproval ? (
              <>
                <p className="tab-description active-desc">
                  ⚠️ Action Required: Review tool approval request below
                </p>
                <ApprovalCard
                  approvalId={liveApproval.id || 'live-gate-1'}
                  toolName={liveApproval.tool}
                  arguments={liveApproval.args || {}}
                  diff={liveApproval.diff || {}}
                  dangerousParams={liveApproval.dangerous_params || []}
                  warnings={liveApproval.warnings || []}
                  riskLevel={liveApproval.risk_level || 'high'}
                  isTainted={liveApproval.is_tainted}
                />
              </>
            ) : (
              <div className="empty-security-gate">
                <ShieldCheck size={36} className="empty-shield-icon" />
                <p className="empty-title">Security Gate Clear</p>
                <span className="empty-sub">
                  No pending tool execution approvals or taint alerts for this session.
                </span>
                <div className="security-standby-pill">
                  <span className="standby-dot"></span>
                  Human-in-the-Loop Gate Standby
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default Overview;
