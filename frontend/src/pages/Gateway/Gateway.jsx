import React, { useState } from 'react';
import Card from '../../components/common/Card';
import TabBar from '../../components/common/TabBar';
import EmptyState from '../../components/common/EmptyState';
import { useChat } from '../../context/ChatContext';
import { Radio, ArrowDownLeft, ArrowUpRight, Copy, Check } from 'lucide-react';
import './Gateway.css';

export function Gateway() {
  const { messages } = useChat();
  const [activeTab, setActiveTab] = useState('all');
  const [copiedId, setCopiedId] = useState(null);

  const tabs = [
    { key: 'all', label: 'All Channels', count: messages.length },
    { key: 'web', label: 'Web / CLI', count: messages.length },
    { key: 'telegram', label: 'Telegram (Sprint 4)', count: 0 },
    { key: 'discord', label: 'Discord (Sprint 4)', count: 0 },
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

  // Filter messages based on active tab
  const displayMessages = activeTab === 'telegram' || activeTab === 'discord' ? [] : messages;

  return (
    <div className="gateway-page animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Gateway — Web Channel</h1>
          <p className="page-subtitle">Cross-channel message routing and inbound event telemetry</p>
        </div>
      </div>

      <Card className="gateway-card">
        <TabBar tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />

        <div className="gateway-body">
          {displayMessages.length === 0 ? (
            <div className="gateway-empty-wrap">
              <EmptyState
                icon={Radio}
                title={
                  activeTab === 'telegram' || activeTab === 'discord'
                    ? 'Channel Not Connected'
                    : 'No Gateway Events Yet'
                }
                subtitle={
                  activeTab === 'telegram' || activeTab === 'discord'
                    ? 'This channel adapter is scheduled for Sprint 4 integration.'
                    : 'Messages will appear here as you chat with the agent.'
                }
              />
            </div>
          ) : (
            <div className="gateway-table-container">
              <table className="gateway-table">
                <thead>
                  <tr>
                    <th>Time</th>
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
                              onClick={() => copyToClipboard(msg.runId, msg.id)}
                              title="Click to copy Run ID"
                            >
                              <span>{msg.runId.slice(0, 8)}...</span>
                              {copiedId === msg.id ? (
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
