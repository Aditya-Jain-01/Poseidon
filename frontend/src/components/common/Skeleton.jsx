import React from 'react';
import './Skeleton.css';

export function Skeleton({
  width = '100%',
  height = '16px',
  borderRadius = 'var(--radius)',
  className = '',
  style = {},
}) {
  const customStyle = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
    borderRadius,
    ...style,
  };

  return <div className={`common-skeleton ${className}`} style={customStyle} />;
}

export default Skeleton;
