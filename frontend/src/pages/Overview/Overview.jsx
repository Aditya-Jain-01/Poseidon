import React from 'react';
import Card from '../../components/common/Card';
import StatusBadge from '../../components/common/StatusBadge';
import ArchitectureMap from '../../components/ArchitectureMap/ArchitectureMap';
import { useHealth } from '../../context/HealthContext';
import { useChat } from '../../context/ChatContext';
import { Cpu, Activity, MessageSquare, Layers } from 'lucide-react';
import './Overview.css';

export function Overview() {
  const { isConnected, modelName, isLoading: isHealthLoading } = useHealth();
  const { messages } = useChat();

  const userMessagesCount = messages.filter((m) => m.role === 'user').length;
  const totalMessagesCount = messages.length;

  return (
    <div className="overview-page animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">System Overview</h1>
          <p className="page-subtitle">
            Sprint 1 — Working Memory only · Ephemeral single-turn agent runtime
          </p>
        </div>
        <StatusBadge
          status={isHealthLoading ? 'loading' : isConnected ? 'connected' : 'disconnected'}
          label={isConnected ? 'Backend Active' : 'Backend Offline'}
        />
      </div>

      <div className="overview-content">
        {/* System Topology / Architecture Map */}
        <Card title="System Topology" className="architecture-card">
          <ArchitectureMap activeNodes={isConnected ? ['gateway', 'harness', 'agent'] : []} />
        </Card>

        {/* Status Telemetry Cards Grid */}
        <div className="telemetry-grid">
          {/* Card 1: Model */}
          <Card className="telemetry-card">
            <div className="telemetry-header">
              <div className="telemetry-icon-wrapper">
                <Cpu size={16} className="telemetry-icon accent" />
              </div>
              <span className="telemetry-label">Active Model</span>
            </div>
            <div className="telemetry-value-box">
              <span className="telemetry-value mono" title={modelName || 'None'}>
                {modelName ? modelName.replace('google/', '') : isConnected ? 'Detected' : 'Offline'}
              </span>
            </div>
            <span className="telemetry-footnote">Configured via Fast-API Harness</span>
          </Card>

          {/* Card 2: Status */}
          <Card className="telemetry-card">
            <div className="telemetry-header">
              <div className="telemetry-icon-wrapper">
                <Activity size={16} className="telemetry-icon teal" />
              </div>
              <span className="telemetry-label">Backend Status</span>
            </div>
            <div className="telemetry-value-box">
              <StatusBadge
                status={isHealthLoading ? 'loading' : isConnected ? 'connected' : 'disconnected'}
                label={isConnected ? 'Connected' : 'Disconnected'}
              />
            </div>
            <span className="telemetry-footnote">Polling /health every 30s</span>
          </Card>

          {/* Card 3: Session Activity */}
          <Card className="telemetry-card">
            <div className="telemetry-header">
              <div className="telemetry-icon-wrapper">
                <MessageSquare size={16} className="telemetry-icon amber" />
              </div>
              <span className="telemetry-label">Session Messages</span>
            </div>
            <div className="telemetry-value-box">
              <span className="telemetry-value-number">
                {totalMessagesCount}
              </span>
              <span className="telemetry-unit">
                ({userMessagesCount} user {userMessagesCount === 1 ? 'prompt' : 'prompts'})
              </span>
            </div>
            <span className="telemetry-footnote">Stored in Local Working Memory</span>
          </Card>

          {/* Card 4: Sprint Milestone */}
          <Card className="telemetry-card">
            <div className="telemetry-header">
              <div className="telemetry-icon-wrapper">
                <Layers size={16} className="telemetry-icon accent" />
              </div>
              <span className="telemetry-label">Milestone</span>
            </div>
            <div className="telemetry-value-box">
              <span className="telemetry-value highlight">
                Sprint 1
              </span>
            </div>
            <span className="telemetry-footnote">Working Memory &amp; Ephemeral Run</span>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default Overview;
