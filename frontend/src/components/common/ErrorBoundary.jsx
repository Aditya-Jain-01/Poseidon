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
          color: 'var(--ink, #fff)',
          background: 'var(--bg, #0a0f1e)',
          minHeight: '100vh',
          fontFamily: 'var(--font-body, sans-serif)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          gap: '16px'
        }}>
          <h2 style={{ color: 'var(--danger, #ff6b7a)' }}>Something went wrong</h2>
          <p style={{ color: 'var(--muted, #9aa8c7)', maxWidth: '500px' }}>
            {this.state.error?.message || 'An unexpected rendering error occurred.'}
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              background: 'var(--accent, #7c9cff)',
              color: '#060a14',
              fontWeight: 600,
              cursor: 'pointer',
              border: 'none'
            }}
          >
            Reload Dashboard
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
