import React from 'react';
import { useAgents } from '../../context/AgentContext';
import { Bot, Zap, MessageSquare, Shield, Activity } from 'lucide-react';
import './AgentView.css';

/**
 * Agent Profile View — displayed when sidebar is in Agent mode
 */
export default function AgentView() {
  const { activeAgent, healthStatus, llmSettings, agents } = useAgents();

  if (!activeAgent) {
    return (
      <div className="agent-view-empty">
        <div className="empty-icon-wrap">
          <Bot size={48} strokeWidth={1.5} />
        </div>
        <h2>Select an agent</h2>
        <p>Choose an agent from the sidebar to view their profile and capabilities</p>
      </div>
    );
  }

  const status = healthStatus[activeAgent.id]?.status || 'offline';
  const statusMessage = healthStatus[activeAgent.id]?.message || '';
  const agentLLM = llmSettings?.agent_overrides?.[activeAgent.id] || {};
  const model = healthStatus[activeAgent.id]?.model || agentLLM.model || 'Not configured';

  return (
    <div className="agent-view">
      <div className="agent-view-content">
        {/* Profile Card */}
        <div className="agent-profile-card">
          <div 
            className="agent-profile-avatar" 
            style={{ backgroundColor: activeAgent.color || '#a855f7' }}
          >
            {activeAgent.avatar || activeAgent.display_name?.[0]?.toUpperCase() || 'A'}
          </div>
          <h2 className="agent-profile-name">{activeAgent.display_name || activeAgent.id}</h2>
          <span className="agent-profile-role">{activeAgent.role || 'Agent'}</span>
          
          <div className={`agent-profile-status ${status}`}>
            <span className="profile-status-dot" />
            <span>
              {status === 'online' ? 'Online' : status === 'checking' ? 'Checking...' : 'Offline'}
            </span>
          </div>

          {activeAgent.description && (
            <p className="agent-profile-description">{activeAgent.description}</p>
          )}
        </div>

        {/* Details Grid */}
        <div className="agent-details-grid">
          {/* Model Info */}
          <div className="agent-detail-card">
            <h3>
              <Activity size={16} />
              <span>Model</span>
            </h3>
            <p className="detail-value mono">{model}</p>
          </div>

          {/* Personality */}
          {activeAgent.personality && (
            <div className="agent-detail-card">
              <h3>
                <MessageSquare size={16} />
                <span>Personality</span>
              </h3>
              <p>{activeAgent.personality}</p>
            </div>
          )}

          {/* Tools */}
          {activeAgent.tools?.length > 0 && (
            <div className="agent-detail-card">
              <h3>
                <Zap size={16} />
                <span>Tools</span>
              </h3>
              <div className="detail-chips">
                {activeAgent.tools.map((t) => (
                  <span key={t} className="detail-chip">{t}</span>
                ))}
              </div>
            </div>
          )}

          {/* Routing Signals */}
          {activeAgent.routing_signals?.length > 0 && (
            <div className="agent-detail-card">
              <h3>
                <Shield size={16} />
                <span>Routing Signals</span>
              </h3>
              <div className="detail-chips">
                {activeAgent.routing_signals.map((s) => (
                  <span key={s} className="detail-chip">{s}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
