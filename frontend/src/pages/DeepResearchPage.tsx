import { useState } from 'react';
import type { FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { useI18n } from '../i18n';
import { DEMO_MODE } from '../services/demo';
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

// ── Demo fixture ──────────────────────────────────────────────────────────────
const demoReport: Report = {
  id: 'demo', query: 'distal radius fracture outcomes in elderly patients',
  status: 'completed', papers_analyzed: 12, source_mode: 'pubmed',
  metadata: { duration_seconds: 45.2, source: 'pubmed' },
  papers: [
    { pmid: '38901234', title: 'Functional outcomes after volar locking plate fixation in patients over 65', authors: 'Johnson A et al.', journal: 'J Hand Surg', year: '2023', abstract: '' },
    { pmid: '38765432', title: 'Conservative vs surgical management: a systematic review', authors: 'Chen X, Rodriguez M', journal: 'Bone Joint J', year: '2022', abstract: '' },
    { pmid: '38654321', title: 'Patient-reported outcomes in distal radius fracture treatment', authors: 'Davis K et al.', journal: 'Clin Orthop', year: '2023', abstract: '' },
  ],
  sections: [
    { key: 'overview', title: 'Research Overview', content: 'This deep research report analyzes 12 papers on functional outcomes following distal radius fracture treatment in elderly patients (≥65 years).' },
    { key: 'key_findings', title: 'Key Findings', content: 'Volar locking plate demonstrates superior radiographic outcomes but similar functional results at 12 months compared to cast immobilization [1][2].' },
    { key: 'methodology', title: 'Methodology Trends', content: 'Most studies employed retrospective cohort designs (7/12), with 3 RCTs and 2 systematic reviews.' },
    { key: 'consensus', title: 'Consensus & Controversies', content: 'Strong consensus exists around volar locking plates for unstable fractures. Controversy persists for extra-articular fractures with acceptable alignment.' },
    { key: 'gaps', title: 'Research Gaps', content: 'Key gaps: (1) Lack of cost-effectiveness analyses. (2) Insufficient data for patients >80 years. (3) Need for standardized PROMs.' },
    { key: 'conclusion', title: 'Conclusion', content: 'Current evidence supports individualized management. Surgical fixation offers better radiographic outcomes; functional results are similar to conservative treatment at 12 months.' },
  ],
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
      setError('Selecciona un proyecto para usar su biblioteca.');
      return;
    }
    setError(null);
    setLoading(true);
    setReport(null);
    try {
      if (DEMO_MODE) {
        await new Promise(r => setTimeout(r, 2000));
        setReport({ ...demoReport, query });
      } else {
        const payload: any = { query, source_mode: sourceMode };
        if (sourceMode === 'pubmed') payload.max_papers = 15;
        if (sourceMode === 'project') payload.project_id = projectId;
        const r = await api.post('/research/deep', payload);
        setReport(r.data);
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to generate report');
    } finally { setLoading(false); }
  }

  const selectedProject = projects.find(p => p.id === projectId);
  const isEs = locale === 'es';

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
            className={`rc-btn ${sourceMode === 'pubmed' ? 'rc-btn--primary' : ''}`}
            style={{ flex: 1, padding: '8px 0', fontSize: 13 }}
            onClick={() => setSourceMode('pubmed')}
          >
            🌐 PubMed {isEs ? '(búsqueda nueva)' : '(fresh search)'}
          </button>
          <button
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
          type="submit"
          className="rc-btn rc-btn--primary"
          disabled={loading || !query.trim() || (sourceMode === 'project' && !projectId)}
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
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Header */}
          <div className="rc-card" style={{ padding: 20, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 17, letterSpacing: '-0.02em' }}>
                {report.query}
              </div>
              <div style={{ display: 'flex', gap: 12, marginTop: 6, fontSize: 12, color: 'var(--rc-muted)', flexWrap: 'wrap' }}>
                <span>{report.papers_analyzed} {isEs ? 'papers analizados' : 'papers analyzed'}</span>
                <span>{isEs ? 'Generado en' : 'Generated in'} {report.metadata.duration_seconds.toFixed(1)}s</span>
                <span style={{ fontWeight: 600, color: report.source_mode === 'project_library' ? '#059669' : '#2563eb' }}>
                  {report.source_mode === 'project_library'
                    ? `📚 ${isEs ? 'Biblioteca del proyecto' : 'Project library'}`
                    : '🌐 PubMed'}
                </span>
              </div>
            </div>
            <span style={{ padding: '4px 12px', borderRadius: 999, fontSize: 11, fontWeight: 700,
              background: 'rgba(16,185,129,0.1)', color: '#059669', border: '1px solid rgba(16,185,129,0.2)' }}>
              ✓ {report.status}
            </span>
          </div>

          {/* Sections */}
          {report.sections.map(section => (
            <div key={section.key} className="rc-card" style={{ padding: 24 }}>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 16,
                letterSpacing: '-0.02em', marginBottom: 12, paddingBottom: 10, borderBottom: '1px solid var(--rc-border)' }}>
                {section.title}
              </div>
              <div style={{ fontSize: 14, lineHeight: 1.75, color: 'var(--rc-text-secondary)', whiteSpace: 'pre-wrap' }}>
                {section.content}
              </div>
            </div>
          ))}

          {/* Source papers */}
          <div className="rc-card" style={{ padding: 20 }}>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 15,
              marginBottom: 14, letterSpacing: '-0.02em' }}>
              {isEs ? 'Papers fuente' : 'Source Papers'} ({report.papers.length})
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {report.papers.map((p, i) => (
                <div key={p.pmid || i}
                  style={{ padding: '10px 14px', borderRadius: 10, background: 'var(--rc-surface-2)',
                    cursor: p.abstract ? 'pointer' : 'default' }}
                  onClick={() => p.abstract && setExpandedPaper(expandedPaper === (p.pmid || String(i)) ? null : (p.pmid || String(i)))}
                >
                  <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                    <span style={{ flexShrink: 0, width: 22, height: 22, borderRadius: 6,
                      background: 'rgba(99,102,241,0.08)', color: '#6366f1',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 11, fontWeight: 700 }}>{i + 1}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                        <div style={{ fontWeight: 650, fontSize: 13, lineHeight: 1.4, flex: 1 }}>{p.title}</div>
                        <SourceBadge source={p.source} hasFullText={p.has_full_text} />
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--rc-muted)', marginTop: 3 }}>
                        {p.authors} — {p.journal} ({p.year})
                        {p.pmid && (
                          <a href={`https://pubmed.ncbi.nlm.nih.gov/${p.pmid}/`} target="_blank" rel="noopener"
                            style={{ marginLeft: 8, color: '#2563eb', fontSize: 11 }}
                            onClick={e => e.stopPropagation()}>
                            PubMed ↗
                          </a>
                        )}
                        {p.doi && !p.pmid && (
                          <a href={`https://doi.org/${p.doi}`} target="_blank" rel="noopener"
                            style={{ marginLeft: 8, color: '#6366f1', fontSize: 11 }}
                            onClick={e => e.stopPropagation()}>
                            DOI ↗
                          </a>
                        )}
                      </div>
                      {expandedPaper === (p.pmid || String(i)) && p.abstract && (
                        <div style={{ marginTop: 8, fontSize: 12, color: 'var(--rc-text-secondary)',
                          lineHeight: 1.6, borderTop: '1px solid var(--rc-border)', paddingTop: 8 }}>
                          {p.abstract}
                        </div>
                      )}
                    </div>
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
