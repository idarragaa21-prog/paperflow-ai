import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { useI18n } from '../i18n';

export default function SignupPage() {
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { t } = useI18n();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const invitationToken = searchParams.get('invitation_token');
  const invitationEmail = searchParams.get('email');

  useEffect(() => { if (user) navigate('/dashboard'); }, [user, navigate]);
  useEffect(() => {
    if (invitationEmail && !email) {
      setEmail(invitationEmail);
    }
  }, [email, invitationEmail]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) { setError(t.auth.passwordMinLength); return; }
    if (password !== confirmPw) { setError(t.auth.passwordMismatch); return; }
    setLoading(true);
    try {
      const payload: Record<string, string | null> = {
        email,
        password,
        full_name: fullName || null,
      };
      if (invitationToken) {
        payload.invitation_token = invitationToken;
      }
      const response = await api.post('/auth/register', payload);
      const acceptedProjectId = (response.data as { accepted_project_id?: string | null } | undefined)?.accepted_project_id;
      navigate(
        invitationToken
          ? `/login?email=${encodeURIComponent(email)}&invited=1${acceptedProjectId ? `&accepted_project_id=${encodeURIComponent(acceptedProjectId)}` : `&invitation_token=${encodeURIComponent(invitationToken)}`}`
          : '/login'
      );
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Registration failed');
    } finally { setLoading(false); }
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--rc-bg)' }}>
      {/* Left panel (same as login) */}
      <div className="login-left-panel" style={{
        flex: '0 0 460px',
        background: 'var(--rc-bg)',
        display: 'flex', flexDirection: 'column', justifyContent: 'center',
        padding: '48px', borderRight: '1px solid var(--rc-surface-2)',
        position: 'relative', overflow: 'hidden',
      }}>
        <div style={{ position: 'absolute', inset: 0, opacity: 0.6,
          backgroundImage: 'radial-gradient(circle at 20% 80%, var(--rc-primary-weak) 0%, transparent 60%), radial-gradient(circle at 80% 20%, var(--rc-primary-weak) 0%, transparent 50%)',
          pointerEvents: 'none' }} />
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 40 }}>
            <div style={{ width: 40, height: 40, borderRadius: 12,
              background: 'var(--rc-primary)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 4px 20px var(--rc-primary-weak)' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
            </div>
            <span style={{ fontSize: 20, fontWeight: 800, color: 'var(--rc-text)', letterSpacing: '-0.03em', fontFamily: 'var(--font-display)' }}>PaperFlow</span>
          </div>
          <div style={{ fontSize: 21, fontWeight: 800, color: 'var(--rc-text)', letterSpacing: '-0.03em', lineHeight: 1.25, fontFamily: 'var(--font-display)' }}>
            Your personal<br />AI research workspace
          </div>
          <div style={{ marginTop: 8, fontSize: 13, color: 'var(--rc-muted)', lineHeight: 1.6 }}>
            Search, extract, analyze and write<br />— everything local, nothing in the cloud.
          </div>
        </div>
      </div>

      {/* Right panel — form */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 32px', background: 'var(--rc-bg)' }}>
        <div style={{ width: '100%', maxWidth: 380 }}>
          <div style={{ marginBottom: 32 }}>
            <div style={{ fontSize: 26, fontWeight: 850, letterSpacing: '-0.03em', color: 'var(--rc-text)', fontFamily: 'var(--font-display)' }}>
              {t.auth.createAccountTitle}
            </div>
            <div style={{ marginTop: 6, fontSize: 14, color: 'var(--rc-muted)' }}>{t.auth.createAccountSubtitle}</div>
          </div>

          <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {invitationToken ? (
              <div style={{ padding: '10px 14px', borderRadius: 10, background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.18)', color: '#4338ca', fontSize: 13 }}>
                Create an account with the invited email to join the shared project.
              </div>
            ) : null}
            <div>
              <label htmlFor="signup-fullname" className="rc-kicker" style={{ display: 'block' }}>{t.auth.fullName}</label>
              <input id="signup-fullname" className="rc-input" type="text" value={fullName} onChange={e => setFullName(e.target.value)}
                placeholder={t.auth.fullNamePlaceholder} autoComplete="name" style={{ fontSize: 14 }} />
            </div>
            <div>
              <label htmlFor="signup-email" className="rc-kicker" style={{ display: 'block' }}>{t.auth.email}</label>
              <input id="signup-email" className="rc-input" type="email" value={email} onChange={e => setEmail(e.target.value)}
                placeholder={t.auth.emailPlaceholder} autoComplete="email" autoFocus required style={{ fontSize: 14 }} />
            </div>
            <div>
              <label htmlFor="signup-password" className="rc-kicker" style={{ display: 'block' }}>{t.auth.password}</label>
              <input id="signup-password" className="rc-input" type="password" value={password} onChange={e => setPassword(e.target.value)}
                placeholder={t.auth.passwordPlaceholder} autoComplete="new-password" required style={{ fontSize: 14 }} />
            </div>
            <div>
              <label htmlFor="signup-confirm-password" className="rc-kicker" style={{ display: 'block' }}>{t.auth.confirmPassword}</label>
              <input id="signup-confirm-password" className="rc-input" type="password" value={confirmPw} onChange={e => setConfirmPw(e.target.value)}
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

          <div style={{ marginTop: 24, textAlign: 'center', fontSize: 13, color: 'var(--rc-muted)' }}>
            {t.auth.hasAccount}{' '}
            <Link
              to={invitationToken ? `/login?invitation_token=${encodeURIComponent(invitationToken)}${email ? `&email=${encodeURIComponent(email)}` : invitationEmail ? `&email=${encodeURIComponent(invitationEmail)}` : ''}` : '/login'}
              style={{ fontWeight: 700 }}
            >
              {t.auth.signIn}
            </Link>
          </div>

          <div style={{ marginTop: 24, paddingTop: 20, borderTop: '1px solid var(--rc-surface-3)', textAlign: 'center', fontSize: 12, color: 'var(--rc-muted)' }}>
            {t.auth.tagline}
          </div>
        </div>
      </div>

      <style>{`.login-left-panel { display: flex !important; } @media(max-width:780px){.login-left-panel{display:none!important}}`}</style>
    </div>
  );
}
