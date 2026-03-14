import { useEffect, useRef, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';

type ServiceHealth = { ok: boolean; latency_ms: number | null };
type ServicesHealth = Record<string, ServiceHealth>;
const CRITICAL = ['ollama', 'openclaw'];

export default function ServiceStatusBanner({ compact = false }: { compact?: boolean }) {
  const user = useAuthStore((s) => s.user);
  const [services, setServices] = useState<ServicesHealth | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!user) return;
    api.get('/health/services').then((r) => setServices(r.data as ServicesHealth)).catch(() => {});
  }, [user]);

  if (!user || !services) return null;
  const downCritical = CRITICAL.filter((k) => services[k] && !services[k].ok);
  if (downCritical.length === 0) return null;

  if (compact) {
    return (
      <div
        ref={ref}
        style={{ position: 'relative', display: 'inline-flex' }}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <div style={{
          width: 8, height: 8, borderRadius: '50%',
          background: 'var(--rc-warning)',
          boxShadow: '0 0 0 3px var(--rc-warning-weak)',
          cursor: 'pointer',
        }} />
        {showTooltip && (
          <div style={{
            position: 'absolute', right: 0, top: '100%', marginTop: 6,
            background: 'var(--rc-text)', color: '#fff', padding: '6px 10px',
            borderRadius: 8, fontSize: 12, whiteSpace: 'nowrap',
            zIndex: 200, boxShadow: 'var(--rc-shadow-lg)',
          }}>
            ⚠️ LLM offline: {downCritical.join(', ')}
          </div>
        )}
      </div>
    );
  }

  if (dismissed) return null;
  return (
    <div style={{
      background: 'var(--rc-warning-weak)',
      border: '1px solid rgba(217,119,6,0.2)',
      borderRadius: 10,
      padding: '10px 14px',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <AlertTriangle size={14} style={{ color: 'var(--rc-warning)', flexShrink: 0 }} />
        <span style={{ fontSize: 13, color: 'var(--rc-warning)', fontWeight: 600 }}>
          LLM services offline
        </span>
        <span className="rc-help">Reader, Drafts y Extraction pueden no funcionar. ({downCritical.join(', ')})</span>
      </div>
      <button className="rc-btn rc-btn--ghost" style={{ padding: '3px 8px', fontSize: 11 }} onClick={() => setDismissed(true)}>✕</button>
    </div>
  );
}
