import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../../components/common/Card';
import TabBar from '../../components/common/TabBar';
import { useChat } from '../../context/ChatContext';
import { useHealth } from '../../context/HealthContext';
import { 
  Radio, 
  ArrowDownLeft, 
  ArrowUpRight, 
  Copy, 
  Check, 
  ArrowLeft, 
  MessageSquare,
  Layers,
  Filter
} from 'lucide-react';
import './Gateway.css';

export function Gateway() {
  const navigate = useNavigate();
  const { sessions, activeSessionId, switchSession, messages: activeSessionMessages } = useChat();
  const { isConnected, telegramPolling } = useHealth();
  
  const [selectedScope, setSelectedScope] = useState('current'); // 'current' | 'all' | <sessionId>
  const [activeTab, setActiveTab] = useState('all');
  const [copiedId, setCopiedId] = useState(null);

  // Return to chat on ESC
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        navigate('/');
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate]);

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  // Assemble events based on selected chat scope
  const scopedMessages = useMemo(() => {
    if (selectedScope === 'all') {
      const allMsgs = [];
      sessions.forEach((s) => {
        (s.messages || []).forEach((m) => {
          allMsgs.push({
            ...m,
            sessionId: s.id,
            sessionTitle: s.title || 'Untitled Session',
          });
        });
      });
      // Sort chronologically descending
      return allMsgs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    }

    if (selectedScope === 'current') {
      return (activeSessionMessages || []).map((m) => ({
        ...m,
        sessionId: activeSessionId,
        sessionTitle: activeSession?.title || 'Current Session',
      }));
    }

    // Specific session selected
    const targetSession = sessions.find((s) => s.id === selectedScope);
    if (!targetSession) return [];
    return (targetSession.messages || []).map((m) => ({
      ...m,
      sessionId: targetSession.id,
      sessionTitle: targetSession.title || 'Untitled Session',
    }));
  }, [selectedScope, sessions, activeSessionId, activeSessionMessages, activeSession]);

  // Filter messages based on channel tab
  const displayMessages = useMemo(() => {
    if (activeTab === 'telegram' || activeTab === 'discord') return [];
    return scopedMessages;
  }, [activeTab, scopedMessages]);

  const tabs = [
    { key: 'all', label: 'All Channels', count: scopedMessages.length },
    { key: 'web', label: 'Web / CLI', count: scopedMessages.length, status: isConnected ? 'connected' : undefined },
    {
      key: 'telegram',
      label: 'Telegram',
      badge: telegramPolling ? 'Polling' : 'Disabled',
      badgeVariant: telegramPolling ? 'connected' : 'planned',
      status: telegramPolling ? 'connected' : undefined,
    },
    { key: 'discord', label: 'Discord', badge: 'Planned', badgeVariant: 'planned' },
  ];

  const formatTimestamp = (isoString) => {
    if (!isoString) return '—';
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoString;
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1800);
  };

  const handleOpenInChat = (sessionId) => {
    if (sessionId) {
      switchSession(sessionId);
    }
    navigate('/');
  };

  const currentChatTitle = selectedScope === 'current'
    ? (activeSession?.title || 'Active Session')
    : selectedScope === 'all'
    ? 'All Conversations'
    : (sessions.find(s => s.id === selectedScope)?.title || 'Selected Session');

  return (
    <div className="gateway-page animate-fade-in">
      {/* Top Header */}
      <div className="page-header">
        <div className="page-header-info">
          <h1 className="page-title">Gateway &amp; API Ledger</h1>
          <p className="page-subtitle">Cross-channel message routing and inbound event telemetry</p>
        </div>

        <div className="page-header-actions">
          <button 
            className="gateway-back-btn" 
            onClick={() => navigate('/')}
            title="Return to Chat Workspace (ESC)"
          >
            <ArrowLeft size={14} />
            <span>Back to Chat</span>
          </button>
        </div>
      </div>

      <section className="gateway-overview" aria-label="Gateway summary">
        <article className="gateway-summary-item">
          <div className="gateway-summary-icon"><MessageSquare size={16} /></div>
          <div>
            <span className="gateway-summary-label">Events in scope</span>
            <strong>{scopedMessages.length}</strong>
          </div>
        </article>
        <article className="gateway-summary-item">
          <div className="gateway-summary-icon"><Layers size={16} /></div>
          <div>
            <span className="gateway-summary-label">Conversations</span>
            <strong>{sessions.length}</strong>
          </div>
        </article>
        <article className="gateway-summary-item gateway-summary-status">
          <div className={`gateway-summary-icon ${telegramPolling ? 'is-live' : ''}`}><Radio size={16} /></div>
          <div>
            <span className="gateway-summary-label">Channel runtime</span>
            <strong>{telegramPolling ? 'Web + Telegram live' : 'Web / CLI live'}</strong>
          </div>
          <span className={`runtime-indicator ${isConnected ? 'is-live' : 'is-offline'}`}>
            {isConnected ? 'Backend online' : 'Backend offline'}
          </span>
        </article>
      </section>

      {/* Scope Toolbar & Session Switcher */}
      <div className="gateway-scope-toolbar">
        <div className="scope-select-group">
          <Filter size={13} className="scope-filter-icon" />
          <span className="scope-filter-label">Chat Scope:</span>
          <select 
            className="gateway-scope-select"
            value={selectedScope}
            onChange={(e) => setSelectedScope(e.target.value)}
            aria-label="Filter gateway telemetry by chat session"
          >
            <option value="current">Current Chat: {activeSession?.title || 'Active Session'}</option>
            <option value="all">All Conversations ({sessions.length} sessions, {sessions.reduce((acc, s) => acc + (s.messages?.length || 0), 0)} events)</option>
            {sessions.length > 0 && (
              <optgroup label="Saved Conversations">
                {sessions.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.title || 'Untitled Chat'} ({s.messages?.length || 0} msgs)
                  </option>
                ))}
              </optgroup>
            )}
          </select>
        </div>

        <div className="scope-actions-group">
          {selectedScope !== 'all' && (
            <button 
              className="scope-open-chat-btn"
              onClick={() => handleOpenInChat(selectedScope === 'current' ? activeSessionId : selectedScope)}
              title="Open this conversation in Chat canvas"
            >
              <MessageSquare size={13} />
              <span>Open in Chat</span>
              <ArrowUpRight size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Main Ledger Card */}
      <Card className="gateway-card">
        <TabBar tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />

        <div className="gateway-body">
          {displayMessages.length === 0 ? (
            <div className="gateway-empty-wrap">
              {activeTab === 'telegram' ? (
                <div className="channel-state-panel">
                  <div className="channel-state-copy">
                    <div className={`channel-state-icon ${telegramPolling ? 'is-live' : ''}`}>
                      <Radio size={20} />
                    </div>
                    <div>
                      <span className="channel-state-eyebrow">
                        Telegram · {telegramPolling ? 'polling enabled' : 'polling disabled'}
                      </span>
                      <h2>{telegramPolling ? 'Telegram is listening' : 'Telegram is available but inactive'}</h2>
                      <p>
                        {telegramPolling
                          ? 'The backend adapter is receiving Telegram updates. This local ledger currently shows browser and CLI events only.'
                          : 'Add a bot token and enable Telegram polling in the local environment to start the adapter.'}
                      </p>
                    </div>
                  </div>
                  <div className="channel-state-details" aria-label="Telegram adapter capabilities">
                    <div><span>Inbound messages</span><strong>{telegramPolling ? 'Listening' : 'Paused'}</strong></div>
                    <div><span>Outbound replies</span><strong>{telegramPolling ? 'Enabled' : 'Paused'}</strong></div>
                    <div><span>Ledger visibility</span><strong>Not connected</strong></div>
                  </div>
                  <button className="gateway-action-btn secondary" onClick={() => setActiveTab('web')}>
                    View Web / CLI traffic
                    <ArrowUpRight size={13} />
                  </button>
                </div>
              ) : activeTab === 'discord' ? (
                <div className="channel-state-panel">
                  <div className="channel-state-copy">
                    <div className="channel-state-icon"><Radio size={20} /></div>
                    <div>
                      <span className="channel-state-eyebrow">Discord · roadmap</span>
                      <h2>Discord is not connected</h2>
                      <p>The adapter has not been implemented yet. No connection or event data is being simulated on this page.</p>
                    </div>
                  </div>
                  <button className="gateway-action-btn secondary" onClick={() => setActiveTab('web')}>
                    View active channel
                    <ArrowUpRight size={13} />
                  </button>
                </div>
              ) : (
                <div className="channel-state-panel compact">
                  <div className="channel-state-copy">
                    <div className="channel-state-icon"><MessageSquare size={20} /></div>
                    <div>
                      <span className="channel-state-eyebrow">No events yet</span>
                      <h2>No traffic in {currentChatTitle}</h2>
                      <p>Send a prompt in Chat and the inbound request and assistant response will appear here.</p>
                    </div>
                  </div>
                  <button className="gateway-action-btn" onClick={() => navigate('/')}>
                    Open Chat
                    <ArrowUpRight size={13} />
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="gateway-table-container">
              <table className="gateway-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    {selectedScope === 'all' && <th>Chat Session</th>}
                    <th>Channel</th>
                    <th>Direction</th>
                    <th>Content</th>
                    <th>Run ID</th>
                  </tr>
                </thead>
                <tbody>
                  {displayMessages.map((msg, index) => {
                    const isInbound = msg.role === 'user';
                    return (
                      <tr key={msg.id || index} className="gateway-row">
                        <td className="gateway-cell-time mono">
                          {formatTimestamp(msg.timestamp)}
                        </td>

                        {selectedScope === 'all' && (
                          <td className="gateway-cell-session">
                            <button 
                              className="session-tag-pill"
                              onClick={() => handleOpenInChat(msg.sessionId)}
                              title="Jump to this chat session"
                            >
                              <MessageSquare size={11} />
                              <span>{msg.sessionTitle}</span>
                            </button>
                          </td>
                        )}

                        <td className="gateway-cell-channel">
                          <span className="channel-badge web">web</span>
                        </td>

                        <td className="gateway-cell-direction">
                          {isInbound ? (
                            <span className="direction-badge inbound">
                              <ArrowDownLeft size={13} />
                              IN
                            </span>
                          ) : (
                            <span className="direction-badge outbound">
                              <ArrowUpRight size={13} />
                              OUT
                            </span>
                          )}
                        </td>

                        <td className="gateway-cell-content" title={msg.content}>
                          <span className="content-text truncate">
                            {msg.content}
                          </span>
                        </td>

                        <td className="gateway-cell-runid mono">
                          {msg.runId ? (
                            <button
                              className="run-id-pill"
                              onClick={() => copyToClipboard(msg.runId, msg.id || index)}
                              title="Click to copy Run ID"
                            >
                              <span>{msg.runId.slice(0, 8)}...</span>
                              {copiedId === (msg.id || index) ? (
                                <Check size={12} className="copy-icon success" />
                              ) : (
                                <Copy size={12} className="copy-icon" />
                              )}
                            </button>
                          ) : (
                            <span className="muted-dim">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

export default Gateway;
