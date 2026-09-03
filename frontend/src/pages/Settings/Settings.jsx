import React, { useState } from 'react';
import {
  Users,
  Cpu,
  Plus,
  Lock,
  Edit2,
  Trash2,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Activity,
  Sparkles,
  Radio,
  X,
  Check,
  Server,
} from 'lucide-react';
import { useAgents } from '../../context/AgentContext';
import './Settings.css';

const AVAILABLE_TOOLS = [
  { id: 'crm_read', name: 'CRM Read', tier: 'auto', desc: 'Query contacts and relationships' },
  { id: 'crm_write', name: 'CRM Write', tier: 'approval', desc: 'Create, update, or remove contacts' },
  { id: 'notes_reminders_read', name: 'Notes/Reminders Read', tier: 'auto', desc: 'Read personal notes and reminders' },
  { id: 'notes_reminders_create', name: 'Notes/Reminders Create', tier: 'approval', desc: 'Create new notes or scheduled reminders' },
  { id: 'notes_reminders_delete', name: 'Notes/Reminders Delete', tier: 'approval', desc: 'Delete notes or reminders' },
  { id: 'calendar_read', name: 'Calendar Read', tier: 'auto', desc: 'Read upcoming events and schedule' },
  { id: 'calendar_create', name: 'Calendar Create', tier: 'approval', desc: 'Book new appointments and calendar items' },
  { id: 'skill_manage_read', name: 'Skill Manage Read', tier: 'auto', desc: 'Inspect procedural memory skills' },
  { id: 'skill_manage_write', name: 'Skill Manage Write', tier: 'approval', desc: 'Teach new procedural memory skills' },
];

const PRESET_COLORS = ['#39ff14', '#00bfff', '#ff4500', '#a855f7', '#f59e0b', '#ec4899', '#06b6d4', '#10b981'];

const MODEL_PRESETS = [
  { id: 'local', label: 'Local (Ollama)', tag: '100% LOCAL', cost: 'Free' },
  { id: 'cloud_free', label: 'Cloud Free (NVIDIA NIM)', tag: 'FREE CLOUD', cost: 'Free' },
  { id: 'cloud_paid', label: 'Cloud Paid (OpenAI/Codex)', tag: 'PAID TIER', cost: 'Subscription' },
  { id: 'custom', label: 'Custom Endpoint', tag: 'CUSTOM', cost: 'Custom' },
];

export function Settings() {
  const {
    agents,
    llmSettings,
    isLoading,
    error,
    healthStatus,
    canCreateCustom,
    createAgent,
    updateAgent,
    deleteAgent,
    reloadFromDisk,
    updateLLMProvider,
    checkAgentHealth,
    testAllConnections,
  } = useAgents();

  const [activeTab, setActiveTab] = useState('party'); // 'party' | 'providers'
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // 'create' | 'edit'
  const [editingAgentId, setEditingAgentId] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [formError, setFormError] = useState(null);

  // Form State
  const [formData, setFormData] = useState({
    display_name: '',
    avatar: 'A',
    color: '#a855f7',
    role: '',
    description: '',
    personality: '',
    model_preset: 'cloud_free',
    tools: [],
    routing_signals: '',
  });

  const openCreateModal = () => {
    setModalMode('create');
    setEditingAgentId(null);
    setFormData({
      display_name: '',
      avatar: 'A',
      color: '#a855f7',
      role: 'Autonomous Assistant',
      description: 'Specialized agent assisting in workflow automation.',
      personality: '# Custom Agent\n\nYou are a helpful specialized assistant.',
      model_preset: 'cloud_free',
      tools: ['notes_reminders_read', 'notes_reminders_create'],
      routing_signals: 'assist, help, custom',
    });
    setFormError(null);
    setModalOpen(true);
  };

  const openEditModal = (agent) => {
    setModalMode('edit');
    setEditingAgentId(agent.id);
    setFormData({
      display_name: agent.display_name || '',
      avatar: agent.avatar || agent.display_name?.[0] || 'A',
      color: agent.color || '#38bdf8',
      role: agent.role || '',
      description: agent.description || '',
      personality: agent.personality || '',
      model_preset: agent.model_preset || 'cloud_free',
      tools: agent.tools || [],
      routing_signals: Array.isArray(agent.routing_signals) ? agent.routing_signals.join(', ') : '',
    });
    setFormError(null);
    setModalOpen(true);
  };

  const closeModal = () => {
    if (isSaving) return;
    setModalOpen(false);
  };

  const handleToolToggle = (toolId) => {
    setFormData((prev) => {
      const exists = prev.tools.includes(toolId);
      return {
        ...prev,
        tools: exists ? prev.tools.filter((t) => t !== toolId) : [...prev.tools, toolId],
      };
    });
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    if (!formData.display_name.trim()) {
      setFormError('Display name is required.');
      return;
    }

    const payload = {
      display_name: formData.display_name.trim(),
      avatar: (formData.avatar.trim() || formData.display_name[0] || 'A').slice(0, 1).toUpperCase(),
      color: formData.color,
      role: formData.role.trim(),
      description: formData.description.trim(),
      personality: formData.personality.trim(),
      model_preset: formData.model_preset,
      tools: formData.tools,
      routing_signals: formData.routing_signals
        .split(',')
        .map((s) => s.trim().toLowerCase())
        .filter(Boolean),
    };

    setIsSaving(true);
    setFormError(null);
    try {
      if (modalMode === 'create') {
        await createAgent(payload);
      } else {
        await updateAgent(editingAgentId, payload);
      }
      setModalOpen(false);
    } catch (err) {
      setFormError(err.message || 'Failed to save agent.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteAgent = async (agent) => {
    if (agent.is_prebuilt) {
      alert('Prebuilt agents cannot be deleted.');
      return;
    }
    if (window.confirm(`Are you sure you want to dismiss agent "${agent.display_name}"? Their .soul.md file will be removed.`)) {
      try {
        await deleteAgent(agent.id);
      } catch (err) {
        alert(err.message || 'Failed to delete agent.');
      }
    }
  };

  const handleProviderChange = async (agentId, preset) => {
    try {
      await updateLLMProvider(agentId, { preset });
    } catch (err) {
      alert(err.message || 'Failed to update LLM provider.');
    }
  };

  const totalSlots = 5;
  const emptySlotsCount = Math.max(0, totalSlots - agents.length);

  return (
    <div className="settings-page-container animate-fade-in">
      {/* ── Cockpit Header ── */}
      <header className="settings-header">
        <div className="settings-header-left">
          <div className="cockpit-icon-wrapper">
            <Radio size={20} className="cockpit-beacon-icon" />
          </div>
          <div>
            <h1 className="settings-title">Developer Cockpit &amp; Party Select</h1>
            <p className="settings-subtitle">
              Manage drop-in multi-agent souls (*.soul.md), assign LLM inference providers, and test live connectivity.
            </p>
          </div>
        </div>

        <div className="settings-header-actions">
          <button
            className="cockpit-btn secondary"
            onClick={reloadFromDisk}
            title="Scan memory-store/agents for new *.soul.md files"
            disabled={isLoading}
          >
            <RefreshCw size={13} className={isLoading ? 'spin-icon' : ''} />
            <span>Reload Souls</span>
          </button>

          <button
            className="cockpit-btn primary"
            onClick={openCreateModal}
            disabled={!canCreateCustom || isLoading}
            title={canCreateCustom ? 'Create a custom agent slot' : 'Maximum 2 custom agent slots reached'}
          >
            <Plus size={14} />
            <span>Create Agent</span>
          </button>
        </div>
      </header>

      {/* ── Navigation Tabs ── */}
      <div className="settings-tabs-bar">
        <button
          className={`settings-tab-btn ${activeTab === 'party' ? 'active' : ''}`}
          onClick={() => setActiveTab('party')}
        >
          <Users size={14} />
          <span>Agent Party</span>
          <span className="tab-count-pill">{agents.length} / 5</span>
        </button>

        <button
          className={`settings-tab-btn ${activeTab === 'providers' ? 'active' : ''}`}
          onClick={() => setActiveTab('providers')}
        >
          <Cpu size={14} />
          <span>LLM Providers</span>
        </button>
      </div>

      {error && (
        <div className="settings-banner error">
          <XCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* ── TAB 1: AGENT PARTY (RETRO PARTY SELECT CARDS) ── */}
      {activeTab === 'party' && (
        <div className="agent-party-view">
          <div className="party-cards-grid">
            {agents.map((agent) => {
              const color = agent.color || '#38bdf8';
              const isPrebuilt = agent.is_prebuilt;
              const presetInfo = MODEL_PRESETS.find((p) => p.id === agent.model_preset) || MODEL_PRESETS[1];
              const health = healthStatus[agent.id];

              return (
                <div key={agent.id} className={`party-agent-card ${isPrebuilt ? 'is-prebuilt' : 'is-custom'}`}>
                  {/* Card Header */}
                  <div className="card-top-bar">
                    <div className="agent-avatar-badge" style={{ backgroundColor: color, boxShadow: `0 0 14px ${color}55` }}>
                      <span>{agent.avatar || agent.display_name?.[0] || 'A'}</span>
                    </div>

                    <div className="card-tags-group">
                      {isPrebuilt ? (
                        <span className="party-badge prebuilt" title="Prebuilt System Agent">
                          <Lock size={10} />
                          <span>Prebuilt</span>
                        </span>
                      ) : (
                        <span className="party-badge custom" title="User-Defined Drop-in Soul">
                          <Sparkles size={10} />
                          <span>Custom</span>
                        </span>
                      )}

                      <span className={`party-badge preset ${agent.model_preset || 'cloud_free'}`}>
                        {presetInfo.tag}
                      </span>
                    </div>
                  </div>

                  {/* Identity Info */}
                  <div className="card-identity-block">
                    <h3 className="agent-card-name" style={{ color: color }}>
                      {agent.display_name}
                    </h3>
                    <p className="agent-card-role">{agent.role}</p>
                    <p className="agent-card-desc">{agent.description || 'No description provided.'}</p>
                  </div>

                  {/* Tools & Signals Chip Ledger */}
                  <div className="card-tools-summary">
                    <div className="summary-field">
                      <span className="field-label">Tools ({agent.tools?.length || 0})</span>
                      <div className="tools-chips-row">
                        {agent.tools && agent.tools.length > 0 ? (
                          agent.tools.slice(0, 3).map((t) => (
                            <span key={t} className="tool-chip">
                              {t}
                            </span>
                          ))
                        ) : (
                          <span className="empty-chip">No tools assigned</span>
                        )}
                        {agent.tools && agent.tools.length > 3 && (
                          <span className="tool-chip more">+{agent.tools.length - 3}</span>
                        )}
                      </div>
                    </div>

                    <div className="summary-field">
                      <span className="field-label">Routing Signals</span>
                      <div className="signals-chips-row">
                        {agent.routing_signals && agent.routing_signals.length > 0 ? (
                          agent.routing_signals.slice(0, 4).map((s) => (
                            <span key={s} className="signal-chip">
                              #{s}
                            </span>
                          ))
                        ) : (
                          <span className="empty-chip">None</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Health Check Status Pill */}
                  {health && (
                    <div className={`agent-health-pill ${health.status}`}>
                      {health.status === 'checking' ? (
                        <RefreshCw size={11} className="spin-icon" />
                      ) : health.status === 'online' ? (
                        <CheckCircle2 size={11} />
                      ) : (
                        <XCircle size={11} />
                      )}
                      <span>{health.message}</span>
                    </div>
                  )}

                  {/* Card Action Controls */}
                  <div className="card-actions-footer">
                    <button
                      className="card-action-btn ping"
                      onClick={() => checkAgentHealth(agent.id)}
                      title="Ping LLM connection"
                    >
                      <Activity size={12} />
                      <span>Ping</span>
                    </button>

                    <button
                      className="card-action-btn edit"
                      onClick={() => openEditModal(agent)}
                      title="Edit Agent Persona & frontmatter"
                    >
                      <Edit2 size={12} />
                      <span>Edit</span>
                    </button>

                    {!isPrebuilt && (
                      <button
                        className="card-action-btn delete"
                        onClick={() => handleDeleteAgent(agent)}
                        title="Delete custom agent"
                      >
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Empty Slots for Custom Agents */}
            {Array.from({ length: emptySlotsCount }).map((_, idx) => (
              <div
                key={`empty-${idx}`}
                className="party-empty-slot-card"
                onClick={openCreateModal}
                role="button"
                tabIndex={0}
              >
                <div className="empty-slot-plus">
                  <Plus size={24} />
                </div>
                <h4 className="empty-slot-title">Empty Agent Slot</h4>
                <p className="empty-slot-sub">
                  Drop a <code>*.soul.md</code> into <code>memory-store/agents/</code> or click here to build one.
                </p>
                <span className="empty-slot-cta">Deploy Custom Soul +</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── TAB 2: LLM PROVIDERS ── */}
      {activeTab === 'providers' && (
        <div className="llm-providers-view">
          <div className="providers-view-toolbar">
            <div className="toolbar-info">
              <h2 className="view-section-title">Per-Agent Provider Allocation</h2>
              <p className="view-section-desc">
                Any agent can run on any provider. Select between local Ollama (100% free), free cloud endpoints, or your own OpenAI keys.
              </p>
            </div>
            <button className="cockpit-btn primary" onClick={testAllConnections} disabled={isLoading}>
              <Activity size={13} />
              <span>Test All Connections</span>
            </button>
          </div>

          {/* Allocation Matrix */}
          <div className="provider-allocation-matrix">
            <table className="matrix-table">
              <thead>
                <tr>
                  <th>Agent</th>
                  <th>Role</th>
                  <th>Assigned Provider</th>
                  <th>Resolved Model</th>
                  <th>Target Endpoint</th>
                  <th>Health Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {agents.map((agent) => {
                  const resolved = llmSettings.agents?.[agent.id] || {};
                  const currentPreset = resolved.preset || agent.model_preset || 'cloud_free';
                  const health = healthStatus[agent.id];

                  return (
                    <tr key={agent.id}>
                      <td className="agent-identity-cell">
                        <div
                          className="matrix-avatar"
                          style={{ backgroundColor: agent.color || '#38bdf8' }}
                        >
                          {agent.avatar || agent.display_name[0]}
                        </div>
                        <div>
                          <div className="matrix-name">{agent.display_name}</div>
                          <div className="matrix-id">id: {agent.id}</div>
                        </div>
                      </td>

                      <td className="matrix-role">{agent.role}</td>

                      <td>
                        <select
                          className="provider-select-dropdown"
                          value={currentPreset}
                          onChange={(e) => handleProviderChange(agent.id, e.target.value)}
                        >
                          {MODEL_PRESETS.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.label}
                            </option>
                          ))}
                        </select>
                      </td>

                      <td className="matrix-model">
                        <code>{resolved.model || 'default'}</code>
                      </td>

                      <td className="matrix-url">
                        <span className="url-text" title={resolved.base_url}>
                          {resolved.base_url || 'https://integrate.api.nvidia.com/v1'}
                        </span>
                      </td>

                      <td>
                        {health ? (
                          <span className={`status-pill ${health.status}`}>
                            {health.status === 'checking' ? (
                              <RefreshCw size={11} className="spin-icon" />
                            ) : health.status === 'online' ? (
                              <CheckCircle2 size={11} />
                            ) : (
                              <XCircle size={11} />
                            )}
                            <span>{health.status.toUpperCase()}</span>
                          </span>
                        ) : (
                          <span className="status-pill idle">STANDBY</span>
                        )}
                      </td>

                      <td>
                        <button
                          className="matrix-test-btn"
                          onClick={() => checkAgentHealth(agent.id)}
                          title="Ping connection"
                        >
                          Ping
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Provider Presets Catalog */}
          <div className="provider-presets-catalog">
            <h3 className="presets-title">Configured Infrastructure Endpoints</h3>
            <div className="presets-cards-grid">
              {Object.entries(llmSettings.providers || {}).map(([key, prov]) => (
                <div key={key} className="preset-info-card">
                  <div className="preset-card-header">
                    <Server size={14} className="preset-icon" />
                    <span className="preset-name">{key.toUpperCase()}</span>
                    <span className="preset-cost-tag">
                      {key === 'local' ? 'FREE LOCAL' : key === 'cloud_free' ? 'FREE CLOUD' : 'CONFIGURED'}
                    </span>
                  </div>
                  <div className="preset-detail-row">
                    <span className="detail-label">Base URL:</span>
                    <code className="detail-val">{prov.base_url}</code>
                  </div>
                  <div className="preset-detail-row">
                    <span className="detail-label">Default Model:</span>
                    <code className="detail-val">{prov.default_model}</code>
                  </div>
                  <div className="preset-detail-row">
                    <span className="detail-label">Auth Key:</span>
                    <span className="detail-val auth-status">
                      {prov.api_key_env ? `Env (${prov.api_key_env})` : prov.api_key ? 'Direct Key' : 'No Auth Required'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── CREATE / EDIT AGENT MODAL ── */}
      {modalOpen && (
        <div className="modal-backdrop-overlay" onClick={closeModal}>
          <div className="agent-editor-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-group">
                <Sparkles size={16} className="modal-sparkle-icon" />
                <h2>{modalMode === 'create' ? 'Create Drop-in Agent Soul' : `Edit Agent: ${formData.display_name}`}</h2>
              </div>
              <button className="modal-close-btn" onClick={closeModal} disabled={isSaving}>
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleFormSubmit} className="modal-form-content">
              {formError && (
                <div className="modal-error-banner">
                  <XCircle size={14} />
                  <span>{formError}</span>
                </div>
              )}

              {/* Identity Row */}
              <div className="form-grid-row">
                <div className="form-group flex-2">
                  <label>Display Name *</label>
                  <input
                    type="text"
                    value={formData.display_name}
                    onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                    placeholder="e.g. Proteus"
                    required
                  />
                </div>

                <div className="form-group flex-1">
                  <label>Avatar Letter</label>
                  <input
                    type="text"
                    maxLength={1}
                    value={formData.avatar}
                    onChange={(e) => setFormData({ ...formData, avatar: e.target.value.toUpperCase() })}
                    placeholder="P"
                  />
                </div>

                <div className="form-group flex-1">
                  <label>Accent Color</label>
                  <div className="color-picker-row">
                    <input
                      type="color"
                      value={formData.color}
                      onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                    />
                    <div className="preset-colors-row">
                      {PRESET_COLORS.map((c) => (
                        <button
                          type="button"
                          key={c}
                          className="color-swatch-dot"
                          style={{ backgroundColor: c }}
                          onClick={() => setFormData({ ...formData, color: c })}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Role & Description */}
              <div className="form-grid-row">
                <div className="form-group flex-1">
                  <label>Role</label>
                  <input
                    type="text"
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    placeholder="e.g. Deep Security Auditor"
                  />
                </div>

                <div className="form-group flex-1">
                  <label>Model Preset</label>
                  <select
                    value={formData.model_preset}
                    onChange={(e) => setFormData({ ...formData, model_preset: e.target.value })}
                  >
                    {MODEL_PRESETS.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.label} ({p.cost})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>Description</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="One sentence summary of what this agent does."
                />
              </div>

              {/* Routing Signals */}
              <div className="form-group">
                <label>Routing Signals (Comma-separated keywords)</label>
                <input
                  type="text"
                  value={formData.routing_signals}
                  onChange={(e) => setFormData({ ...formData, routing_signals: e.target.value })}
                  placeholder="e.g. audit, inspect, review, vuln"
                />
                <span className="field-hint">
                  When a user message matches these keywords, Poseidon routes to this agent.
                </span>
              </div>

              {/* Tool Selection */}
              <div className="form-group">
                <label>Allowed Tools</label>
                <div className="tools-checkbox-grid">
                  {AVAILABLE_TOOLS.map((tool) => {
                    const isChecked = formData.tools.includes(tool.id);
                    return (
                      <label key={tool.id} className={`tool-checkbox-item ${isChecked ? 'checked' : ''}`}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => handleToolToggle(tool.id)}
                        />
                        <div className="tool-info">
                          <span className="tool-name">{tool.name}</span>
                          <span className={`tool-tier-tag ${tool.tier}`}>
                            {tool.tier === 'approval' ? 'GATE' : 'AUTO'}
                          </span>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Markdown Personality Prompt */}
              <div className="form-group">
                <label>Persona &amp; System Prompt (Markdown Body)</label>
                <textarea
                  rows={8}
                  value={formData.personality}
                  onChange={(e) => setFormData({ ...formData, personality: e.target.value })}
                  placeholder="# Agent Name\n\nYou are a specialized assistant..."
                />
              </div>

              {/* Modal Actions */}
              <div className="modal-actions-footer">
                <button type="button" className="cockpit-btn secondary" onClick={closeModal} disabled={isSaving}>
                  Cancel
                </button>
                <button type="submit" className="cockpit-btn primary" disabled={isSaving}>
                  {isSaving ? (
                    <>
                      <RefreshCw size={13} className="spin-icon" />
                      <span>Saving Soul...</span>
                    </>
                  ) : (
                    <>
                      <Check size={13} />
                      <span>{modalMode === 'create' ? 'Create Soul File' : 'Save Changes'}</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Settings;
