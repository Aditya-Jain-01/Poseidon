import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download, PanelRight, PanelRightClose, Brain, Cpu, FileText, RotateCw } from 'lucide-react';
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

export function ChatDock() {
  const navigate = useNavigate();
  const {
    sessions,
    messages,
    isLoading,
    sendMessage,
    stopGeneration,
    activeSessionId,
    isOverviewOpen,
    toggleOverview,
    openOverview,
    clearChat,
  } = useChat();

  const [activeView, setActiveView] = useState('chat'); // 'chat' | 'trajectory'

  const greeting = getGreeting();
  const messagesEndRef = useRef(null);
  const messageListRef = useRef(null);

  const activeSession = sessions.find((s) => s.id === activeSessionId);
  const sessionTitle = activeSession?.title || 'New Chat';

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
      {/* Minimal Top Bar */}
      {!isEmpty && (
        <div className="chat-top-bar">
          <div className="top-bar-left">
            {messages.length > 0 && (
              <div className="view-switcher">
                <button
                  type="button"
                  className={`view-btn ${activeView === 'chat' ? 'active' : ''}`}
                  onClick={() => setActiveView('chat')}
                >
                  Chat
                </button>
                <button
                  type="button"
                  className={`view-btn ${activeView === 'trajectory' ? 'active' : ''}`}
                  onClick={() => setActiveView('trajectory')}
                >
                  Trajectory
                </button>
              </div>
            )}
          </div>

          <span className="top-bar-title">{sessionTitle}</span>

          <div className="top-bar-right">
            <button
              type="button"
              className="top-bar-icon-btn"
              onClick={handleExportSessionLog}
              title="Export session log"
            >
              <Download size={16} />
            </button>
            <button
              type="button"
              className={`top-bar-icon-btn ${isOverviewOpen ? 'active' : ''}`}
              onClick={toggleOverview}
              title={isOverviewOpen ? 'Hide inspector' : 'Show inspector'}
            >
              {isOverviewOpen ? <PanelRightClose size={16} /> : <PanelRight size={16} />}
            </button>
          </div>
        </div>
      )}

      {/* Main View */}
      {activeView === 'trajectory' ? (
        <div className="chat-canvas-trajectory-view animate-fade-in">
          <TrajectoryView messages={messages} sessionTitle={sessionTitle} />
        </div>
      ) : isEmpty ? (
        /* Clean Empty State Hero */
        <div className="chat-hero-container animate-fade-in">
          <h1 className="hero-greeting">{greeting}</h1>
          <p className="hero-subtitle">How can I help you today?</p>

          <div className="hero-actions">
            <button type="button" className="hero-action-card" onClick={() => navigate('/settings?tab=memory')}>
              <Brain size={20} />
              <span>Inspect Memory</span>
            </button>
            <button type="button" className="hero-action-card" onClick={() => openOverview('telemetry')}>
              <Cpu size={20} />
              <span>System Health</span>
            </button>
            <button type="button" className="hero-action-card" onClick={() => navigate('/settings?tab=memory')}>
              <FileText size={20} />
              <span>View Skills</span>
            </button>
            <button type="button" className="hero-action-card" onClick={clearChat}>
              <RotateCw size={20} />
              <span>Fresh Session</span>
            </button>
          </div>

          <div className="hero-input-wrapper">
            <MessageInput onSend={sendMessage} onStop={stopGeneration} disabled={isLoading} isHero={true} />
          </div>
        </div>
      ) : (
        /* Active Chat Message Stream */
        <>
          <div className="chat-canvas-messages" ref={messageListRef}>
            <div className="messages-column">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}

              {isLoading && <TypingIndicator />}

              <div ref={messagesEndRef} />
            </div>
          </div>

          <div className="chat-canvas-input-wrapper">
            <MessageInput onSend={sendMessage} onStop={stopGeneration} disabled={isLoading} isHero={false} />
          </div>
        </>
      )}
    </div>
  );
}

export default ChatDock;
