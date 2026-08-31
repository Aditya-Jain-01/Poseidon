import React, { useState } from 'react';
import { History, Plus, Trash2, Edit2, Check, X, Search, MessageSquare, Calendar } from 'lucide-react';
import { useChat } from '../../context/ChatContext';
import './HistoryDrawer.css';

export function HistoryDrawer() {
  const {
    sessions,
    activeSessionId,
    switchSession,
    createNewSession,
    deleteSession,
    renameSession,
    clearAllHistory,
    isHistoryOpen,
    closeHistory,
  } = useChat();

  const [searchQuery, setSearchQuery] = useState('');
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

  const handleKeyDownRename = (sessionId, e) => {
    if (e.key === 'Enter') {
      handleSaveRename(sessionId, e);
    } else if (e.key === 'Escape') {
      setEditingId(null);
    }
  };

  const handleDelete = (sessionId, e) => {
    e.stopPropagation();
    if (window.confirm('Delete this chat session?')) {
      deleteSession(sessionId);
    }
  };

  const handleClearAll = () => {
    if (window.confirm('Are you sure you want to clear all chat history?')) {
      clearAllHistory();
    }
  };

  // Filter sessions by search query
  const filteredSessions = sessions.filter((s) => {
    const q = searchQuery.toLowerCase();
    if (!q) return true;
    if (s.title.toLowerCase().includes(q)) return true;
    return s.messages.some((m) => m.content.toLowerCase().includes(q));
  });

  // Group sessions by date
  const grouped = groupSessionsByDate(filteredSessions);

  return (
    <div className={`history-drawer ${isHistoryOpen ? 'open' : ''}`}>
      {/* Header */}
      <div className="history-header">
        <div className="history-title-row">
          <div className="history-brand">
            <History size={18} className="history-icon" />
            <span>Chat History</span>
          </div>
          <button className="history-close-btn" onClick={closeHistory} title="Close History (ESC)">
            <X size={18} />
          </button>
        </div>

        {/* New Chat Button */}
        <button
          className="history-new-chat-btn"
          onClick={() => {
            createNewSession();
            closeHistory();
          }}
        >
          <Plus size={16} />
          <span>New Chat</span>
        </button>

        {/* Search Bar */}
        <div className="history-search-wrapper">
          <Search size={14} className="search-icon" />
          <input
            type="text"
            className="history-search-input"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button className="search-clear-btn" onClick={() => setSearchQuery('')}>
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Session List */}
      <div className="history-list">
        {filteredSessions.length === 0 ? (
          <div className="history-empty">
            <MessageSquare size={32} className="empty-icon" />
            <p className="empty-text">
              {searchQuery ? 'No matching conversations' : 'No saved conversations'}
            </p>
          </div>
        ) : (
          Object.entries(grouped).map(([groupTitle, groupSessions]) => {
            if (groupSessions.length === 0) return null;
            return (
              <div key={groupTitle} className="history-group">
                <div className="history-group-header">
                  <Calendar size={12} />
                  <span>{groupTitle}</span>
                </div>

                <div className="history-group-items">
                  {groupSessions.map((session) => {
                    const isActive = session.id === activeSessionId;
                    const isEditing = editingId === session.id;
                    const msgCount = session.messages.length;

                    return (
                      <div
                        key={session.id}
                        className={`history-item ${isActive ? 'active' : ''}`}
                        onClick={() => {
                          switchSession(session.id);
                          closeHistory();
                        }}
                      >
                        <MessageSquare size={15} className="item-icon" />

                        <div className="item-details">
                          {isEditing ? (
                            <input
                              type="text"
                              className="item-rename-input"
                              value={editTitle}
                              onChange={(e) => setEditTitle(e.target.value)}
                              onKeyDown={(e) => handleKeyDownRename(session.id, e)}
                              onBlur={(e) => handleSaveRename(session.id, e)}
                              autoFocus
                              onClick={(e) => e.stopPropagation()}
                            />
                          ) : (
                            <span className="item-title" title={session.title}>
                              {session.title || 'Untitled Chat'}
                            </span>
                          )}

                          <span className="item-meta">
                            {msgCount} {msgCount === 1 ? 'msg' : 'msgs'} · {formatTime(session.updatedAt)}
                          </span>
                        </div>

                        {/* Item Actions */}
                        <div className="item-actions">
                          {isEditing ? (
                            <button
                              className="action-btn save-btn"
                              onClick={(e) => handleSaveRename(session.id, e)}
                              title="Save title"
                            >
                              <Check size={14} />
                            </button>
                          ) : (
                            <>
                              <button
                                className="action-btn"
                                onClick={(e) => handleStartRename(session, e)}
                                title="Rename chat"
                              >
                                <Edit2 size={13} />
                              </button>
                              <button
                                className="action-btn delete-btn"
                                onClick={(e) => handleDelete(session.id, e)}
                                title="Delete chat"
                              >
                                <Trash2 size={13} />
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      {sessions.length > 0 && (
        <div className="history-footer">
          <button className="history-clear-all-btn" onClick={handleClearAll}>
            <Trash2 size={14} />
            <span>Clear All History</span>
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * Helper to group sessions by timeframe (Today, Yesterday, Previous 7 Days, Older).
 */
function groupSessionsByDate(sessions) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const yesterday = today - 86400000;
  const last7Days = today - 7 * 86400000;

  const groups = {
    Today: [],
    Yesterday: [],
    'Previous 7 Days': [],
    Older: [],
  };

  sessions.forEach((session) => {
    const time = new Date(session.updatedAt || session.createdAt).getTime();
    if (time >= today) {
      groups.Today.push(session);
    } else if (time >= yesterday) {
      groups.Yesterday.push(session);
    } else if (time >= last7Days) {
      groups['Previous 7 Days'].push(session);
    } else {
      groups.Older.push(session);
    }
  });

  return groups;
}

/**
 * Format relative time or short date string.
 */
function formatTime(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

export default HistoryDrawer;
