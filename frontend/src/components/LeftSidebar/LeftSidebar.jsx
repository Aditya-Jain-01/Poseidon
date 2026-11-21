import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { 
  Search, 
  SquarePen,
  Trash2, 
  Edit2, 
  Check, 
  PanelLeftClose, 
  PanelLeft,
  MessageSquare,
  Bot, BrainCircuit, Globe, MoreHorizontal, Settings, Moon, Sun,
} from 'lucide-react';
import { useChat } from '../../context/ChatContext';
import { useAgents } from '../../context/AgentContext';
import './LeftSidebar.css';
import { useTheme } from '../../context/ThemeContext';

const AVATAR_COLORS = ['#507d73', '#7a8665', '#667b85', '#866f65', '#6c7688', '#567f82'];

/**
 * Format timestamp into compact short indicator like "11h", "12h", "2d"
 */
function formatShortTime(timestamp) {
  if (!timestamp) return '';
  const now = Date.now();
  const then = new Date(timestamp).getTime();
  const diffSec = Math.max(0, Math.floor((now - then) / 1000));
  if (diffSec < 60) return 'now';
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h`;
  if (diffSec < 604800) return `${Math.floor(diffSec / 86400)}d`;
  return `${Math.floor(diffSec / 604800)}w`;
}

/**
 * Get a deterministic color for a session based on its index
 */
function getSessionColor(index) {
  return AVATAR_COLORS[index % AVATAR_COLORS.length];
}

export function LeftSidebar({ isCollapsed, onToggleCollapse, sidebarMode, onModeChange, width, resizeHandlers }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const {
    sessions,
    activeSessionId,
    switchSession,
    createNewSession,
    deleteSession,
    renameSession
  } = useChat();

  const { agents, activeAgentId, setActiveAgentId, healthStatus } = useAgents();

  const handleCreateNewSession = () => {
    createNewSession();
    onModeChange('chat');
    navigate('/');
  };

  const handleSelectSession = (sessionId) => {
    switchSession(sessionId);
    if (sidebarMode !== 'chat') onModeChange('chat');
    navigate('/');
  };

  const handleSelectAgent = (agentId) => {
    setActiveAgentId(agentId);
    navigate('/');
  };

  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [showAllSessions, setShowAllSessions] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  const handleStartRename = (session, e) => {
    e.stopPropagation();
    setEditingId(session.id);
    setEditTitle(session.title);
  };

  const handleSaveRename = (sessionId, e) => {
    if (e) e.stopPropagation();
    if (editTitle.trim()) {
      renameSession(sessionId, editTitle.trim());
    }
    setEditingId(null);
  };

  const handleDelete = (sessionId, e) => {
    e.stopPropagation();
    if (window.confirm('Delete this conversation?')) {
      deleteSession(sessionId);
    }
  };

  const filteredSessions = sessions.filter((s) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return s.title.toLowerCase().includes(q) || s.messages?.some(m => m.content.toLowerCase().includes(q));
  });

  const DISPLAY_LIMIT = 8;
  const visibleSessions = showAllSessions ? filteredSessions : filteredSessions.slice(0, DISPLAY_LIMIT);
  const hiddenCount = filteredSessions.length - visibleSessions.length;

  return (
    <aside className={`left-sidebar ${isCollapsed ? 'collapsed' : ''}`} style={{ width }}>
      {/* Header / Brand */}
      <div className="sidebar-header">
        <button type="button" className="brand-wrapper" onClick={() => { onModeChange('chat'); navigate('/'); }} title="Go to Chat">
          {!isCollapsed && (
            <span className="brand-title">Poseidon</span>
          )}
        </button>

        <div className="sidebar-header-actions">
          {!isCollapsed && <button className="sidebar-toggle-btn" onClick={() => setIsSearchOpen(!isSearchOpen)} title="Search conversations" aria-label="Search conversations"><Search size={17} /></button>}
          <button
            className="sidebar-toggle-btn"
            onClick={onToggleCollapse}
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
          </button>
        </div>
      </div>

      <div className="sidebar-action-container">
        <button className="new-session-btn" onClick={handleCreateNewSession} title="New session"><SquarePen size={17} />{!isCollapsed && <span>New Session</span>}</button>
      </div>
      <nav className="sidebar-primary-nav" aria-label="Workspace navigation">
        {[
          { label: 'Agents', icon: Bot, path: '/', mode: 'agents' },
          { label: 'Brain', icon: BrainCircuit, path: '/brain', mode: 'chat' },
          { label: 'Gateway', icon: Globe, path: '/gateway', mode: 'chat' },
        ].map(({ label, icon: Icon, path, mode }) => <button key={label} title={label} className={location.pathname === path && sidebarMode === mode ? 'active' : ''} onClick={() => { onModeChange(mode); navigate(path); }}><Icon size={18} />{!isCollapsed && <span>{label}</span>}</button>)}
      </nav>
      <div className="sidebar-body-scrollable">
        {sidebarMode === 'chat' ? (
          <>
            {!isCollapsed && (
              <>
                {/* Search */}
                <div className="session-section-header">
                  <span className="section-title">Conversations</span>
                </div>

                {isSearchOpen && (
                  <div className="search-bar">
                    <Search size={14} className="search-icon" />
                    <input
                      type="text"
                      placeholder="Search conversations..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      autoFocus
                    />
                  </div>
                )}

                {/* Session List */}
                <div className="session-list">
                  {filteredSessions.length === 0 ? (
                    <div className="empty-state">
                      <MessageSquare size={20} />
                      <p>No conversations yet</p>
                    </div>
                  ) : (
                    <>
                      {visibleSessions.map((session, index) => {
                        const isActive = session.id === activeSessionId;
                        const isEditing = editingId === session.id;
                        const timeStr = formatShortTime(session.updatedAt || session.createdAt);

                        return (
                          <div
                            key={session.id}
                            className={`session-item ${isActive ? 'active' : ''}`}
                            onClick={() => handleSelectSession(session.id)}
                          >
                            <div className="session-avatar" style={{ backgroundColor: getSessionColor(index) }}>
                              {(session.title || 'N')[0].toUpperCase()}
                            </div>

                            {isEditing ? (
                              <input
                                type="text"
                                className="session-edit-input"
                                value={editTitle}
                                onChange={(e) => setEditTitle(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') handleSaveRename(session.id, e);
                                  if (e.key === 'Escape') setEditingId(null);
                                }}
                                onBlur={(e) => handleSaveRename(session.id, e)}
                                autoFocus
                                onClick={(e) => e.stopPropagation()}
                              />
                            ) : (
                              <>
                                <span className="session-title" title={session.title}>
                                  {session.title || 'New Chat'}
                                </span>
                                {timeStr && (
                                  <span className="session-time">{timeStr}</span>
                                )}
                              </>
                            )}

                            <div className="session-actions">
                              {isEditing ? (
                                <button className="action-btn" onClick={(e) => handleSaveRename(session.id, e)}>
                                  <Check size={12} />
                                </button>
                              ) : (
                                <>
                                  <button className="action-btn" onClick={(e) => handleStartRename(session, e)}>
                                    <Edit2 size={12} />
                                  </button>
                                  <button className="action-btn delete" onClick={(e) => handleDelete(session.id, e)}>
                                    <Trash2 size={12} />
                                  </button>
                                </>
                              )}
                            </div>
                          </div>
                        );
                      })}

                      {hiddenCount > 0 && !showAllSessions && (
                        <button
                          className="show-more-btn"
                          onClick={() => setShowAllSessions(true)}
                        >
                          Show {hiddenCount} more
                        </button>
                      )}

                      {showAllSessions && filteredSessions.length > DISPLAY_LIMIT && (
                        <button
                          className="show-more-btn"
                          onClick={() => setShowAllSessions(false)}
                        >
                          Show less
                        </button>
                      )}
                    </>
                  )}
                </div>
              </>
            )}
          </>
        ) : (
          /* ─── Agent Mode ─── */
          <>
            {!isCollapsed && (
              <>
                <div className="session-section-header">
                  <span className="section-title">Agents</span>
                  <span className="section-count">{agents.length}</span>
                </div>

                <div className="agent-list">
                  {agents.length === 0 ? (
                    <div className="empty-state">
                      <Bot size={24} />
                      <p>No agents configured</p>
                      <span className="empty-hint">Configure agents in Settings</span>
                    </div>
                  ) : (
                    agents.map((agent, index) => {
                      const isActive = agent.id === activeAgentId;
                      const status = healthStatus[agent.id]?.status || 'offline';
                      const color = agent.color || AVATAR_COLORS[index % AVATAR_COLORS.length];
                      return (
                        <div
                          key={agent.id}
                          className={`agent-item ${isActive ? 'active' : ''}`}
                          onClick={() => handleSelectAgent(agent.id)}
                        >
                          <div className="agent-avatar" style={{ backgroundColor: color }}>
                            {agent.avatar || agent.display_name?.[0]?.toUpperCase() || 'A'}
                          </div>
                          <div className="agent-info">
                            <span className="agent-name">{agent.display_name || agent.id}</span>
                            <span className="agent-role">{agent.role || 'Agent'}</span>
                          </div>
                          <span className={`agent-status-dot ${status}`} title={status} />
                        </div>
                      );
                    })
                  )}
                </div>
              </>
            )}

            {isCollapsed && agents.map((agent, index) => {
              const isActive = agent.id === activeAgentId;
              const color = agent.color || AVATAR_COLORS[index % AVATAR_COLORS.length];
              return (
                <div
                  key={agent.id}
                  className={`agent-item-collapsed ${isActive ? 'active' : ''}`}
                  onClick={() => handleSelectAgent(agent.id)}
                  title={agent.display_name || agent.id}
                >
                  <div className="agent-avatar" style={{ backgroundColor: color }}>
                    {agent.avatar || agent.display_name?.[0]?.toUpperCase() || 'A'}
                  </div>
                </div>
              );
            })}
          </>
        )}
      </div>
      <details className="sidebar-more">
        <summary title="More"><MoreHorizontal size={18} />{!isCollapsed && <span>More</span>}</summary>
        <div className="sidebar-more-menu">
          <button onClick={(event) => { event.currentTarget.closest('details').open = false; navigate('/settings'); }}><Settings size={17} />Settings</button>
          <button onClick={toggleTheme}>{theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}{theme === 'dark' ? 'Light appearance' : 'Dark appearance'}</button>
        </div>
      </details>
      {!isCollapsed && <div className="left-sidebar-resize-handle" role="separator" tabIndex={0} aria-label="Resize conversations sidebar" aria-orientation="vertical" aria-valuenow={width} aria-valuemin={220} aria-valuemax={360} {...resizeHandlers} />}

    </aside>
  );
}

export default LeftSidebar;
