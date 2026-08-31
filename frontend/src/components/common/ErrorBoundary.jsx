import React from 'react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '32px',
          color: 'var(--text-primary, #f1f5f9)',
          background: 'var(--bg-canvas, #090a0f)',
          minHeight: '100vh',
          fontFamily: 'var(--font-body, sans-serif)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          gap: '12px'
        }}>
          <h2 style={{ color: 'var(--danger, #ef4444)', fontSize: '1.1rem', fontWeight: 600 }}>System Render Error</h2>
          <p style={{ color: 'var(--text-secondary, #94a3b8)', maxWidth: '460px', fontSize: '0.85rem' }}>
            {this.state.error?.message || 'An unexpected rendering error occurred in the workspace.'}
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: '8px',
              padding: '6px 14px',
              borderRadius: 'var(--radius-md, 6px)',
              background: 'var(--accent-primary, #3b82f6)',
              color: '#ffffff',
              fontWeight: 500,
              fontSize: '0.8rem',
              cursor: 'pointer',
              border: 'none',
              transition: 'background 0.15s ease'
            }}
          >
            Reload Workspace
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
