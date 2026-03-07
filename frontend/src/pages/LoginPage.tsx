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
    await login(email, password);
  }

  return (
    <div style={{ maxWidth: 460, margin: '70px auto', padding: 16 }}>
      <div className="rc-card">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ fontWeight: 900, fontSize: 18, letterSpacing: '-0.02em' }}>PaperFlow AI</div>
          <div className="rc-help">Sign in to access projects, libraries, extraction workspaces and writing tools.</div>
        </div>

        <div style={{ height: 14 }} />

        <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div>
            <div className="rc-kicker">Email</div>
            <input data-testid="login-email" className="rc-input" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
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
            />
          </div>

          <button data-testid="login-submit" className="rc-btn rc-btn--primary" disabled={loading} type="submit">
            {loading ? '…' : 'Login'}
          </button>

          {error ? <div className="rc-error" style={{ fontSize: 13 }}>{error}</div> : null}
        </form>

        <div style={{ height: 12 }} />
        <div className="rc-help">created by <b>alejolo30</b></div>
      </div>
    </div>
  );
}
