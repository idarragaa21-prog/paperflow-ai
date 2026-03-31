import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

type ConfirmOpts = {
  title: string;
  body?: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
};

type ConfirmApi = (opts: ConfirmOpts) => Promise<boolean>;

type Pending = {
  opts: ConfirmOpts;
  resolve: (v: boolean) => void;
};

const Ctx = createContext<ConfirmApi | null>(null);

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [pending, setPending] = useState<Pending | null>(null);

  const confirm = useCallback((opts: ConfirmOpts) => {
    return new Promise<boolean>((resolve) => setPending({ opts, resolve }));
  }, []);

  const api = useMemo(() => confirm, [confirm]);

  function close(v: boolean) {
    const p = pending;
    setPending(null);
    p?.resolve(v);
  }

  return (
    <Ctx.Provider value={api}>
      {children}
      {pending ? (
        <div
          className="rc-modal-overlay"
          onClick={() => close(false)}
          role="dialog"
          aria-modal="true"
          aria-label={pending.opts.title}
        >
          <div className="rc-card rc-modal-content" style={{ width: 'min(520px, 96vw)' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ fontWeight: 950, fontSize: 16 }}>{pending.opts.title}</div>
            {pending.opts.body ? <div className="rc-help" style={{ marginTop: 8 }}>{pending.opts.body}</div> : null}
            <div className="rc-row" style={{ justifyContent: 'flex-end', marginTop: 14 }}>
              <button className="rc-btn" onClick={() => close(false)}>{pending.opts.cancelText || 'Cancel'}</button>
              <button
                className={pending.opts.danger ? 'rc-btn rc-btn--ghost' : 'rc-btn rc-btn--primary'}
                onClick={() => close(true)}
                style={pending.opts.danger ? { borderColor: 'rgba(185,28,28,0.25)', color: 'var(--rc-danger)' } : undefined}
              >
                {pending.opts.confirmText || (pending.opts.danger ? 'Delete' : 'Confirm')}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </Ctx.Provider>
  );
}

export function useConfirm(): ConfirmApi {
  const v = useContext(Ctx);
  if (!v) throw new Error('useConfirm must be used within ConfirmProvider');
  return v;
}
