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
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span className="common-tab-badge">{tab.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export default TabBar;
