import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useI18n } from '../i18n';
import { PageHero } from '../components/WorkflowPrimitives';
import type { StudyRow, PaperRow } from '../types/api';

type StudyFull = StudyRow & {
  study_json?: any;
  paper?: PaperRow;
};

type SortColumn = 'title' | 'year' | 'journal' | 'design' | 'rob' | 'confidence';
type SortDir = 'asc' | 'desc';

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  return (
    <span style={{ marginLeft: 4, opacity: active ? 1 : 0.3, fontSize: 10 }}>
      {active ? (dir === 'asc' ? '▲' : '▼') : '⇅'}
    </span>
  );
}

export default function LiteratureReviewPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { locale } = useI18n();
  const isEs = locale === 'es';
  const isPt = locale === 'pt';
  const [studies, setStudies] = useState<StudyFull[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [sortColumn, setSortColumn] = useState<SortColumn>('title');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [aiSummary, setAiSummary] = useState<{ loading?: boolean; text?: string; error?: string | null }>({});

  const loadData = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const rStudies = await api.get(`/meta/studies?project_id=${projectId}`);
      const studiesData = rStudies.data as StudyRow[];

      const rPapers = await api.get(`/projects/${projectId}/library`);
      const papersMap = new Map((rPapers.data as PaperRow[]).map(p => [p.id, p]));

      const studiesFull = await Promise.all(
        studiesData.map(async (st) => {
          try {
            const stDetail = await api.get(`/meta/studies/${st.id}`);
            return {
              ...st,
              study_json: stDetail.data?.study_json,
              paper: stDetail.data?.paper_id ? papersMap.get(stDetail.data.paper_id) : undefined,
            } as StudyFull;
          } catch {
            return {
              ...st,
              paper: (st as any).paper_id ? papersMap.get((st as any).paper_id) : undefined,
            } as StudyFull;
          }
        })
      );

      setStudies(studiesFull);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load literature comparison');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { void loadData(); }, [loadData]);

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelectedIds(next);
  };

  const toggleAll = () => {
    setSelectedIds(selectedIds.size === studies.length ? new Set() : new Set(studies.map(s => s.id)));
  };

  const handleSendToDraft = () => {
    if (selectedIds.size === 0) return;
    navigate(`/projects/${projectId}/drafts?studies=${Array.from(selectedIds).join(',')}`);
  };

  const handleAiSummary = async () => {
    if (selectedIds.size === 0) return;
    setAiSummary({ loading: true });
    try {
      const selected = studies.filter(s => selectedIds.has(s.id));
      const summaryInput = selected.map(s => {
        const sj = s.study_json || {};
        return `${s.paper_title || s.title || 'Untitled'}: ${sj.objective || sj.outcomes?.map((o: any) => o.outcome_name).join(', ') || ''}`;
      }).join('\n');
      const res = await api.post('/search/synthesize', {
        query: summaryInput,
        papers: selected.map(s => ({
          title: s.paper_title || s.title || '',
          authors: s.paper?.authors || s.study_json?.authors || '',
          journal: s.paper?.journal || '',
          year: s.paper?.publication_year || s.study_json?.year || '',
          abstract: s.study_json?.objective || '',
          pmid: s.paper?.pmid || '',
        })),
      });
      setAiSummary({ text: res.data.answer });
    } catch (e: any) {
      setAiSummary({ error: e?.response?.data?.detail || (isEs ? 'Error al generar resumen' : isPt ? 'Erro ao gerar resumo' : 'Failed to generate summary') });
    }
  };

  // ── Column sort ──────────────────────────────────────────────────────────
  const handleSort = (col: SortColumn) => {
    if (sortColumn === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(col);
      setSortDir('asc');
    }
  };

  const sortedStudies = useMemo(() => {
    return [...studies].sort((a, b) => {
      const sj_a = a.study_json || {};
      const sj_b = b.study_json || {};
      let va: string | number = '';
      let vb: string | number = '';

      switch (sortColumn) {
        case 'title':
          va = a.paper_title || a.title || '';
          vb = b.paper_title || b.title || '';
          break;
        case 'year':
          va = Number(a.paper?.publication_year || sj_a.year || 0);
          vb = Number(b.paper?.publication_year || sj_b.year || 0);
          break;
        case 'journal':
          va = a.paper?.journal || '';
          vb = b.paper?.journal || '';
          break;
        case 'design':
          va = sj_a.study_design || a.design || '';
          vb = sj_b.study_design || b.design || '';
          break;
        case 'rob':
          va = a.rob_score ? Math.round(a.rob_score * 100) : -1;
          vb = b.rob_score ? Math.round(b.rob_score * 100) : -1;
          break;
        case 'confidence':
          va = Number(a.extraction_confidence) || 0;
          vb = Number(b.extraction_confidence) || 0;
          break;
      }

      if (typeof va === 'number' && typeof vb === 'number') {
        return sortDir === 'asc' ? va - vb : vb - va;
      }
      const cmp = String(va).localeCompare(String(vb), undefined, { sensitivity: 'base' });
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [studies, sortColumn, sortDir]);

  // ── CSV Export ───────────────────────────────────────────────────────────
  const exportCsv = () => {
    const toExport = selectedIds.size > 0
      ? sortedStudies.filter(s => selectedIds.has(s.id))
      : sortedStudies;

    const headers = ['Title', 'Authors', 'Year', 'Journal', 'Design', 'Population', 'Key Finding', 'RoB Level', 'RoB %', 'Confidence %'];
    const escape = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`;

    const rows = toExport.map(study => {
      const sj = study.study_json || {};
      const authors = study.paper?.authors || sj.authors || sj.first_author || '';
      const year = study.paper?.publication_year || sj.year || '';
      const journal = study.paper?.journal || '';
      const design = sj.study_design || study.design || '';
      const population = sj.population_description || '';
      const findings = Array.isArray(sj.outcomes) && sj.outcomes.length > 0
        ? sj.outcomes.map((o: any) => o.outcome_name).join('; ')
        : sj.objective || '';
      const robScore = study.rob_score ? Math.round(study.rob_score * 100) : '';
      let robLevel = '';
      if (typeof robScore === 'number') {
        robLevel = robScore <= 40 ? 'Low' : robScore <= 70 ? 'Medium' : 'High';
      }
      const confScore = Number(study.extraction_confidence);
      const confidence = !isNaN(confScore) ? Math.round(confScore * 100) : '';
      const title = study.paper_title || study.title || '';

      return [title, authors, year, journal, design, population, findings, robLevel, robScore, confidence].map(escape).join(',');
    });

    const csv = [headers.map(escape).join(','), ...rows].join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `literature-matrix-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const thStyle = (): React.CSSProperties => ({
    cursor: 'pointer',
    userSelect: 'none',
    whiteSpace: 'nowrap',
  });

  return (
    <div className="rc-page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <PageHero
        eyebrow={isEs ? 'Análisis' : isPt ? 'Análise' : 'Analysis'}
        title={isEs ? 'Matriz de Comparación de Literatura' : isPt ? 'Matriz de Comparação de Literatura' : 'Literature Comparison Matrix'}
        subtitle={isEs
          ? 'Compara estudios lado a lado para identificar patrones, evaluar riesgo de sesgo y consolidar evidencia estructurada.'
          : isPt
            ? 'Compare estudos lado a lado para identificar padrões, avaliar risco de viés e consolidar evidência estruturada.'
            : 'Compare studies side-by-side to identify patterns, evaluate risk of bias, and consolidate structured evidence.'}
        metrics={[
          { label: isEs ? 'estudios extraídos' : isPt ? 'estudos extraídos' : 'studies extracted', value: studies.length, tone: 'success' },
          { label: isEs ? 'seleccionados' : isPt ? 'selecionados' : 'selected', value: selectedIds.size, tone: selectedIds.size > 0 ? 'primary' : 'neutral' },
        ]}
        actions={
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              className="rc-btn"
              onClick={exportCsv}
              disabled={studies.length === 0}
              title={selectedIds.size > 0
                ? (isEs ? `Exportar ${selectedIds.size} estudios seleccionados` : `Export ${selectedIds.size} selected studies`)
                : (isEs ? 'Exportar todos los estudios' : 'Export all studies')}
              style={{ fontWeight: 600, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3M3 17v3a1 1 0 001 1h16a1 1 0 001-1v-3" /></svg>
              {selectedIds.size > 0
                ? (isEs ? `Exportar ${selectedIds.size} CSV` : `Export ${selectedIds.size} CSV`)
                : (isEs ? 'Exportar CSV' : 'Export CSV')}
            </button>
            <button
              className="rc-btn"
              disabled={selectedIds.size === 0 || aiSummary.loading}
              onClick={handleAiSummary}
              style={{ fontWeight: 600, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6,
                background: 'linear-gradient(135deg, rgba(99,102,241,0.08), rgba(139,92,246,0.04))',
                border: '1px solid rgba(99,102,241,0.25)',
              }}
            >
              {aiSummary.loading
                ? <><span className="rc-spinner" style={{ width: 12, height: 12 }} /> {isEs ? 'Resumiendo…' : 'Summarizing…'}</>
                : <>✨ {isEs ? 'Resumir con IA' : isPt ? 'Resumir com IA' : 'Summarize with AI'}</>}
            </button>
            <button
              className="rc-btn rc-btn--primary"
              disabled={selectedIds.size === 0}
              onClick={handleSendToDraft}
              style={{ fontWeight: 600, boxShadow: '0 4px 10px rgba(79, 70, 229, 0.25)' }}
            >
              ✍️ {isEs ? 'Enviar' : isPt ? 'Enviar' : 'Send'} {selectedIds.size > 0 ? selectedIds.size : ''} {isEs ? 'a Borradores IA →' : isPt ? 'para Rascunhos IA →' : 'to AI Drafts →'}
            </button>
          </div>
        }
      />

      {/* AI Summary result */}
      {aiSummary.text && (
        <div className="rc-card" style={{
          padding: 20,
          background: 'linear-gradient(145deg, rgba(99,102,241,0.06), rgba(139,92,246,0.03))',
          border: '1px solid rgba(99,102,241,0.2)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <div style={{ fontWeight: 800, fontSize: 14 }}>
              ✨ {isEs ? 'Resumen IA de estudios seleccionados' : isPt ? 'Resumo IA dos estudos selecionados' : 'AI Summary of selected studies'}
            </div>
            <button className="rc-btn rc-btn--sm rc-btn--ghost" onClick={() => setAiSummary({})}>✕</button>
          </div>
          <div style={{ whiteSpace: 'pre-wrap', fontSize: 14, lineHeight: 1.7, color: 'var(--rc-text)' }}>
            {aiSummary.text}
          </div>
        </div>
      )}
      {aiSummary.error && (
        <div className="rc-error">{aiSummary.error}</div>
      )}

      {loading ? (
        <div className="rc-card" style={{ padding: 40, textAlign: 'center' }}>
          <div className="rc-spinner" style={{ margin: '0 auto 12px' }} />
          <div>{isEs ? 'Compilando matriz…' : isPt ? 'Compilando matriz…' : 'Compiling matrix...'}</div>
        </div>
      ) : error ? (
        <div className="rc-error">{error}</div>
      ) : studies.length === 0 ? (
        <div className="rc-card rc-muted" style={{ padding: 40, textAlign: 'center' }}>
          {isEs
            ? 'No se encontraron estudios extraídos. Ve al paso de Extracción (Meta) para procesar papers primero.'
            : isPt
              ? 'Nenhum estudo extraído encontrado. Vá à etapa de Extração (Meta) para processar papers primeiro.'
              : 'No extracted studies found. Go to the Extraction (Meta) step to process papers first.'}
        </div>
      ) : (
        <div className="rc-datagrid-container">
          <table className="rc-datagrid">
            <thead>
              <tr>
                <th style={{ width: 40, textAlign: 'center' }}>
                  <input
                    type="checkbox"
                    checked={selectedIds.size === studies.length && studies.length > 0}
                    onChange={toggleAll}
                  />
                </th>
                <th style={{ width: '20%', ...thStyle() }} onClick={() => handleSort('title')}>
                  {isEs ? 'Estudio' : isPt ? 'Estudo' : 'Study'} <SortIcon active={sortColumn === 'title'} dir={sortDir} />
                </th>
                <th style={{ width: '8%', ...thStyle() }} onClick={() => handleSort('year')}>
                  {isEs ? 'Año' : isPt ? 'Ano' : 'Year'} <SortIcon active={sortColumn === 'year'} dir={sortDir} />
                </th>
                <th style={{ width: '14%', ...thStyle() }} onClick={() => handleSort('journal')}>
                  {isEs ? 'Revista' : isPt ? 'Revista' : 'Journal'} <SortIcon active={sortColumn === 'journal'} dir={sortDir} />
                </th>
                <th style={{ width: '16%', ...thStyle() }} onClick={() => handleSort('design')}>
                  {isEs ? 'Diseño / Población' : isPt ? 'Desenho / População' : 'Design / Population'} <SortIcon active={sortColumn === 'design'} dir={sortDir} />
                </th>
                <th style={{ width: '22%' }}>{isEs ? 'Hallazgos Clave' : isPt ? 'Achados Chave' : 'Key Findings'}</th>
                <th style={{ width: '12%', ...thStyle() }} onClick={() => handleSort('rob')}>
                  {isEs ? 'Sesgo (RoB)' : isPt ? 'Viés (RoB)' : 'Bias (RoB)'} <SortIcon active={sortColumn === 'rob'} dir={sortDir} />
                </th>
                <th style={{ width: '8%', ...thStyle() }} onClick={() => handleSort('confidence')}>
                  {isEs ? 'Conf.' : 'Conf.'} <SortIcon active={sortColumn === 'confidence'} dir={sortDir} />
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedStudies.map(study => {
                const sj = study.study_json || {};
                const authors = study.paper?.authors || sj.authors || sj.first_author || '';
                const year = study.paper?.publication_year || sj.year || '';
                const journal = study.paper?.journal || '';
                const design = sj.study_design || study.design || 'Not reported';
                const population = sj.population_description || '—';

                const findings = Array.isArray(sj.outcomes) && sj.outcomes.length > 0
                  ? sj.outcomes.map((o: any) => o.outcome_name).join(', ')
                  : sj.objective || '—';

                const robScore = study.rob_score ? Math.round(study.rob_score * 100) : null;
                let robLevel = 'low';
                if (robScore && robScore > 40 && robScore <= 70) robLevel = 'medium';
                if (robScore && robScore > 70) robLevel = 'high';

                const confNum = Number(study.extraction_confidence);
                const confScore = !isNaN(confNum) ? confNum * 100 : null;

                return (
                  <tr
                    key={study.id}
                    className={selectedIds.has(study.id) ? 'selected' : ''}
                    onClick={() => toggleSelect(study.id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td style={{ textAlign: 'center' }} onClick={e => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.has(study.id)}
                        onChange={() => toggleSelect(study.id)}
                      />
                    </td>
                    {/* Title + authors */}
                    <td>
                      <div style={{ fontWeight: 800, color: '#111827', lineHeight: 1.3, marginBottom: 4 }}>
                        {study.paper_title || study.title || (isEs ? 'Estudio sin título' : isPt ? 'Estudo sem título' : 'Untitled Study')}
                      </div>
                      {authors && (
                        <span className="rc-tag rc-tag--slate" style={{ padding: '2px 8px', fontSize: 11 }}>{authors}</span>
                      )}
                    </td>
                    {/* Year */}
                    <td>
                      {year && (
                        <span className="rc-tag rc-tag--slate" style={{ padding: '2px 8px', fontSize: 11, fontWeight: 700 }}>{year}</span>
                      )}
                    </td>
                    {/* Journal */}
                    <td style={{ fontSize: 12, color: 'var(--rc-text-secondary)', lineHeight: 1.4 }}>
                      {journal
                        ? <span style={{ fontStyle: 'italic' }}>{journal.length > 40 ? journal.slice(0, 40) + '…' : journal}</span>
                        : <span className="rc-muted">—</span>
                      }
                    </td>
                    {/* Design / Population */}
                    <td>
                      <span className="rc-badge rc-tag--primary" style={{ marginBottom: 6 }}>
                        {design}
                      </span>
                      <div style={{ color: 'var(--rc-text-secondary)', lineHeight: 1.5, fontSize: 12 }}>
                        {population.length > 70 ? population.substring(0, 70) + '...' : population}
                      </div>
                      {study.n != null && (
                        <div style={{ fontWeight: 800, marginTop: 4, fontSize: 11, color: 'var(--rc-text)' }}>N = {study.n}</div>
                      )}
                    </td>
                    {/* Key Findings */}
                    <td style={{ color: 'var(--rc-text-secondary)', lineHeight: 1.6, fontSize: 13 }}>
                      {findings.length > 120 ? findings.substring(0, 120) + '...' : findings}
                    </td>
                    {/* RoB */}
                    <td>
                      {robScore !== null ? (
                        <div style={{ paddingRight: 16 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, fontWeight: 700, marginBottom: 2 }}>
                            <span style={{ color: robLevel === 'high' ? 'var(--rc-danger)' : robLevel === 'medium' ? 'var(--rc-warning)' : 'var(--rc-success)' }}>
                              {robLevel === 'low' ? (isEs ? 'Bajo' : isPt ? 'Baixo' : 'Low') : robLevel === 'medium' ? (isEs ? 'Mod' : 'Mod') : (isEs ? 'Alto' : isPt ? 'Alto' : 'High')}
                            </span>
                            <span style={{ color: 'var(--rc-muted)' }}>{robScore}%</span>
                          </div>
                          <div className="rc-rob-bar">
                            <div className={`rc-rob-fill rc-rob-${robLevel}`} style={{ width: `${robScore}%` }} />
                          </div>
                        </div>
                      ) : (
                        <span className="rc-muted">{isEs ? 'Sin datos' : isPt ? 'Sem dados' : 'No data'}</span>
                      )}
                    </td>
                    {/* Confidence */}
                    <td>
                      {confScore !== null ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{
                            width: 32, height: 32, borderRadius: '50%',
                            background: confScore > 80 ? 'var(--rc-success-bg)' : 'var(--rc-warning-bg)',
                            color: confScore > 80 ? 'var(--rc-success)' : 'var(--rc-warning)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontWeight: 800, fontSize: 11,
                          }}>
                            {Math.round(confScore)}
                          </div>
                        </div>
                      ) : (
                        <span className="rc-muted">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
