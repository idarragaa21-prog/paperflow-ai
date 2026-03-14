import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';

type Mode = 'login' | 'register';

export default function LoginPage() {
  const login = useAuthStore((s) => s.login);
  const loading = useAuthStore((s) => s.loading);
  const error = useAuthStore((s) => s.error);
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();

  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [regError, setRegError] = useState<string | null>(null);
  const [regOk, setRegOk] = useState(false);
  const [regBusy, setRegBusy] = useState(false);
  const [registrationClosed, setRegistrationClosed] = useState(false);

  useEffect(() => {
    if (user) navigate('/projects');
  }, [user, navigate]);

  async function onLogin(e: FormEvent) {
    e.preventDefault();
    await login(email, password);
  }

  async function onRegister(e: FormEvent) {
    e.preventDefault();
    setRegError(null);
    setRegBusy(true);
    try {
      await api.post('/auth/register', { email, password, full_name: fullName || undefined });
      setRegOk(true);
      // Auto-navigate — login was set via cookie
      setTimeout(() => navigate('/projects'), 800);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Error al registrarse.';
      if (err?.response?.status === 403) {
        setRegistrationClosed(true);
      }
      setRegError(detail);
    } finally {
      setRegBusy(false);
    }
  }

  return (
    <div style={{ maxWidth: 460, margin: '70px auto', padding: 16 }}>
      <div className="rc-card">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ fontWeight: 900, fontSize: 18, letterSpacing: '-0.02em' }}>PaperFlow AI</div>
          <div className="rc-help">
            {mode === 'login'
              ? 'Sign in to access projects, libraries, extraction workspaces and writing tools.'
              : 'Create your account to start using PaperFlow AI.'}
          </div>
        </div>

        <div style={{ height: 14 }} />

        {mode === 'login' ? (
          <form onSubmit={onLogin} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <div className="rc-kicker">Email</div>
              <input className="rc-input" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
            </div>
            <div>
              <div className="rc-kicker">Password</div>
              <input
                className="rc-input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
            <button className="rc-btn rc-btn--primary" disabled={loading} type="submit">
              {loading ? '…' : 'Login'}
            </button>
            {error ? <div className="rc-error" style={{ fontSize: 13 }}>{error}</div> : null}
          </form>
        ) : (
          <form onSubmit={onRegister} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {registrationClosed ? (
              <div className="rc-card" style={{ background: 'rgba(180,83,9,0.07)', border: '1px solid rgba(180,83,9,0.2)', padding: 12 }}>
                <div style={{ fontWeight: 700, color: 'var(--rc-warning)', marginBottom: 4 }}>Acceso por invitación</div>
                <div className="rc-help">
                  El registro público está cerrado. Contacta a{' '}
                  <a href="mailto:idarragaa21@gmail.com">idarragaa21@gmail.com</a> para solicitar acceso.
                </div>
              </div>
            ) : null}
            <div>
              <div className="rc-kicker">Nombre completo (opcional)</div>
              <input className="rc-input" value={fullName} onChange={(e) => setFullName(e.target.value)} autoComplete="name" />
            </div>
            <div>
              <div className="rc-kicker">Email</div>
              <input className="rc-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
            </div>
            <div>
              <div className="rc-kicker">Contraseña (mínimo 8 caracteres)</div>
              <input
                className="rc-input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
              />
            </div>
            {regOk ? (
              <div style={{ color: 'var(--rc-success)', fontWeight: 700 }}>✓ Cuenta creada. Redirigiendo…</div>
            ) : (
              <button className="rc-btn rc-btn--primary" disabled={regBusy} type="submit">
                {regBusy ? '…' : 'Crear cuenta'}
              </button>
            )}
            {regError && !registrationClosed ? <div className="rc-error" style={{ fontSize: 13 }}>{regError}</div> : null}
          </form>
        )}

        <div style={{ height: 14 }} />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="rc-help">created by <b>alejolo30</b></div>
          <button
            className="rc-btn rc-btn--ghost"
            style={{ fontSize: 12, padding: '4px 8px' }}
            onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setRegError(null); setRegistrationClosed(false); }}
          >
            {mode === 'login' ? '¿No tienes cuenta? Solicitar acceso' : '← Volver al login'}
          </button>
        </div>
      </div>
    </div>
  );
}
