import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { useI18n } from '../i18n';
import type { Project } from '../types/api';

type Section = { key: string; title: string; content: string };
type Paper = {
  pmid: string; doi?: string; title: string; authors: string;
  journal: string; year: string; abstract: string;
  source?: string; has_full_text?: boolean;
};
type Report = {
  id: string; query: string; status: string;
  sections: Section[]; papers: Paper[];
  papers_analyzed: number; source_mode?: string;
  metadata: { duration_seconds: number; source?: string; project_id?: string };
};

export default function DeepResearchPage() {
  const { locale } = useI18n();
  const [query, setQuery] = useState('');
  const [sourceMode, setSourceMode] = useState<'pubmed' | 'project'>('pubmed');
  const [projectId, setProjectId] = useState('');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const reportRef = useRef<HTMLDivElement>(null);
  const isEs = locale === 'es';

  const { data: projects = [] } = useQuery<Pick<Project, 'id' | 'title'>[]>({
    queryKey: ['projects-list'],
    queryFn: async () => {
      const r = await api.get('/projects');
      return (r.data as Array<Pick<Project, 'id' | 'title'>>).map(p => ({ id: p.id, title: p.title }));
    },
    staleTime: 60_000,
  });

  const { data: paperCount } = useQuery<number>({
    queryKey: ['project-paper-count', projectId],
    queryFn: async () => {
      const r = await api.get(`/projects/${projectId}/library`);
      return (r.data as unknown[]).length;
    },
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    if (sourceMode === 'project' && !projectId) {
      setError(isEs ? 'Selecciona un proyecto para usar su biblioteca.' : 'Select a project to use its library.');
      return;
    }
    setError(null);
    setLoading(true);
    setReport(null);
    try {
      const payload: Record<string, unknown> = { query, source_mode: sourceMode };
      if (sourceMode === 'pubmed') payload.max_papers = 15;
      if (sourceMode === 'project') payload.project_id = projectId;
      const r = await api.post('/research/deep', payload);
      setReport(r.data);
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || 'Failed to generate report');
    } finally {
      setLoading(false);
    }
  }

  async function handleDownloadPdf() {
    if (!reportRef.current || !report) return;
    setDownloadingPdf(true);
    try {
      const [{ default: html2canvas }, { default: jsPDF }] = await Promise.all([
        import('html2canvas'),
        import('jspdf'),
      ]);
      const canvas = await html2canvas(reportRef.current, {
        scale: 2, useCORS: true, backgroundColor: '#ffffff', logging: false,
      });
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
      const pageW = pdf.internal.pageSize.getWidth();
      const pageH = pdf.internal.pageSize.getHeight();
      const imgW = pageW;
      const imgH = (canvas.height * imgW) / canvas.width;
      let yOffset = 0;
      while (yOffset < imgH) {
        if (yOffset > 0) pdf.addPage();
        pdf.addImage(imgData, 'PNG', 0, -yOffset, imgW, imgH);
        yOffset += pageH;
      }
      const safeName = report.query.slice(0, 40).replace(/[^a-z0-9\s-]/gi, '').trim().replace(/\s+/g, '-');
      pdf.save(`deep-research-${safeName || 'report'}.pdf`);
    } catch (err) {
      console.error('PDF export failed:', err);
    } finally {
      setDownloadingPdf(false);
    }
  }

  const canGenerate =
    query.trim().length > 0 &&
    (sourceMode !== 'project' || (Boolean(projectId) && (paperCount ?? 0) > 0));

  return (
    <div className="pg-fade-in pg-stack-lg" style={{ maxWidth: 860 }}>
      <div>
        <div className="pg-kicker" style={{ marginBottom: 4 }}>
          {isEs ? 'Investigación' : 'Research'}
        </div>
        <h1 className="pg-h1">{isEs ? 'Investigación profunda' : 'Deep Research'}</h1>
        <p className="pg-muted" style={{ marginTop: 4, fontSize: 14, maxWidth: 620 }}>
          {isEs
            ? 'La IA analiza papers y genera un reporte integral con citas.'
            : 'AI analyzes papers and generates a comprehensive research report with citations.'}
        </p>
      </div>

      <div className="pg-card" style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div>
          <div className="pg-label" style={{ marginBottom: 6 }}>
            {isEs ? 'Fuente de papers' : 'Paper source'}
          </div>
          <div className="pg-tabs" style={{ width: 'fit-content' }}>
            <button
              type="button"
              data-testid="deep-research-source-pubmed"
              className={`pg-tab${sourceMode === 'pubmed' ? ' active' : ''}`}
              onClick={() => setSourceMode('pubmed')}
            >
              PubMed
            </button>
            <button
              type="button"
              data-testid="deep-research-source-project"
              className={`pg-tab${sourceMode === 'project' ? ' active' : ''}`}
              onClick={() => setSourceMode('project')}
            >
              {isEs ? 'Biblioteca del proyecto' : 'Project library'}
            </button>
          </div>
        </div>

        {sourceMode === 'project' && (
          <div>
            <label htmlFor="deep-research-project" className="pg-label">
              {isEs ? 'Proyecto' : 'Project'}
            </label>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <select
                id="deep-research-project"
                data-testid="deep-research-project-select"
                className="pg-input"
                value={projectId}
                onChange={e => setProjectId(e.target.value)}
                style={{ flex: 1 }}
              >
                <option value="">{isEs ? '— Elegir proyecto —' : '— Choose project —'}</option>
                {projects.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
              </select>
              {projectId && paperCount !== undefined && (
                <span className={`pg-badge${paperCount > 0 ? ' pg-badge--info' : ''}`}>
                  {paperCount > 0
                    ? `${paperCount} paper${paperCount !== 1 ? 's' : ''}`
                    : isEs ? 'Sin papers' : 'No papers'}
                </span>
              )}
            </div>
            {projectId && paperCount === 0 && (
              <div className="pg-muted" style={{ fontSize: 13, marginTop: 6, color: 'var(--pg-danger)' }}>
                {isEs
                  ? 'Este proyecto no tiene papers. Añade PDFs en la Biblioteca primero.'
                  : 'This project has no papers. Add PDFs in the Library first.'}
              </div>
            )}
          </div>
        )}

        <form onSubmit={onSubmit} style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <input
            data-testid="deep-research-query-input"
            className="pg-input"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={isEs
              ? 'Pregunta de investigación (ej. "resultados artroscopia de rodilla en adultos mayores")'
              : 'Research question (e.g. "ACL reconstruction outcomes in elderly patients")'}
            required
            disabled={loading}
            style={{ flex: 1, minWidth: 280 }}
          />
          <button
            data-testid="deep-research-generate-button"
            type="submit"
            className="pg-btn pg-btn--primary"
            disabled={loading || !canGenerate}
          >
            {loading ? (isEs ? 'Generando…' : 'Generating…') : (isEs ? 'Generar reporte' : 'Generate report')}
          </button>
        </form>
      </div>

      {error && (
        <div style={{ padding: '10px 12px', borderRadius: 10, background: '#FEF2F2', border: '1px solid #FECACA', color: '#B91C1C', fontSize: 13 }}>
          {error}
        </div>
      )}

      {loading && (
        <div className="pg-card" style={{ padding: 40, textAlign: 'center' }}>
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>
            {isEs ? 'Generando reporte…' : 'Generating report…'}
          </div>
          <div className="pg-muted" style={{ fontSize: 13 }}>
            {sourceMode === 'project'
              ? (isEs ? 'Analizando papers de tu biblioteca…' : 'Analyzing library papers…')
              : (isEs ? 'Buscando en PubMed y redactando secciones…' : 'Searching PubMed and writing sections…')}
          </div>
        </div>
      )}

      {report && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
            <button
              className="pg-btn pg-btn--primary pg-btn--sm"
              onClick={handleDownloadPdf}
              disabled={downloadingPdf}
            >
              {downloadingPdf
                ? (isEs ? 'Exportando…' : 'Exporting…')
                : (isEs ? 'Descargar PDF' : 'Download PDF')}
            </button>
          </div>

          <div
            ref={reportRef}
            style={{
              background: '#fff',
              border: '1px solid var(--pg-line)',
              borderRadius: 12,
              padding: 32,
              display: 'flex', flexDirection: 'column', gap: 24,
            }}
          >
            <div style={{ paddingBottom: 16, borderBottom: '1px solid var(--pg-line)' }}>
              <div className="pg-kicker" style={{ marginBottom: 8 }}>
                {isEs ? 'Reporte clínico sintetizado' : 'Synthesized clinical report'}
              </div>
              <h2 className="pg-h2" style={{ marginBottom: 12 }}>{report.query}</h2>
              <div className="pg-muted" style={{ fontSize: 13, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <span>{report.papers_analyzed} {isEs ? 'papers' : 'papers'}</span>
                <span>·</span>
                <span>{report.metadata.duration_seconds.toFixed(1)}s</span>
                <span>·</span>
                <span>
                  {new Date().toLocaleDateString(isEs ? 'es-CO' : 'en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
                </span>
                <span>·</span>
                <span>
                  {report.source_mode === 'project_library'
                    ? (isEs ? 'Biblioteca del proyecto' : 'Project library')
                    : 'PubMed'}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              {report.sections.map(section => (
                <div key={section.key}>
                  <h3 className="pg-h3" style={{ marginBottom: 10 }}>{section.title}</h3>
                  <div style={{ fontSize: 14, lineHeight: 1.7, whiteSpace: 'pre-wrap', color: 'var(--pg-text)' }}>
                    {section.content}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ paddingTop: 16, borderTop: '1px solid var(--pg-line)' }}>
              <h3 className="pg-h3" style={{ marginBottom: 12 }}>
                {isEs ? 'Referencias' : 'References'} ({report.papers.length})
              </h3>
              <ol style={{ display: 'flex', flexDirection: 'column', gap: 10, paddingLeft: 20, margin: 0 }}>
                {report.papers.map((p, i) => (
                  <li key={p.pmid || i} style={{ fontSize: 13, lineHeight: 1.5 }}>
                    <span style={{ fontWeight: 600 }}>{p.title}</span>
                    <div className="pg-muted" style={{ fontSize: 12, marginTop: 2 }}>
                      {p.authors} — <em>{p.journal}</em> ({p.year})
                    </div>
                    {(p.pmid || p.doi) && (
                      <div style={{ fontSize: 12, marginTop: 2, display: 'flex', gap: 10 }}>
                        {p.pmid && (
                          <a href={`https://pubmed.ncbi.nlm.nih.gov/${p.pmid}/`} target="_blank" rel="noopener noreferrer">
                            PMID: {p.pmid}
                          </a>
                        )}
                        {p.doi && (
                          <a href={`https://doi.org/${p.doi}`} target="_blank" rel="noopener noreferrer">
                            DOI: {p.doi}
                          </a>
                        )}
                      </div>
                    )}
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
