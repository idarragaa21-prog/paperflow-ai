import { useEffect, useMemo, useState } from 'react';
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
    void load();
  }, []);

  const latestProject = useMemo(() => projects[0] || null, [projects]);

  return (
    <div className="rc-section-shell">
      <div className="rc-hero-card">
        <div style={{ maxWidth: 760 }}>
          <div className="rc-pill">Projects</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>Projects</h1>
          <div className="rc-subtitle">
            One home for literature search, PDF reading, evidence extraction, drafting and reproducible analysis.
          </div>
          <div className="rc-help" style={{ marginTop: 12, maxWidth: 640 }}>
            Start a new research workspace or jump back into the one you were using. PaperFlow is organized around the work you want to complete, not around disconnected tools.
          </div>
        </div>
        <div className="rc-kpi-strip" style={{ minWidth: 320 }}>
          <div className="rc-hero-stat">
            <strong>{projects.length}</strong>
            <span>Active projects</span>
          </div>
          <div className="rc-hero-stat">
            <strong>{latestProject ? 'Ready' : 'Start'}</strong>
            <span>{latestProject ? 'Latest workspace available' : 'Create your first workspace'}</span>
          </div>
        </div>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <div className="rc-shelf">
        <div className="rc-card">
          <div className="rc-card-title">Start a new research workspace</div>
          <div className="rc-help" style={{ marginBottom: 12 }}>
            Give the project a specific working title so search, extraction and writing stay focused around the same question.
          </div>
          <div className="rc-row" style={{ alignItems: 'flex-end' }}>
            <div style={{ minWidth: 280, flex: 1 }}>
              <div className="rc-kicker">Project title</div>
              <input
                data-testid="project-title-input"
                className="rc-input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Rotator cuff repair outcomes in older adults"
              />
            </div>
            <button data-testid="project-create-button" className="rc-btn rc-btn--primary" onClick={create} disabled={!title.trim()}>
              Create project
            </button>
          </div>
          <div className="rc-help" style={{ marginTop: 10 }}>
            Tip: good titles mention the population, intervention or outcome you care about.
          </div>
        </div>

        <div className="rc-card">
          <div className="rc-card-title">How PaperFlow works</div>
          <div className="rc-guided-grid" style={{ gridTemplateColumns: '1fr' }}>
            <div className="rc-flow-card">
              <div className="rc-stage-label rc-stage-label--teal">Step 1</div>
              <h3>Find the right papers</h3>
              <p>Search across major scholarly sources and save the evidence that matters to your question.</p>
            </div>
            <div className="rc-flow-card">
              <div className="rc-stage-label rc-stage-label--warm">Step 2</div>
              <h3>Read, extract and compare</h3>
              <p>Ask grounded questions, extract structured study data and review evidence in one workspace.</p>
            </div>
            <div className="rc-flow-card">
              <div className="rc-stage-label rc-stage-label--teal">Step 3</div>
              <h3>Write and analyze</h3>
              <p>Build drafts with citations and run reproducible analyses without breaking context.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="rc-card">
        <div className="rc-toolbar">
          <div>
            <div className="rc-card-title" style={{ marginBottom: 4 }}>Recent workspaces</div>
            <div className="rc-help">Pick up where you left off or open a project directly into its research workflow.</div>
          </div>
          <button className="rc-btn" onClick={() => void load()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {projects.length === 0 ? (
        <div className="rc-empty-state">
          <div style={{ fontWeight: 800, marginBottom: 6 }}>No projects yet</div>
          <div className="rc-help">Create your first project above and PaperFlow will open a full research workspace around it.</div>
        </div>
      ) : (
        <div className="rc-guided-grid">
          {projects.map((project, index) => (
            <div
              data-testid={`project-card-${project.id}`}
              key={project.id}
              className="rc-flow-card"
              onClick={() => navigate(`/projects/${project.id}/research`)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  navigate(`/projects/${project.id}/research`);
                }
              }}
              role="button"
              tabIndex={0}
              style={{ cursor: 'pointer' }}
            >
              <div className="rc-detail-header">
                <span className={`rc-stage-label ${index === 0 ? 'rc-stage-label--teal' : 'rc-stage-label--warm'}`}>
                  {index === 0 ? 'Continue' : 'Workspace'}
                </span>
                {project.archived ? <span className="rc-badge">Archived</span> : <span className="rc-badge rc-badge--success">Active</span>}
              </div>
              <h3>{project.title}</h3>
              <p>
                {project.description ||
                  project.clinical_area ||
                  'Open the workspace to search, read, extract, write and analyze from the same project context.'}
              </p>
              <Link
                data-testid={`project-open-${project.id}`}
                to={`/projects/${project.id}/research`}
                className="rc-flow-link"
                onClick={(e) => e.stopPropagation()}
              >
                Open workspace
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
