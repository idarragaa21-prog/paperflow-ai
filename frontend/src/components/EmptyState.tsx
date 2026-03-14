type EmptyStateVariant = 'papers' | 'projects' | 'notes' | 'references' | 'search' | 'generic';

const illustrations: Record<EmptyStateVariant, JSX.Element> = {
  projects: (
    <svg width="120" height="100" viewBox="0 0 120 100" fill="none">
      <rect x="8" y="22" width="50" height="62" rx="6" fill="rgba(67,56,202,0.07)" stroke="rgba(67,56,202,0.2)" strokeWidth="1.5"/>
      <rect x="62" y="30" width="50" height="54" rx="6" fill="rgba(67,56,202,0.05)" stroke="rgba(67,56,202,0.15)" strokeWidth="1.5"/>
      <rect x="18" y="35" width="30" height="3" rx="1.5" fill="rgba(67,56,202,0.3)"/>
      <rect x="18" y="43" width="24" height="2.5" rx="1.25" fill="rgba(67,56,202,0.18)"/>
      <rect x="18" y="50" width="28" height="2.5" rx="1.25" fill="rgba(67,56,202,0.14)"/>
      <rect x="72" y="44" width="30" height="3" rx="1.5" fill="rgba(67,56,202,0.25)"/>
      <rect x="72" y="52" width="22" height="2.5" rx="1.25" fill="rgba(67,56,202,0.15)"/>
      <circle cx="60" cy="14" r="10" fill="rgba(67,56,202,0.1)" stroke="rgba(67,56,202,0.3)" strokeWidth="1.5"/>
      <line x1="60" y1="10" x2="60" y2="18" stroke="rgba(67,56,202,0.5)" strokeWidth="2" strokeLinecap="round"/>
      <line x1="56" y1="14" x2="64" y2="14" stroke="rgba(67,56,202,0.5)" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  ),
  papers: (
    <svg width="120" height="100" viewBox="0 0 120 100" fill="none">
      <rect x="20" y="10" width="80" height="80" rx="7" fill="rgba(67,56,202,0.06)" stroke="rgba(67,56,202,0.18)" strokeWidth="1.5" strokeDasharray="4 3"/>
      <rect x="34" y="28" width="52" height="4" rx="2" fill="rgba(67,56,202,0.25)"/>
      <rect x="34" y="38" width="42" height="3" rx="1.5" fill="rgba(67,56,202,0.15)"/>
      <rect x="34" y="46" width="48" height="3" rx="1.5" fill="rgba(67,56,202,0.12)"/>
      <rect x="34" y="54" width="36" height="3" rx="1.5" fill="rgba(67,56,202,0.1)"/>
      <circle cx="60" cy="72" r="8" fill="rgba(67,56,202,0.12)" stroke="rgba(67,56,202,0.28)" strokeWidth="1.5"/>
      <path d="M57 72l2 2 4-4" stroke="rgba(67,56,202,0.6)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  notes: (
    <svg width="120" height="100" viewBox="0 0 120 100" fill="none">
      <rect x="25" y="15" width="70" height="70" rx="7" fill="rgba(67,56,202,0.06)" stroke="rgba(67,56,202,0.18)" strokeWidth="1.5"/>
      <line x1="37" y1="35" x2="83" y2="35" stroke="rgba(67,56,202,0.2)" strokeWidth="2" strokeLinecap="round"/>
      <line x1="37" y1="45" x2="75" y2="45" stroke="rgba(67,56,202,0.15)" strokeWidth="2" strokeLinecap="round"/>
      <line x1="37" y1="55" x2="79" y2="55" stroke="rgba(67,56,202,0.15)" strokeWidth="2" strokeLinecap="round"/>
      <line x1="37" y1="65" x2="65" y2="65" stroke="rgba(67,56,202,0.12)" strokeWidth="2" strokeLinecap="round"/>
      <circle cx="93" cy="75" r="14" fill="rgba(67,56,202,0.12)" stroke="rgba(67,56,202,0.3)" strokeWidth="1.5"/>
      <path d="M89 75l1.5 1.5 3.5-4" stroke="rgba(67,56,202,0.7)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  references: (
    <svg width="120" height="100" viewBox="0 0 120 100" fill="none">
      <rect x="15" y="18" width="48" height="64" rx="5" fill="rgba(67,56,202,0.06)" stroke="rgba(67,56,202,0.18)" strokeWidth="1.5"/>
      <rect x="57" y="28" width="48" height="54" rx="5" fill="rgba(67,56,202,0.04)" stroke="rgba(67,56,202,0.13)" strokeWidth="1.5"/>
      <rect x="24" y="30" width="30" height="3" rx="1.5" fill="rgba(67,56,202,0.3)"/>
      <rect x="24" y="38" width="24" height="2.5" rx="1.25" fill="rgba(67,56,202,0.18)"/>
      <rect x="24" y="45" width="28" height="2.5" rx="1.25" fill="rgba(67,56,202,0.14)"/>
      <path d="M51 50 L69 50" stroke="rgba(67,56,202,0.35)" strokeWidth="1.5" strokeDasharray="3 2"/>
      <circle cx="69" cy="50" r="3" fill="rgba(67,56,202,0.3)"/>
    </svg>
  ),
  search: (
    <svg width="120" height="100" viewBox="0 0 120 100" fill="none">
      <circle cx="52" cy="46" r="26" fill="rgba(67,56,202,0.06)" stroke="rgba(67,56,202,0.2)" strokeWidth="1.5"/>
      <circle cx="52" cy="46" r="16" fill="none" stroke="rgba(67,56,202,0.15)" strokeWidth="1.5" strokeDasharray="4 3"/>
      <line x1="71" y1="65" x2="88" y2="82" stroke="rgba(67,56,202,0.25)" strokeWidth="3" strokeLinecap="round"/>
      <path d="M44 46h16M52 38v16" stroke="rgba(67,56,202,0.4)" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  ),
  generic: (
    <svg width="120" height="100" viewBox="0 0 120 100" fill="none">
      <rect x="20" y="20" width="80" height="60" rx="8" fill="rgba(67,56,202,0.06)" stroke="rgba(67,56,202,0.18)" strokeWidth="1.5" strokeDasharray="5 3"/>
      <circle cx="60" cy="50" r="16" fill="rgba(67,56,202,0.08)" stroke="rgba(67,56,202,0.2)" strokeWidth="1.5"/>
      <path d="M60 43v8M60 55v2" stroke="rgba(67,56,202,0.45)" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  ),
};

interface EmptyStateProps {
  variant?: EmptyStateVariant;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ variant = 'generic', title, description, action }: EmptyStateProps) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '48px 24px',
      gap: 16,
      textAlign: 'center',
    }}>
      <div style={{ marginBottom: 4, opacity: 0.9 }}>
        {illustrations[variant]}
      </div>
      <div style={{
        fontFamily: 'var(--font-display)',
        fontWeight: 700,
        fontSize: 16,
        color: 'var(--rc-text)',
        letterSpacing: '-0.01em',
      }}>
        {title}
      </div>
      {description && (
        <div style={{
          fontSize: 13,
          color: 'var(--rc-muted)',
          maxWidth: 320,
          lineHeight: 1.6,
        }}>
          {description}
        </div>
      )}
      {action && <div style={{ marginTop: 8 }}>{action}</div>}
    </div>
  );
}
