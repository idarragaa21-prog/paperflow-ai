import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../services/api';

type Project = {
  id: string;
  title: string;
  description?: string | null;
  clinical_area?: string | null;
  archived: boolean;
};

export default function ProjectsPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
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

  async function create() {
    if (!title.trim()) return;
    setError(null);
    try {
      await api.post('/projects', { title: title.trim() });
      setTitle('');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to create project');
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div className="rc-hero-card">
        <div>
          <div className="rc-pill">Projects</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>Research workspaces</h1>
          <div className="rc-subtitle" style={{ maxWidth: 720 }}>
            Organize literature search, library curation, extraction, writing, analysis and screening by project.
          </div>
        </div>
        <div className="rc-row">
          <div className="rc-hero-stat">
            <strong>{projects.length}</strong>
            <span>active workspaces</span>
          </div>
          <button className="rc-btn" onClick={load} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <div className="rc-card" style={{ padding: 18 }}>
        <div className="rc-card-title">Create project</div>
        <div className="rc-row" style={{ alignItems: 'flex-end' }}>
            <div style={{ minWidth: 280, flex: 1 }}>
              <div className="rc-kicker">Title</div>
            <input data-testid="project-title-input" className="rc-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Distal radius fracture outcomes in older adults" />
          </div>
          <button data-testid="project-create-button" className="rc-btn rc-btn--primary" onClick={create} disabled={!title.trim()}>
            Create
          </button>
        </div>
        <div className="rc-help" style={{ marginTop: 8 }}>
          Tip: keep titles specific enough to guide search, extraction and writing.
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 12 }}>
        {projects.length === 0 ? <div className="rc-muted">No projects yet.</div> : null}
        {projects.map((p) => (
          <div
            data-testid={`project-card-${p.id}`}
            key={p.id}
            className="rc-card"
            onClick={() => navigate(`/projects/${p.id}/research`)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                navigate(`/projects/${p.id}/research`);
              }
            }}
            role="button"
            tabIndex={0}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              gap: 12,
              alignItems: 'center',
              cursor: 'pointer',
              minHeight: 170,
            }}
          >
            <div style={{ flex: 1 }}>
              <div className="rc-pill rc-pill--soft" style={{ marginBottom: 12 }}>{p.archived ? 'Archived' : 'Ready'}</div>
              <div style={{ fontWeight: 850, letterSpacing: '-0.02em' }}>
                {p.title}
              </div>
              {p.clinical_area ? <div className="rc-help">{p.clinical_area}</div> : null}
              {p.description ? <div className="rc-help" style={{ marginTop: 8 }}>{p.description}</div> : null}
              <div className="rc-help" style={{ marginTop: 12 }}>Open research, reader, library, extraction, writing and analysis workspace.</div>
            </div>
            <div className="rc-row">
              <Link
                data-testid={`project-open-${p.id}`}
                to={`/projects/${p.id}/research`}
                className="rc-btn rc-btn--primary"
                onClick={(e) => e.stopPropagation()}
              >
                Open Workspace
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
