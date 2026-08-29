import React from 'react';
import './EmptyState.css';

export function EmptyState({
  icon: Icon,
  title = 'No Data',
  subtitle = '',
  action = null,
  className = '',
}) {
  return (
    <div className={`empty-state ${className}`}>
      {Icon && (
        <div className="empty-state-icon">
          {typeof Icon === 'function' || typeof Icon === 'object' ? (
            React.isValidElement(Icon) ? Icon : <Icon size={24} />
          ) : null}
        </div>
      )}
      {title && <h4 className="empty-state-title">{title}</h4>}
      {subtitle && <p className="empty-state-subtitle">{subtitle}</p>}
      {action && <div className="empty-state-action">{action}</div>}
    </div>
  );
}

export default EmptyState;
