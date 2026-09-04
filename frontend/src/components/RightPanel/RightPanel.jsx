import React, { useState, useEffect } from 'react';
import { 
  X, 
  Brain, 
  Layers, 
  Activity, 
  Terminal, 
  Cpu, 
  CheckCircle2, 
  AlertTriangle,
  Calendar,
  FileText
} from 'lucide-react';
import { useChat } from '../../context/ChatContext';
import { useHealth } from '../../context/HealthContext';
import ArchitectureMap from '../ArchitectureMap/ArchitectureMap';
import './RightPanel.css';

export function RightPanel({ isCollapsed, onToggleCollapse, width, onMouseDownResize }) {
  const { messages, isLoading, selectedTurn, overviewTab, setOverviewTab } = useChat();
  const { isConnected, modelName } = useHealth();
  const [activeTab, setActiveTab] = useState('turn'); // 'turn' | 'topology' | 'telemetry'

  // Synchronize when overviewTab changes from outside (e.g. slash commands)
  useEffect(() => {
    if (overviewTab === 'turn' || overviewTab === 'memory' || overviewTab === 'skills' || overviewTab === 'trajectory') {
      setActiveTab('turn');
    } else if (overviewTab === 'topology') {
      setActiveTab('topology');
    } else if (overviewTab === 'telemetry' || overviewTab === 'status') {
      setActiveTab('telemetry');
    }
  }, [overviewTab]);

  // If a turn was selected, switch to 'turn' tab
  useEffect(() => {
    if (selectedTurn) {
      setActiveTab('turn');
    }
  }, [selectedTurn]);

  const handleTabClick = (tab) => {
    setActiveTab(tab);
    if (setOverviewTab) setOverviewTab(tab);
  };

  // Find latest agent message if none specifically selected
  const displayTurn = selectedTurn || messages.slice().reverse().find((m) => m.role === 'agent');

  // Auto-cycle nodes during loading animation
  const [pulseStepIndex, setPulseStepIndex] = useState(0);
  useEffect(() => {
    if (!isLoading) return;
    const interval = setInterval(() => {
      setPulseStepIndex((prev) => (prev + 1) % 5);
    }, 700);
    return () => clearInterval(interval);
  }, [isLoading]);

  let activeNodes = ['gateway', 'harness', 'agent'];
  if (isLoading) {
    const pulseSequences = [
      ['gateway'],
      ['harness', 'agent'],
      ['harness', 'agent', 'procedural', 'semantic'],
      ['harness', 'agent', 'tools'],
      ['gateway', 'agent', 'episodic', 'summarizer']
    ];
    activeNodes = pulseSequences[pulseStepIndex];
  }

  if (isCollapsed) return null;

  const mem = displayTurn?.memoryContext || {
    semantic_facts: [],
    episodic_events: [],
    procedural_skills: [],
  };

  const trajectory = displayTurn?.trajectory || [];

  return (
    <aside className="right-panel" style={{ width: width ? `${width}px` : undefined }}>
      {/* Resizable Drag Handle / Slider */}
      <div 
        className="right-panel-resize-handle" 
        onMouseDown={onMouseDownResize}
        title="Drag to resize Inspector window"
      />

      {/* Header */}
      <div className="right-panel-header">
        <div className="right-header-title">
          <h3>Inspector</h3>
          <span className="panel-badge">{activeTab.toUpperCase()}</span>
        </div>

        <div className="right-header-actions">
          <button className="icon-action-btn" onClick={onToggleCollapse} title="Close Inspector">
            <X size={15} />
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="inspector-tabs-bar">
        <button
          type="button"
          className={`inspector-tab-item ${activeTab === 'turn' ? 'active' : ''}`}
          onClick={() => handleTabClick('turn')}
        >
          <Brain size={13} />
          <span>Turn Audit</span>
        </button>
        <button
          type="button"
          className={`inspector-tab-item ${activeTab === 'topology' ? 'active' : ''}`}
          onClick={() => handleTabClick('topology')}
        >
          <Layers size={13} />
          <span>Topology</span>
        </button>
        <button
          type="button"
          className={`inspector-tab-item ${activeTab === 'telemetry' ? 'active' : ''}`}
          onClick={() => handleTabClick('telemetry')}
        >
          <Activity size={13} />
          <span>Telemetry</span>
        </button>
      </div>

      {/* Content Area */}
      <div className="right-panel-content">
        {activeTab === 'turn' && (
          <div className="turn-inspector-view animate-fade-in">
            {displayTurn ? (
              <div className="turn-inspector-body">
                {/* Turn Header */}
                <div className="turn-meta-card">
                  <div className="turn-meta-row">
                    <span className="turn-meta-label">Run ID</span>
                    <span className="turn-meta-val font-mono">{displayTurn.runId || 'none'}</span>
                  </div>
                  <div className="turn-meta-row">
                    <span className="turn-meta-label">Active Agent</span>
                    <span className="turn-meta-val font-mono">{displayTurn.activeAgent || 'poseidon'}</span>
                  </div>
                  <div className="turn-meta-row">
                    <span className="turn-meta-label">Timestamp</span>
                    <span className="turn-meta-val">{new Date(displayTurn.timestamp).toLocaleTimeString()}</span>
                  </div>
                </div>

                {/* Section: Semantic Facts */}
                <div className="inspector-section">
                  <div className="inspector-section-header">
                    <Brain size={13} className="text-emerald" />
                    <span>Semantic Facts Injected ({mem.semantic_facts?.length || 0})</span>
                  </div>
                  {mem.semantic_facts?.length > 0 ? (
                    <ul className="inspector-fact-list">
                      {mem.semantic_facts.map((fact, idx) => (
                        <li key={idx} className="inspector-fact-item">{fact}</li>
                      ))}
                    </ul>
                  ) : (
                    <div className="inspector-empty-block">No semantic facts matched query.</div>
                  )}
                </div>

                {/* Section: Episodic Memory */}
                <div className="inspector-section">
                  <div className="inspector-section-header">
                    <Calendar size={13} className="text-blue" />
                    <span>Episodic Memory Recalled ({mem.episodic_events?.length || 0})</span>
                  </div>
                  {mem.episodic_events?.length > 0 ? (
                    <div className="inspector-event-list">
                      {mem.episodic_events.map((ev, idx) => (
                        <div key={idx} className="inspector-event-item">
                          <span className="inspector-event-role">{ev.role}:</span>
                          <span className="inspector-event-text">{ev.content}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="inspector-empty-block">No vector episodic turns retrieved.</div>
                  )}
                </div>

                {/* Section: Procedural Skills */}
                <div className="inspector-section">
                  <div className="inspector-section-header">
                    <FileText size={13} className="text-amber" />
                    <span>Active Skills ({mem.procedural_skills?.length || 0})</span>
                  </div>
                  {mem.procedural_skills?.length > 0 ? (
                    <div className="inspector-skill-chips">
                      {mem.procedural_skills.map((s, idx) => (
                        <span key={idx} className="inspector-skill-chip">{s}</span>
                      ))}
                    </div>
                  ) : (
                    <div className="inspector-empty-block">No procedural playbooks triggered.</div>
                  )}
                </div>

                {/* Section: Trajectory Steps */}
                <div className="inspector-section">
                  <div className="inspector-section-header">
                    <Terminal size={13} />
                    <span>Execution Trajectory ({trajectory.length} steps)</span>
                  </div>
                  {trajectory.length > 0 ? (
                    <div className="inspector-trajectory-list">
                      {trajectory.map((step, idx) => (
                        <div key={idx} className="inspector-trajectory-step">
                          <div className="step-header">
                            <span className="step-num">#{idx + 1}</span>
                            <span className="step-type">{step.step_type}</span>
                            {step.risk_level && (
                              <span className={`step-risk risk-${step.risk_level}`}>{step.risk_level}</span>
                            )}
                          </div>
                          {step.tool_name && (
                            <div className="step-tool">tool: <code>{step.tool_name}</code></div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="inspector-empty-block">Single-turn direct generation (0 tools).</div>
                  )}
                </div>
              </div>
            ) : (
              <div className="inspector-no-turn">
                <Brain size={32} />
                <p>Send a message or select a turn to inspect retrieved memory slices.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'topology' && (
          <div className="topology-tab-view animate-fade-in">
            <p className="tab-hint">
              Poseidon Multi-Tier Memory &amp; Harness Architecture
            </p>
            <div className="topology-wrapper">
              <ArchitectureMap activeNodes={activeNodes} />
            </div>
          </div>
        )}

        {activeTab === 'telemetry' && (
          <div className="telemetry-tab-view animate-fade-in">
            <div className="telemetry-card">
              <div className="telemetry-item">
                <span className="telemetry-label">LLM Service</span>
                <span className="telemetry-value">
                  {isConnected ? (
                    <span className="status-online"><CheckCircle2 size={12} /> Connected</span>
                  ) : (
                    <span className="status-offline"><AlertTriangle size={12} /> Offline</span>
                  )}
                </span>
              </div>
              <div className="telemetry-item">
                <span className="telemetry-label">Active Model</span>
                <span className="telemetry-value font-mono">{modelName || 'llama3.2'}</span>
              </div>
              <div className="telemetry-item">
                <span className="telemetry-label">Cognitive Memory</span>
                <span className="telemetry-value">4 Tiers Active</span>
              </div>
              <div className="telemetry-item">
                <span className="telemetry-label">Sandbox Engine</span>
                <span className="telemetry-value">SandboxGuard In-Process</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

export default RightPanel;
