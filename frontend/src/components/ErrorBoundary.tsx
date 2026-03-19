import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

type Props = { children: ReactNode; fallback?: ReactNode };
type State = { error: Error | null };

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          minHeight: 320, padding: 32, textAlign: 'center',
        }}>
          <div style={{
            width: 56, height: 56, borderRadius: 16, marginBottom: 16,
            background: 'var(--rc-danger-bg)', border: '1px solid var(--rc-danger-border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24,
          }}>⚠️</div>
          <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 18, marginBottom: 8 }}>
            Something went wrong
          </div>
          <div style={{ color: 'var(--rc-muted)', fontSize: 13, maxWidth: 400, marginBottom: 20 }}>
            {this.state.error.message}
          </div>
          <button
            className="rc-btn rc-btn--primary"
            onClick={() => { this.setState({ error: null }); window.location.reload(); }}
          >
            Reload page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
