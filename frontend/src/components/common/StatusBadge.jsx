import React from 'react';
import './StatusBadge.css';

export function StatusBadge({ status = 'disconnected', label = '', className = '' }) {
  const normalizedStatus = ['connected', 'disconnected', 'loading'].includes(status)
    ? status
    : 'disconnected';

  return (
    <div className={`status-badge ${className}`}>
      <span className={`status-dot ${normalizedStatus}`} />
      <span className="status-label">{label || normalizedStatus}</span>
    </div>
  );
}

export default StatusBadge;
