import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { 
  Plus, 
  Search, 
  Trash2, 
  Edit2, 
  Check, 
  PanelLeftClose, 
  PanelLeft,
  Globe,
  Settings as SettingsIcon,
  Sun,
  Moon,
  MessageSquare,
  Users,
  Bot
} from 'lucide-react';
import { useChat } from '../../context/ChatContext';
import { useHealth } from '../../context/HealthContext';
import { useTheme } from '../../context/ThemeContext';
import { useAgents } from '../../context/AgentContext';
import lightLogo from '../../assets/light.png';
import darkLogo from '../../assets/dark.png';
import './LeftSidebar.css';

const AVATAR_COLORS = ['#2F81F7', '#38BDF8', '#0284C7', '#1D4ED8', '#0EA5E9', '#06B6D4'];

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

export function LeftSidebar({ isCollapsed, onToggleCollapse, sidebarMode, onModeChange }) {
  const navigate = useNavigate();
  const {
    sessions,
    activeSessionId,
    switchSession,
    createNewSession,
    deleteSession,
    renameSession
  } = useChat();

  const { agents, activeAgentId, setActiveAgentId, healthStatus } = useAgents();
  const { theme, toggleTheme } = useTheme();
  const logoSrc = theme === 'light' ? lightLogo : darkLogo;

  const handleCreateNewSession = () => {
    createNewSession();
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
    <aside className={`left-sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      {/* Header / Brand */}
      <div className="sidebar-header">
        <div className="brand-wrapper" onClick={() => navigate('/')} title="Go to Chat" style={{ cursor: 'pointer' }}>
          <div className="brand-logo" aria-hidden="true">
            <img 
              src={logoSrc} 
              alt="Poseidon Logo" 
              className="brand-logo-img" 
            />
          </div>
          {!isCollapsed && (
            <span className="brand-title">Poseidon</span>
          )}
        </div>

        <button 
          className="sidebar-toggle-btn"
          onClick={onToggleCollapse}
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
        </button>
      </div>

      {/* Mode Toggle — Chat / Agents */}
      {!isCollapsed && (
        <div className="mode-toggle-container">
          <div className="mode-toggle-pill">
            <button
              className={`mode-toggle-btn ${sidebarMode === 'chat' ? 'active' : ''}`}
              onClick={() => onModeChange('chat')}
            >
              <MessageSquare size={14} />
              <span>Chat</span>
            </button>
            <button
              className={`mode-toggle-btn ${sidebarMode === 'agents' ? 'active' : ''}`}
              onClick={() => onModeChange('agents')}
            >
              <Bot size={14} />
              <span>Agents</span>
            </button>
            <div className={`mode-toggle-slider ${sidebarMode === 'agents' ? 'right' : 'left'}`} />
          </div>
        </div>
      )}

      {/* Mode Content */}
      <div className="sidebar-body-scrollable">
        {sidebarMode === 'chat' ? (
          /* ─── Chat Mode ─── */
          <>
            {/* New Session Button */}
            <div className="sidebar-action-container">
              <button
                className="new-session-btn"
                onClick={handleCreateNewSession}
                title="Start New Session"
              >
                <Plus size={16} />
                {!isCollapsed && <span>New Chat</span>}
              </button>
            </div>

            {!isCollapsed && (
              <>
                {/* Search */}
                <div className="session-section-header">
                  <span className="section-title">Recent</span>
                  <button
                    className={`section-action-btn ${isSearchOpen ? 'active' : ''}`}
                    onClick={() => setIsSearchOpen(!isSearchOpen)}
                    title="Search"
                  >
                    <Search size={14} />
                  </button>
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

      {/* Footer */}
      <div className="sidebar-footer">
        <NavLink to="/gateway" className={({ isActive }) => `footer-link ${isActive ? 'active' : ''}`} title="Gateway & API">
          <Globe size={16} />
          {!isCollapsed && <span>Gateway</span>}
        </NavLink>

        <NavLink to="/settings" className={({ isActive }) => `footer-link ${isActive ? 'active' : ''}`} title="Settings">
          <SettingsIcon size={16} />
          {!isCollapsed && <span>Settings</span>}
        </NavLink>

        <button 
          className="footer-link"
          onClick={toggleTheme}
          title={theme === 'dark' ? "Light mode" : "Dark mode"}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          {!isCollapsed && <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>}
        </button>
      </div>
    </aside>
  );
}

export default LeftSidebar;
