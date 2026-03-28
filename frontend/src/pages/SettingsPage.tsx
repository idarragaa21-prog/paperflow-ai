import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { useToast } from '../ui/Toast/ToastProvider';
import { useI18n } from '../i18n';
import type { Locale } from '../i18n';
import { useTheme } from '../components/ThemeProvider';
import type {
  BillingUsageHistoryMonth,
  BillingUsageSummary,
  MembershipRole,
  Project,
  ProjectMember,
} from '../types/api';

type ServiceRow = {
  name: string;
  status: string;
  latency_ms: number;
  detail?: string;
};

type SettingsTab = 'general' | 'usage' | 'team';

const RUNTIME_MODES = [
  { value: 'local_only', label: 'Local only', desc: 'All processing with Ollama + Grobid + Qdrant on localhost. No external API calls.' },
  { value: 'hybrid', label: 'Hybrid', desc: 'Local pipeline with optional cloud fallback for extraction or summarization.' },
  { value: 'cloud', label: 'Cloud', desc: 'Cloud-based LLMs (requires API keys). Best quality but requires internet.' },
];

const TEAM_ROLE_OPTIONS: MembershipRole[] = ['owner', 'editor', 'viewer'];
const TEAM_ROLE_LABELS: Record<MembershipRole, string> = {
  owner: 'Owner',
  editor: 'Editor',
  viewer: 'Viewer',
};

const TAB_LABELS: Record<SettingsTab, string> = {
  general: 'General',
  usage: 'Uso & Facturación',
  team: 'Equipo',
};

const ROLE_BADGE_STYLES: Record<MembershipRole, CSSProperties> = {
  owner: { background: 'rgba(239,68,68,0.12)', color: 'rgb(185,28,28)', border: '1px solid rgba(239,68,68,0.18)' },
  editor: { background: 'rgba(59,130,246,0.12)', color: 'rgb(29,78,216)', border: '1px solid rgba(59,130,246,0.18)' },
  viewer: { background: 'rgba(16,185,129,0.12)', color: 'rgb(4,120,87)', border: '1px solid rgba(16,185,129,0.18)' },
};

function formatInteger(value: number | undefined): string {
  return Number(value || 0).toLocaleString();
}

function UsageBarChart({ months }: { months: BillingUsageHistoryMonth[] }) {
  const maxTokens = useMemo(() => Math.max(...months.map((month) => month.total_tokens), 1), [months]);

  if (months.length === 0) {
    return <div className="rc-muted">No monthly usage history yet.</div>;
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${months.length}, minmax(80px, 1fr))`, gap: 12, alignItems: 'end' }}>
      {months.map((month) => {
        const height = Math.max(18, Math.round((month.total_tokens / maxTokens) * 120));
        return (
          <div key={month.month} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div
              title={`${month.month}: ${formatInteger(month.total_tokens)} tokens`}
              style={{
                height,
                borderRadius: 14,
                background: 'linear-gradient(180deg, rgba(59,130,246,0.82) 0%, rgba(16,185,129,0.72) 100%)',
                boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.28)',
              }}
            />
            <div style={{ fontSize: 11, fontWeight: 700 }}>{month.month}</div>
            <div className="rc-help">{formatInteger(month.total_tokens)} tok</div>
          </div>
        );
      })}
    </div>
  );
}

export default function SettingsPage() {
  const toast = useToast();
  const user = useAuthStore((s) => s.user);
  const checkAuth = useAuthStore((s) => s.checkAuth);
  const { t, locale, setLocale, localeNames } = useI18n();
  const { theme, setTheme } = useTheme();

  const [activeTab, setActiveTab] = useState<SettingsTab>('general');

  const [fullName, setFullName] = useState(user?.full_name || '');
  const [savingProfile, setSavingProfile] = useState(false);

  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [savingPw, setSavingPw] = useState(false);

  const [services, setServices] = useState<ServiceRow[]>([]);
  const [loadingServices, setLoadingServices] = useState(false);
  const [runtimeMode, setRuntimeMode] = useState(() => localStorage.getItem('pf_runtime_mode') || 'local_only');

  const [billingSummary, setBillingSummary] = useState<BillingUsageSummary | null>(null);
  const [billingHistory, setBillingHistory] = useState<BillingUsageHistoryMonth[]>([]);
  const [loadingUsage, setLoadingUsage] = useState(false);

  const [ownedProjects, setOwnedProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [projectMembers, setProjectMembers] = useState<ProjectMember[]>([]);
  const [loadingTeam, setLoadingTeam] = useState(false);
  const [savingTeam, setSavingTeam] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<MembershipRole>('viewer');

  const [error, setError] = useState<string | null>(null);

  const selectedProject = ownedProjects.find((project) => project.id === selectedProjectId) || null;

  useEffect(() => {
    setFullName(user?.full_name || '');
  }, [user?.full_name]);

  async function saveProfile() {
    setSavingProfile(true);
    setError(null);
    try {
      await api.patch('/auth/me', { full_name: fullName });
      await checkAuth();
      toast.success('Saved', 'Profile updated.');
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Error saving profile');
    } finally {
      setSavingProfile(false);
    }
  }

  async function changePassword() {
    if (newPw !== confirmPw) {
      setError('Passwords do not match.');
      return;
    }
    if (newPw.length < 8) {
      setError('New password must be at least 8 characters.');
      return;
    }
    setSavingPw(true);
    setError(null);
    try {
      await api.post('/auth/change-password', { current_password: currentPw, new_password: newPw });
      toast.success('Updated', 'Password changed successfully.');
      setCurrentPw('');
      setNewPw('');
      setConfirmPw('');
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Error changing password');
    } finally {
      setSavingPw(false);
    }
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
    } catch {
      setServices([]);
    } finally {
      setLoadingServices(false);
    }
  }

  async function loadUsage() {
    setLoadingUsage(true);
    try {
      const [usageResponse, historyResponse] = await Promise.all([
        api.get('/billing/usage'),
        api.get('/billing/history', { params: { months: 6 } }),
      ]);
      setBillingSummary(usageResponse.data as BillingUsageSummary);
      setBillingHistory(((historyResponse.data as { months?: BillingUsageHistoryMonth[] })?.months || []).slice().reverse());
    } catch (e: any) {
      setBillingSummary(null);
      setBillingHistory([]);
      setError(e?.response?.data?.detail || 'Could not load usage information');
    } finally {
      setLoadingUsage(false);
    }
  }

  async function loadProjects() {
    try {
      const response = await api.get('/projects');
      const projects = (response.data as Project[]).filter((project) => !project.archived);
      setOwnedProjects(projects);
      setSelectedProjectId((current) => (current && projects.some((project) => project.id === current) ? current : projects[0]?.id || ''));
    } catch (e: any) {
      setOwnedProjects([]);
      setSelectedProjectId('');
      setError(e?.response?.data?.detail || 'Could not load projects');
    }
  }

  async function loadTeamMembers(projectId: string) {
    if (!projectId) {
      setProjectMembers([]);
      return;
    }
    setLoadingTeam(true);
    try {
      const response = await api.get(`/projects/${projectId}/members`);
      setProjectMembers(response.data as ProjectMember[]);
    } catch (e: any) {
      setProjectMembers([]);
      setError(e?.response?.data?.detail || 'Could not load project members');
    } finally {
      setLoadingTeam(false);
    }
  }

  useEffect(() => {
    void loadServices();
    void loadUsage();
    void loadProjects();
  }, []);

  useEffect(() => {
    void loadTeamMembers(selectedProjectId);
  }, [selectedProjectId]);

  function handleRuntimeChange(val: string) {
    setRuntimeMode(val);
    localStorage.setItem('pf_runtime_mode', val);
    toast.info('Runtime mode', `Set to "${val}" (local preference).`);
  }

  async function inviteMember() {
    const email = inviteEmail.trim().toLowerCase();
    if (!selectedProjectId || !email) return;
    if (!email.includes('@')) {
      setError('Enter a valid email.');
      return;
    }

    setSavingTeam(true);
    setError(null);
    try {
      await api.post(`/projects/${selectedProjectId}/members`, { email, role: inviteRole });
      setInviteEmail('');
      setInviteRole('viewer');
      toast.success('Member invited', `${email} now has ${TEAM_ROLE_LABELS[inviteRole]} access.`);
      await loadTeamMembers(selectedProjectId);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not invite member');
    } finally {
      setSavingTeam(false);
    }
  }

  async function updateMemberRole(member: ProjectMember, role: MembershipRole) {
    if (!selectedProjectId || role === member.role) return;
    setSavingTeam(true);
    setError(null);
    try {
      await api.patch(`/projects/${selectedProjectId}/members/${member.user_id}`, { role });
      toast.success('Role updated', `${member.email} is now ${TEAM_ROLE_LABELS[role]}.`);
      await loadTeamMembers(selectedProjectId);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not update member');
    } finally {
      setSavingTeam(false);
    }
  }

  async function removeMember(member: ProjectMember) {
    if (!selectedProjectId) return;
    setSavingTeam(true);
    setError(null);
    try {
      await api.delete(`/projects/${selectedProjectId}/members/${member.user_id}`);
      toast.info('Member removed', `${member.email} no longer has access.`);
      await loadTeamMembers(selectedProjectId);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not remove member');
    } finally {
      setSavingTeam(false);
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18, maxWidth: 920 }}>
      <div>
        <h1 className="rc-page-title">{t.settings.title}</h1>
        <div className="rc-subtitle">Manage your profile, usage and collaboration settings.</div>
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {(Object.keys(TAB_LABELS) as SettingsTab[]).map((tab) => (
          <button
            key={tab}
            className={`rc-btn${activeTab === tab ? ' rc-btn--primary' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {error ? <div className="rc-error">{error}</div> : null}

      {activeTab === 'general' && (
        <>
          <div className="rc-card" style={{ padding: 20 }}>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 750, fontSize: 15, marginBottom: 4 }}>{t.settings.language}</div>
            <div className="rc-help" style={{ marginBottom: 14 }}>{t.settings.languageDesc}</div>
            <div style={{ display: 'flex', gap: 8 }}>
              {(Object.keys(localeNames) as Locale[]).map((l) => (
                <button
                  key={l}
                  className={`rc-btn${locale === l ? ' rc-btn--primary' : ''}`}
                  style={{ padding: '7px 16px', fontSize: 13 }}
                  onClick={() => setLocale(l)}
                >
                  {localeNames[l]}
                </button>
              ))}
            </div>
          </div>

          <div className="rc-card" style={{ padding: 20 }}>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 750, fontSize: 15, marginBottom: 4 }}>Theme</div>
            <div className="rc-help" style={{ marginBottom: 14 }}>Choose your preferred appearance</div>
            <div style={{ display: 'flex', gap: 8 }}>
              {(['light', 'dark', 'system'] as const).map((mode) => (
                <button
                  key={mode}
                  className={`rc-btn${theme === mode ? ' rc-btn--primary' : ''}`}
                  style={{ padding: '7px 16px', fontSize: 13, textTransform: 'capitalize' }}
                  onClick={() => setTheme(mode)}
                >
                  {mode === 'light' ? '☀️ Light' : mode === 'dark' ? '🌙 Dark' : '💻 System'}
                </button>
              ))}
            </div>
          </div>

          <div className="rc-card">
            <div className="rc-card-title">Profile</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div>
                <div className="rc-kicker">Email</div>
                <input className="rc-input" value={user?.email || ''} readOnly style={{ opacity: 0.6 }} />
              </div>
              <div>
                <div className="rc-kicker">Full name</div>
                <input className="rc-input" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Your name" />
              </div>
              <button className="rc-btn rc-btn--primary" onClick={saveProfile} disabled={savingProfile} style={{ alignSelf: 'flex-start' }}>
                {savingProfile ? 'Saving…' : 'Save changes'}
              </button>
            </div>
          </div>

          <div className="rc-card">
            <div className="rc-card-title">Change password</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div>
                <div className="rc-kicker">Current password</div>
                <input className="rc-input" type="password" value={currentPw} onChange={(e) => setCurrentPw(e.target.value)} />
              </div>
              <div>
                <div className="rc-kicker">New password (min 8 chars)</div>
                <input className="rc-input" type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} />
              </div>
              <div>
                <div className="rc-kicker">Confirm new password</div>
                <input className="rc-input" type="password" value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)} />
              </div>
              <button className="rc-btn rc-btn--primary" onClick={changePassword} disabled={savingPw || !currentPw || !newPw} style={{ alignSelf: 'flex-start' }}>
                {savingPw ? 'Updating…' : 'Update password'}
              </button>
            </div>
          </div>

          <div className="rc-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <div className="rc-card-title" style={{ margin: 0 }}>LLM Services status</div>
              <button className="rc-btn" style={{ padding: '6px 12px', fontSize: 12 }} onClick={loadServices} disabled={loadingServices}>
                {loadingServices ? '…' : 'Refresh'}
              </button>
            </div>
            {services.length === 0 && !loadingServices ? (
              <div className="rc-muted">No service data. Click Refresh to check.</div>
            ) : null}
            {services.length > 0 ? (
              <table className="rc-table">
                <thead>
                  <tr>
                    <th>Service</th>
                    <th>Status</th>
                    <th>Latency</th>
                    <th>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {services.map((service) => (
                    <tr key={service.name}>
                      <td style={{ fontWeight: 700, textTransform: 'capitalize' }}>{service.name.replace(/_/g, ' ')}</td>
                      <td>
                        <span className={`rc-status-dot rc-status-dot--${service.status === 'ok' ? 'ready' : 'failed'}`}>
                          <span className="rc-status-dot__dot" />
                          {service.status}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'monospace', fontSize: 12 }}>
                        {service.latency_ms > 0 ? `${service.latency_ms} ms` : '—'}
                      </td>
                      <td className="rc-help">{service.detail || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : null}
          </div>

          <div className="rc-card">
            <div className="rc-card-title">Runtime mode</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {RUNTIME_MODES.map((mode) => (
                <label
                  key={mode.value}
                  style={{
                    display: 'flex',
                    gap: 10,
                    alignItems: 'flex-start',
                    cursor: 'pointer',
                    padding: '8px 10px',
                    borderRadius: 10,
                    background: runtimeMode === mode.value ? 'var(--rc-primary-weak)' : undefined,
                    border: runtimeMode === mode.value ? '1px solid rgba(79,70,229,0.2)' : '1px solid transparent',
                  }}
                >
                  <input type="radio" name="runtime" checked={runtimeMode === mode.value} onChange={() => handleRuntimeChange(mode.value)} style={{ marginTop: 3 }} />
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 13 }}>{mode.label}</div>
                    <div className="rc-help">{mode.desc}</div>
                  </div>
                </label>
              ))}
              <div className="rc-help" style={{ marginTop: 4 }}>
                This preference is saved in your browser (localStorage). It does not affect the backend default.
              </div>
            </div>
          </div>
        </>
      )}

      {activeTab === 'usage' && (
        <>
          <div className="rc-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div className="rc-card-title" style={{ margin: 0 }}>Uso del mes actual</div>
              <button className="rc-btn" onClick={loadUsage} disabled={loadingUsage}>
                {loadingUsage ? 'Refreshing…' : 'Refresh usage'}
              </button>
            </div>
            {!billingSummary && !loadingUsage ? (
              <div className="rc-muted">No billing activity yet.</div>
            ) : null}
            {billingSummary ? (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 12, marginBottom: 18 }}>
                  <div className="rc-card" style={{ padding: 16 }}>
                    <div className="rc-kicker">Monthly calls</div>
                    <div style={{ fontSize: 26, fontWeight: 800 }}>{formatInteger(billingSummary.calls_used)}</div>
                    <div className="rc-help">Remaining: {billingSummary.quota_calls === -1 ? 'Unlimited' : formatInteger(billingSummary.quota_remaining)}</div>
                  </div>
                  <div className="rc-card" style={{ padding: 16 }}>
                    <div className="rc-kicker">Input tokens</div>
                    <div style={{ fontSize: 26, fontWeight: 800 }}>{formatInteger(billingSummary.tokens_in)}</div>
                    <div className="rc-help">Output: {formatInteger(billingSummary.tokens_out)}</div>
                  </div>
                  <div className="rc-card" style={{ padding: 16 }}>
                    <div className="rc-kicker">Total tokens</div>
                    <div style={{ fontSize: 26, fontWeight: 800 }}>{formatInteger(billingSummary.total_tokens)}</div>
                    <div className="rc-help">Tier: {billingSummary.tier}</div>
                  </div>
                  <div className="rc-card" style={{ padding: 16 }}>
                    <div className="rc-kicker">Estimated cost</div>
                    <div style={{ fontSize: 26, fontWeight: 800 }}>${billingSummary.cost_usd.toFixed(4)}</div>
                    <div className="rc-help">Aggregated from tracked model calls</div>
                  </div>
                </div>

                <div className="rc-card" style={{ padding: 18, marginBottom: 18 }}>
                  <div className="rc-card-title" style={{ marginBottom: 10 }}>Últimos 6 meses</div>
                  <UsageBarChart months={billingHistory} />
                </div>

                <div className="rc-card" style={{ padding: 18, marginBottom: 18 }}>
                  <div className="rc-card-title" style={{ marginBottom: 10 }}>Modelos usados este mes</div>
                  {billingSummary.models.length === 0 ? (
                    <div className="rc-muted">No model usage captured yet.</div>
                  ) : (
                    <table className="rc-table">
                      <thead>
                        <tr>
                          <th>Model</th>
                          <th>Calls</th>
                          <th>Input</th>
                          <th>Output</th>
                          <th>Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {billingSummary.models.map((item) => (
                          <tr key={item.model}>
                            <td style={{ fontWeight: 700 }}>{item.model}</td>
                            <td>{formatInteger(item.calls)}</td>
                            <td>{formatInteger(item.tokens_in)}</td>
                            <td>{formatInteger(item.tokens_out)}</td>
                            <td>{formatInteger(item.total_tokens)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>

                <div className="rc-card" style={{ padding: 18 }}>
                  <div className="rc-card-title" style={{ marginBottom: 10 }}>Actividad reciente</div>
                  {billingSummary.recent.length === 0 ? (
                    <div className="rc-muted">No recent tracked calls.</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {billingSummary.recent.map((item, index) => (
                        <div key={`${item.at || 'usage'}-${index}`} className="rc-product-record rc-product-record--soft">
                          <div className="rc-product-record__header">
                            <div style={{ fontWeight: 800 }}>{item.models.map((model) => model.model).join(', ') || 'Unknown model'}</div>
                            <div className="rc-help">{item.at ? new Date(item.at).toLocaleString() : 'No timestamp'}</div>
                          </div>
                          <div className="rc-help" style={{ marginTop: 8 }}>
                            {formatInteger(item.tokens_in)} in · {formatInteger(item.tokens_out)} out · {formatInteger(item.total_tokens)} total · ${item.cost_usd.toFixed(4)}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            ) : null}
          </div>
        </>
      )}

      {activeTab === 'team' && (
        <>
          <div className="rc-card">
            <div className="rc-card-title">Team management</div>
            <div className="rc-help" style={{ marginBottom: 14 }}>
              Invite collaborators to your projects by email and manage roles without leaving Settings.
            </div>

            <label className="rc-discover-filter-field">
              <span>Project</span>
              <select className="rc-input" value={selectedProjectId} onChange={(e) => setSelectedProjectId(e.target.value)}>
                {ownedProjects.length === 0 ? <option value="">No owned projects available</option> : null}
                {ownedProjects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.title}
                  </option>
                ))}
              </select>
            </label>

            {selectedProject ? (
              <div className="rc-help" style={{ marginTop: 10 }}>
                Managing access for <b>{selectedProject.title}</b>.
              </div>
            ) : null}
          </div>

          <div className="rc-product-two-column">
            <section className="rc-product-card">
              <div className="rc-product-card__header">
                <div>
                  <div className="rc-card-title">Invite member</div>
                  <div className="rc-help">The invite resolves against an existing PaperFlow account by email.</div>
                </div>
              </div>

              <div className="rc-product-form-grid rc-product-form-grid--three">
                <label className="rc-discover-filter-field" style={{ gridColumn: 'span 2' }}>
                  <span>Email</span>
                  <input
                    className="rc-input"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="researcher@example.com"
                  />
                </label>
                <label className="rc-discover-filter-field">
                  <span>Role</span>
                  <select className="rc-input" value={inviteRole} onChange={(e) => setInviteRole(e.target.value as MembershipRole)}>
                    {TEAM_ROLE_OPTIONS.map((role) => (
                      <option key={role} value={role}>
                        {TEAM_ROLE_LABELS[role]}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <button className="rc-btn rc-btn--primary" onClick={inviteMember} disabled={savingTeam || !selectedProjectId || !inviteEmail.trim()}>
                {savingTeam ? 'Saving…' : 'Invite member'}
              </button>
            </section>

            <section className="rc-product-card">
              <div className="rc-product-card__header">
                <div>
                  <div className="rc-card-title">Role policy</div>
                  <div className="rc-help">Owners manage access, editors work on content, viewers can inspect the project.</div>
                </div>
              </div>
              <div className="rc-product-record-list">
                {TEAM_ROLE_OPTIONS.map((role) => (
                  <div key={role} className="rc-product-study-panel">
                    <div style={{ fontWeight: 800 }}>{TEAM_ROLE_LABELS[role]}</div>
                    <div className="rc-help" style={{ marginTop: 6 }}>
                      {role === 'owner'
                        ? 'Can invite, change roles and remove other members.'
                        : role === 'editor'
                          ? 'Can work across project modules and contribute actively.'
                          : 'Read-only access for review, follow-up or stakeholder visibility.'}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <section className="rc-product-card">
            <div className="rc-product-card__header">
              <div>
                <div className="rc-card-title">Project members</div>
                <div className="rc-help">Owners appear first, followed by editors and viewers.</div>
              </div>
              <div className="rc-discover-badge">{projectMembers.length} members</div>
            </div>

            {loadingTeam ? <div className="rc-muted">Loading members…</div> : null}
            {!loadingTeam && selectedProjectId && projectMembers.length === 0 ? <div className="rc-empty-state">This project has no collaborators yet.</div> : null}
            {!selectedProjectId ? <div className="rc-empty-state">Select a project to manage its team.</div> : null}

            {projectMembers.map((member) => (
              <div key={`${member.user_id}-${member.role}`} className="rc-product-record rc-product-record--soft">
                <div className="rc-product-record__header">
                  <div>
                    <div style={{ fontWeight: 800 }}>{member.full_name || member.email}</div>
                    <div className="rc-help">{member.email}</div>
                  </div>
                  <span className="rc-discover-badge" style={ROLE_BADGE_STYLES[member.role]}>
                    {TEAM_ROLE_LABELS[member.role]}
                  </span>
                </div>
                <div className="rc-product-actions" style={{ marginTop: 12 }}>
                  <select
                    className="rc-input"
                    value={member.role}
                    onChange={(e) => updateMemberRole(member, e.target.value as MembershipRole)}
                    disabled={savingTeam || member.role === 'owner'}
                  >
                    {TEAM_ROLE_OPTIONS.map((role) => (
                      <option key={role} value={role}>
                        {TEAM_ROLE_LABELS[role]}
                      </option>
                    ))}
                  </select>
                  <button
                    className="rc-btn"
                    onClick={() => removeMember(member)}
                    disabled={savingTeam || member.role === 'owner'}
                  >
                    Remove
                  </button>
                  {member.role === 'owner' ? <span className="rc-help">Primary owners cannot be removed from Settings.</span> : null}
                </div>
              </div>
            ))}
          </section>
        </>
      )}
    </div>
  );
}
