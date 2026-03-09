import { useEffect, useMemo, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useParams } from 'react-router-dom';
import { downloadBlob } from './meta/exportUtils';
import { api } from '../services/api';

type Project = {
  id: string;
  title: string;
  description?: string | null;
  clinical_area?: string | null;
  runtime_mode: string;
  archived: boolean;
};

type Dashboard = {
  project_id: string;
  counts: {
    papers: number;
    notes: number;
    presentations: number;
    meta_studies_current: number;
    references: number;
  };
};

const PRIMARY_TASKS = [
  {
    label: 'Descubrir',
    to: 'research',
    kicker: 'Paso 1',
    copy: 'Busca en fuentes cientificas y guarda los papers correctos.',
  },
  {
    label: 'Leer y preguntar',
    to: 'reader',
    kicker: 'Paso 2',
    copy: 'Lee papers con respuestas basadas en evidencia y citas por pagina.',
  },
  {
    label: 'Extraer',
    to: 'meta',
    kicker: 'Paso 3',
    copy: 'Convierte PDFs en estudios estructurados y revisa los resultados.',
  },
  {
    label: 'Redactar',
    to: 'drafts',
    kicker: 'Paso 4',
    copy: 'Crea borradores, sintesis y secciones respaldadas por evidencia.',
  },
  {
    label: 'Analizar',
    to: 'analysis',
    kicker: 'Paso 5',
    copy: 'Ejecuta analisis reproducibles y exporta artefactos finales.',
  },
];

const SECONDARY_TOOLS = [
  { label: 'Biblioteca', to: 'library', copy: 'Gestiona PDFs y archivos fuente.' },
  { label: 'Referencias', to: 'references', copy: 'Ordena tu bibliografia y exporta citas.' },
  { label: 'Revision', to: 'screening', copy: 'Controla elegibilidad, comentarios y decisiones.' },
  { label: 'Equipo', to: 'collaboration', copy: 'Gestiona miembros, roles y revisiones.' },
  { label: 'Notas', to: 'notes', copy: 'Consulta resúmenes y notas del proyecto.' },
];

const ALL_MODULES = [...PRIMARY_TASKS.map(({ label, to }) => ({ label, to })), ...SECONDARY_TOOLS.map(({ label, to }) => ({ label, to }))];

export default function ProjectLayout() {
  const { projectId } = useParams();
  const location = useLocation();
  const [project, setProject] = useState<Project | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [exportJobId, setExportJobId] = useState<string | null>(null);
  const [exportJobStatus, setExportJobStatus] = useState<{ status: string; progress: number; error?: string | null; output?: any } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const currentSegment = useMemo(() => location.pathname.split('/').filter(Boolean).pop() || 'research', [location.pathname]);

  const currentModule = useMemo(() => {
    return ALL_MODULES.find((module) => module.to === currentSegment)?.label || 'Espacio de trabajo';
  }, [currentSegment]);

  const activePrimaryTask = useMemo(
    () => PRIMARY_TASKS.find((task) => task.to === currentSegment) || null,
    [currentSegment],
  );

  const activeSecondaryTool = useMemo(
    () => SECONDARY_TOOLS.find((tool) => tool.to === currentSegment) || null,
    [currentSegment],
  );

  useEffect(() => {
    let mounted = true;
    async function load() {
      if (!projectId) return;
      setError(null);
      try {
        const [projectResponse, dashboardResponse] = await Promise.all([
          api.get(`/projects/${projectId}`),
          api.get(`/projects/${projectId}/dashboard`),
        ]);
        if (mounted) setProject(projectResponse.data as Project);
        if (mounted) setDashboard(dashboardResponse.data as Dashboard);
      } catch (e: any) {
        if (mounted) setError(e?.response?.data?.detail || 'No se pudo cargar el proyecto');
      }
    }
    void load();
    return () => {
      mounted = false;
    };
  }, [projectId]);

  async function startExportZip() {
    if (!projectId) return;
    setError(null);
    try {
      const r = await api.post(`/projects/${projectId}/export-zip`, {});
      const jid = String((r.data as any)?.job_id || '');
      setExportJobId(jid);
      setExportJobStatus({ status: 'queued', progress: 0, error: null });
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'La exportacion ZIP fallo');
    }
  }

  async function downloadZip() {
    if (!projectId || !exportJobId) return;
    setError(null);
    try {
      const filename = String(exportJobStatus?.output?.filename || `exportacion_proyecto_${projectId}.zip`);
      const r = await api.get(`/projects/${projectId}/export-zip/${exportJobId}/download`, { responseType: 'blob' });
      downloadBlob(r.data as Blob, filename);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'La descarga ZIP fallo');
    }
  }

  useEffect(() => {
    if (!exportJobId) return;
    let stopped = false;

    async function poll() {
      if (stopped) return;
      try {
        const r = await api.get(`/jobs/${exportJobId}`);
        const status = String((r.data as any)?.status || 'unknown');
        const progress = Number((r.data as any)?.progress_percent || 0);
        const err = (r.data as any)?.error || null;
        const result = (r.data as any)?.result || {};
        const output = result?.output || result?.rq_result?.output;
        setExportJobStatus({ status, progress, error: err, output });
        if (status === 'completed' || status === 'failed') return;
      } catch (e: any) {
        setExportJobStatus({ status: 'polling_error', progress: 0, error: e?.response?.data?.detail || 'Polling failed' });
      }
    }

    void poll();
    const timer = window.setInterval(() => {
      void poll();
    }, 2000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [exportJobId]);

  if (!projectId) return <div>Falta el id del proyecto</div>;
  if (error) return <div style={{ color: 'crimson' }}>{String(error)}</div>;

  return (
    <div className="rc-section-shell">
      <div className="rc-hero-card">
        <div style={{ maxWidth: 760 }}>
          <div className="rc-pill">Espacio de trabajo</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>{project?.title || 'Proyecto'}</h1>
          <div className="rc-subtitle">
            {project?.description ||
              project?.clinical_area ||
              'Pasa del descubrimiento de evidencia a la redaccion y al analisis dentro de un unico espacio guiado.'}
          </div>
          <div className="rc-help" style={{ marginTop: 12 }}>
            Ahora estas en <strong>{currentModule}</strong>. El flujo principal es Descubrir → Leer → Extraer → Redactar → Analizar.
            {activeSecondaryTool ? ` Estás usando una herramienta complementaria para apoyar ese flujo.` : ''}
          </div>
        </div>

        <div className="rc-stack" style={{ minWidth: 360, flex: 1 }}>
          <div className="rc-card">
            <div className="rc-card-title">Resumen del proyecto</div>
            <div className="rc-kpi-strip">
              <div className="rc-metric-tile"><strong>{dashboard?.counts?.papers ?? '—'}</strong><span>Articulos guardados</span></div>
              <div className="rc-metric-tile"><strong>{dashboard?.counts?.references ?? '—'}</strong><span>Referencias</span></div>
              <div className="rc-metric-tile"><strong>{dashboard?.counts?.meta_studies_current ?? '—'}</strong><span>Estudios extraidos</span></div>
              <div className="rc-metric-tile"><strong>{dashboard?.counts?.notes ?? '—'}</strong><span>Notas</span></div>
            </div>
          </div>

          <div className="rc-next-step">
            <div className="rc-kicker">Modo actual del espacio</div>
            <div style={{ fontWeight: 800, letterSpacing: '-0.02em', marginTop: 4 }}>{project?.runtime_mode || 'solo-local'}</div>
            <div className="rc-help" style={{ marginTop: 8 }}>Si necesitas una copia portable o entregar el trabajo, exporta el paquete completo del proyecto.</div>
            <div className="rc-row" style={{ marginTop: 12 }}>
              <button className="rc-btn" onClick={startExportZip}>Exportar ZIP del proyecto</button>
              {exportJobId && exportJobStatus?.status === 'completed' ? (
                <button className="rc-btn rc-btn--primary" onClick={downloadZip}>Descargar ZIP</button>
              ) : null}
            </div>
            {exportJobId ? <div className="rc-help" style={{ marginTop: 8 }}>{exportJobStatus?.status || 'queued'} · {exportJobStatus?.progress ?? 0}%</div> : null}
            {exportJobStatus?.error ? <div className="rc-error" style={{ marginTop: 8 }}>{String(exportJobStatus.error)}</div> : null}
          </div>
        </div>
      </div>

      <div className="rc-card">
        <div className="rc-toolbar" style={{ marginBottom: 12 }}>
          <div>
            <div className="rc-card-title" style={{ marginBottom: 4 }}>Flujo principal</div>
            <div className="rc-help">Concéntrate en estos cinco pasos. Las herramientas de apoyo quedan abajo para no distraerte.</div>
          </div>
          {activePrimaryTask ? (
            <div className="rc-stage-label rc-stage-label--teal">{activePrimaryTask.kicker} · {activePrimaryTask.label}</div>
          ) : activeSecondaryTool ? (
            <div className="rc-stage-label rc-stage-label--warm">Herramienta complementaria · {activeSecondaryTool.label}</div>
          ) : (
            <Link className="rc-flow-link" to={`/projects/${projectId}/research`}>Volver al inicio</Link>
          )}
        </div>

        <div className="rc-workflow-bar">
          {PRIMARY_TASKS.map((task) => (
            <NavLink
              key={task.to}
              to={`/projects/${projectId}/${task.to}`}
              end
              className={({ isActive }) => `rc-workflow-tab ${isActive ? 'rc-workflow-tab--active' : ''}`}
            >
              <span className="rc-workflow-tab__kicker">{task.kicker}</span>
              <strong>{task.label}</strong>
              <span>{task.copy}</span>
            </NavLink>
          ))}
        </div>
      </div>

      <div className="rc-card" style={{ padding: 14 }}>
        <div className="rc-toolbar" style={{ marginBottom: 10 }}>
          <div>
            <div className="rc-kicker">Herramientas complementarias</div>
            <div className="rc-help">Úsalas cuando necesites profundizar, pero no deberían reemplazar el flujo principal.</div>
          </div>
          <Link className="rc-flow-link" to={`/projects/${projectId}/research`}>Ir al paso 1</Link>
        </div>
        <div className="rc-secondary-tools">
          {SECONDARY_TOOLS.map((tool) => (
            <NavLink
              key={tool.to}
              to={`/projects/${projectId}/${tool.to}`}
              end
              className={({ isActive }) => `rc-secondary-tool ${isActive ? 'rc-secondary-tool--active' : ''}`}
            >
              <strong>{tool.label}</strong>
              <span>{tool.copy}</span>
            </NavLink>
          ))}
        </div>
      </div>

      <div className="rc-card">
        <Outlet />
      </div>
    </div>
  );
}
