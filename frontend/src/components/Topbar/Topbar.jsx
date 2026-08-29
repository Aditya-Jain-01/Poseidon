import React from 'react';
import { NavLink } from 'react-router-dom';
import { MessageSquare } from 'lucide-react';
import StatusBadge from '../common/StatusBadge';
import { useHealth } from '../../context/HealthContext';
import './Topbar.css';

export function Topbar({ isChatOpen = true, onToggleChat, statusSlot = null }) {
  const { isConnected, modelName, isLoading } = useHealth();

  const statusLabel = isConnected
    ? modelName ? modelName.replace('google/', '') : 'Connected'
    : isLoading ? 'Connecting...' : 'Disconnected';

  const statusType = isLoading ? 'loading' : isConnected ? 'connected' : 'disconnected';

  return (
    <header className="topbar">
      <div className="topbar-left">
        <NavLink to="/" className="topbar-brand">
          <span>POSEIDON</span>
          <span className="topbar-brand-dot" />
        </NavLink>
        <span className="topbar-brand-tag">v0.1</span>
      </div>

      <nav className="topbar-nav">
        <NavLink
          to="/"
          end
          className={({ isActive }) => `topbar-link ${isActive ? 'active' : ''}`}
        >
          Overview
        </NavLink>
        <NavLink
          to="/gateway"
          className={({ isActive }) => `topbar-link ${isActive ? 'active' : ''}`}
        >
          Gateway
        </NavLink>
      </nav>

      <div className="topbar-right">
        {statusSlot || (
          <StatusBadge
            status={statusType}
            label={statusLabel}
          />
        )}

        <button
          className={`topbar-chat-btn ${isChatOpen ? 'active' : ''}`}
          onClick={onToggleChat}
          title={isChatOpen ? 'Hide Chat Dock' : 'Show Chat Dock'}
          aria-label="Toggle chat dock"
        >
          <MessageSquare size={16} />
        </button>
      </div>
    </header>
  );
}

export default Topbar;
