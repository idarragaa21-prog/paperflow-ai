import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';

type Project = {
  id: string;
  title: string;
  description?: string | null;
  clinical_area?: string | null;
  archived: boolean;
};

const PROJECT_PROMPTS = [
  'Comparación de estrategias para control de dolor postoperatorio',
  'Resultados de reconstrucción ACL con distintos injertos',
  'Efectividad de monitoreo remoto en insuficiencia cardiaca',
];

export default function ProjectsPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/projects');
      setProjects(response.data as Project[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudieron cargar los proyectos');
    } finally {
      setLoading(false);
    }
  }

  async function create() {
    if (!title.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const response = await api.post('/projects', { title: title.trim() });
      const project = response.data as Project;
      setTitle('');
      await load();
      navigate(`/projects/${project.id}/research`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo crear el proyecto');
    } finally {
      setCreating(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const latestProject = useMemo(() => projects[0] || null, [projects]);

  return (
    <div className="rc-projects-home">
      <section className="rc-projects-home__hero">
        <div className="rc-projects-home__hero-copy">
          <div className="rc-kicker">PaperFlow workspace</div>
          <h1>Empieza una investigación sin ruido.</h1>
          <p>
            Crea un proyecto, entra directo a `Descubrir` y mantén búsqueda, lectura, extracción y análisis dentro del
            mismo espacio.
          </p>
        </div>

        <div className="rc-projects-home__composer">
          <div className="rc-projects-home__composer-title">Crear nuevo proyecto</div>
          <input
            data-testid="project-title-input"
            className="rc-input rc-projects-home__input"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Haz una pregunta o define el foco del proyecto…"
          />

          <div className="rc-chip-list">
            {PROJECT_PROMPTS.map((prompt) => (
              <button key={prompt} type="button" className="rc-discover-mini-chip" onClick={() => setTitle(prompt)}>
                {prompt}
              </button>
            ))}
          </div>

          <div className="rc-row">
            <button
              data-testid="project-create-button"
              className="rc-btn rc-btn--primary"
              onClick={() => void create()}
              disabled={!title.trim() || creating}
            >
              {creating ? 'Creando…' : 'Crear proyecto'}
            </button>
            <button className="rc-btn rc-btn--subtle" onClick={() => void load()} disabled={loading}>
              {loading ? 'Actualizando…' : 'Actualizar'}
            </button>
          </div>
        </div>
      </section>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <section className="rc-projects-home__summary">
        <div className="rc-discover-badge">{projects.length} proyectos</div>
        <div className="rc-discover-badge">{latestProject ? 'Listo para continuar' : 'Crea tu primer espacio'}</div>
      </section>

      {projects.length === 0 ? (
        <div className="rc-empty-state">
          <div style={{ fontWeight: 800, marginBottom: 6 }}>Todavía no hay proyectos</div>
          <div className="rc-help">Crea uno arriba y PaperFlow te llevará directo al flujo principal de búsqueda.</div>
        </div>
      ) : (
        <section className="rc-projects-grid">
          {projects.map((project) => (
            <button
              data-testid={`project-card-${project.id}`}
              key={project.id}
              type="button"
              className="rc-project-card"
              onClick={() => navigate(`/projects/${project.id}/research`)}
            >
              <div className="rc-project-card__top">
                <span className="rc-discover-badge">{project.archived ? 'Archivado' : 'Activo'}</span>
              </div>
              <h3>{project.title}</h3>
              <p>
                {project.description ||
                  project.clinical_area ||
                  'Abrir este proyecto te lleva directo a una experiencia centrada en descubrir literatura y construir el trabajo desde ahí.'}
              </p>
              <span data-testid={`project-open-${project.id}`} className="rc-project-card__link">
                Abrir espacio
              </span>
            </button>
          ))}
        </section>
      )}
    </div>
  );
}
