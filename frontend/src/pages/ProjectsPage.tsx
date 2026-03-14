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

function WelcomeScreen({ onCreate }: { onCreate: (title: string, area: string) => Promise<void> }) {
  const [title, setTitle] = useState('');
  const [area, setArea] = useState('');
  const [busy, setBusy] = useState(false);

  async function handleCreate() {
    if (!title.trim()) return;
    setBusy(true);
    await onCreate(title.trim(), area.trim());
    setBusy(false);
  }

  return (
    <div style={{ maxWidth: 600, margin: '40px auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ textAlign: 'center' }}>
        <h1 style={{ fontWeight: 900, fontSize: 26, letterSpacing: '-0.03em', margin: 0 }}>
          Bienvenido a PaperFlow
        </h1>
        <p style={{ marginTop: 10, color: 'rgba(15,23,42,0.65)', fontSize: 15 }}>
          Tu espacio de investigación científica. Empieza creando tu primer proyecto.
        </p>
      </div>

      <div className="rc-card" style={{ padding: 20 }}>
        <div className="rc-card-title">Crea tu primer proyecto</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div>
            <div className="rc-kicker">Título del proyecto</div>
            <input
              className="rc-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="ej. Osteotomía tibial alta — retorno al deporte"
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              autoFocus
            />
          </div>
          <div>
            <div className="rc-kicker">Área clínica (opcional)</div>
            <input
              className="rc-input"
              value={area}
              onChange={(e) => setArea(e.target.value)}
              placeholder="ej. Cirugía ortopédica"
            />
          </div>
          <button
            className="rc-btn rc-btn--primary"
            disabled={!title.trim() || busy}
            onClick={handleCreate}
            style={{ marginTop: 4 }}
          >
            {busy ? 'Creando…' : 'Crear proyecto →'}
          </button>
        </div>
      </div>

      <div className="rc-row" style={{ justifyContent: 'center', gap: 10 }}>
        {['Búsqueda federada PubMed', 'Extracción meta-análisis', 'Generación de drafts'].map((chip) => (
          <span key={chip} className="rc-badge rc-badge--info" style={{ fontSize: 13 }}>
            {chip}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  async function createProject(t: string, area?: string) {
    setError(null);
    try {
      await api.post('/projects', { title: t, clinical_area: area || undefined });
      setTitle('');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to create project');
    }
  }

  useEffect(() => { load(); }, []);

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: 'rgba(15,23,42,0.45)' }}>
        Cargando proyectos…
      </div>
    );
  }

  if (projects.length === 0 && !error) {
    return <WelcomeScreen onCreate={createProject} />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Projects</h1>
        <div className="rc-subtitle">Organize literature searches, libraries, extraction workspaces and scientific writing by project.</div>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <div className="rc-card">
        <div className="rc-card-title">New project</div>
        <div className="rc-row">
          <div style={{ minWidth: 280, flex: 1 }}>
            <div className="rc-kicker">Title</div>
            <input
              className="rc-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Distal radius fracture outcomes in older adults"
              onKeyDown={(e) => e.key === 'Enter' && createProject(title)}
            />
          </div>
          <button className="rc-btn rc-btn--primary" onClick={() => createProject(title)} disabled={!title.trim()}>
            Create
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
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
            <Link to={`/projects/${p.id}/research`} className="rc-btn">Open →</Link>
          </div>
        ))}
      </div>
    </div>
  );
}
