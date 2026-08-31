import React, { useState, useEffect } from 'react';
import { 
  X,
  Layers,
  Activity
} from 'lucide-react';
import { useChat } from '../../context/ChatContext';
import { useHealth } from '../../context/HealthContext';
import ArchitectureMap from '../ArchitectureMap/ArchitectureMap';
import './RightPanel.css';

export function RightPanel({ isCollapsed, onToggleCollapse, width, onMouseDownResize }) {
  const { messages, isLoading } = useChat();
  const { isConnected, modelName } = useHealth();

  // Auto-cycle nodes during loading animation
  const [pulseStepIndex, setPulseStepIndex] = useState(0);

  useEffect(() => {
    if (!isLoading) return;
    const interval = setInterval(() => {
      setPulseStepIndex((prev) => (prev + 1) % 5);
    }, 700);
    return () => clearInterval(interval);
  }, [isLoading]);

  // Determine active nodes for topology map
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
          <h3>Architecture Map</h3>
          <span className="panel-badge">Topology CAD</span>
        </div>

        <div className="right-header-actions">
          <button className="icon-action-btn" onClick={onToggleCollapse} title="Close Inspector">
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Content: Dedicated Architecture Topology View */}
      <div className="right-panel-content">
        <div className="topology-tab-view animate-fade-in">
          <p className="tab-hint">
            Poseidon Multi-Tier Memory &amp; Harness Architecture
          </p>
          <div className="topology-wrapper">
            <ArchitectureMap activeNodes={activeNodes} />
          </div>
        </div>
      </div>
    </aside>
  );
}

export default RightPanel;
