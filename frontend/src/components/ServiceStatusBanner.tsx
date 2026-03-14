import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';

type ServiceHealth = { ok: boolean; latency_ms: number | null };
type ServicesHealth = Record<string, ServiceHealth>;

const CRITICAL = ['ollama', 'openclaw'];

export default function ServiceStatusBanner() {
  const user = useAuthStore((s) => s.user);
  const [services, setServices] = useState<ServicesHealth | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (!user) return;
    api.get('/health/services')
      .then((r) => setServices(r.data as ServicesHealth))
      .catch(() => {}); // silent — banner is a nice-to-have
  }, [user]);

  if (!user || !services || dismissed) return null;

  const downCritical = CRITICAL.filter((k) => services[k] && !services[k].ok);
  if (downCritical.length === 0) return null;

  return (
    <div
      style={{
        background: 'rgba(180,83,9,0.08)',
        border: '1px solid rgba(180,83,9,0.22)',
        borderRadius: 10,
        padding: '10px 14px',
        margin: '0 0 14px 0',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 12,
      }}
    >
      <div>
        <span style={{ color: 'var(--rc-warning)', fontWeight: 700 }}>
          ⚠️ Algunos servicios LLM no están disponibles.
        </span>{' '}
        <span className="rc-help" style={{ color: 'inherit' }}>
          Reader, Drafts y Extraction pueden no funcionar.{' '}
          <span style={{ opacity: 0.7 }}>
            (Caídos: {downCritical.join(', ')})
          </span>
        </span>
      </div>
      <button
        className="rc-btn rc-btn--ghost"
        style={{ fontSize: 12, padding: '4px 8px', whiteSpace: 'nowrap' }}
        onClick={() => setDismissed(true)}
      >
        Cerrar ✕
      </button>
    </div>
  );
}
