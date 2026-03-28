import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { useI18n } from '../i18n';

export default function SignupPage() {
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  const { t } = useI18n();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { if (user) navigate('/dashboard'); }, [user, navigate]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) { setError(t.auth.passwordMinLength); return; }
    if (password !== confirmPw) { setError(t.auth.passwordMismatch); return; }
    setLoading(true);
    try {
      await api.post('/auth/register', { email, password, full_name: fullName || null });
      navigate('/login');
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Registration failed');
    } finally { setLoading(false); }
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#0f0e1a' }}>
      {/* Left panel (same as login) */}
      <div className="login-left-panel" style={{
        flex: '0 0 460px',
        background: 'linear-gradient(145deg, #13122a 0%, #1a1040 50%, #0e1628 100%)',
        display: 'flex', flexDirection: 'column', justifyContent: 'center',
        padding: '48px', borderRight: '1px solid rgba(255,255,255,0.06)',
        position: 'relative', overflow: 'hidden',
      }}>
        <div style={{ position: 'absolute', inset: 0, opacity: 0.6,
          backgroundImage: 'radial-gradient(circle at 20% 80%, rgba(99,102,241,0.18) 0%, transparent 60%), radial-gradient(circle at 80% 20%, rgba(139,92,246,0.12) 0%, transparent 50%)',
          pointerEvents: 'none' }} />
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 40 }}>
            <div style={{ width: 40, height: 40, borderRadius: 12,
              background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 4px 20px rgba(99,102,241,0.4)' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
            </div>
            <span style={{ fontSize: 20, fontWeight: 800, color: 'white', letterSpacing: '-0.03em', fontFamily: 'var(--font-display)' }}>PaperFlow</span>
          </div>
          <div style={{ fontSize: 21, fontWeight: 800, color: 'white', letterSpacing: '-0.03em', lineHeight: 1.25, fontFamily: 'var(--font-display)' }}>
            Your personal<br />AI research workspace
          </div>
          <div style={{ marginTop: 8, fontSize: 13, color: 'rgba(255,255,255,0.4)', lineHeight: 1.6 }}>
            Search, extract, analyze and write<br />— everything local, nothing in the cloud.
          </div>
        </div>
      </div>

      {/* Right panel — form */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 32px', background: '#f7f6f2' }}>
        <div style={{ width: '100%', maxWidth: 380 }}>
          <div style={{ marginBottom: 32 }}>
            <div style={{ fontSize: 26, fontWeight: 850, letterSpacing: '-0.03em', color: '#1a1929', fontFamily: 'var(--font-display)' }}>
              {t.auth.createAccountTitle}
            </div>
            <div style={{ marginTop: 6, fontSize: 14, color: 'rgba(26,25,41,0.5)' }}>{t.auth.createAccountSubtitle}</div>
          </div>

          <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <div className="rc-kicker">{t.auth.fullName}</div>
              <input className="rc-input" type="text" value={fullName} onChange={e => setFullName(e.target.value)}
                placeholder={t.auth.fullNamePlaceholder} autoComplete="name" style={{ fontSize: 14 }} />
            </div>
            <div>
              <div className="rc-kicker">{t.auth.email}</div>
              <input className="rc-input" type="email" value={email} onChange={e => setEmail(e.target.value)}
                placeholder={t.auth.emailPlaceholder} autoComplete="email" autoFocus required style={{ fontSize: 14 }} />
            </div>
            <div>
              <div className="rc-kicker">{t.auth.password}</div>
              <input className="rc-input" type="password" value={password} onChange={e => setPassword(e.target.value)}
                placeholder={t.auth.passwordPlaceholder} autoComplete="new-password" required style={{ fontSize: 14 }} />
            </div>
            <div>
              <div className="rc-kicker">{t.auth.confirmPassword}</div>
              <input className="rc-input" type="password" value={confirmPw} onChange={e => setConfirmPw(e.target.value)}
                placeholder={t.auth.passwordPlaceholder} autoComplete="new-password" required style={{ fontSize: 14 }} />
            </div>

            {error && (
              <div style={{ padding: '10px 14px', borderRadius: 10, background: 'rgba(185,28,28,0.08)', border: '1px solid rgba(185,28,28,0.18)', color: '#b91c1c', fontSize: 13 }}>
                {error}
              </div>
            )}

            <button type="submit" className="rc-btn rc-btn--primary" disabled={loading || !email || !password}
              style={{ width: '100%', padding: '11px 16px', fontSize: 14, marginTop: 4, borderRadius: 12 }}>
              {loading ? t.auth.creatingAccount : `${t.auth.signUp} →`}
            </button>
          </form>

          <div style={{ marginTop: 24, textAlign: 'center', fontSize: 13, color: 'rgba(26,25,41,0.5)' }}>
            {t.auth.hasAccount}{' '}
            <Link to="/login" style={{ fontWeight: 700 }}>{t.auth.signIn}</Link>
          </div>

          <div style={{ marginTop: 24, paddingTop: 20, borderTop: '1px solid rgba(26,25,41,0.1)', textAlign: 'center', fontSize: 12, color: 'rgba(26,25,41,0.3)' }}>
            {t.auth.tagline}
          </div>
        </div>
      </div>

      <style>{`.login-left-panel { display: flex !important; } @media(max-width:780px){.login-left-panel{display:none!important}}`}</style>
    </div>
  );
}
