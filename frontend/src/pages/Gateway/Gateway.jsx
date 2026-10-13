import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../../components/common/Card';
import TabBar from '../../components/common/TabBar';
import { useChat } from '../../context/ChatContext';
import { useHealth } from '../../context/HealthContext';
import { fetchGatewayEvents } from '../../api/audit';
import { 
  Radio, 
  ArrowDownLeft, 
  ArrowUpRight, 
  Copy, 
  Check, 
  ArrowLeft, 
  MessageSquare,
  Activity,
  RefreshCw,
  Search
} from 'lucide-react';
import './Gateway.css';

export function Gateway() {
  const navigate = useNavigate();
  const { inspectTurn } = useChat();
  const { isConnected, telegramPolling } = useHealth();
  
  const [activeTab, setActiveTab] = useState('all');
  const [backendEvents, setBackendEvents] = useState([]);
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);
  const [eventsError, setEventsError] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const [filterQuery, setFilterQuery] = useState('');

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

  // Load durable backend ledger events
  const loadLedgerEvents = useCallback(async () => {
    setIsLoadingEvents(true);
    setEventsError(null);
    try {
      const channelParam = activeTab === 'all' ? undefined : activeTab;
      const res = await fetchGatewayEvents({ channel: channelParam, limit: 100 });
      setBackendEvents(res?.events || []);
    } catch (err) {
      setEventsError(err.message || 'Failed to load gateway ledger events');
    } finally {
      setIsLoadingEvents(false);
    }
  }, [activeTab]);

  useEffect(() => {
    let ignore = false;
    const channelParam = activeTab === 'all' ? undefined : activeTab;
    fetchGatewayEvents({ channel: channelParam, limit: 100 })
      .then((res) => {
        if (!ignore) {
          setBackendEvents(res?.events || []);
          setEventsError(null);
        }
      })
      .catch((err) => {
        if (!ignore) {
          setEventsError(err.message || 'Failed to load gateway ledger events');
        }
      });
    return () => {
      ignore = true;
    };
  }, [activeTab]);

  // Tab configuration: Telegram only when configured, Discord absent
  const tabs = useMemo(() => {
    const list = [
      { key: 'all', label: 'All Channels', count: backendEvents.length },
      { key: 'web', label: 'Web / CLI', status: isConnected ? 'connected' : undefined },
    ];
    if (telegramPolling) {
      list.push({
        key: 'telegram',
        label: 'Telegram',
        badge: 'Polling Active',
        badgeVariant: 'connected',
        status: 'connected',
      });
    }
    return list;
  }, [backendEvents.length, isConnected, telegramPolling]);

  // Filter events by tab and text query
  const displayedEvents = useMemo(() => {
    return backendEvents.filter((ev) => {
      if (activeTab !== 'all' && ev.channel !== activeTab) return false;
      if (!filterQuery.trim()) return true;
      const q = filterQuery.toLowerCase();
      const content = typeof ev.payload === 'object' ? JSON.stringify(ev.payload) : String(ev.payload || '');
      return (
        ev.event_id?.toLowerCase().includes(q) ||
        ev.run_id?.toLowerCase().includes(q) ||
        ev.event_type?.toLowerCase().includes(q) ||
        ev.status?.toLowerCase().includes(q) ||
        content.toLowerCase().includes(q)
      );
    });
  }, [backendEvents, activeTab, filterQuery]);

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

  const handleInspectRun = (runId) => {
    if (runId && inspectTurn) {
      inspectTurn({ runId, trajectory: [] });
    }
    navigate('/');
  };

  return (
    <div className="gateway-page animate-fade-in">
      {/* Top Header */}
      <div className="page-header">
        <div className="page-header-info">
          <h1 className="page-title">Gateway &amp; API Ledger</h1>
          <p className="page-subtitle">Durable cross-channel event telemetry backed by SQLite</p>
        </div>

        <div className="page-header-actions">
          <button 
            className="gateway-action-btn secondary"
            onClick={loadLedgerEvents}
            disabled={isLoadingEvents}
            title="Refresh Ledger Events"
          >
            <RefreshCw size={13} className={isLoadingEvents ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
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
            <span className="gateway-summary-label">Durable Ledger Events</span>
            <span className="gateway-summary-value">{backendEvents.length}</span>
          </div>
        </article>

        <article className="gateway-summary-item">
          <div className="gateway-summary-icon"><Radio size={16} /></div>
          <div>
            <span className="gateway-summary-label">Channels Configured</span>
            <span className="gateway-summary-value">{telegramPolling ? '2 Active (Web, Telegram)' : '1 Active (Web)'}</span>
          </div>
        </article>

        <article className="gateway-summary-item">
          <div className="gateway-summary-icon"><Activity size={16} /></div>
          <div>
            <span className="gateway-summary-label">Storage Integrity</span>
            <span className="gateway-summary-value">SQLite Durable</span>
          </div>
        </article>
      </section>

      {/* Main Ledger Card */}
      <Card className="gateway-card">
        <TabBar tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />

        <div className="gateway-controls" style={{ padding: '10px 14px', borderBottom: '1px solid var(--border)', display: 'flex', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flex: 1 }}>
            <Search size={14} className="text-muted" />
            <input
              type="text"
              placeholder="Filter by event ID, run ID, event type, status, or content..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              style={{
                width: '100%',
                background: 'transparent',
                border: 'none',
                color: 'var(--text-display)',
                fontSize: '12px',
                fontFamily: 'var(--font-mono)',
                outline: 'none',
              }}
            />
          </div>
        </div>

        <div className="gateway-body">
          {eventsError && (
            <div className="gateway-error-banner" style={{ padding: '10px 14px', background: 'var(--accent-subtle)', color: 'var(--accent)', fontSize: '12px' }}>
              ⚠️ {eventsError}
            </div>
          )}

          {displayedEvents.length === 0 ? (
            <div className="gateway-empty-wrap">
              <div className="channel-state-panel compact">
                <div className="channel-state-copy">
                  <div className="channel-state-icon"><MessageSquare size={20} /></div>
                  <div>
                    <span className="channel-state-eyebrow">Durable Ledger</span>
                    <h2>No events found in this view</h2>
                    <p>Inbound and outbound messages from Web and Telegram are logged here automatically.</p>
                  </div>
                </div>
                <button className="gateway-action-btn" onClick={() => navigate('/')}>
                  Open Chat
                  <ArrowUpRight size={13} />
                </button>
              </div>
            </div>
          ) : (
            <div className="gateway-table-container">
              <table className="gateway-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Channel</th>
                    <th>Direction</th>
                    <th>Event Type</th>
                    <th>Status</th>
                    <th>Event ID</th>
                    <th>Run ID</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {displayedEvents.map((ev, index) => {
                    const isInbound = ev.direction === 'inbound';
                    const payloadSnippet = typeof ev.payload === 'object'
                      ? (ev.payload.text || ev.payload.reply || JSON.stringify(ev.payload))
                      : String(ev.payload || '');

                    return (
                      <tr key={ev.event_id || index} className="gateway-row">
                        <td className="gateway-cell-time mono">
                          {formatTimestamp(ev.created_at)}
                        </td>

                        <td className="gateway-cell-channel">
                          <span className={`channel-badge ${ev.channel}`}>{ev.channel}</span>
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

                        <td className="gateway-cell-content mono" title={payloadSnippet}>
                          <span className="content-text truncate">
                            <strong>{ev.event_type}</strong>
                            {payloadSnippet ? ` — ${payloadSnippet.slice(0, 40)}` : ''}
                          </span>
                        </td>

                        <td>
                          <span className={`delivery-badge status-${ev.status || 'completed'}`} style={{
                            fontSize: '10px',
                            fontFamily: 'var(--font-mono)',
                            padding: '2px 6px',
                            borderRadius: '3px',
                            textTransform: 'uppercase',
                            background: ev.status === 'failed' ? 'var(--accent-subtle)' : 'var(--surface-raised)',
                            color: ev.status === 'failed' ? 'var(--accent)' : 'var(--text-display)',
                            border: '1px solid var(--border)',
                          }}>
                            {ev.status || 'completed'}
                          </span>
                        </td>

                        <td className="gateway-cell-eventid mono">
                          <button
                            className="run-id-pill"
                            onClick={() => copyToClipboard(ev.event_id, `ev-${index}`)}
                            title="Click to copy Event ID"
                          >
                            <span>{(ev.event_id || '').slice(0, 10)}...</span>
                            {copiedId === `ev-${index}` ? (
                              <Check size={12} className="copy-icon success" />
                            ) : (
                              <Copy size={12} className="copy-icon" />
                            )}
                          </button>
                        </td>

                        <td className="gateway-cell-runid mono">
                          {ev.run_id ? (
                            <button
                              className="run-id-pill"
                              onClick={() => copyToClipboard(ev.run_id, `run-${index}`)}
                              title="Click to copy Run ID"
                            >
                              <span>{(ev.run_id || '').slice(0, 10)}...</span>
                              {copiedId === `run-${index}` ? (
                                <Check size={12} className="copy-icon success" />
                              ) : (
                                <Copy size={12} className="copy-icon" />
                              )}
                            </button>
                          ) : (
                            <span className="muted-dim">—</span>
                          )}
                        </td>

                        <td>
                          {ev.run_id ? (
                            <button
                              className="gateway-action-btn secondary"
                              style={{ padding: '3px 8px', fontSize: '11px' }}
                              onClick={() => handleInspectRun(ev.run_id)}
                              title="Navigate to run trajectory"
                            >
                              <span>Inspect</span>
                              <ArrowUpRight size={11} />
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
