import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Brain,
  Shield,
  Server,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Search,
  Zap,
  Sliders,
  Database,
  Lock,
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import { useAgents } from '../../context/AgentContext';
import { useHealth } from '../../context/HealthContext';
import { 
  fetchSemanticMemory, 
  fetchProceduralMemory, 
  fetchMemoryStatus, 
  triggerConsolidation 
} from '../../api/memory';
import './Settings.css';

const AVAILABLE_TOOLS = [
  { id: 'crm_read', name: 'CRM Read', tier: 'auto', desc: 'Query contacts and relationships' },
  { id: 'crm_write', name: 'CRM Write', tier: 'approval', desc: 'Create, update, or remove contacts' },
  { id: 'notes_reminders_read', name: 'Notes/Reminders Read', tier: 'auto', desc: 'Read personal notes and reminders' },
  { id: 'notes_reminders_create', name: 'Notes/Reminders Create', tier: 'approval', desc: 'Create new notes or scheduled reminders' },
  { id: 'notes_reminders_delete', name: 'Notes/Reminders Delete', tier: 'approval', desc: 'Delete notes or reminders' },
  { id: 'calendar_read', name: 'Calendar Read', tier: 'auto', desc: 'Read upcoming events and schedule' },
  { id: 'calendar_create', name: 'Calendar Create', tier: 'approval', desc: 'Book appointments and calendar items' },
  { id: 'skill_manage_read', name: 'Skill Manage Read', tier: 'auto', desc: 'Inspect procedural memory skills' },
  { id: 'skill_manage_write', name: 'Skill Manage Write', tier: 'approval', desc: 'Create procedural memory skills' },
];

const MODEL_PRESETS = [
  { id: 'local', label: 'Local (Ollama)', tag: '100% LOCAL', desc: 'Runs locally on Ollama. Complete data privacy.', cost: 'Free' },
  { id: 'cloud_free', label: 'Cloud Free (Nvidia/OpenRouter)', tag: 'FREE CLOUD', desc: 'Zero-cost cloud inference via free tier APIs.', cost: 'Free' },
  { id: 'cloud_paid', label: 'Cloud Paid (OpenAI)', tag: 'PAID TIER', desc: 'Commercial high-throughput models (GPT-4o, Claude).', cost: 'Usage' },
  { id: 'custom', label: 'Custom Endpoint', tag: 'CUSTOM', desc: 'Any OpenAI-compatible base URL & endpoint.', cost: 'Variable' },
];

export function Settings() {
  const { llmSettings, updateLLMProvider, checkAgentHealth, healthStatus } = useAgents();
  const { modelName, isConnected, refreshHealth } = useHealth();
  const [activeTab, setActiveTab] = useState('models'); // 'models' | 'memory' | 'security'

  // Model Settings Form State
  const poseidonConfig = llmSettings?.agent_overrides?.poseidon || { preset: 'cloud_free' };
  const [selectedPreset, setSelectedPreset] = useState(poseidonConfig.preset || 'cloud_free');
  const [ollamaUrl, setOllamaUrl] = useState(llmSettings?.providers?.local?.base_url || 'http://localhost:11434/v1');
  const [localModel, setLocalModel] = useState(llmSettings?.providers?.local?.default_model || 'llama3.2');
  const [isSavingLLM, setIsSavingLLM] = useState(false);
  const [isTestingLLM, setIsTestingLLM] = useState(false);
  const [llmSaveMsg, setLlmSaveMsg] = useState(null);

  // Sync state when llmSettings loads
  useEffect(() => {
    if (llmSettings?.agent_overrides?.poseidon?.preset) {
      setSelectedPreset(llmSettings.agent_overrides.poseidon.preset);
    }
  }, [llmSettings]);

  // Memory Studio State
  const [semanticFacts, setSemanticFacts] = useState([]);
  const [proceduralSkills, setProceduralSkills] = useState([]);
  const [memoryStats, setMemoryStats] = useState(null);
  const [factQuery, setFactQuery] = useState('');
  const [isConsolidating, setIsConsolidating] = useState(false);
  const [consolidationResult, setConsolidationResult] = useState(null);

  // Load Memory Studio Data
  useEffect(() => {
    if (activeTab === 'memory') {
      loadMemoryData();
    }
  }, [activeTab]);

  const loadMemoryData = async () => {
    try {
      const [semRes, procRes, statRes] = await Promise.all([
        fetchSemanticMemory('local_user', factQuery || null),
        fetchProceduralMemory(),
        fetchMemoryStatus('local_user'),
      ]);
      setSemanticFacts(semRes?.facts || []);
      setProceduralSkills(procRes?.skills || []);
      setMemoryStats(statRes);
    } catch (e) {
      console.error('Failed to load memory studio data:', e);
    }
  };

  const handleSaveLLM = async () => {
    setIsSavingLLM(true);
    setLlmSaveMsg(null);
    try {
      const payload = { preset: selectedPreset };
      if (selectedPreset === 'local') {
        payload.model = localModel || 'llama3.2';
        payload.base_url = ollamaUrl || 'http://localhost:11434/v1';
      } else if (selectedPreset === 'cloud_free') {
        payload.model = llmSettings?.providers?.cloud_free?.default_model || 'nvidia/nemotron-3-ultra-550b-a55b';
      } else if (selectedPreset === 'cloud_paid') {
        payload.model = llmSettings?.providers?.cloud_paid?.default_model || 'gpt-5.4-medium';
      }
      await updateLLMProvider('poseidon', payload);
      setLlmSaveMsg({ type: 'success', text: `Inference preset updated to '${selectedPreset}' and saved.` });
      refreshHealth();
    } catch (err) {
      setLlmSaveMsg({ type: 'error', text: err.message || 'Failed to update settings.' });
    } finally {
      setIsSavingLLM(false);
    }
  };

  const handleTestLLM = async () => {
    setIsTestingLLM(true);
    setLlmSaveMsg(null);
    try {
      const res = await checkAgentHealth('poseidon');
      if (res.available) {
        setLlmSaveMsg({ type: 'success', text: `Connection successful: ${res.message || 'Endpoint reachable'}` });
      } else {
        setLlmSaveMsg({ type: 'error', text: `Connection failed: ${res.message || 'Endpoint unreachable'}` });
      }
    } catch (err) {
      setLlmSaveMsg({ type: 'error', text: err.message || 'Connectivity check failed.' });
    } finally {
      setIsTestingLLM(false);
    }
  };

  const handleTriggerConsolidation = async () => {
    setIsConsolidating(true);
    setConsolidationResult(null);
    try {
      const res = await triggerConsolidation('local_user', true);
      setConsolidationResult(res);
      loadMemoryData();
    } catch (err) {
      setConsolidationResult({ status: 'failed', error: err.message });
    } finally {
      setIsConsolidating(false);
    }
  };

  return (
    <div className="settings-page-root animate-fade-in">
      {/* Settings Header */}
      <div className="settings-page-header">
        <div>
          <h1 className="settings-title">Developer Console Settings</h1>
          <p className="settings-subtitle">Manage runtime endpoints, 4-tier cognitive memory, and execution boundaries.</p>
        </div>
      </div>

      {/* Tabs Bar */}
      <div className="settings-tabs-row">
        <button
          type="button"
          className={`settings-tab-btn ${activeTab === 'models' ? 'active' : ''}`}
          onClick={() => setActiveTab('models')}
        >
          <Cpu size={14} />
          <span>Models &amp; Endpoints</span>
        </button>

        <button
          type="button"
          className={`settings-tab-btn ${activeTab === 'memory' ? 'active' : ''}`}
          onClick={() => setActiveTab('memory')}
        >
          <Brain size={14} />
          <span>Memory Studio</span>
        </button>

        <button
          type="button"
          className={`settings-tab-btn ${activeTab === 'security' ? 'active' : ''}`}
          onClick={() => setActiveTab('security')}
        >
          <Shield size={14} />
          <span>Harness &amp; Security</span>
        </button>
      </div>

      {/* Tab 1: Models & Endpoints (Pure .env Authority) */}
      {activeTab === 'models' && (
        <div className="settings-tab-content animate-fade-in">
          <div className="settings-card">
            <div className="card-header-between">
              <div>
                <h3 className="card-heading">Active Environment Configuration</h3>
                <p className="card-desc">
                  Inference endpoints, credentials, and models are configured exclusively via your <code>.env</code> file.
                </p>
              </div>
              <span className="env-authority-badge" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 12px', borderRadius: 'var(--radius-full)', background: 'rgba(255, 255, 255, 0.08)', border: '1px solid rgba(255, 255, 255, 0.16)', color: '#FFFFFF', fontSize: '0.72rem', fontWeight: 600, fontFamily: 'var(--font-dot)' }}>
                <Zap size={12} style={{ color: 'var(--accent-red, #D71921)' }} />
                <span>Single Source: .env</span>
              </span>
            </div>

            <div className="provider-form-block" style={{ marginTop: '16px' }}>
              <div className="form-group">
                <label>Active Model (POSEIDON_MODEL)</label>
                <input
                  type="text"
                  readOnly
                  value={modelName || 'openai/gpt-oss-120b'}
                  className="settings-text-input font-mono"
                  style={{ opacity: 0.9 }}
                />
                <span className="form-hint">Loaded directly from POSEIDON_MODEL in your project .env.</span>
              </div>

              <div className="form-group">
                <label>Inference Base URL (POSEIDON_BASE_URL)</label>
                <input
                  type="text"
                  readOnly
                  value={llmSettings?.providers?.env?.base_url || 'https://api.groq.com/openai/v1'}
                  className="settings-text-input font-mono"
                  style={{ opacity: 0.9 }}
                />
                <span className="form-hint">Loaded from POSEIDON_BASE_URL in .env. Compatible with Groq, Ollama, OpenRouter, and OpenAI.</span>
              </div>

              <div className="form-group">
                <label>API Key Status</label>
                <input
                  type="text"
                  readOnly
                  value="Configured in .env (OPENROUTER_API_KEY / GROQ_API_KEY)"
                  className="settings-text-input font-mono"
                  style={{ opacity: 0.9 }}
                />
              </div>
            </div>

            {/* How to Switch Providers Card */}
            <div className="env-quick-switch-guide" style={{ margin: '16px 0', padding: '18px', background: '#18181A', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '16px', fontSize: '0.78rem' }}>
              <div style={{ fontWeight: 600, color: '#FFFFFF', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sliders size={13} style={{ color: 'var(--accent-red, #D71921)' }} />
                <span style={{ letterSpacing: '0.04em', textTransform: 'uppercase', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>How to switch providers in .env:</span>
              </div>
              <ul style={{ margin: 0, paddingLeft: '18px', color: '#D1D1D6', lineHeight: 1.7 }}>
                <li style={{ marginBottom: '6px' }}><strong style={{ color: '#FFFFFF' }}>Groq:</strong> Set <code>POSEIDON_BASE_URL=https://api.groq.com/openai/v1</code>, <code>OPENROUTER_API_KEY=gsk_...</code>, and model like <code>llama-3.3-70b-versatile</code></li>
                <li style={{ marginBottom: '6px' }}><strong style={{ color: '#FFFFFF' }}>Local Ollama:</strong> Set <code>POSEIDON_BASE_URL=http://localhost:11434/v1</code> and <code>POSEIDON_MODEL=llama3.2</code></li>
                <li><strong style={{ color: '#FFFFFF' }}>OpenRouter:</strong> Set <code>POSEIDON_BASE_URL=https://openrouter.ai/api/v1</code>, <code>OPENROUTER_API_KEY=sk-or-v1-...</code>, and any model ID</li>
              </ul>
            </div>

            {llmSaveMsg && (
              <div className={`settings-alert-msg ${llmSaveMsg.type}`}>
                {llmSaveMsg.text}
              </div>
            )}

            <div className="card-actions-row">
              <button
                type="button"
                className="btn-primary"
                onClick={handleTestLLM}
                disabled={isTestingLLM}
              >
                <RefreshCw size={13} className={isTestingLLM ? 'animate-spin' : ''} />
                <span>{isTestingLLM ? 'Testing Endpoint...' : 'Test .env Connectivity'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Memory Studio */}
      {activeTab === 'memory' && (
        <div className="settings-tab-content animate-fade-in">
          {/* Memory Metrics Overview */}
          <div className="memory-metrics-grid">
            <div className="metric-box">
              <span className="metric-label">Semantic Facts</span>
              <span className="metric-val">{memoryStats?.semantic_facts_count ?? '—'}</span>
              <span className="metric-sub">Indexed in SQLite FTS5</span>
            </div>
            <div className="metric-box">
              <span className="metric-label">Procedural Skills</span>
              <span className="metric-val">{memoryStats?.procedural_skills_count ?? '—'}</span>
              <span className="metric-sub">Flat *.SKILL.md playbooks</span>
            </div>
            <div className="metric-box">
              <span className="metric-label">Unconsolidated Turns</span>
              <span className="metric-val">
                {memoryStats?.consolidation?.unconsolidated_events ?? 0}
              </span>
              <div className="segmented-progress-bar" style={{ margin: '6px 0', height: '4px', display: 'flex', gap: '2px' }}>
                {Array.from({ length: 8 }).map((_, idx) => {
                  const unconsolidated = memoryStats?.consolidation?.unconsolidated_events ?? 0;
                  const threshold = memoryStats?.consolidation?.threshold ?? 30;
                  const filledCount = Math.min(8, Math.round((unconsolidated / threshold) * 8));
                  const isFilled = idx < filledCount;
                  return (
                    <div 
                      key={idx} 
                      className={`segmented-block ${isFilled ? 'is-filled' : ''}`}
                      style={{
                        flex: 1,
                        height: '100%',
                        borderRadius: '1px',
                        background: isFilled ? 'var(--accent)' : 'var(--border-visible)',
                        transition: 'background-color 0.2s ease'
                      }}
                    />
                  );
                })}
              </div>
              <span className="metric-sub">
                Threshold: {memoryStats?.consolidation?.threshold ?? 30} turns
              </span>
            </div>
          </div>

          {/* Consolidation Action Card */}
          <div className="settings-card">
            <div className="card-header-between">
              <div>
                <h3 className="card-heading">Cognitive Consolidation</h3>
                <p className="card-desc">
                  The Summarizer Agent distills durable facts from raw episodic logs into MEMORY.md.
                </p>
              </div>
              <button
                type="button"
                className="btn-secondary"
                onClick={handleTriggerConsolidation}
                disabled={isConsolidating}
              >
                <RefreshCw size={13} className={isConsolidating ? 'animate-spin' : ''} />
                <span>{isConsolidating ? 'Consolidating...' : 'Consolidate Now'}</span>
              </button>
            </div>

            {consolidationResult && (
              <div className="consolidation-result-box">
                <span className="result-status">Status: {consolidationResult.status}</span>
                {consolidationResult.extracted_facts?.length > 0 && (
                  <p>Extracted {consolidationResult.extracted_facts.length} new semantic facts.</p>
                )}
              </div>
            )}
          </div>

          {/* Semantic Facts Table */}
          <div className="settings-card">
            <div className="card-header-between">
              <h3 className="card-heading">Semantic Facts (MEMORY.md)</h3>
              <div className="search-wrap">
                <Search size={13} className="search-icon" />
                <input
                  type="text"
                  value={factQuery}
                  onChange={(e) => setFactQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && loadMemoryData()}
                  placeholder="Filter facts..."
                  className="search-input"
                />
              </div>
            </div>

            <div className="facts-table-wrap">
              {semanticFacts.length > 0 ? (
                <table className="facts-table">
                  <thead>
                    <tr>
                      <th>Fact Content</th>
                      <th>Category</th>
                    </tr>
                  </thead>
                  <tbody>
                    {semanticFacts.map((f, idx) => (
                      <tr key={idx}>
                        <td className="fact-text-cell">{typeof f === 'string' ? f : f.fact}</td>
                        <td className="fact-cat-cell">{typeof f === 'string' ? 'general' : f.category || 'general'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="empty-table-state">No semantic facts found.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Harness & Security */}
      {activeTab === 'security' && (
        <div className="settings-tab-content animate-fade-in">
          <div className="settings-card">
            <h3 className="card-heading">Tool Execution Permissions</h3>
            <p className="card-desc">
              All tools execute within the in-process SandboxGuard boundary. Write tools require human approval.
            </p>

            <table className="tools-perm-table">
              <thead>
                <tr>
                  <th>Tool Identifier</th>
                  <th>Description</th>
                  <th>Permission Tier</th>
                  <th>Guardrail</th>
                </tr>
              </thead>
              <tbody>
                {AVAILABLE_TOOLS.map((t) => (
                  <tr key={t.id}>
                    <td className="tool-id-cell font-mono">{t.id}</td>
                    <td className="tool-desc-cell">{t.desc}</td>
                    <td>
                      <span className={`tier-badge ${t.tier}`}>
                        {t.tier === 'auto' ? 'Auto-Run (Read)' : 'Approval Required (Write)'}
                      </span>
                    </td>
                    <td className="tool-guard-cell font-mono">SandboxGuard</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="security-info-grid">
            <div className="sec-info-box">
              <Lock size={16} className="text-emerald" />
              <div>
                <h4>DLP Output Redactor</h4>
                <p>Scans outbound responses for API keys, bearer tokens, and credentials before replying.</p>
              </div>
            </div>
            <div className="sec-info-box">
              <Shield size={16} className="text-amber" />
              <div>
                <h4>In-Process Sandbox</h4>
                <p>Strict path jailing to workspace roots, 30s timeout enforcement, zero shell execution.</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Settings;
