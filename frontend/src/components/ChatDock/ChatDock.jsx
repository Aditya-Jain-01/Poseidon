import React, { useState, useRef } from 'react';
import { ArrowDown, Download, PanelRight, PanelRightClose } from 'lucide-react';
import { useChat } from '../../context/ChatContext';
import MessageBubble from './MessageBubble';
import MessageInput from './MessageInput';
import TypingIndicator from './TypingIndicator';
import TrajectoryView from '../TrajectoryView/TrajectoryView';
import { useConversationScroll } from './useConversationScroll';
import './ChatDock.css';
import './ChatReference.css';

export function ChatDock() {
  const {
    sessions,
    messages,
    isLoading,
    sendMessage,
    stopGeneration,
    activeSessionId,
    isOverviewOpen,
    toggleOverview,
  } = useChat();

  const [activeView, setActiveView] = useState('chat'); // 'chat' | 'trajectory'

  const messageListRef = useRef(null);
  const { isFollowing, onScroll, jumpToLatest } = useConversationScroll(messageListRef, activeSessionId, messages, isLoading, activeView);

  const activeSession = sessions.find((s) => s.id === activeSessionId);
  const sessionTitle = activeSession?.title || 'New Chat';

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
    <div className={`chat-canvas ${isEmpty && activeView === 'chat' ? 'is-start' : ''}`}>
      {/* Minimal Top Bar */}
      {!isEmpty && (
        <div className="chat-top-bar">
          <div className="top-bar-left">
            <span className="top-bar-title">{sessionTitle}</span>
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
        /* Focused chat start screen */
        <div className="chat-start">
          <h1>What’s on your mind today?</h1>
          <div className="chat-start-input">
            <MessageInput onSend={sendMessage} onStop={stopGeneration} disabled={isLoading} isHero={true} />
          </div>
          <p className="chat-start-note">Poseidon can make mistakes. Verify important information.</p>
        </div>
      ) : (
        /* Active Chat Message Stream */
        <>
          <div className="chat-canvas-messages" ref={messageListRef} onScroll={onScroll}>
            <div className="messages-column">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} sessionId={activeSessionId} />
              ))}

              {isLoading && <TypingIndicator />}

            </div>
          </div>

          {!isFollowing && <button type="button" className="chat-jump-latest" onClick={jumpToLatest}><ArrowDown size={15} /> Latest</button>}

          <div className="chat-canvas-input-wrapper">
            <MessageInput onSend={sendMessage} onStop={stopGeneration} disabled={isLoading} isHero={false} />
          </div>
        </>
      )}
    </div>
  );
}

export default ChatDock;
