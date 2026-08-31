import React, { useState, useRef, useEffect } from 'react';
import { Download, Cpu, ShieldCheck, Activity, Layers, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { useChat } from '../../context/ChatContext';
import MessageBubble from './MessageBubble';
import MessageInput from './MessageInput';
import TypingIndicator from './TypingIndicator';
import TrajectoryView from '../TrajectoryView/TrajectoryView';
import ApprovalCard from '../ApprovalCard/ApprovalCard';
import './ChatDock.css';

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

/**
 * Centered Chat, Trajectory & Security Canvas view
 */
export function ChatDock() {
  const {
    sessions,
    messages,
    isLoading,
    sendMessage,
    activeSessionId,
    isOverviewOpen,
    toggleOverview,
  } = useChat();

  const greeting = getGreeting();
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'trajectory' | 'security'
  const messagesEndRef = useRef(null);
  const messageListRef = useRef(null);

  const activeSession = sessions.find((s) => s.id === activeSessionId);
  const sessionTitle = activeSession?.title || 'New Session';

  // Live approval requests from current messages
  const liveApprovalMsg = messages?.slice().reverse().find((m) => m.approvalRequest);
  const liveApproval = liveApprovalMsg?.approvalRequest;

  // Reset tab to chat when active session changes
  useEffect(() => {
    setActiveTab('chat');
  }, [activeSessionId]);

  // Auto-scroll to bottom when new messages arrive in chat tab
  useEffect(() => {
    if (activeTab === 'chat' && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading, activeTab]);

  const isEmpty = messages.length === 0;

  const handleExportSessionLog = () => {
    if (!activeSession) return;
    const exportData = {
      sessionId: activeSession.id,
      title: activeSession.title,
      createdAt: activeSession.createdAt,
      messages: activeSession.messages,
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `session-${activeSession.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className={`chat-canvas ${isEmpty && activeTab === 'chat' ? 'is-empty-hero' : ''}`}>
      {/* Subheader with Chat, Trajectory, Security Gate, and Topology tabs */}
      {(!isEmpty || activeTab !== 'chat') && (
        <div className="chat-canvas-subheader">
          <div className="subheader-left">
            <div className="subheader-title-row">
              <span className="session-heading-title">{sessionTitle}</span>
              <span className="session-mode-badge">
                <Cpu size={12} className="mode-badge-icon" />
                <span>Standard mode</span>
              </span>
            </div>

            <div className="subheader-tabs-row">
              <button 
                className={`subheader-tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
                onClick={() => setActiveTab('chat')}
              >
                Chat
              </button>
              <button 
                className={`subheader-tab-btn ${activeTab === 'trajectory' ? 'active' : ''}`}
                onClick={() => setActiveTab('trajectory')}
              >
                Trajectory
              </button>
              <button 
                className={`subheader-tab-btn ${activeTab === 'security' ? 'active' : ''}`}
                onClick={() => setActiveTab('security')}
              >
                Security Gate
              </button>
              <button 
                className={`subheader-tab-btn topology-side-btn ${isOverviewOpen ? 'active' : ''}`}
                onClick={toggleOverview}
                title="Toggle Architecture &amp; Topology CAD in right side window"
              >
                Topology
              </button>
            </div>
          </div>

          <div className="subheader-right">
            <button 
              className="session-log-btn"
              onClick={handleExportSessionLog}
              title="Export session execution log"
            >
              <span>Session log</span>
              <Download size={12} />
            </button>
          </div>
        </div>
      )}

      {/* Main Content Area: Chat, Trajectory, or Security Gate */}
      {activeTab === 'trajectory' ? (
        <TrajectoryView messages={messages} sessionTitle={sessionTitle} />
      ) : activeTab === 'security' ? (
        /* Security Gate & Taint Inspector View */
        <div className="workspace-security-view animate-fade-in">
          <div className="security-view-header">
            <div className="security-header-info">
              <span className="security-title">Security Gate &amp; Taint Inspector</span>
              <span className="security-subtitle">Human-in-the-loop parameter verification and untrusted origin taint tracking</span>
            </div>
          </div>

          <div className="security-cards-container">
            {liveApproval ? (
              <div className="live-approval-section">
                <div className="section-gate-badge">
                  <ShieldAlert size={14} />
                  <span>ACTIVE LIVE APPROVAL REQUIRED</span>
                </div>
                <ApprovalCard
                  approvalId={liveApproval.id || 'live-gate-1'}
                  toolName={liveApproval.tool}
                  arguments={liveApproval.args || {}}
                  diff={liveApproval.diff || {}}
                  dangerousParams={liveApproval.dangerous_params || []}
                  warnings={liveApproval.warnings || ['Live tool execution approval required before dispatch.']}
                  riskLevel={liveApproval.risk_level || 'high'}
                  isTainted={liveApproval.is_tainted || false}
                  onApprove={() => alert('Tool action approved.')}
                  onDeny={() => alert('Tool action denied.')}
                />
              </div>
            ) : (
              <div className="empty-security-gate-view">
                <ShieldCheck size={38} className="empty-shield-icon" />
                <h3 className="empty-security-title">No security evaluations pending</h3>
                <p className="empty-security-desc">
                  Human-in-the-loop security gate is armed. Tainted inputs, high-risk operations, or tool parameter overrides will generate verification cards here.
                </p>
                <div className="security-standby-pill">
                  <span className="standby-dot" />
                  <span>Gate Armed · 0 Taint Alerts</span>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : isEmpty ? (
        /* Empty Execution Workspace Hero */
        <div className="chat-hero-container animate-fade-in">
          {/* Subtle Ocean Atmospheric Glow Layer */}
          <div className="ocean-depth-aura" aria-hidden="true" />

          <h1 className="hero-title">{greeting}</h1>

          {/* Centered Command Input Bar */}
          <div className="hero-input-wrapper">
            <MessageInput onSend={sendMessage} disabled={isLoading} isHero={true} />
          </div>
        </div>
      ) : (
        /* Active Chat Message Stream */
        <>
          {/* Message List */}
          <div className="chat-canvas-messages" ref={messageListRef}>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}

            {isLoading && <TypingIndicator />}

            <div ref={messagesEndRef} />
          </div>

          {/* Docked Command Input Bar */}
          <div className="chat-canvas-input-wrapper">
            <MessageInput onSend={sendMessage} disabled={isLoading} isHero={false} />
          </div>
        </>
      )}
    </div>
  );
}

export default ChatDock;
