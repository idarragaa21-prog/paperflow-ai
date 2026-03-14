import { Check } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';

type Mode = 'login' | 'register';

const FEATURES = [
  'Federated search across PubMed, EuropePMC & DOAJ',
  'Structured data extraction with ROB and effect sizes',
  'AI writing studio with grounded citations',
  '100% local — your data never leaves your machine',
];

export default function LoginPage() {
  const login   = useAuthStore(s => s.login);
  const loading = useAuthStore(s => s.loading);
  const error   = useAuthStore(s => s.error);
  const user    = useAuthStore(s => s.user);
  const navigate = useNavigate();

  const [mode, setMode]       = useState<Mode>('login');
  const [email, setEmail]     = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [regError, setRegError] = useState<string | null>(null);
  const [regOk, setRegOk]     = useState(false);
  const [regBusy, setRegBusy] = useState(false);
  const [regClosed, setRegClosed] = useState(false);

  useEffect(() => { if (user) navigate('/projects'); }, [user, navigate]);

  async function onLogin(e: FormEvent) {
    e.preventDefault();
    await login(email, password);
  }

  async function onRegister(e: FormEvent) {
    e.preventDefault();
    setRegError(null); setRegBusy(true);
    try {
      await api.post('/auth/register', { email, password, full_name: fullName || undefined });
      setRegOk(true);
      setTimeout(() => navigate('/projects'), 800);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Error al registrarse.';
      if (err?.response?.status === 403) setRegClosed(true);
      setRegError(detail);
    } finally { setRegBusy(false); }
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* ── Left panel — brand ── */}
      <div style={{
        flex: '0 0 45%',
        background: 'linear-gradient(145deg, #1e1b4b 0%, #312e81 60%, #4338ca 100%)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '60px 56px',
        position: 'relative',
        overflow: 'hidden',
      }} className="rc-login-left">
        {/* Background glow */}
        <div style={{ position: 'absolute', top: -80, right: -80, width: 320, height: 320, borderRadius: '50%', background: 'rgba(99,102,241,0.18)', filter: 'blur(60px)', pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', bottom: -60, left: -60, width: 240, height: 240, borderRadius: '50%', background: 'rgba(124,58,237,0.14)', filter: 'blur(50px)', pointerEvents: 'none' }} />

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 48 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 12,
            background: 'rgba(255,255,255,0.15)',
            border: '1px solid rgba(255,255,255,0.2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 22, fontWeight: 900, color: '#fff',
            backdropFilter: 'blur(4px)',
          }}>P</div>
          <div>
            <div style={{ fontSize: 22, fontWeight: 900, color: '#fff', letterSpacing: '-0.025em' }}>PaperFlow</div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)', marginTop: 1 }}>AI Research Platform</div>
          </div>
        </div>

        <div style={{ marginBottom: 40 }}>
          <h1 style={{ fontSize: 34, fontWeight: 900, color: '#fff', margin: '0 0 14px', letterSpacing: '-0.035em', lineHeight: 1.15 }}>
            Research smarter,<br />not harder.
          </h1>
          <p style={{ fontSize: 16, color: 'rgba(255,255,255,0.65)', margin: 0, lineHeight: 1.6 }}>
            The scientific research platform built for clinicians, researchers and academics who need real results.
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {FEATURES.map(f => (
            <div key={f} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
              <div style={{
                width: 22, height: 22, borderRadius: 6,
                background: 'rgba(99,102,241,0.35)',
                border: '1px solid rgba(255,255,255,0.15)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0, marginTop: 1,
              }}>
                <Check size={13} style={{ color: '#a5b4fc' }} />
              </div>
              <span style={{ fontSize: 14, color: 'rgba(255,255,255,0.80)', lineHeight: 1.5 }}>{f}</span>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 'auto', paddingTop: 48, fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>
          Used by researchers at Hospital Municipal Albert Schweitzer, Rio de Janeiro
        </div>
      </div>

      {/* ── Right panel — form ── */}
      <div style={{
        flex: 1,
        background: '#fff',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 24px',
      }}>
        <div style={{ width: '100%', maxWidth: 360 }}>
          <div style={{ marginBottom: 28, textAlign: 'center' }}>
            <h2 style={{ margin: '0 0 6px', fontSize: 22, fontWeight: 800, letterSpacing: '-0.025em', color: 'var(--rc-text)' }}>
              {mode === 'login' ? 'Sign in' : 'Create account'}
            </h2>
            <p style={{ margin: 0, fontSize: 14, color: 'var(--rc-text-secondary)' }}>
              {mode === 'login' ? 'Welcome back to PaperFlow' : 'Join PaperFlow AI'}
            </p>
          </div>

          {mode === 'login' ? (
            <form onSubmit={onLogin} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <div className="rc-kicker">Email</div>
                <input className="rc-input" type="email" value={email} onChange={e => setEmail(e.target.value)} autoComplete="email" placeholder="you@institution.edu" />
              </div>
              <div>
                <div className="rc-kicker">Password</div>
                <input className="rc-input" type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" />
              </div>
              <button className="rc-btn rc-btn--primary" disabled={loading} type="submit" style={{ width: '100%', justifyContent: 'center', padding: '11px', fontSize: 14, marginTop: 4 }}>
                {loading ? 'Signing in…' : 'Sign in →'}
              </button>
              {error && <div className="rc-error" style={{ textAlign: 'center' }}>{error}</div>}
            </form>
          ) : (
            <form onSubmit={onRegister} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {regClosed && (
                <div style={{ background: 'var(--rc-warning-weak)', border: '1px solid rgba(217,119,6,0.2)', borderRadius: 10, padding: '12px 14px' }}>
                  <div style={{ fontWeight: 700, color: 'var(--rc-warning)', fontSize: 13, marginBottom: 4 }}>Invite-only access</div>
                  <div className="rc-help">Contact <a href="mailto:idarragaa21@gmail.com">idarragaa21@gmail.com</a> to request access.</div>
                </div>
              )}
              <div>
                <div className="rc-kicker">Full name (optional)</div>
                <input className="rc-input" value={fullName} onChange={e => setFullName(e.target.value)} autoComplete="name" placeholder="Dr. Jane Smith" />
              </div>
              <div>
                <div className="rc-kicker">Email</div>
                <input className="rc-input" type="email" value={email} onChange={e => setEmail(e.target.value)} autoComplete="email" placeholder="you@institution.edu" />
              </div>
              <div>
                <div className="rc-kicker">Password (min. 8 characters)</div>
                <input className="rc-input" type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="new-password" />
              </div>
              {regOk
                ? <div style={{ color: 'var(--rc-success)', fontWeight: 700, textAlign: 'center' }}>✓ Account created. Redirecting…</div>
                : <button className="rc-btn rc-btn--primary" disabled={regBusy} type="submit" style={{ width: '100%', justifyContent: 'center', padding: '11px', fontSize: 14 }}>
                    {regBusy ? 'Creating…' : 'Create account →'}
                  </button>
              }
              {regError && !regClosed && <div className="rc-error" style={{ textAlign: 'center' }}>{regError}</div>}
            </form>
          )}

          <div style={{ marginTop: 24, textAlign: 'center', borderTop: '1px solid var(--rc-border)', paddingTop: 18 }}>
            <button
              className="rc-btn rc-btn--ghost"
              style={{ fontSize: 13, color: 'var(--rc-primary)' }}
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setRegError(null); setRegClosed(false); }}
            >
              {mode === 'login' ? "Don't have an account? Request access" : '← Back to sign in'}
            </button>
          </div>

          <div style={{ marginTop: 20, textAlign: 'center' }}>
            <span style={{ fontSize: 11, color: 'var(--rc-text-tertiary)' }}>created by alejolo30</span>
          </div>
        </div>
      </div>
    </div>
  );
}
