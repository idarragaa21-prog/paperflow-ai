import { Component } from 'react';
import type { ReactNode, ErrorInfo } from 'react';

interface Props {
  children: ReactNode;
  /** Optional custom fallback UI */
  fallback?: ReactNode;
  /** Label shown in the error message for easier debugging */
  label?: string;
}

interface State {
  error: Error | null;
}

/**
 * Lightweight per-section error boundary.
 * Wraps any risky section (Mermaid diagrams, StudyViewer, charts…)
 * so one broken component doesn't crash the whole page.
 *
 * Usage:
 *   <SectionErrorBoundary label="Mermaid diagram">
 *     <MermaidBlock code={code} />
 *   </SectionErrorBoundary>
 */
export class SectionErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Non-blocking — just log for debugging
    console.warn(`[SectionErrorBoundary] ${this.props.label ?? 'section'} crashed:`, error, info.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    if (this.props.fallback) return this.props.fallback;

    return (
      <div className="rc-section-error" role="alert">
        <div className="rc-section-error__title">
          ⚠ {this.props.label ? `"${this.props.label}" failed to render` : 'This section failed to render'}
        </div>
        <div className="rc-section-error__msg">
          {error.message || 'An unexpected error occurred in this component.'}
        </div>
        <button
          className="rc-btn rc-btn--sm"
          onClick={() => this.setState({ error: null })}
        >
          Retry
        </button>
      </div>
    );
  }
}

export default SectionErrorBoundary;
