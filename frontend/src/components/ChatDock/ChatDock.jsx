import React, { useState, useRef, useEffect } from 'react';
import { Download, RotateCw, PanelRight, PanelRightClose, Terminal } from 'lucide-react';
import { useChat } from '../../context/ChatContext';
import MessageBubble from './MessageBubble';
import MessageInput from './MessageInput';
import TypingIndicator from './TypingIndicator';
import TrajectoryView from '../TrajectoryView/TrajectoryView';
import './ChatDock.css';

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

/**
 * Centered Developer Console Canvas view (DeepSeek Harness inspired)
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

  const [activeView, setActiveView] = useState('chat'); // 'chat' | 'trajectory'

  const greeting = getGreeting();
  const messagesEndRef = useRef(null);
  const messageListRef = useRef(null);

  const activeSession = sessions.find((s) => s.id === activeSessionId);
  const sessionTitle = activeSession?.title || 'First prompt session';

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (activeView === 'chat' && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading, activeView]);

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
    <div className={`chat-canvas ${isEmpty && activeView === 'chat' ? 'is-empty-hero' : ''}`}>
      {/* Consolidated Top Status Ribbon */}
      <div className="chat-canvas-status-ribbon">
        {/* Left: POSEIDON // SESSION-XXXXXXXX (Mono) */}
        <div className="status-ribbon-left">
          <span className="ribbon-session-brand">
            POSEIDON // {activeSessionId ? `SESSION-${activeSessionId.slice(0, 8).toUpperCase()}` : 'SESSION-LIVE'}
          </span>
        </div>

        {/* Center: Minimal pill toggle for [ CHAT ] and [ TRAJECTORY ] */}
        <div className="status-ribbon-center">
          <div className="ribbon-view-pill">
            <button
              type="button"
              className={`view-pill-btn ${activeView === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveView('chat')}
            >
              CHAT
            </button>
            <button
              type="button"
              className={`view-pill-btn ${activeView === 'trajectory' ? 'active' : ''}`}
              onClick={() => setActiveView('trajectory')}
            >
              TRAJECTORY
            </button>
          </div>
        </div>

        {/* Right: Status indicator dot with READY and quick buttons [ LOG ] [ INSPECTOR ] */}
        <div className="status-ribbon-right">
          <div className="ribbon-status-indicator" title="System Status: Ready">
            <span className="ribbon-status-dot" />
            <span className="ribbon-status-text">READY</span>
          </div>

          <button 
            type="button"
            className="ribbon-pill-btn"
            onClick={handleExportSessionLog}
            title="Export session execution log"
          >
            <Download size={11} />
            <span>LOG</span>
          </button>

          <button
            type="button"
            className={`ribbon-pill-btn ${isOverviewOpen ? 'is-active' : ''}`}
            onClick={toggleOverview}
            title={isOverviewOpen ? 'Hide Inspector Panel' : 'Show Inspector Panel'}
          >
            {isOverviewOpen ? <PanelRightClose size={11} /> : <PanelRight size={11} />}
            <span>INSPECTOR</span>
          </button>
        </div>
      </div>

      {/* Main View: Trajectory View vs Conversation Stream */}
      {activeView === 'trajectory' ? (
        <div className="chat-canvas-trajectory-view animate-fade-in">
          <TrajectoryView messages={messages} sessionTitle={sessionTitle} />
        </div>
      ) : isEmpty ? (
        /* Empty Execution Workspace Hero — Three-Layer Rule (Section 2.1) */
        <div className="chat-hero-container animate-fade-in">
          {/* Layer 3: Top Instrument Tag (ALL CAPS Space Mono) */}
          <div className="hero-badge">
            <span className="hero-badge-status-dot" />
            <span>POSEIDON // COGNITIVE COCKPIT</span>
          </div>

          {/* Layer 1: The ONE Thing (Section 2.1 Display Size with 48–64px breathing room) */}
          <h1 className="hero-title font-display">POSEIDON // 01</h1>
          <p className="hero-subtitle">
            Autonomous agent harness with 4-tier cognitive memory and sandboxed tool execution.
          </p>

          {/* Layer 2: Supporting Context (Quick Action Pills) */}
          <div className="hero-quick-commands">
            <button type="button" className="quick-command-chip" onClick={() => sendMessage('/memory')}>
              /memory · Inspect facts
            </button>
            <button type="button" className="quick-command-chip" onClick={() => sendMessage('/status')}>
              /status · Health check
            </button>
            <button type="button" className="quick-command-chip" onClick={() => sendMessage('/skills')}>
              /skills · List playbooks
            </button>
            <button type="button" className="quick-command-chip" onClick={() => sendMessage('/clear')}>
              /clear · Fresh session
            </button>
          </div>

          {/* Centered Command Input Bar */}
          <div className="hero-input-wrapper">
            <MessageInput onSend={sendMessage} disabled={isLoading} isHero={true} />
          </div>

          {/* Layer 3: Peripheral System Metadata (Pushed to bottom) */}
          <div className="hero-bottom-metadata nothing-label">
            <span>[ SYSTEM: READY ]</span>
            <span className="metadata-dot">·</span>
            <span>[ 4-TIER COGNITION ]</span>
            <span className="metadata-dot">·</span>
            <span>[ SANDBOX: ACTIVE ]</span>
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
