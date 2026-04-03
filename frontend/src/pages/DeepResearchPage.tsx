import { useState } from 'react';
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

// ── Source badge ──────────────────────────────────────────────────────────────
function SourceBadge({ source, hasFullText }: { source?: string; hasFullText?: boolean }) {
  if (source === 'project_library') {
    return (
      <span style={{ fontSize: 10, fontWeight: 700, padding: '1px 6px', borderRadius: 4,
        background: hasFullText ? 'rgba(16,185,129,0.1)' : 'rgba(99,102,241,0.1)',
        color: hasFullText ? '#059669' : '#6366f1',
        border: `1px solid ${hasFullText ? 'rgba(16,185,129,0.25)' : 'rgba(99,102,241,0.2)'}` }}>
        {hasFullText ? '📄 full text' : '📋 abstract'}
      </span>
    );
  }
  return (
    <span style={{ fontSize: 10, fontWeight: 700, padding: '1px 6px', borderRadius: 4,
      background: 'rgba(59,130,246,0.08)', color: '#2563eb', border: '1px solid rgba(59,130,246,0.2)' }}>
      PubMed
    </span>
  );
}

export default function DeepResearchPage() {
  const { locale } = useI18n();
  const [query, setQuery] = useState('');
  const [sourceMode, setSourceMode] = useState<'pubmed' | 'project'>('pubmed');
  const [projectId, setProjectId] = useState('');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedPaper, setExpandedPaper] = useState<string | null>(null);

  // ── Projects list for selector ────────────────────────────────────────────
  const { data: projects = [] } = useQuery<Pick<Project, 'id' | 'title'>[]>({
    queryKey: ['projects-list'],
    queryFn: async () => {
      const r = await api.get('/projects');
      return (r.data as any[]).map(p => ({ id: p.id, title: p.title }));
    },
    staleTime: 60_000,
  });

  // ── Paper count for selected project ─────────────────────────────────────
  const { data: paperCount } = useQuery<number>({
    queryKey: ['project-paper-count', projectId],
    queryFn: async () => {
      const r = await api.get(`/projects/${projectId}/library`);
      return (r.data as any[]).length;
    },
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    if (sourceMode === 'project' && !projectId) {
      setError(locale === 'es' ? 'Selecciona un proyecto para usar su biblioteca.' : 'Select a project to use its library.');
      return;
    }
    setError(null);
    setLoading(true);
    setReport(null);
    try {
      const payload: any = { query, source_mode: sourceMode };
      if (sourceMode === 'pubmed') payload.max_papers = 15;
      if (sourceMode === 'project') payload.project_id = projectId;
      const r = await api.post('/research/deep', payload);
      setReport(r.data);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to generate report');
    } finally { setLoading(false); }
  }

  const selectedProject = projects.find(p => p.id === projectId);
  const isEs = locale === 'es';
  const canGenerate =
    query.trim().length > 0 &&
    (sourceMode !== 'project' || (Boolean(projectId) && (paperCount ?? 0) > 0));

  return (
    <div className="rc-page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 860 }}>
      <div>
        <h1 className="rc-page-title">{isEs ? 'Investigación Profunda' : 'Deep Research'}</h1>
        <div className="rc-subtitle">
          {isEs
            ? 'La IA analiza papers y genera un reporte integral con citas.'
            : 'AI analyzes papers and generates a comprehensive research report with citations.'}
        </div>
      </div>

      {/* ── Source selector ── */}
      <div className="rc-card" style={{ padding: 14 }}>
        <div className="rc-kicker" style={{ marginBottom: 8 }}>
          {isEs ? 'Fuente de papers' : 'Paper source'}
        </div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <button
            data-testid="deep-research-source-pubmed"
            className={`rc-btn ${sourceMode === 'pubmed' ? 'rc-btn--primary' : ''}`}
            style={{ flex: 1, padding: '8px 0', fontSize: 13 }}
            onClick={() => setSourceMode('pubmed')}
          >
            🌐 PubMed {isEs ? '(búsqueda nueva)' : '(fresh search)'}
          </button>
          <button
            data-testid="deep-research-source-project"
            className={`rc-btn ${sourceMode === 'project' ? 'rc-btn--primary' : ''}`}
            style={{ flex: 1, padding: '8px 0', fontSize: 13 }}
            onClick={() => setSourceMode('project')}
          >
            📚 {isEs ? 'Mi biblioteca del proyecto' : 'My project library'}
          </button>
        </div>

        {sourceMode === 'pubmed' && (
          <div className="rc-help">
            {isEs
              ? 'Buscará PubMed en tiempo real con tu query y analizará los mejores resultados.'
              : 'Will search PubMed in real time with your query and analyze the top results.'}
          </div>
        )}

        {sourceMode === 'project' && (
          <div>
            <div className="rc-kicker" style={{ marginBottom: 6 }}>
              {isEs ? 'Selecciona un proyecto' : 'Select a project'}
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <select
                data-testid="deep-research-project-select"
                className="rc-select"
                value={projectId}
                onChange={e => setProjectId(e.target.value)}
                style={{ flex: 1 }}
              >
                <option value="">{isEs ? '-- Elige un proyecto --' : '-- Choose a project --'}</option>
                {projects.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
              </select>
              {projectId && paperCount !== undefined && (
                <span style={{
                  fontSize: 12, fontWeight: 700, padding: '4px 10px', borderRadius: 8,
                  whiteSpace: 'nowrap',
                  background: paperCount > 0 ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.08)',
                  color: paperCount > 0 ? '#059669' : '#ef4444',
                  border: `1px solid ${paperCount > 0 ? 'rgba(16,185,129,0.25)' : 'rgba(239,68,68,0.2)'}`,
                }}>
                  {paperCount > 0
                    ? `✓ ${paperCount} paper${paperCount !== 1 ? 's' : ''}`
                    : isEs ? '⚠ Sin papers' : '⚠ No papers'}
                </span>
              )}
            </div>
            {projectId && selectedProject && paperCount !== undefined && paperCount > 0 && (
              <div className="rc-help" style={{ marginTop: 6 }}>
                {isEs
                  ? `El reporte usará los ${paperCount} papers de "${selectedProject.title}" — incluyendo texto completo cuando esté disponible.`
                  : `Report will use ${paperCount} papers from "${selectedProject.title}" — including full text where extracted.`}
              </div>
            )}
            {projectId && paperCount === 0 && (
              <div className="rc-error" style={{ marginTop: 6, fontSize: 12 }}>
                {isEs
                  ? 'Este proyecto no tiene papers. Añade PDFs en la Library primero.'
                  : 'This project has no papers. Add PDFs in the Library first.'}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Query form ── */}
      <form onSubmit={onSubmit} style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <input
          data-testid="deep-research-query-input"
          className="rc-input"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder={isEs
            ? 'Pregunta de investigación (ej: "resultados cirugía artroscópica rodilla en adultos mayores")'
            : 'Research question (e.g. "ACL reconstruction outcomes in elderly patients")'}
          required
          disabled={loading}
          style={{ flex: 1, minWidth: 300, fontSize: 14 }}
        />
        <button
          data-testid="deep-research-generate-button"
          type="submit"
          className="rc-btn rc-btn--primary"
          disabled={loading || !canGenerate}
          style={{ padding: '10px 24px', whiteSpace: 'nowrap' }}
        >
          {loading ? (
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="rc-spinner" style={{ width: 14, height: 14, borderTopColor: 'white' }} />
              {isEs ? 'Generando…' : 'Generating…'}
            </span>
          ) : isEs ? 'Generar Reporte →' : 'Generate Report →'}
        </button>
      </form>

      {error && <div className="rc-error">{error}</div>}

      {/* ── Tips ── */}
      {!report && !loading && (
        <div className="rc-card" style={{ padding: 20, background: 'var(--rc-surface-2)' }}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>
            {isEs ? 'Consejos para mejores resultados' : 'Tips for best results'}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(isEs
              ? [
                  'Sé específico: "inhibidores SGLT2 en ICC con FE preservada" > "fármacos cardíacos"',
                  'Incluye población: "…en pacientes ≥65 años" o "…en población pediátrica"',
                  sourceMode === 'project'
                    ? 'Modo biblioteca: el reporte se basa en tus papers descargados — texto completo incluido'
                    : 'Modo PubMed: añade marco temporal si es relevante: "…publicados después de 2020"',
                ]
              : [
                  'Be specific: "SGLT2 inhibitors in HFpEF" > "heart drugs"',
                  'Include population: "…in elderly patients" or "…in pediatric populations"',
                  sourceMode === 'project'
                    ? 'Library mode: the report draws from your downloaded papers — full text included when extracted'
                    : 'PubMed mode: add a timeframe if relevant: "…published after 2020"',
                ]
            ).map((tip, i) => (
              <div key={i} style={{ display: 'flex', gap: 8, fontSize: 13, color: 'var(--rc-text-secondary)' }}>
                <span style={{ color: 'var(--rc-primary)', fontWeight: 700, flexShrink: 0 }}>{i + 1}.</span>
                {tip}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Loading ── */}
      {loading && (
        <div className="rc-card" style={{ padding: 40, textAlign: 'center' }}>
          <div className="rc-spinner" style={{ width: 32, height: 32, margin: '0 auto 16px' }} />
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>
            {isEs ? 'Generando reporte…' : 'Generating report…'}
          </div>
          <div style={{ color: 'var(--rc-muted)', fontSize: 13 }}>
            {sourceMode === 'project'
              ? isEs ? 'Analizando papers de tu biblioteca…' : 'Analyzing papers from your library…'
              : isEs ? 'Buscando en PubMed, analizando papers, redactando secciones…' : 'Searching PubMed, analyzing papers, writing report sections…'}
          </div>
        </div>
      )}

      {/* ── Report ── */}
      {report && (
        <div 
          className="print-report-container"
          style={{ 
            display: 'flex', flexDirection: 'column', gap: 24, 
            background: '#ffffff', 
            color: '#111827', 
            padding: '40px 48px', 
            borderRadius: 12, 
            boxShadow: '0 20px 40px rgba(0,0,0,0.3)',
            fontFamily: '"Merriweather", "Georgia", serif',
            position: 'relative'
          }}
        >
          <button 
            className="rc-btn"
            style={{ position: 'absolute', top: 20, right: 20, background: '#f3f4f6', color: '#374151', border: '1px solid #d1d5db', fontSize: 13, padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, fontFamily: '"Inter", "system-ui", sans-serif' }}
            onClick={() => window.print()}
          >
            <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" /></svg>
            Print Report
          </button>
          
          {/* Header */}
          <div style={{ paddingBottom: 20, borderBottom: '2px solid #e5e7eb' }}>
            <div style={{ fontFamily: '"Inter", "system-ui", sans-serif', fontSize: 12, fontWeight: 700, color: '#6366f1', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
              {isEs ? 'Reporte Clínico Sintetizado' : 'Synthesized Clinical Report'}
            </div>
            <div style={{ fontWeight: 900, fontSize: 24, letterSpacing: '-0.02em', lineHeight: 1.3, marginBottom: 16 }}>
              {report.query}
            </div>
            <div style={{ display: 'flex', gap: 16, fontSize: 13, color: '#6b7280', flexWrap: 'wrap', fontFamily: '"Inter", "system-ui", sans-serif', alignItems: 'center' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <svg width="14" height="14" fill="currentColor" viewBox="0 0 20 20"><path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" /><path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" /></svg>
                {report.papers_analyzed} {isEs ? 'papers analizados' : 'papers analyzed'}
              </span>
              <span>•</span>
              <span>{isEs ? 'Generado en' : 'Generated in'} {report.metadata.duration_seconds.toFixed(1)}s</span>
              <span>•</span>
              <span style={{ fontWeight: 600, color: report.source_mode === 'project_library' ? '#059669' : '#2563eb' }}>
                {report.source_mode === 'project_library'
                  ? `📚 ${isEs ? 'Biblioteca del proyecto' : 'Project library'}`
                  : '🌐 PubMed'}
              </span>
              <span style={{ padding: '2px 8px', borderRadius: 999, fontSize: 11, fontWeight: 700,
                background: '#d1fae5', color: '#065f46', marginLeft: 'auto' }}>
                ✓ {report.status}
              </span>
            </div>
          </div>

          {/* Sections */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
            {report.sections.map(section => (
              <div key={section.key}>
                <h3 style={{ fontFamily: '"Inter", "system-ui", sans-serif', fontWeight: 800, fontSize: 18, color: '#1f2937',
                  marginBottom: 12 }}>
                  {section.title}
                </h3>
                <div style={{ fontSize: 15, lineHeight: 1.8, color: '#374151', whiteSpace: 'pre-wrap' }}>
                  {section.content}
                </div>
              </div>
            ))}
          </div>

          {/* Source papers */}
          <div style={{ marginTop: 24, paddingTop: 24, borderTop: '2px solid #e5e7eb' }}>
            <h3 style={{ fontFamily: '"Inter", "system-ui", sans-serif', fontWeight: 800, fontSize: 16, color: '#1f2937',
              marginBottom: 16 }}>
              {isEs ? 'Referencias y Evidencia' : 'References & Evidence'} ({report.papers.length})
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {report.papers.map((p, i) => (
                <div key={p.pmid || i}
                  style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}
                >
                  <span style={{ fontWeight: 700, fontSize: 14, color: '#9ca3af', minWidth: 24 }}>[{i + 1}]</span>
                  <div style={{ flex: 1, fontFamily: '"Inter", "system-ui", sans-serif' }}>
                    <div style={{ fontWeight: 600, fontSize: 14, color: '#111827', lineHeight: 1.5 }}>{p.title}</div>
                    <div style={{ fontSize: 13, color: '#4b5563', marginTop: 4 }}>
                      {p.authors} — <span style={{ fontStyle: 'italic' }}>{p.journal}</span> ({p.year})
                    </div>
                    {(p.pmid || p.doi) && (
                      <div style={{ marginTop: 4, fontSize: 12 }}>
                        {p.pmid && (
                          <a href={`https://pubmed.ncbi.nlm.nih.gov/${p.pmid}/`} target="_blank" rel="noopener"
                            style={{ color: '#4f46e5', textDecoration: 'none', marginRight: 12, fontWeight: 500 }}>
                            PMID: {p.pmid}
                          </a>
                        )}
                        {p.doi && (
                          <a href={`https://doi.org/${p.doi}`} target="_blank" rel="noopener"
                            style={{ color: '#4f46e5', textDecoration: 'none', fontWeight: 500 }}>
                            DOI: {p.doi}
                          </a>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
