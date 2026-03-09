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
          <div className="rc-pill">RC interno</div>
          <h1 className="rc-auth-title">PaperFlow AI</h1>
          <p className="rc-auth-copy">
            Un espacio de investigacion local-first para busqueda bibliografica, extraccion de evidencia, chat con PDFs,
            redaccion, analisis y screening.
          </p>

          <div className="rc-auth-stats">
            <div className="rc-hero-stat">
              <strong>500</strong>
              <span>papers sembrados</span>
            </div>
            <div className="rc-hero-stat">
              <strong>RAG</strong>
              <span>respuestas con evidencia</span>
            </div>
            <div className="rc-hero-stat">
              <strong>R</strong>
              <span>reportes exportados</span>
            </div>
          </div>

          <div className="rc-card" style={{ padding: 16 }}>
            <div className="rc-card-title">Cuentas demo</div>
            <div className="rc-row">
              <button type="button" className="rc-btn" onClick={() => useDemoAccount('rc-owner@paperflow.dev')}>
                Cargar dueno demo
              </button>
              <button type="button" className="rc-btn" onClick={() => useDemoAccount('rc-reviewer@paperflow.dev')}>
                Cargar revisor demo
              </button>
            </div>
            <div className="rc-help" style={{ marginTop: 10 }}>
              Clave para ambos: <b>paperflow-e2e-123</b>
            </div>
          </div>
        </section>

        <section className="rc-auth-panel">
          <div className="rc-card rc-auth-card">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div className="rc-pill rc-pill--soft">Entrar</div>
              <div style={{ fontWeight: 900, fontSize: 26, letterSpacing: '-0.03em' }}>Abre tu espacio de trabajo</div>
              <div className="rc-help">Proyectos, biblioteca, lector, extraccion, escritura y analisis en un solo lugar.</div>
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
                <div className="rc-kicker">Contrasena</div>
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
                {loading ? 'Entrando…' : 'Entrar a PaperFlow'}
              </button>

              {error ? <div className="rc-error" style={{ fontSize: 13 }}>{error}</div> : null}
            </form>

            <div style={{ height: 14 }} />
            <div className="rc-help">Si esta pantalla se queda cargando, la verificacion de sesion ahora falla rapido en vez de quedarse colgada.</div>
          </div>
        </section>
      </div>
    </div>
  );
}
