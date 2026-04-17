import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { DEMO_MODE, demoProjects, demoCounts } from '../services/demo';
import type { Project, ProjectCounts } from '../types/api';
import {
  getProjectNextAction,
  getWorkflowCompletion,
  getWorkflowStages,
  InsightCard,
} from '../components/WorkflowPrimitives';

function StatCard({ label, value, color, icon }: { label: string; value: number; color: string; icon: React.ReactNode }) {
  return (
    <div className="rc-card rc-card--hover" style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '24px' }}>
      <div style={{ width: 48, height: 48, borderRadius: '12px', background: color, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        {icon}
      </div>
      <div>
        <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.03em', fontFamily: 'var(--font-display)', lineHeight: 1, color: 'var(--rc-text)' }}>{value}</div>
        <div style={{ fontSize: 13, color: 'var(--rc-text-secondary)', marginTop: 4, fontWeight: 500 }}>{label}</div>
      </div>
    </div>
  );
}

function NewProjectModal({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
  const [title, setTitle] = useState('');
  const [area, setArea] = useState('');
  const qc = useQueryClient();

  const createMut = useMutation({
    mutationFn: async () => {
      const r = await api.post('/projects', { title: title.trim(), clinical_area: area.trim() || null });
      return r.data as { id: string };
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['dashboard-projects'] });
      onCreated(data.id);
    },
  });

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20, zIndex: 50 }}
      onClick={onClose}
    >
      <div className="rc-card" style={{ width: 'min(480px, 96vw)', display: 'flex', flexDirection: 'column', gap: 14 }} onClick={e => e.stopPropagation()}>
        <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 18 }}>New project</div>

        <div>
          <div className="rc-kicker">Project title *</div>
          <input
            className="rc-input"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="e.g. ACL Reconstruction Outcomes"
            autoFocus
            onKeyDown={e => { if (e.key === 'Enter' && title.trim()) createMut.mutate(); }}
          />
        </div>
        <div>
          <div className="rc-kicker">Clinical area (optional)</div>
          <input
            className="rc-input"
            value={area}
            onChange={e => setArea(e.target.value)}
            placeholder="e.g. Orthopedic Surgery"
          />
        </div>

        {createMut.error && (
          <div className="rc-error">
            {(createMut.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Create failed'}
          </div>
        )}

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button className="rc-btn rc-btn--ghost" onClick={onClose}>Cancel</button>
          <button
            className="rc-btn rc-btn--primary"
            disabled={!title.trim() || createMut.isPending}
            onClick={() => createMut.mutate()}
          >
            {createMut.isPending ? 'Creating…' : 'Create project'}
          </button>
        </div>
      </div>
    </div>
  );
}

const QUICK_ACCESS = [
  {
    label: 'Clinical Consults',
    sub: 'Grounded quick answers',
    to: '/clinical',
    color: 'var(--rc-success-weak, rgba(16,185,129,0.1))',
    stroke: 'var(--rc-success)',
    icon: (
      <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="var(--rc-success)" strokeWidth="1.8" strokeLinecap="round">
        <path d="M10 2v4M8 4h4"/><rect x="3" y="6" width="14" height="12" rx="2"/><path d="M7 10h6M7 13h4"/>
      </svg>
    ),
  },
  {
    label: 'Deep Research',
    sub: 'Comprehensive reports',
    to: '/deep-research',
    color: 'var(--rc-primary-weak, rgba(99,102,241,0.1))',
    stroke: 'var(--rc-primary)',
    icon: (
      <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="var(--rc-primary)" strokeWidth="1.8" strokeLinecap="round">
        <circle cx="9" cy="8" r="5"/><path d="M14 13l3 3"/><path d="M6 8h6"/>
      </svg>
    ),
  },
  {
    label: 'Background Jobs',
    sub: 'Processing & downloads',
    to: '/jobs',
    color: 'var(--rc-warning-weak, rgba(245,158,11,0.1))',
    stroke: 'var(--rc-warning)',
    icon: (
      <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="var(--rc-warning)" strokeWidth="1.8" strokeLinecap="round">
        <circle cx="10" cy="10" r="7"/><path d="M10 6v4l2.5 2.5"/>
      </svg>
    ),
  },
];

export default function DashboardPage() {
  const user = useAuthStore(s => s.user);
  const navigate = useNavigate();
  const [showNewProject, setShowNewProject] = useState(false);

  const firstName = (user?.full_name || user?.email || 'Researcher').split(/[\s@]/)[0];
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

  const { data: projects = [], isLoading } = useQuery<Project[]>({
    queryKey: ['dashboard-projects'],
    queryFn: async () => {
      if (DEMO_MODE) return demoProjects as Project[];
      const r = await api.get('/projects');
      return r.data as Project[];
    },
    staleTime: 60_000,
  });

  const active = projects.filter(p => !p.archived);

  const { data: countsMap = {} } = useQuery<Record<string, ProjectCounts>>({
    queryKey: ['dashboard-counts', active.map(p => p.id).join(',')],
    queryFn: async () => {
      if (DEMO_MODE) return demoCounts as Record<string, ProjectCounts>;
      const entries = await Promise.allSettled(
        active.slice(0, 6).map(p =>
          api.get(`/projects/${p.id}/dashboard`).then(r => [p.id, r.data.counts] as [string, ProjectCounts])
        )
      );
      const map: Record<string, ProjectCounts> = {};
      entries.forEach(e => { if (e.status === 'fulfilled') map[e.value[0]] = e.value[1]; });
      return map;
    },
    enabled: active.length > 0,
    staleTime: 60_000,
  });

  const totalPapers = Object.values(countsMap).reduce((s, c) => s + c.papers, 0);
  const totalRefs = Object.values(countsMap).reduce((s, c) => s + c.references, 0);
  const totalNotes = Object.values(countsMap).reduce((s, c) => s + c.notes, 0);
  const averageCompletion = active.length
    ? Math.round(active.reduce((sum, project) => sum + getWorkflowCompletion(countsMap[project.id]), 0) / active.length)
    : 0;
  const spotlightProject = active[0] ?? null;
  const spotlightCounts = spotlightProject ? countsMap[spotlightProject.id] : undefined;
  const spotlightCompletion = spotlightProject ? getWorkflowCompletion(spotlightCounts) : 0;
  const spotlightNextAction = spotlightProject ? getProjectNextAction(spotlightProject.id, spotlightCounts) : null;
  const spotlightStages = spotlightProject ? getWorkflowStages(spotlightProject.id, spotlightCounts).slice(0, 6) : [];

  return (
    <div className="rc-page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {showNewProject && (
        <NewProjectModal
          onClose={() => setShowNewProject(false)}
          onCreated={(id) => { setShowNewProject(false); navigate(`/projects/${id}/research`); }}
        />
      )}

      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <div className="pg-kicker" style={{ marginBottom: 6 }}>{`${greeting}, ${firstName}`}</div>
          <h1 className="pg-h1" style={{ margin: 0 }}>
            {active.length === 0 ? 'Empieza tu primer proyecto' : '¿Qué vamos a mover hoy?'}
          </h1>
          <p className="pg-muted" style={{ marginTop: 6, maxWidth: 640, fontSize: 14 }}>
            {active.length === 0
              ? 'Un proyecto organiza tu pregunta, tu biblioteca, la matriz de extracción, los meta-análisis y la escritura final.'
              : `${active.length} proyectos activos · ${totalPapers} papers · ${totalRefs} referencias · ${averageCompletion}% avance promedio`}
          </p>
        </div>
        <div className="pg-row">
          <button onClick={() => setShowNewProject(true)} className="pg-btn pg-btn--primary">
            + Nuevo proyecto
          </button>
          <Link to="/projects" className="pg-btn">Ver todos</Link>
          <Link to="/deep-research" className="pg-btn">Deep Research</Link>
        </div>
      </header>

      {DEMO_MODE && (
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 12, padding: '6px 12px', fontSize: 12, color: 'rgba(245,158,11,0.92)', alignSelf: 'flex-start' }}>
          <span>⚡</span> Demo mode — UI preview with mock data
        </div>
      )}

      {!isLoading && spotlightProject && spotlightNextAction && (
        <section className="rc-spotlight">
          <div className="rc-spotlight__main">
            <div className="rc-spotlight__eyebrow">Project spotlight</div>
            <h2 className="rc-spotlight__title">{spotlightProject.title}</h2>
            <p className="rc-spotlight__subtitle">
              {spotlightProject.clinical_area
                ? `${spotlightProject.clinical_area} · `
                : ''}
              This project is the clearest place to continue momentum right now. Keep the workflow moving from research to extraction, then into writing and analysis.
            </p>
            <div className="rc-spotlight__meta">
              <div className="rc-spotlight__meta-item">
                <span className="rc-spotlight__meta-value">{spotlightCompletion}%</span>
                <span className="rc-spotlight__meta-label">Workflow complete</span>
              </div>
              <div className="rc-spotlight__meta-item">
                <span className="rc-spotlight__meta-value">{spotlightCounts?.papers ?? 0}</span>
                <span className="rc-spotlight__meta-label">Papers in scope</span>
              </div>
              <div className="rc-spotlight__meta-item">
                <span className="rc-spotlight__meta-value">{spotlightCounts?.meta_studies_current ?? 0}</span>
                <span className="rc-spotlight__meta-label">Studies extracted</span>
              </div>
              <div className="rc-spotlight__meta-item">
                <span className="rc-spotlight__meta-value">{spotlightCounts?.references ?? 0}</span>
                <span className="rc-spotlight__meta-label">References ready</span>
              </div>
            </div>
            <div className="rc-progress rc-progress--md">
              <div style={{ width: `${spotlightCompletion}%` }} />
            </div>
            <div className="rc-spotlight__actions">
              <Link to={spotlightNextAction.to} className="rc-btn rc-btn--primary" style={{ textDecoration: 'none' }}>
                {spotlightNextAction.label}
              </Link>
              <Link to={`/projects/${spotlightProject.id}/research`} className="rc-btn" style={{ textDecoration: 'none' }}>
                Open project workflow
              </Link>
            </div>
          </div>

          <div className="rc-spotlight__side">
            <InsightCard
              eyebrow="Next best action"
              title={spotlightNextAction.label}
              body={spotlightNextAction.description}
              tone="primary"
            />
            <div className="rc-stage-inline-list">
              {spotlightStages.map((stage) => (
                <div key={stage.key} className="rc-stage-inline-item">
                  <div className="rc-stage-inline-item__copy">
                    <span className="rc-stage-inline-item__title">{stage.label}</span>
                    <span className="rc-stage-inline-item__desc">{stage.description}</span>
                  </div>
                  <span className="rc-stage-inline-item__metric">{stage.metricValue}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Stats */}
      {!isLoading && active.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(175px,1fr))', gap: 12 }}>
          <StatCard label="Active projects" value={active.length} color="var(--rc-primary-weak, rgba(99,102,241,0.12))"
            icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--rc-primary)" strokeWidth="2" strokeLinecap="round"><rect x="2" y="3" width="8" height="8" rx="1.5"/><rect x="14" y="3" width="8" height="8" rx="1.5"/><rect x="2" y="13" width="8" height="8" rx="1.5"/><rect x="14" y="13" width="8" height="8" rx="1.5"/></svg>} />
          <StatCard label="Total papers" value={totalPapers} color="var(--rc-success-weak, rgba(16,185,129,0.12))"
            icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--rc-success)" strokeWidth="2" strokeLinecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>} />
          <StatCard label="References" value={totalRefs} color="var(--rc-warning-weak, rgba(245,158,11,0.12))"
            icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--rc-warning)" strokeWidth="2" strokeLinecap="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>} />
          <StatCard label="Notes" value={totalNotes} color="rgba(139,92,246,0.12)"
            icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="rgba(139,92,246,0.9)" strokeWidth="2" strokeLinecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>} />
        </div>
      )}

      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, gap: 12, flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, letterSpacing: '-0.03em' }}>Continue your projects</div>
            <div className="rc-help">Each card now acts like a workflow checkpoint, not just a shortcut.</div>
          </div>
          <Link to="/projects" style={{ fontSize: 12, color: 'var(--rc-primary)', textDecoration: 'none' }}>View all →</Link>
        </div>
        {isLoading ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))', gap: 12 }}>
            {[1, 2, 3].map(i => <div key={i} className="rc-card rc-skeleton" style={{ height: 110 }} />)}
          </div>
        ) : active.length === 0 ? (
          <div className="rc-card" style={{ textAlign: 'center', padding: '40px 24px' }}>
            <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 8, fontFamily: 'var(--font-display)' }}>No projects yet</div>
            <div className="rc-help" style={{ marginBottom: 18 }}>
              Projects are the core of PaperFlow — organize papers, run searches, extract data, build matrix versions and generate grounded clinical consults.
            </div>
            <button
              className="rc-btn rc-btn--primary"
              onClick={() => setShowNewProject(true)}
            >
              Create your first project
            </button>
          </div>
        ) : (
          <div className="rc-list-stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(320px,1fr))', gap: 14 }}>
            {active.slice(0, 6).map(p => {
              const c = countsMap[p.id];
              const nextAction = getProjectNextAction(p.id, c);
              const completion = getWorkflowCompletion(c);
              return (
                <div
                  key={p.id}
                  className="rc-card rc-card--hover"
                  style={{ display: 'flex', flexDirection: 'column', gap: 12 }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0 }}>
                      <Link to={`/projects/${p.id}/research`} style={{ fontWeight: 750, fontSize: 16, letterSpacing: '-0.03em', fontFamily: 'var(--font-display)', lineHeight: 1.2, textDecoration: 'none', color: 'inherit' }}>
                        {p.title}
                      </Link>
                      <div className="rc-help">{completion}% workflow complete</div>
                    </div>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--rc-muted)" strokeWidth="2" strokeLinecap="round" style={{ flexShrink: 0, marginTop: 2 }}><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                  </div>
                  {p.clinical_area && <div className="rc-help">{p.clinical_area}</div>}
                  <div className="rc-progress"><div style={{ width: `${completion}%` }} /></div>
                  {c && (
                    <div style={{ display: 'flex', gap: 14, marginTop: 'auto', paddingTop: 10, borderTop: '1px solid var(--rc-border)', flexWrap: 'wrap' }}>
                      {([['Papers', c.papers, 'var(--rc-primary)'], ['Refs', c.references, 'var(--rc-warning)'], ['Notes', c.notes, '#7c3aed']] as [string, number, string][]).map(([l, v, col]) => (
                        <div key={l} style={{ fontSize: 12 }}>
                          <span style={{ fontWeight: 750, color: col }}>{v}</span>
                          <span style={{ color: 'var(--rc-muted)', marginLeft: 3 }}>{l}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  <div style={{ borderRadius: 14, border: '1px solid rgba(67,56,202,0.12)', background: 'var(--rc-primary-weak)', padding: '12px 14px' }}>
                    <div className="rc-kicker" style={{ marginBottom: 4 }}>Next best action</div>
                    <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>{nextAction.label}</div>
                    <div className="rc-help" style={{ color: 'var(--rc-text-secondary)' }}>{nextAction.description}</div>
                  </div>
                  <div className="rc-row" style={{ justifyContent: 'space-between', marginTop: 'auto', paddingTop: 4 }}>
                    <Link to={nextAction.to} className="rc-btn rc-btn--primary rc-btn--sm" style={{ textDecoration: 'none' }}>
                      Continue
                    </Link>
                    <Link to={`/projects/${p.id}/research`} className="rc-btn rc-btn--sm" style={{ textDecoration: 'none' }}>
                      Open workflow
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div>
        <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, letterSpacing: '-0.02em', marginBottom: 12 }}>Specialized surfaces</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(190px,1fr))', gap: 10 }}>
          {QUICK_ACCESS.map(item => (
            <Link key={item.to} to={item.to} style={{ textDecoration: 'none' }}>
              <div className="rc-card rc-card--hover" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 38, height: 38, borderRadius: 10, background: item.color, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {item.icon}
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>{item.label}</div>
                  <div className="rc-help">{item.sub}</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
