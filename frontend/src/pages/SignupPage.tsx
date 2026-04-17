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
  const { t, locale } = useI18n();
  const L = (o: Record<string, string>) => o[locale] || o.es;

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
    if (invitationEmail && !email) setEmail(invitationEmail);
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
      if (invitationToken) payload.invitation_token = invitationToken;
      const response = await api.post('/auth/register', payload);
      const acceptedProjectId = (response.data as { accepted_project_id?: string | null } | undefined)?.accepted_project_id;
      navigate(
        invitationToken
          ? `/login?email=${encodeURIComponent(email)}&invited=1${acceptedProjectId ? `&accepted_project_id=${encodeURIComponent(acceptedProjectId)}` : `&invitation_token=${encodeURIComponent(invitationToken)}`}`
          : '/login'
      );
    } catch (e) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || 'Registration failed');
    } finally { setLoading(false); }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)' }}>
      <aside
        className="pg-login-side"
        style={{
          background: 'linear-gradient(160deg, var(--pg-navy-900) 0%, var(--pg-navy-700) 100%)',
          color: '#fff',
          padding: '56px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}
      >
        <Link to="/" className="pg-brand" style={{ color: '#fff', textDecoration: 'none' }}>
          <span className="pg-brand-mark" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
            </svg>
          </span>
          PaperFlow
        </Link>

        <div style={{ maxWidth: 440 }}>
          <h2 className="pg-h1" style={{ color: '#fff', fontSize: 36 }}>
            {L({
              es: 'Crea tu cuenta local en 10 segundos.',
              en: 'Create your local account in 10 seconds.',
              pt: 'Crie sua conta local em 10 segundos.',
            })}
          </h2>
          <p style={{ marginTop: 14, color: 'rgba(255,255,255,0.72)', fontSize: 15, lineHeight: 1.6 }}>
            {L({
              es: 'No necesitas email verificado. No hay sincronización con la nube. Eres tú y tus papers.',
              en: 'No email verification. No cloud sync. Just you and your papers.',
              pt: 'Sem verificação de email. Sem sincronização na nuvem. Só você e seus papers.',
            })}
          </p>
        </div>

        <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>
          © {new Date().getFullYear()} PaperFlow · local-first
        </div>
      </aside>

      <main style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '56px 32px', background: '#fff' }}>
        <div style={{ width: '100%', maxWidth: 420 }}>
          <h1 className="pg-h1">{t.auth.createAccountTitle}</h1>
          <p className="pg-muted" style={{ marginTop: 6, fontSize: 15 }}>{t.auth.createAccountSubtitle}</p>

          <form onSubmit={onSubmit} style={{ marginTop: 28, display: 'grid', gap: 16 }}>
            {invitationToken ? (
              <div className="pg-card pg-card--soft" style={{ padding: 14, fontSize: 13, color: 'var(--pg-navy-700)' }}>
                {L({
                  es: 'Crea una cuenta con el email invitado para unirte al proyecto compartido.',
                  en: 'Create an account with the invited email to join the shared project.',
                  pt: 'Crie uma conta com o email convidado para participar do projeto compartilhado.',
                })}
              </div>
            ) : null}

            <div>
              <label className="pg-label" htmlFor="signup-fullname">{t.auth.fullName}</label>
              <input id="signup-fullname" className="pg-input" type="text" value={fullName}
                onChange={(e) => setFullName(e.target.value)} placeholder={t.auth.fullNamePlaceholder} autoComplete="name" />
            </div>

            <div>
              <label className="pg-label" htmlFor="signup-email">{t.auth.email}</label>
              <input id="signup-email" className="pg-input" type="email" value={email}
                onChange={(e) => setEmail(e.target.value)} placeholder={t.auth.emailPlaceholder} autoComplete="email" autoFocus required />
            </div>

            <div>
              <label className="pg-label" htmlFor="signup-password">{t.auth.password}</label>
              <input id="signup-password" className="pg-input" type="password" value={password}
                onChange={(e) => setPassword(e.target.value)} placeholder={t.auth.passwordPlaceholder} autoComplete="new-password" required />
            </div>

            <div>
              <label className="pg-label" htmlFor="signup-confirm-password">{t.auth.confirmPassword}</label>
              <input id="signup-confirm-password" className="pg-input" type="password" value={confirmPw}
                onChange={(e) => setConfirmPw(e.target.value)} placeholder={t.auth.passwordPlaceholder} autoComplete="new-password" required />
            </div>

            {error && (
              <div style={{ padding: '10px 12px', borderRadius: 10, background: '#FEF2F2', border: '1px solid #FECACA', color: '#B91C1C', fontSize: 13 }}>
                {error}
              </div>
            )}

            <button type="submit" className="pg-btn pg-btn--primary pg-btn--lg"
              disabled={loading || !email || !password}
              style={{ width: '100%', justifyContent: 'center' }}>
              {loading ? t.auth.creatingAccount : t.auth.signUp}
            </button>
          </form>

          <div style={{ marginTop: 24, textAlign: 'center', fontSize: 14, color: 'var(--pg-muted)' }}>
            {t.auth.hasAccount}{' '}
            <Link
              to={invitationToken
                ? `/login?invitation_token=${encodeURIComponent(invitationToken)}${email ? `&email=${encodeURIComponent(email)}` : invitationEmail ? `&email=${encodeURIComponent(invitationEmail)}` : ''}`
                : '/login'}
              style={{ fontWeight: 600, color: 'var(--pg-navy-800)', textDecoration: 'none' }}
            >
              {t.auth.signIn}
            </Link>
          </div>

          <div className="pg-divider" style={{ margin: '28px 0 12px' }} />
          <p style={{ fontSize: 12, color: 'var(--pg-soft)', textAlign: 'center', margin: 0 }}>{t.auth.tagline}</p>
        </div>
      </main>

      <style>{`
        @media (max-width: 960px) {
          .pg-login-side { display: none !important; }
          body > #root > div[style*="grid-template-columns"] { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}
