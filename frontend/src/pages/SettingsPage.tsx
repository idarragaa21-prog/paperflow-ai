import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { useToast } from '../ui/Toast/ToastProvider';
import { useI18n } from '../i18n';
import type { Locale } from '../i18n';

type ServiceRow = {
  name: string;
  status: string;
  latency_ms: number;
  detail?: string;
};

const RUNTIME_MODES = [
  { value: 'local_only', label: 'Local only', desc: 'All processing with Ollama + Grobid + Qdrant on localhost. No external API calls.' },
  { value: 'hybrid', label: 'Hybrid', desc: 'Local pipeline with optional cloud fallback for extraction or summarization.' },
  { value: 'cloud', label: 'Cloud', desc: 'Cloud-based LLMs (requires API keys). Best quality but requires internet.' },
];

export default function SettingsPage() {
  const toast = useToast();
  const user = useAuthStore(s => s.user);
  const checkAuth = useAuthStore(s => s.checkAuth);
  const { t, locale, setLocale, localeNames } = useI18n();

  // Profile
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [savingProfile, setSavingProfile] = useState(false);

  // Password
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [savingPw, setSavingPw] = useState(false);

  // Services
  const [services, setServices] = useState<ServiceRow[]>([]);
  const [loadingServices, setLoadingServices] = useState(false);

  // Runtime
  const [runtimeMode, setRuntimeMode] = useState(() => localStorage.getItem('pf_runtime_mode') || 'local_only');

  const [error, setError] = useState<string | null>(null);

  useEffect(() => { setFullName(user?.full_name || ''); }, [user?.full_name]);

  async function saveProfile() {
    setSavingProfile(true); setError(null);
    try {
      await api.patch('/auth/me', { full_name: fullName });
      await checkAuth();
      toast.success('Saved', 'Profile updated.');
    } catch (e: any) { setError(e?.response?.data?.detail || 'Error saving profile'); }
    finally { setSavingProfile(false); }
  }

  async function changePassword() {
    if (newPw !== confirmPw) { setError('Passwords do not match.'); return; }
    if (newPw.length < 8) { setError('New password must be at least 8 characters.'); return; }
    setSavingPw(true); setError(null);
    try {
      await api.post('/auth/change-password', { current_password: currentPw, new_password: newPw });
      toast.success('Updated', 'Password changed successfully.');
      setCurrentPw(''); setNewPw(''); setConfirmPw('');
    } catch (e: any) { setError(e?.response?.data?.detail || 'Error changing password'); }
    finally { setSavingPw(false); }
  }

  async function loadServices() {
    setLoadingServices(true);
    try {
      const r = await api.get('/health/services');
      const svc = (r.data as any)?.services || {};
      setServices(Object.entries(svc).map(([name, val]: [string, any]) => ({
        name,
        status: val.status || 'unknown',
        latency_ms: val.latency_ms || 0,
        detail: val.detail,
      })));
    } catch { setServices([]); }
    finally { setLoadingServices(false); }
  }

  useEffect(() => { loadServices(); }, []);

  function handleRuntimeChange(val: string) {
    setRuntimeMode(val);
    localStorage.setItem('pf_runtime_mode', val);
    toast.info('Runtime mode', `Set to "${val}" (local preference).`);
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18, maxWidth: 680 }}>
      <div>
        <h1 className="rc-page-title">{t.settings.title}</h1>
        <div className="rc-subtitle">Manage your profile, security and service configuration.</div>
      </div>

      {error && <div className="rc-error">{error}</div>}

      {/* Language */}
      <div className="rc-card" style={{ padding: 20 }}>
        <div style={{ fontFamily: 'var(--font-display)', fontWeight: 750, fontSize: 15, marginBottom: 4 }}>{t.settings.language}</div>
        <div className="rc-help" style={{ marginBottom: 14 }}>{t.settings.languageDesc}</div>
        <div style={{ display: 'flex', gap: 8 }}>
          {(Object.keys(localeNames) as Locale[]).map(l => (
            <button key={l} className={`rc-btn${locale === l ? ' rc-btn--primary' : ''}`}
              style={{ padding: '7px 16px', fontSize: 13 }}
              onClick={() => setLocale(l)}>
              {localeNames[l]}
            </button>
          ))}
        </div>
      </div>

      {/* Profile */}
      <div className="rc-card">
        <div className="rc-card-title">Profile</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div>
            <div className="rc-kicker">Email</div>
            <input className="rc-input" value={user?.email || ''} readOnly style={{ opacity: 0.6 }} />
          </div>
          <div>
            <div className="rc-kicker">Full name</div>
            <input className="rc-input" value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Your name" />
          </div>
          <button className="rc-btn rc-btn--primary" onClick={saveProfile} disabled={savingProfile} style={{ alignSelf: 'flex-start' }}>
            {savingProfile ? 'Saving\u2026' : 'Save changes'}
          </button>
        </div>
      </div>

      {/* Change password */}
      <div className="rc-card">
        <div className="rc-card-title">Change password</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div>
            <div className="rc-kicker">Current password</div>
            <input className="rc-input" type="password" value={currentPw} onChange={e => setCurrentPw(e.target.value)} />
          </div>
          <div>
            <div className="rc-kicker">New password (min 8 chars)</div>
            <input className="rc-input" type="password" value={newPw} onChange={e => setNewPw(e.target.value)} />
          </div>
          <div>
            <div className="rc-kicker">Confirm new password</div>
            <input className="rc-input" type="password" value={confirmPw} onChange={e => setConfirmPw(e.target.value)} />
          </div>
          <button className="rc-btn rc-btn--primary" onClick={changePassword} disabled={savingPw || !currentPw || !newPw} style={{ alignSelf: 'flex-start' }}>
            {savingPw ? 'Updating\u2026' : 'Update password'}
          </button>
        </div>
      </div>

      {/* LLM Services status */}
      <div className="rc-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div className="rc-card-title" style={{ margin: 0 }}>LLM Services status</div>
          <button className="rc-btn" style={{ padding: '6px 12px', fontSize: 12 }} onClick={loadServices} disabled={loadingServices}>
            {loadingServices ? '\u2026' : 'Refresh'}
          </button>
        </div>
        {services.length === 0 && !loadingServices && <div className="rc-muted">No services data.</div>}
        {services.length > 0 && (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--rc-border)', textAlign: 'left' }}>
                <th style={{ padding: '6px 8px' }}>Service</th>
                <th style={{ padding: '6px 8px', width: 90 }}>Status</th>
                <th style={{ padding: '6px 8px', width: 90 }}>Latency</th>
              </tr>
            </thead>
            <tbody>
              {services.map(s => (
                <tr key={s.name} style={{ borderBottom: '1px solid var(--rc-border)' }}>
                  <td style={{ padding: '6px 8px', fontWeight: 700, textTransform: 'capitalize' }}>{s.name}</td>
                  <td style={{ padding: '6px 8px' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', background: s.status === 'ok' ? '#16a34a' : '#b91c1c' }} />
                      {s.status}
                    </span>
                  </td>
                  <td style={{ padding: '6px 8px', fontFamily: 'monospace', fontSize: 12 }}>{s.latency_ms} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Runtime mode */}
      <div className="rc-card">
        <div className="rc-card-title">Runtime mode</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {RUNTIME_MODES.map(m => (
            <label key={m.value} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', cursor: 'pointer', padding: '8px 10px', borderRadius: 10, background: runtimeMode === m.value ? 'var(--rc-primary-weak)' : undefined, border: runtimeMode === m.value ? '1px solid rgba(79,70,229,0.2)' : '1px solid transparent' }}>
              <input type="radio" name="runtime" checked={runtimeMode === m.value} onChange={() => handleRuntimeChange(m.value)} style={{ marginTop: 3 }} />
              <div>
                <div style={{ fontWeight: 700, fontSize: 13 }}>{m.label}</div>
                <div className="rc-help">{m.desc}</div>
              </div>
            </label>
          ))}
          <div className="rc-help" style={{ marginTop: 4 }}>This preference is saved in your browser (localStorage). It does not affect the backend default.</div>
        </div>
      </div>
    </div>
  );
}
