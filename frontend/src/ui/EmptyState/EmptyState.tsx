import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export default function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', padding: '48px 24px', gap: 12, textAlign: 'center',
    }}>
      {icon && <div style={{ opacity: 0.25, color: 'var(--rc-primary)' }}>{icon}</div>}
      <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--rc-text)' }}>{title}</div>
      {description && <div className="rc-help" style={{ maxWidth: 380 }}>{description}</div>}
      {action && (
        <button className="rc-btn rc-btn--primary" style={{ marginTop: 6 }} onClick={action.onClick}>
          {action.label}
        </button>
      )}
    </div>
  );
}
