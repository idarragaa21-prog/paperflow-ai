import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';

type Project = {
  id: string;
  title: string;
  description?: string | null;
  clinical_area?: string | null;
  archived: boolean;
};

export default function ProjectsPage() {
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
      <div>
        <h1 className="rc-page-title">Projects</h1>
        <div className="rc-subtitle">Organize literature searches, project libraries, extraction workspaces and scientific writing by project.</div>
      </div>

      <div className="rc-row">
        <button className="rc-btn" onClick={load} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <div className="rc-card">
        <div className="rc-card-title">Create project</div>
        <div className="rc-row">
            <div style={{ minWidth: 280, flex: 1 }}>
              <div className="rc-kicker">Title</div>
            <input className="rc-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Distal radius fracture outcomes in older adults" />
          </div>
          <button className="rc-btn rc-btn--primary" onClick={create} disabled={!title.trim()}>
            Create
          </button>
        </div>
        <div className="rc-help" style={{ marginTop: 8 }}>
          Tip: keep titles specific enough to guide search, extraction and writing.
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {projects.length === 0 ? <div className="rc-muted">No projects yet.</div> : null}
        {projects.map((p) => (
          <div key={p.id} className="rc-card" style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 850, letterSpacing: '-0.02em' }}>
                {p.title}{' '}
                {p.archived ? <span className="rc-badge">archived</span> : null}
              </div>
              {p.clinical_area ? <div className="rc-help">{p.clinical_area}</div> : null}
              {p.description ? <div className="rc-help">{p.description}</div> : null}
            </div>
            <div className="rc-row">
              <Link to={`/projects/${p.id}/research`}>Open</Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
