import React from 'react';
import './Card.css';

export function Card({ title, actions, children, className = '', style = {}, ...props }) {
  return (
    <div className={`common-card ${className}`} style={style} {...props}>
      {(title || actions) && (
        <div className="common-card-header">
          {title && <div className="common-card-title">{title}</div>}
          {actions && <div className="common-card-actions">{actions}</div>}
        </div>
      )}
      <div className="common-card-body">{children}</div>
    </div>
  );
}

export default Card;
