import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Cpu,
  Brain,
  Shield,
  RefreshCw,
  Search,
  Zap,
  Sliders,
  Lock,
  Server,
  KeyRound,
  Activity,
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
  { id: 'notes_reminders_create', name: 'Notes/Reminders Create', tier: 'guarded', desc: 'Create new notes or scheduled reminders' },
  { id: 'notes_reminders_delete', name: 'Notes/Reminders Delete', tier: 'approval', desc: 'Delete notes or reminders' },
  { id: 'skill_manage_read', name: 'Skill Manage Read', tier: 'auto', desc: 'Inspect procedural memory skills' },
  { id: 'skill_manage_write', name: 'Skill Manage Write', tier: 'approval', desc: 'Create procedural memory skills' },
];

export function Settings() {
  const [searchParams] = useSearchParams();
  const { llmSettings, checkAgentHealth } = useAgents();
  const { modelName, isConnected, lastChecked } = useHealth();
  const requestedTab = searchParams.get('tab');
  const initialTab = ['models', 'memory', 'security'].includes(requestedTab) ? requestedTab : 'models';
  const [activeTab, setActiveTab] = useState(initialTab); // 'models' | 'memory' | 'security'

  const [isTestingLLM, setIsTestingLLM] = useState(false);
  const [llmSaveMsg, setLlmSaveMsg] = useState(null);

  const activeBaseUrl = llmSettings?.providers?.env?.base_url || 'https://api.groq.com/openai/v1';
  const activeProvider = activeBaseUrl.includes('groq.com')
    ? 'Groq'
    : activeBaseUrl.includes('openrouter.ai')
      ? 'OpenRouter'
      : activeBaseUrl.includes('localhost') || activeBaseUrl.includes('127.0.0.1')
        ? 'Local / Ollama'
        : activeBaseUrl.includes('openai.com')
          ? 'OpenAI'
          : 'Custom endpoint';
  const hasApiKey = Boolean(llmSettings?.agents?.poseidon?.has_api_key);

  // Memory Studio State
  const [semanticFacts, setSemanticFacts] = useState([]);
  const [proceduralSkills, setProceduralSkills] = useState([]);
  const [memoryStats, setMemoryStats] = useState(null);
  const [factQuery, setFactQuery] = useState('');
  const [isConsolidating, setIsConsolidating] = useState(false);
  const [consolidationResult, setConsolidationResult] = useState(null);

  const loadMemoryData = useCallback(async (query = null) => {
    try {
      const [semRes, procRes, statRes] = await Promise.all([
        fetchSemanticMemory('local_user', query || null),
        fetchProceduralMemory(),
        fetchMemoryStatus('local_user'),
      ]);
      setSemanticFacts(semRes?.facts || []);
      setProceduralSkills(procRes?.skills || []);
      setMemoryStats(statRes);
    } catch (e) {
      console.error('Failed to load memory studio data:', e);
    }
  }, []);

  // Load Memory Studio Data
  useEffect(() => {
    if (activeTab === 'memory') {
      loadMemoryData();
    }
  }, [activeTab, loadMemoryData]);

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
          <h1 className="settings-title">Runtime settings</h1>
          <p className="settings-subtitle">Inspect the local model connection, memory system, and execution policy.</p>
        </div>
      </div>

      {/* Tabs Bar */}
      <div className="settings-tabs-row" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'models'}
          className={`settings-tab-btn ${activeTab === 'models' ? 'active' : ''}`}
          onClick={() => setActiveTab('models')}
        >
          <Cpu size={14} />
          <span>Models &amp; Endpoints</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'memory'}
          className={`settings-tab-btn ${activeTab === 'memory' ? 'active' : ''}`}
          onClick={() => setActiveTab('memory')}
        >
          <Brain size={14} />
          <span>Memory Studio</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'security'}
          className={`settings-tab-btn ${activeTab === 'security' ? 'active' : ''}`}
          onClick={() => setActiveTab('security')}
        >
          <Shield size={14} />
          <span>Harness &amp; Security</span>
        </button>
      </div>

      {/* Tab 1: Models & Endpoints (Pure .env Authority) */}
      {activeTab === 'models' && (
        <div className="settings-tab-content animate-fade-in" role="tabpanel">
          <section className="runtime-summary-grid" aria-label="Active runtime summary">
            <article className="runtime-summary-item">
              <span className="runtime-summary-icon"><Cpu size={16} /></span>
              <div>
                <span className="runtime-summary-label">Active model</span>
                <strong>{modelName || 'Loading model...'}</strong>
                <small>POSEIDON_MODEL</small>
              </div>
            </article>
            <article className="runtime-summary-item">
              <span className="runtime-summary-icon"><Server size={16} /></span>
              <div>
                <span className="runtime-summary-label">Provider</span>
                <strong>{activeProvider}</strong>
                <small>OpenAI-compatible API</small>
              </div>
            </article>
            <article className="runtime-summary-item">
              <span className={`runtime-summary-icon ${isConnected ? 'is-online' : 'is-offline'}`}>
                <Activity size={16} />
              </span>
              <div>
                <span className="runtime-summary-label">Backend</span>
                <strong>{isConnected ? 'Online' : 'Unavailable'}</strong>
                <small>{lastChecked ? `Checked ${lastChecked.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'Checking connection...'}</small>
              </div>
            </article>
          </section>

          <div className="settings-card">
            <div className="card-header-between">
              <div>
                <h3 className="card-heading">Environment configuration</h3>
                <p className="card-desc">
                  Read-only values currently loaded by the backend. Restart Poseidon after changing <code>.env</code>.
                </p>
              </div>
              <div className="environment-header-actions">
                <span className="env-authority-badge">
                  <Zap size={12} className="env-authority-icon" />
                  <span>Source: .env</span>
                </span>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleTestLLM}
                  disabled={isTestingLLM}
                >
                  <RefreshCw size={13} className={isTestingLLM ? 'animate-spin' : ''} />
                  <span>{isTestingLLM ? 'Testing...' : 'Test connection'}</span>
                </button>
              </div>
            </div>

            <div className="environment-values" role="list">
              <div className="environment-value-row" role="listitem">
                <span className="environment-value-icon"><Cpu size={15} /></span>
                <div className="environment-value-copy">
                  <span className="environment-value-label">POSEIDON_MODEL</span>
                  <code>{modelName || 'openai/gpt-oss-120b'}</code>
                </div>
                <span className="environment-value-state">Loaded</span>
              </div>
              <div className="environment-value-row" role="listitem">
                <span className="environment-value-icon"><Server size={15} /></span>
                <div className="environment-value-copy">
                  <span className="environment-value-label">POSEIDON_BASE_URL</span>
                  <code>{activeBaseUrl}</code>
                </div>
                <span className="environment-value-state">{activeProvider}</span>
              </div>
              <div className="environment-value-row" role="listitem">
                <span className="environment-value-icon"><KeyRound size={15} /></span>
                <div className="environment-value-copy">
                  <span className="environment-value-label">Provider credential</span>
                  <code>{hasApiKey ? 'Configured and hidden' : 'Not configured'}</code>
                </div>
                <span className={`environment-value-state ${hasApiKey ? '' : 'is-warning'}`}>
                  {hasApiKey ? 'Available' : 'Missing'}
                </span>
              </div>
            </div>

            <div className="env-quick-switch-guide">
              <div className="env-quick-switch-title">
                <Sliders size={13} className="env-quick-switch-icon" />
                <span>Provider recipes</span>
              </div>
              <div className="provider-recipe-grid">
                <article className={`provider-recipe ${activeProvider === 'Groq' ? 'is-active' : ''}`}>
                  <div><strong>Groq</strong>{activeProvider === 'Groq' && <span>Active</span>}</div>
                  <code>https://api.groq.com/openai/v1</code>
                  <p>Hosted, low-latency inference.</p>
                </article>
                <article className={`provider-recipe ${activeProvider === 'Local / Ollama' ? 'is-active' : ''}`}>
                  <div><strong>Local Ollama</strong>{activeProvider === 'Local / Ollama' && <span>Active</span>}</div>
                  <code>http://localhost:11434/v1</code>
                  <p>Private inference on this machine.</p>
                </article>
                <article className={`provider-recipe ${activeProvider === 'OpenRouter' ? 'is-active' : ''}`}>
                  <div><strong>OpenRouter</strong>{activeProvider === 'OpenRouter' && <span>Active</span>}</div>
                  <code>https://openrouter.ai/api/v1</code>
                  <p>One endpoint for multiple model providers.</p>
                </article>
              </div>
            </div>

            {llmSaveMsg && (
              <div className={`settings-alert-msg ${llmSaveMsg.type}`}>
                {llmSaveMsg.text}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Memory Studio */}
      {activeTab === 'memory' && (
        <div className="settings-tab-content animate-fade-in" role="tabpanel">
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
                {memoryStats?.consolidation?.unconsolidated_count ?? 0}
              </span>
              <div className="segmented-progress-bar">
                {Array.from({ length: 8 }).map((_, idx) => {
                  const unconsolidated = memoryStats?.consolidation?.unconsolidated_count ?? 0;
                  const threshold = memoryStats?.consolidation?.threshold ?? 30;
                  const filledCount = Math.min(8, Math.round((unconsolidated / threshold) * 8));
                  const isFilled = idx < filledCount;
                  return (
                    <div 
                      key={idx} 
                      className={`segmented-block ${isFilled ? 'is-filled' : ''}`}
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
                className="btn-primary"
                onClick={handleTriggerConsolidation}
                disabled={isConsolidating}
              >
                <RefreshCw size={13} className={isConsolidating ? 'animate-spin' : ''} />
                <span>{isConsolidating ? 'Consolidating...' : 'Consolidate Now'}</span>
              </button>
            </div>

            {consolidationResult && (
              <div className="consolidation-result-box">
                <span className="result-status">
                  Status: {consolidationResult.consolidated ? 'success' : (consolidationResult.status || 'not run')}
                </span>
                {typeof consolidationResult.facts_added === 'number' && (
                  <p>
                    Processed {consolidationResult.events_processed || 0} events and added {consolidationResult.facts_added} semantic facts.
                  </p>
                )}
                {consolidationResult.error && <p>{consolidationResult.error}</p>}
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
                  onKeyDown={(e) => e.key === 'Enter' && loadMemoryData(factQuery)}
                  placeholder="Filter facts..."
                  className="search-input"
                  aria-label="Filter semantic facts"
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

          {/* Procedural Skills Table */}
          <div className="settings-card">
            <div className="card-header-between">
              <div>
                <h3 className="card-heading">Procedural Skills (*.SKILL.md)</h3>
                <p className="card-desc">Trigger-matched playbooks loaded from local Markdown files.</p>
              </div>
            </div>

            <div className="facts-table-wrap">
              {proceduralSkills.length > 0 ? (
                <table className="facts-table">
                  <thead>
                    <tr>
                      <th>Skill</th>
                      <th>Triggers</th>
                    </tr>
                  </thead>
                  <tbody>
                    {proceduralSkills.map((skill, idx) => (
                      <tr key={skill.name || idx}>
                        <td className="fact-text-cell">
                          <strong>{skill.name || 'Unnamed skill'}</strong>
                          {skill.description && <div className="skill-description">{skill.description}</div>}
                        </td>
                        <td className="fact-cat-cell">
                          {Array.isArray(skill.triggers) && skill.triggers.length > 0
                            ? skill.triggers.join(', ')
                            : 'No triggers'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="empty-table-state">No procedural skills found.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Harness & Security */}
      {activeTab === 'security' && (
        <div className="settings-tab-content animate-fade-in" role="tabpanel">
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
                        {t.tier === 'auto'
                          ? 'Auto-Run (Read)'
                          : t.tier === 'guarded'
                            ? 'Guarded Auto-Run'
                            : 'Approval Required (Write)'}
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
              <Lock size={16} className="text-ocean-cyan" />
              <div>
                <h4>DLP Output Redactor</h4>
                <p>Scans outbound responses for API keys, bearer tokens, and credentials before replying.</p>
              </div>
            </div>
            <div className="sec-info-box">
              <Shield size={16} className="text-ocean-blue" />
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
