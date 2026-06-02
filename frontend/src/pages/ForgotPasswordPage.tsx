import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { useI18n } from '../i18n';

export default function ForgotPasswordPage() {
  const { t } = useI18n();
  const [step, setStep] = useState<'email' | 'code' | 'done'>('email');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [newPw, setNewPw] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function sendCode(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.post('/auth/forgot-password', { email });
      setStep('code');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error');
    } finally { setLoading(false); }
  }

  async function resetPassword(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (newPw.length < 8) { setError(t.auth.passwordMinLength); return; }
    setLoading(true);
    try {
      await api.post('/auth/reset-password', { email, code, new_password: newPw });
      setStep('done');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error');
    } finally { setLoading(false); }
  }

  if (step === 'done') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--rc-bg)', padding: 32 }}>
        <div style={{ maxWidth: 400, textAlign: 'center' }}>
          <div style={{ width: 64, height: 64, borderRadius: 20, margin: '0 auto 20px',
            background: 'var(--rc-success-bg)', border: '1px solid var(--rc-success-border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28 }}>✓</div>
          <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 20, marginBottom: 8 }}>
            {t.auth.passwordReset}
          </div>
          <Link to="/login" className="rc-btn rc-btn--primary" style={{ textDecoration: 'none', marginTop: 16, display: 'inline-block' }}>
            {t.auth.signIn} →
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--rc-bg)', padding: 32 }}>
      <div style={{ width: '100%', maxWidth: 400 }}>
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 26, fontWeight: 850, letterSpacing: '-0.03em', color: 'var(--rc-text)', fontFamily: 'var(--font-display)' }}>
            {t.auth.resetPassword}
          </div>
          <div style={{ marginTop: 6, fontSize: 14, color: 'var(--rc-muted)' }}>
            {step === 'email' ? t.auth.resetSubtitle : t.auth.codeSent}
          </div>
        </div>

        {step === 'email' && (
          <form onSubmit={sendCode} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <label htmlFor="forgot-email" className="rc-kicker" style={{ display: 'block' }}>{t.auth.email}</label>
              <input id="forgot-email" className="rc-input" type="email" value={email} onChange={e => setEmail(e.target.value)}
                placeholder={t.auth.emailPlaceholder} autoFocus required style={{ fontSize: 14 }} />
            </div>
            {error && <div style={{ padding: '10px 14px', borderRadius: 10, background: 'rgba(185,28,28,0.08)', border: '1px solid rgba(185,28,28,0.18)', color: '#b91c1c', fontSize: 13 }}>{error}</div>}
            <button type="submit" className="rc-btn rc-btn--primary" disabled={loading || !email}
              style={{ width: '100%', padding: '11px 16px', fontSize: 14, borderRadius: 12 }}>
              {loading ? t.auth.sendingCode : t.auth.sendCode}
            </button>
          </form>
        )}

        {step === 'code' && (
          <form onSubmit={resetPassword} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <label htmlFor="reset-code" className="rc-kicker" style={{ display: 'block' }}>{t.auth.resetCode}</label>
              <input id="reset-code" className="rc-input" type="text" value={code} onChange={e => setCode(e.target.value)}
                placeholder={t.auth.resetCodePlaceholder} autoFocus required maxLength={6}
                style={{ fontSize: 20, letterSpacing: '0.3em', textAlign: 'center', fontWeight: 700 }} />
            </div>
            <div>
              <label htmlFor="new-password" className="rc-kicker" style={{ display: 'block' }}>{t.auth.newPassword}</label>
              <input id="new-password" className="rc-input" type="password" value={newPw} onChange={e => setNewPw(e.target.value)}
                placeholder={t.auth.passwordPlaceholder} required style={{ fontSize: 14 }} />
            </div>
            {error && <div style={{ padding: '10px 14px', borderRadius: 10, background: 'rgba(185,28,28,0.08)', border: '1px solid rgba(185,28,28,0.18)', color: '#b91c1c', fontSize: 13 }}>{error}</div>}
            <button type="submit" className="rc-btn rc-btn--primary" disabled={loading || !code || !newPw}
              style={{ width: '100%', padding: '11px 16px', fontSize: 14, borderRadius: 12 }}>
              {loading ? t.auth.resetting : t.auth.resetNow}
            </button>
          </form>
        )}

        <div style={{ marginTop: 24, textAlign: 'center' }}>
          <Link to="/login" style={{ fontSize: 13, color: 'var(--rc-primary)' }}>{t.auth.backToLogin}</Link>
        </div>
      </div>
    </div>
  );
}
