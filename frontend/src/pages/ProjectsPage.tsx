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
      setError(e?.response?.data?.detail || 'No se pudieron cargar los proyectos');
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
      setError(e?.response?.data?.detail || 'No se pudo crear el proyecto');
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
          <div className="rc-pill">Proyectos</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>Proyectos</h1>
          <div className="rc-subtitle">
            Un solo lugar para busqueda bibliografica, lectura de PDFs, extraccion de evidencia, redaccion y analisis reproducible.
          </div>
          <div className="rc-help" style={{ marginTop: 12, maxWidth: 640 }}>
            Empieza un nuevo espacio de investigacion o vuelve al que estabas usando. PaperFlow se organiza alrededor del trabajo que quieres completar, no de herramientas desconectadas.
          </div>
        </div>
        <div className="rc-kpi-strip" style={{ minWidth: 320 }}>
          <div className="rc-hero-stat">
            <strong>{projects.length}</strong>
            <span>Proyectos activos</span>
          </div>
          <div className="rc-hero-stat">
            <strong>{latestProject ? 'Listo' : 'Empieza'}</strong>
            <span>{latestProject ? 'Ultimo espacio disponible' : 'Crea tu primer espacio'}</span>
          </div>
        </div>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <div className="rc-shelf">
        <div className="rc-card">
          <div className="rc-card-title">Crear un nuevo espacio de investigacion</div>
          <div className="rc-help" style={{ marginBottom: 12 }}>
            Dale al proyecto un titulo especifico para que la busqueda, la extraccion y la redaccion se mantengan enfocadas en la misma pregunta.
          </div>
          <div className="rc-row" style={{ alignItems: 'flex-end' }}>
            <div style={{ minWidth: 280, flex: 1 }}>
              <div className="rc-kicker">Titulo del proyecto</div>
              <input
                data-testid="project-title-input"
                className="rc-input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="ej. Resultados de reparacion del manguito rotador en adultos mayores"
              />
            </div>
            <button data-testid="project-create-button" className="rc-btn rc-btn--primary" onClick={create} disabled={!title.trim()}>
              Crear proyecto
            </button>
          </div>
          <div className="rc-help" style={{ marginTop: 10 }}>
            Consejo: un buen titulo menciona la poblacion, la intervencion o el resultado que te interesa.
          </div>
        </div>

        <div className="rc-card">
          <div className="rc-card-title">Como funciona PaperFlow</div>
          <div className="rc-guided-grid" style={{ gridTemplateColumns: '1fr' }}>
            <div className="rc-flow-card">
              <div className="rc-stage-label rc-stage-label--teal">Paso 1</div>
              <h3>Encuentra los papers correctos</h3>
              <p>Busca en las principales fuentes cientificas y guarda la evidencia que de verdad responde tu pregunta.</p>
            </div>
            <div className="rc-flow-card">
              <div className="rc-stage-label rc-stage-label--warm">Paso 2</div>
              <h3>Lee, extrae y compara</h3>
              <p>Haz preguntas con evidencia, extrae datos estructurados y revisa los hallazgos dentro del mismo espacio.</p>
            </div>
            <div className="rc-flow-card">
              <div className="rc-stage-label rc-stage-label--teal">Paso 3</div>
              <h3>Redacta y analiza</h3>
              <p>Construye borradores con citas y ejecuta analisis reproducibles sin perder el contexto.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="rc-card">
        <div className="rc-toolbar">
          <div>
            <div className="rc-card-title" style={{ marginBottom: 4 }}>Espacios recientes</div>
            <div className="rc-help">Retoma donde lo dejaste o abre un proyecto directamente en su flujo de investigacion.</div>
          </div>
          <button className="rc-btn" onClick={() => void load()} disabled={loading}>
            {loading ? 'Actualizando...' : 'Actualizar'}
          </button>
        </div>
      </div>

      {projects.length === 0 ? (
        <div className="rc-empty-state">
          <div style={{ fontWeight: 800, marginBottom: 6 }}>Todavia no hay proyectos</div>
          <div className="rc-help">Crea tu primer proyecto arriba y PaperFlow abrira un espacio completo de investigacion alrededor de el.</div>
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
                  {index === 0 ? 'Continuar' : 'Espacio'}
                </span>
                {project.archived ? <span className="rc-badge">Archivado</span> : <span className="rc-badge rc-badge--success">Activo</span>}
              </div>
              <h3>{project.title}</h3>
              <p>
                {project.description ||
                  project.clinical_area ||
                  'Abre el espacio para buscar, leer, extraer, redactar y analizar dentro del mismo contexto del proyecto.'}
              </p>
              <Link
                data-testid={`project-open-${project.id}`}
                to={`/projects/${project.id}/research`}
                className="rc-flow-link"
                onClick={(e) => e.stopPropagation()}
              >
                Abrir espacio
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
