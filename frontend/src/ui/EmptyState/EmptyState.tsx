import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export default function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 20px',
        gap: 12,
        textAlign: 'center',
      }}
    >
      {icon ? (
        <div style={{ fontSize: 32, opacity: 0.3 }}>{icon}</div>
      ) : (
        <div style={{ fontSize: 32, opacity: 0.2 }}>○</div>
      )}
      <div style={{ fontWeight: 750, fontSize: 15, color: 'var(--rc-text)' }}>{title}</div>
      {description ? (
        <div className="rc-help" style={{ maxWidth: 380 }}>{description}</div>
      ) : null}
      {action ? (
        <button className="rc-btn rc-btn--primary" style={{ marginTop: 4 }} onClick={action.onClick}>
          {action.label}
        </button>
      ) : null}
    </div>
  );
}
