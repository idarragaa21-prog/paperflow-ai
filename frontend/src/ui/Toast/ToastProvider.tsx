import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import type { Toast, ToastKind } from './types';

type ToastInput = {
  kind: ToastKind;
  title: string;
  message?: string;
  action?: { label: string; onClick: () => void };
  ttlMs?: number;
};

type ToastApi = {
  push: (t: ToastInput) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
};

const Ctx = createContext<ToastApi | null>(null);

function kindClass(kind: ToastKind): string {
  if (kind === 'success') return 'rc-badge rc-badge--success';
  if (kind === 'error') return 'rc-badge rc-badge--danger';
  return 'rc-badge rc-badge--info';
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const timers = useRef<Record<string, any>>({});

  const remove = useCallback((id: string) => {
    setItems((prev) => prev.filter((t) => t.id !== id));
    const tm = timers.current[id];
    if (tm) {
      clearTimeout(tm);
      delete timers.current[id];
    }
  }, []);

  const push = useCallback(
    (t: ToastInput) => {
      const id = Math.random().toString(36).slice(2);
      const toast: Toast = {
        id,
        kind: t.kind,
        title: t.title,
        message: t.message,
        action: t.action,
        createdAtMs: Date.now(),
      };
      setItems((prev) => [toast, ...prev].slice(0, 4));
      const ttl = t.ttlMs ?? (t.kind === 'error' ? 9000 : 4500);
      timers.current[id] = setTimeout(() => remove(id), ttl);
    },
    [remove],
  );

  const api: ToastApi = useMemo(
    () => ({
      push,
      success: (title, message) => push({ kind: 'success', title, message }),
      error: (title, message) => push({ kind: 'error', title, message }),
      info: (title, message) => push({ kind: 'info', title, message }),
    }),
    [push],
  );

  return (
    <Ctx.Provider value={api}>
      {children}
      <div role="status" aria-live="polite" style={{ position: 'fixed', right: 14, bottom: 14, zIndex: 1000, display: 'flex', flexDirection: 'column', gap: 10, width: 'min(420px, 92vw)' }}>
        {items.map((t) => (
          <div key={t.id} className="rc-card rc-toast-item" style={{ padding: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <span className={kindClass(t.kind)} style={{ width: 'fit-content' }}>{t.kind}</span>
                <div style={{ fontWeight: 900 }}>{t.title}</div>
                {t.message ? <div className="rc-help">{t.message}</div> : null}
                {t.action ? (
                  <button className="rc-btn" onClick={() => { try { t.action?.onClick(); } finally { remove(t.id); } }} style={{ width: 'fit-content' }}>
                    {t.action.label}
                  </button>
                ) : null}
              </div>
              <button className="rc-btn rc-btn--ghost" onClick={() => remove(t.id)} aria-label="Dismiss">
                ×
              </button>
            </div>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export function useToast(): ToastApi {
  const v = useContext(Ctx);
  if (!v) throw new Error('useToast must be used within ToastProvider');
  return v;
}
