import React from 'react';
import Card from '../../components/common/Card';
import StatusBadge from '../../components/common/StatusBadge';
import Skeleton from '../../components/common/Skeleton';
import './Overview.css';

export function Overview() {
  return (
    <div className="overview-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Overview</h1>
          <p className="page-subtitle">Agent architecture and live status telemetry</p>
        </div>
        <StatusBadge status="connected" label="Core System Ready" />
      </div>

      <div className="overview-grid">
        <Card title="System Topology">
          <p className="muted">Architecture Map component slot (Person 3).</p>
          <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <Skeleton height="24px" width="60%" />
            <Skeleton height="16px" width="80%" />
            <Skeleton height="16px" width="40%" />
          </div>
        </Card>

        <Card title="Quick Status">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="mono">FastAPI Backend</span>
              <StatusBadge status="loading" label="Connecting..." />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="mono">Persistent Memory</span>
              <StatusBadge status="connected" label="Active" />
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

export default Overview;
