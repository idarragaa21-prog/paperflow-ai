import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useI18n } from '../i18n';

export default function LoginPage() {
  const login = useAuthStore((s) => s.login);
  const loading = useAuthStore((s) => s.loading);
  const error = useAuthStore((s) => s.error);
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { t, locale } = useI18n();
  const L = (o: Record<string, string>) => o[locale] || o.es;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const invitationToken = searchParams.get('invitation_token');
  const invitationEmail = searchParams.get('email');
  const invitedAfterSignup = searchParams.get('invited') === '1';
  const acceptedProjectId = searchParams.get('accepted_project_id');
  const hasInvitationContext = Boolean(invitationToken || invitedAfterSignup || acceptedProjectId);

  useEffect(() => {
    if (invitationEmail && !email) setEmail(invitationEmail);
  }, [email, invitationEmail]);

  useEffect(() => {
    if (!user) return;
    if (acceptedProjectId) {
      navigate(`/projects/${acceptedProjectId}/research`, { replace: true });
      return;
    }
    if (invitationToken) {
      navigate(`/project-invitations/${invitationToken}`, { replace: true });
      return;
    }
    navigate('/dashboard');
  }, [acceptedProjectId, user, invitationToken, navigate]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await login(email, password);
  }

  return (
    <div style={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)' }}>
      {/* Left side — brand / value */}
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
          <h2 className="pg-h1" style={{ color: '#fff', fontSize: 40 }}>
            {L({
              es: 'Tu espacio de investigación privado.',
              en: 'Your private research workspace.',
              pt: 'Seu espaço de pesquisa privado.',
            })}
          </h2>
          <p style={{ marginTop: 14, color: 'rgba(255,255,255,0.72)', fontSize: 16, lineHeight: 1.6 }}>
            {L({
              es: 'Busca, lee, extrae, meta-analiza y escribe con IA local. Sin nube por defecto.',
              en: 'Search, read, extract, meta-analyze and write with local AI. No cloud by default.',
              pt: 'Pesquise, leia, extraia, meta-analise e escreva com IA local. Sem nuvem por padrão.',
            })}
          </p>
          <ul style={{ marginTop: 28, padding: 0, listStyle: 'none', display: 'grid', gap: 12 }}>
            {[
              L({ es: 'Búsqueda PubMed con síntesis IA', en: 'PubMed search with AI synthesis', pt: 'Busca PubMed com síntese IA' }),
              L({ es: 'Matrix de extracción versionada', en: 'Versioned extraction matrix', pt: 'Matriz de extração versionada' }),
              L({ es: 'Meta-análisis con R · DOCX/PDF', en: 'Meta-analysis with R · DOCX/PDF', pt: 'Meta-análise com R · DOCX/PDF' }),
            ].map((it) => (
              <li key={it} style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'rgba(255,255,255,0.88)', fontSize: 14 }}>
                <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="4 10 8 14 16 6" />
                </svg>
                {it}
              </li>
            ))}
          </ul>
        </div>

        <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>
          © {new Date().getFullYear()} PaperFlow · local-first
        </div>
      </aside>

      {/* Right side — form */}
      <main style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '56px 32px', background: '#fff' }}>
        <div style={{ width: '100%', maxWidth: 420 }}>
          <h1 className="pg-h1">
            {L({ es: 'Iniciar sesión', en: 'Sign in', pt: 'Entrar' })}
          </h1>
          <p className="pg-muted" style={{ marginTop: 6, fontSize: 15 }}>
            {L({
              es: 'Accede a tu workspace local para continuar.',
              en: 'Access your local workspace to continue.',
              pt: 'Acesse seu workspace local para continuar.',
            })}
          </p>

          <form onSubmit={onSubmit} style={{ marginTop: 28, display: 'grid', gap: 16 }}>
            {hasInvitationContext ? (
              <div className="pg-card pg-card--soft" style={{ padding: 14, fontSize: 13, color: 'var(--pg-navy-700)' }}>
                {invitedAfterSignup
                  ? acceptedProjectId
                    ? L({ es: 'Cuenta creada. Inicia sesión para abrir tu proyecto compartido.', en: 'Account created. Sign in to open your shared project.', pt: 'Conta criada. Entre para abrir seu projeto compartilhado.' })
                    : L({ es: 'Cuenta creada. Inicia sesión para aceptar la invitación.', en: 'Account created. Sign in to accept the invitation.', pt: 'Conta criada. Entre para aceitar o convite.' })
                  : L({ es: 'Inicia sesión con el email invitado para aceptar.', en: 'Sign in with the invited email to accept.', pt: 'Entre com o email convidado para aceitar.' })}
              </div>
            ) : null}

            <div>
              <label className="pg-label" htmlFor="login-email">Email</label>
              <input
                id="login-email"
                type="email"
                className="pg-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="tu@correo.com"
                autoComplete="email"
                autoFocus
                required
              />
            </div>

            <div>
              <div className="pg-row-between" style={{ marginBottom: 6 }}>
                <label className="pg-label" htmlFor="login-password" style={{ marginBottom: 0 }}>
                  {L({ es: 'Contraseña', en: 'Password', pt: 'Senha' })}
                </label>
                <Link to="/forgot-password" style={{ fontSize: 13, color: 'var(--pg-navy-700)', fontWeight: 500, textDecoration: 'none' }}>
                  {L({ es: '¿La olvidaste?', en: 'Forgot?', pt: 'Esqueceu?' })}
                </Link>
              </div>
              <div style={{ position: 'relative' }}>
                <input
                  id="login-password"
                  type={showPw ? 'text' : 'password'}
                  className="pg-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                  style={{ paddingRight: 44 }}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  aria-label={showPw ? 'Ocultar' : 'Mostrar'}
                  style={{
                    position: 'absolute',
                    right: 10,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--pg-soft)',
                    cursor: 'pointer',
                    padding: 6,
                    display: 'inline-flex',
                  }}
                >
                  {showPw ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                      <path d="M17.94 17.94A10 10 0 0 1 12 20c-7 0-11-8-11-8a18 18 0 0 1 5.06-5.94M9.9 4.24A9 9 0 0 1 12 4c7 0 11 8 11 8a18 18 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {error && (
              <div style={{ padding: '10px 12px', borderRadius: 10, background: '#FEF2F2', border: '1px solid #FECACA', color: '#B91C1C', fontSize: 13 }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              className="pg-btn pg-btn--primary pg-btn--lg"
              disabled={loading || !email || !password}
              style={{ width: '100%', justifyContent: 'center' }}
            >
              {loading ? t.auth.signingIn : L({ es: 'Entrar', en: 'Sign in', pt: 'Entrar' })}
            </button>
          </form>

          <div style={{ marginTop: 24, textAlign: 'center', fontSize: 14, color: 'var(--pg-muted)' }}>
            {t.auth.noAccount}{' '}
            <Link
              to={invitationToken ? `/signup?invitation_token=${encodeURIComponent(invitationToken)}${invitationEmail ? `&email=${encodeURIComponent(invitationEmail)}` : ''}` : '/signup'}
              style={{ fontWeight: 600, color: 'var(--pg-navy-800)', textDecoration: 'none' }}
            >
              {t.auth.signUp}
            </Link>
          </div>

          <div className="pg-divider" style={{ margin: '32px 0 16px' }} />
          <p style={{ fontSize: 12, color: 'var(--pg-soft)', textAlign: 'center', margin: 0 }}>
            {L({ es: 'Demo: demo@paperflow.ai / demo1234', en: 'Demo: demo@paperflow.ai / demo1234', pt: 'Demo: demo@paperflow.ai / demo1234' })}
          </p>
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
