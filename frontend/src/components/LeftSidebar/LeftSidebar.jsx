import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { 
  Plus, 
  Folder, 
  FolderPlus,
  SlidersHorizontal,
  Search, 
  Trash2, 
  Edit2, 
  Check, 
  PanelLeftClose, 
  PanelLeft,
  ChevronDown,
  ChevronRight,
  Globe,
  Sun,
  Moon
} from 'lucide-react';
import { useChat } from '../../context/ChatContext';
import { useHealth } from '../../context/HealthContext';
import { useTheme } from '../../context/ThemeContext';
import lightLogo from '../../assets/light.png';
import darkLogo from '../../assets/dark.png';
import './LeftSidebar.css';

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

export function LeftSidebar({ isCollapsed, onToggleCollapse }) {
  const navigate = useNavigate();
  const {
    sessions,
    activeSessionId,
    switchSession,
    createNewSession,
    deleteSession,
    renameSession
  } = useChat();

  const { modelName, isConnected } = useHealth();
  const { theme, toggleTheme } = useTheme();
  const logoSrc = theme === 'light' ? lightLogo : darkLogo;

  const handleCreateNewSession = () => {
    createNewSession();
    navigate('/');
  };

  const handleSelectSession = (sessionId) => {
    switchSession(sessionId);
    navigate('/');
  };

  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isWorkspaceExpanded, setIsWorkspaceExpanded] = useState(true);
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

  const DISPLAY_LIMIT = 5;
  const visibleSessions = showAllSessions ? filteredSessions : filteredSessions.slice(0, DISPLAY_LIMIT);
  const hiddenCount = filteredSessions.length - visibleSessions.length;

  return (
    <aside className={`left-sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      {/* Header / Brand with Harness Badge */}
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
            <div className="brand-harness-group">
              <span className="brand-harness-title">poseidon</span>
              <span className="brand-harness-badge">HARNESS</span>
            </div>
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

      {/* New Session Action Pill */}
      <div className="sidebar-action-container">
        <button
          className="new-chat-pill-btn"
          onClick={handleCreateNewSession}
          title="Start New Session"
        >
          <div className="plus-icon-circle">
            <Plus size={13} />
          </div>
          {!isCollapsed && <span className="new-chat-pill-label">New Session</span>}
        </button>
      </div>

      {!isCollapsed && (
        <div className="sidebar-body-scrollable">
          {/* Workspaces Section Header */}
          <div className="workspaces-section-header">
            <span className="workspaces-title">Workspaces</span>
            <div className="workspaces-actions">
              <button 
                className={`workspace-icon-btn ${isSearchOpen ? 'active' : ''}`}
                onClick={() => setIsSearchOpen(!isSearchOpen)}
                title="Search Sessions"
              >
                <Search size={13} />
              </button>
              <button 
                className="workspace-icon-btn"
                title="Workspace Filter &amp; Settings"
              >
                <SlidersHorizontal size={13} />
              </button>
              <button 
                className="workspace-icon-btn"
                onClick={handleCreateNewSession}
                title="Create Workspace / Session"
              >
                <FolderPlus size={13} />
              </button>
            </div>
          </div>

          {/* Search Bar Input */}
          {isSearchOpen && (
            <div className="workspace-search-bar">
              <input
                type="text"
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                autoFocus
              />
            </div>
          )}

          {/* Workspace Folder Node */}
          <div className="workspace-folder-tree">
            <div 
              className="workspace-folder-item"
              onClick={() => setIsWorkspaceExpanded(!isWorkspaceExpanded)}
            >
              <Folder size={14} className="workspace-folder-icon" />
              <span className="workspace-folder-name">PoseidonHarness</span>
              <div className="folder-chevron">
                {isWorkspaceExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              </div>
            </div>

            {/* Nested Session Items */}
            {isWorkspaceExpanded && (
              <div className="workspace-nested-sessions">
                {filteredSessions.length === 0 ? (
                  <div className="empty-chats">No conversations</div>
                ) : (
                  <>
                    {visibleSessions.map((session) => {
                      const isActive = session.id === activeSessionId;
                      const isEditing = editingId === session.id;
                      const timeStr = formatShortTime(session.updatedAt || session.createdAt);

                      return (
                        <div
                          key={session.id}
                          className={`harness-session-item ${isActive ? 'active' : ''}`}
                          onClick={() => handleSelectSession(session.id)}
                        >
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
                              <span className="session-title-text" title={session.title}>
                                {session.title || 'New Session'}
                              </span>
                              {timeStr && !isActive && (
                                <span className="session-time-text">{timeStr}</span>
                              )}
                            </>
                          )}

                          <div className="session-item-actions">
                            {isEditing ? (
                              <button className="action-btn" onClick={(e) => handleSaveRename(session.id, e)}>
                                <Check size={12} />
                              </button>
                            ) : (
                              <>
                                <button className="action-btn" onClick={(e) => handleStartRename(session, e)}>
                                  <Edit2 size={11} />
                                </button>
                                <button className="action-btn delete" onClick={(e) => handleDelete(session.id, e)}>
                                  <Trash2 size={11} />
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      );
                    })}

                    {/* Show more sessions toggle */}
                    {hiddenCount > 0 && !showAllSessions && (
                      <button 
                        className="show-more-sessions-btn"
                        onClick={() => setShowAllSessions(true)}
                      >
                        Show {hiddenCount} more {hiddenCount === 1 ? 'session' : 'sessions'}
                      </button>
                    )}

                    {showAllSessions && filteredSessions.length > DISPLAY_LIMIT && (
                      <button 
                        className="show-more-sessions-btn"
                        onClick={() => setShowAllSessions(false)}
                      >
                        Show less
                      </button>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Footer Theme Toggle & Gateway API Link */}
      <div className="sidebar-footer">
        <NavLink to="/gateway" className={({ isActive }) => `sidebar-gateway-pill ${isActive ? 'active' : ''}`} title="Gateway &amp; API Ledger">
          <Globe size={13} />
          {!isCollapsed && <span>Gateway &amp; API Ledger</span>}
        </NavLink>

        <button 
          className="sidebar-theme-pill"
          onClick={toggleTheme}
          title={theme === 'dark' ? "Switch to Light Theme" : "Switch to Dark Theme"}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun size={13} /> : <Moon size={13} />}
          {!isCollapsed && <span>{theme === 'dark' ? 'Light Theme' : 'Dark Theme'}</span>}
        </button>
      </div>
    </aside>
  );
}

export default LeftSidebar;
