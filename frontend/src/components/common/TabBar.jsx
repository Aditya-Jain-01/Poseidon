import React from 'react';
import './TabBar.css';

export function TabBar({ tabs = [], activeTab, onTabChange, className = '' }) {
  return (
    <div className={`common-tab-bar ${className}`} role="tablist">
      {tabs.map((tab) => {
        const isActive = activeTab === tab.key;
        return (
          <button
            key={tab.key}
            role="tab"
            aria-selected={isActive}
            className={`common-tab-btn ${isActive ? 'active' : ''}`}
            onClick={() => onTabChange && onTabChange(tab.key)}
          >
            {tab.status && (
              <span className={`common-tab-status-dot ${tab.status}`} aria-hidden="true" />
            )}
            <span>{tab.label}</span>
            {tab.badge ? (
              <span className={`common-tab-badge ${tab.badgeVariant || ''}`}>{tab.badge}</span>
            ) : tab.count !== undefined ? (
              <span className="common-tab-badge">{tab.count}</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

export default TabBar;
