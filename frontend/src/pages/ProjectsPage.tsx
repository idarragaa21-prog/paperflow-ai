import { FileText, FlaskConical, Microscope, Plus, Search, Shield, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';

type Project = {
  id: string; title: string; description?: string | null;
  clinical_area?: string | null; archived: boolean;
};

function CreateModal({ onClose, onCreate }: {
  onClose: () => void;
  onCreate: (t: string, a: string) => Promise<void>;
}) {
  const [title, setTitle] = useState('');
  const [area, setArea]   = useState('');
  const [busy, setBusy]   = useState(false);

  async function submit() {
    if (!title.trim()) return;
    setBusy(true);
    await onCreate(title.trim(), area.trim());
    setBusy(false);
    onClose();
  }

  return (
    <div className="rc-overlay" onClick={onClose}>
      <div className="rc-modal" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 800, letterSpacing: '-0.02em' }}>New project</h2>
          <button className="rc-btn rc-btn--ghost" style={{ padding: 6 }} onClick={onClose}>
            <X size={15} />
          </button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <div className="rc-kicker">Title *</div>
            <input
              className="rc-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. ACL reconstruction outcomes systematic review"
              onKeyDown={(e) => e.key === 'Enter' && submit()}
              autoFocus
            />
          </div>
          <div>
            <div className="rc-kicker">Clinical area (optional)</div>
            <input
              className="rc-input"
              value={area}
              onChange={(e) => setArea(e.target.value)}
              placeholder="e.g. Orthopedic surgery"
            />
          </div>
          <div className="rc-row" style={{ justifyContent: 'flex-end', gap: 8 }}>
            <button className="rc-btn" onClick={onClose}>Cancel</button>
            <button className="rc-btn rc-btn--primary" disabled={!title.trim() || busy} onClick={submit}>
              {busy ? 'Creating…' : 'Create project →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function WelcomeScreen({ onCreate }: { onCreate: (t: string, a: string) => Promise<void> }) {
  const [showModal, setShowModal] = useState(false);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28, padding: '60px 20px', maxWidth: 560, margin: '0 auto' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ marginBottom: 16 }}>
          <Microscope size={52} style={{ color: 'var(--rc-primary)', opacity: 0.35 }} />
        </div>
        <h1 style={{ margin: '0 0 10px', fontWeight: 900, fontSize: 26, letterSpacing: '-0.03em' }}>
          Welcome to PaperFlow
        </h1>
        <p style={{ margin: 0, color: 'var(--rc-text-secondary)', fontSize: 15, lineHeight: 1.6 }}>
          Your scientific research workspace. Search literature, extract data, and write papers — faster.
        </p>
      </div>

      <button className="rc-btn rc-btn--primary" style={{ padding: '11px 24px', fontSize: 14 }} onClick={() => setShowModal(true)}>
        <Plus size={15} /> Create your first project
      </button>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 10, width: '100%' }}>
        {[
          { icon: <Search size={15} />,       label: 'Federated PubMed search',  sub: 'EuropePMC · DOAJ · deduplication' },
          { icon: <FlaskConical size={15} />, label: 'Meta-analysis extraction', sub: 'ROB · effect sizes · Excel export' },
          { icon: <FileText size={15} />,     label: 'AI writing studio',        sub: 'Grounded drafts with citations' },
          { icon: <Shield size={15} />,       label: '100% local & private',     sub: 'Your data never leaves your machine' },
        ].map(({ icon, label, sub }) => (
          <div key={label} style={{
            background: 'var(--rc-surface-1)',
            border: '1px solid var(--rc-border)',
            borderRadius: 'var(--rc-radius-md)',
            padding: '12px 14px',
            display: 'flex', gap: 10, alignItems: 'flex-start',
          }}>
            <span style={{ color: 'var(--rc-primary)', marginTop: 1 }}>{icon}</span>
            <div>
              <div style={{ fontSize: 13, fontWeight: 650, color: 'var(--rc-text)' }}>{label}</div>
              <div style={{ fontSize: 11, color: 'var(--rc-text-tertiary)', marginTop: 2 }}>{sub}</div>
            </div>
          </div>
        ))}
      </div>

      {showModal && <CreateModal onClose={() => setShowModal(false)} onCreate={onCreate} />}
    </div>
  );
}

export default function ProjectsPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);

  async function load() {
    setError(null);
    try {
      const r = await api.get('/projects');
      setProjects(r.data as Project[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  }

  async function createProject(title: string, area: string) {
    await api.post('/projects', { title, clinical_area: area || undefined });
    await load();
  }

  useEffect(() => { load(); }, []);

  if (loading) return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {[1,2,3].map(i => (
        <div key={i} className="rc-skeleton" style={{ height: 88, borderRadius: 14 }} />
      ))}
    </div>
  );

  if (!loading && projects.length === 0 && !error) return <WelcomeScreen onCreate={createProject} />;

  const active   = projects.filter(p => !p.archived);
  const archived = projects.filter(p => p.archived);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h1 className="rc-page-title">Projects</h1>
            <span className="rc-tag rc-tag--slate">{projects.length}</span>
          </div>
          <div className="rc-subtitle">Research workspaces with search, extraction and writing.</div>
        </div>
        <button className="rc-btn rc-btn--primary" onClick={() => setShowModal(true)}>
          <Plus size={14} /> New project
        </button>
      </div>

      {error && <div className="rc-error">{error}</div>}

      {/* Active projects grid */}
      {active.length > 0 && (
        <div className="rc-projects-grid">
          {active.map((p) => (
            <div
              key={p.id}
              className="rc-project-card"
              onClick={() => navigate(`/projects/${p.id}/research`)}
            >
              <div className="rc-project-card-title">{p.title}</div>
              {p.clinical_area && <span className="rc-tag rc-tag--indigo" style={{ width: 'fit-content' }}>{p.clinical_area}</span>}
              {p.description && <div className="rc-help" style={{ lineHeight: 1.5 }}>{p.description}</div>}
              <div className="rc-project-card-footer">
                <span className="rc-help">Click to open</span>
                <span style={{ fontSize: 12, fontWeight: 650, color: 'var(--rc-primary)' }}>Open →</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Archived */}
      {archived.length > 0 && (
        <div>
          <div className="rc-section-header">
            <span className="rc-section-title" style={{ color: 'var(--rc-text-tertiary)', fontSize: 12 }}>
              ARCHIVED ({archived.length})
            </span>
          </div>
          <div className="rc-projects-grid">
            {archived.map((p) => (
              <div key={p.id} className="rc-project-card" style={{ opacity: 0.6 }}
                onClick={() => navigate(`/projects/${p.id}/research`)}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <div className="rc-project-card-title">{p.title}</div>
                  <span className="rc-tag rc-tag--slate">archived</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {showModal && <CreateModal onClose={() => setShowModal(false)} onCreate={createProject} />}
    </div>
  );
}
