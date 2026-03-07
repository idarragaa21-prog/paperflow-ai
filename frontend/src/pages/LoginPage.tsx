import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export default function LoginPage() {
  const login = useAuthStore((s) => s.login);
  const loading = useAuthStore((s) => s.loading);
  const error = useAuthStore((s) => s.error);
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  useEffect(() => {
    if (user) navigate('/projects');
  }, [user, navigate]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      await login(email, password);
      navigate('/projects');
    } catch {
      // error state already handled in the store
    }
  }

  function useDemoAccount(nextEmail: string) {
    setEmail(nextEmail);
    setPassword('paperflow-e2e-123');
  }

  return (
    <div className="rc-auth-shell">
      <div className="rc-auth-grid">
        <section className="rc-auth-hero">
          <div className="rc-pill">Internal RC</div>
          <h1 className="rc-auth-title">PaperFlow AI</h1>
          <p className="rc-auth-copy">
            A local-first research workspace for literature search, evidence extraction, grounded PDF chat,
            writing, analysis and screening.
          </p>

          <div className="rc-auth-stats">
            <div className="rc-hero-stat">
              <strong>500</strong>
              <span>seeded papers</span>
            </div>
            <div className="rc-hero-stat">
              <strong>RAG</strong>
              <span>grounded answers</span>
            </div>
            <div className="rc-hero-stat">
              <strong>R</strong>
              <span>real exported reports</span>
            </div>
          </div>

          <div className="rc-card" style={{ padding: 16 }}>
            <div className="rc-card-title">Demo accounts</div>
            <div className="rc-row">
              <button type="button" className="rc-btn" onClick={() => useDemoAccount('rc-owner@paperflow.dev')}>
                Fill owner demo
              </button>
              <button type="button" className="rc-btn" onClick={() => useDemoAccount('rc-reviewer@paperflow.dev')}>
                Fill reviewer demo
              </button>
            </div>
            <div className="rc-help" style={{ marginTop: 10 }}>
              Password for both: <b>paperflow-e2e-123</b>
            </div>
          </div>
        </section>

        <section className="rc-auth-panel">
          <div className="rc-card rc-auth-card">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div className="rc-pill rc-pill--soft">Sign in</div>
              <div style={{ fontWeight: 900, fontSize: 26, letterSpacing: '-0.03em' }}>Open your workspace</div>
              <div className="rc-help">Projects, library, reader, extraction, writing studio and analysis in one place.</div>
            </div>

            <div style={{ height: 18 }} />

            <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <div className="rc-kicker">Email</div>
                <input
                  data-testid="login-email"
                  className="rc-input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  placeholder="rc-owner@paperflow.dev"
                />
              </div>

              <div>
                <div className="rc-kicker">Password</div>
                <input
                  data-testid="login-password"
                  className="rc-input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  placeholder="••••••••••••"
                />
              </div>

              <button data-testid="login-submit" className="rc-btn rc-btn--primary" disabled={loading} type="submit">
                {loading ? 'Signing in…' : 'Enter PaperFlow'}
              </button>

              {error ? <div className="rc-error" style={{ fontSize: 13 }}>{error}</div> : null}
            </form>

            <div style={{ height: 14 }} />
            <div className="rc-help">If this screen keeps loading, the backend session check will now fail fast instead of hanging indefinitely.</div>
          </div>
        </section>
      </div>
    </div>
  );
}
