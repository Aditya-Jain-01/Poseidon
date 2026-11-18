import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, ArrowUpRight, Bot, Cpu, RefreshCw, Route, Settings2, Wrench } from 'lucide-react';
import { useAgents } from '../../context/AgentContext';
import './AgentView.css';

function agentStatus(health) {
  if (!health) return { label: 'Not checked', tone: 'unknown' };
  if (health.status === 'online') return { label: 'Connected', tone: 'online' };
  if (health.status === 'checking') return { label: 'Checking', tone: 'checking' };
  return { label: 'Unavailable', tone: 'offline' };
}

export default function AgentView() {
  const navigate = useNavigate();
  const { agents, activeAgent, setActiveAgentId, healthStatus, llmSettings,
    checkAgentHealth, testAllConnections, isLoading, error } = useAgents();

  const connected = agents.filter((agent) => healthStatus[agent.id]?.status === 'online').length;
  const tested = agents.filter((agent) => Boolean(healthStatus[agent.id])).length;
  const toolCount = new Set(agents.flatMap((agent) => agent.tools || [])).size;
  const selected = activeAgent || agents[0];
  const selectedHealth = selected ? healthStatus[selected.id] : null;
  const selectedStatus = agentStatus(selectedHealth);
  const selectedModel = selected
    ? selectedHealth?.model || llmSettings?.agent_overrides?.[selected.id]?.model || llmSettings?.agents?.[selected.id]?.model || 'Not configured'
    : 'Not configured';

  return (
    <main className="agent-view">
      <div className="agent-view-content">
        <header className="agent-dashboard-header">
          <div>
            <h1>Agents</h1>
            <p>Inspect the people and tools behind Poseidon’s work.</p>
          </div>
          <button type="button" className="agent-refresh" onClick={testAllConnections} disabled={isLoading || agents.length === 0}>
            <RefreshCw size={15} /> Check all connections
          </button>
        </header>

        {error && <p className="agent-dashboard-error" role="alert">{error}</p>}

        <div className="agent-summary" aria-label="Agent summary">
          <div><span>Configured agents</span><strong>{agents.length}</strong></div>
          <div><span>Connected</span><strong>{connected}<small> / {tested} checked</small></strong></div>
          <div><span>Available tool types</span><strong>{toolCount}</strong></div>
        </div>

        {agents.length === 0 ? (
          <section className="agent-empty">
            <Bot size={34} strokeWidth={1.5} />
            <h2>{isLoading ? 'Loading agents' : 'No agents configured'}</h2>
            <p>{isLoading ? 'Reading the local roster.' : 'Create an agent in Settings to see its model, tools, and health here.'}</p>
            {!isLoading && <button type="button" onClick={() => navigate('/settings')}>Open Settings <ArrowUpRight size={15} /></button>}
          </section>
        ) : (
          <div className="agent-dashboard-grid">
            <div className="agent-dashboard-main">
              <section className="agent-feature" aria-label="Selected agent">
                <div className="agent-feature-top">
                  <div className="agent-feature-avatar" style={{ backgroundColor: selected.color || '#557b69' }} aria-hidden="true">
                    {selected.avatar || selected.display_name?.[0]?.toUpperCase() || 'A'}
                  </div>
                  <span className={`agent-status agent-status-${selectedStatus.tone}`}><span />{selectedStatus.label}</span>
                </div>
                <h2>{selected.display_name || selected.id}</h2>
                <p className="agent-feature-role">{selected.role || 'Agent'}</p>
                <p className="agent-feature-description">{selected.description || 'This agent is ready to be configured for a specific job.'}</p>
                <div className="agent-feature-actions">
                  <button type="button" onClick={() => checkAgentHealth(selected.id)} disabled={selectedStatus.tone === 'checking'}><Activity size={15} /> Test connection</button>
                  <button type="button" onClick={() => navigate('/settings')}><Settings2 size={15} /> Configure</button>
                </div>
              </section>

              <section className="agent-roster" aria-label="Agent roster">
                <div className="agent-section-heading"><h2>Agent roster</h2><span>{agents.length} configured</span></div>
                <div className="agent-roster-list">
                  {agents.map((agent) => {
                    const status = agentStatus(healthStatus[agent.id]);
                    return <button type="button" key={agent.id}
                      className={`agent-roster-row ${selected.id === agent.id ? 'selected' : ''}`}
                      onClick={() => setActiveAgentId(agent.id)} aria-pressed={selected.id === agent.id}>
                      <span className="agent-roster-avatar" style={{ backgroundColor: agent.color || '#557b69' }} aria-hidden="true">{agent.avatar || agent.display_name?.[0]?.toUpperCase() || 'A'}</span>
                      <span className="agent-roster-name"><strong>{agent.display_name || agent.id}</strong><small>{agent.role || 'Agent'}</small></span>
                      <span className={`agent-status agent-status-${status.tone}`}><span />{status.label}</span>
                      <span className="agent-roster-tools">{agent.tools?.length || 0} tools</span>
                    </button>;
                  })}
                </div>
              </section>

              <div className="agent-capabilities">
                <section className="agent-capability" aria-label="Agent tools">
                  <h3><Wrench size={16} /> Tools</h3>
                  {selected.tools?.length ? <div className="agent-chips">{selected.tools.map((tool) => <span key={tool}>{tool}</span>)}</div> : <p>No tools assigned.</p>}
                </section>
                <section className="agent-capability" aria-label="Routing signals">
                  <h3><Route size={16} /> Routing signals</h3>
                  {selected.routing_signals?.length ? <div className="agent-chips">{selected.routing_signals.map((signal) => <span key={signal}>{signal}</span>)}</div> : <p>No routing signals set.</p>}
                </section>
              </div>
            </div>

            <aside className="agent-dashboard-side" aria-label="Selected agent details">
              <div className="agent-side-heading"><Cpu size={17} /><h2>Configuration</h2></div>
              <dl>
                <div><dt>Model</dt><dd>{selectedModel}</dd></div>
                <div><dt>Provider health</dt><dd>{selectedStatus.label}</dd></div>
                <div><dt>Tools</dt><dd>{selected.tools?.length || 0} assigned</dd></div>
              </dl>
              {selectedHealth?.message && <p className="agent-health-message">{selectedHealth.message}</p>}
              {selected.personality && <div className="agent-personality"><h3>Personality</h3><p>{selected.personality}</p></div>}
              <button type="button" className="agent-side-link" onClick={() => navigate('/settings')}>Manage agents <ArrowUpRight size={15} /></button>
            </aside>
          </div>
        )}
      </div>
    </main>
  );
}
