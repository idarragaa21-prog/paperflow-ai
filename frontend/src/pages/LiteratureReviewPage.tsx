import { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { PageHero } from '../components/WorkflowPrimitives';
import type { StudyRow, PaperRow } from '../types/api';

type StudyFull = StudyRow & {
  study_json?: any;
  paper?: PaperRow;
};

export default function LiteratureReviewPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [studies, setStudies] = useState<StudyFull[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Selection state for sending to drafts
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const loadData = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      // 1. Load studies
      const rStudies = await api.get(`/meta/studies?project_id=${projectId}`);
      const studiesData = rStudies.data as StudyRow[];
      
      // 2. Load papers to attach authors
      const rPapers = await api.get(`/projects/${projectId}/library`);
      const papersMap = new Map((rPapers.data as PaperRow[]).map(p => [p.id, p]));
      
      // 3. For each study, we need its json. This might be heavy if there are many studies,
      // but for a Comparison Matrix to show Population/Findings, we need `study_json`.
      // We will do a parallel Promise.all, or just fetch them one by one.
      const studiesFull = await Promise.all(
        studiesData.map(async (st) => {
          try {
            const stDetail = await api.get(`/meta/studies/${st.id}`);
            return {
              ...st,
              study_json: stDetail.data?.study_json,
              paper: stDetail.data?.paper_id ? papersMap.get(stDetail.data.paper_id) : undefined
            } as StudyFull;
          } catch {
            return {
              ...st,
              paper: (st as any).paper_id ? papersMap.get((st as any).paper_id) : undefined
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

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };
  
  const toggleAll = () => {
    if (selectedIds.size === studies.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(studies.map(s => s.id)));
  }

  const handleSendToDraft = () => {
    if (selectedIds.size === 0) return;
    const ids = Array.from(selectedIds).join(',');
    navigate(`/projects/${projectId}/drafts?studies=${ids}`);
  };

  return (
    <div className="rc-page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <PageHero
        eyebrow="Analysis"
        title="Literature Comparison Matrix"
        subtitle="Compare studies side-by-side to identify patterns, evaluate risk of bias, and consolidate structured evidence."
        metrics={[
          { label: 'studies extracted', value: studies.length, tone: 'success' },
          { label: 'selected', value: selectedIds.size, tone: selectedIds.size > 0 ? 'primary' : 'neutral' },
        ]}
        actions={
          <button 
            className="rc-btn rc-btn--primary" 
            disabled={selectedIds.size === 0}
            onClick={handleSendToDraft}
            style={{ fontWeight: 600, boxShadow: '0 4px 10px rgba(79, 70, 229, 0.25)' }}
          >
            ✍️ Send {selectedIds.size > 0 ? selectedIds.size : ''} to AI Drafts →
          </button>
        }
      />

      {loading ? (
        <div className="rc-card" style={{ padding: 40, textAlign: 'center' }}>
          <div className="rc-spinner" style={{ margin: '0 auto 12px' }} />
          <div>Compiling matrix...</div>
        </div>
      ) : error ? (
        <div className="rc-error">{error}</div>
      ) : studies.length === 0 ? (
        <div className="rc-card rc-muted" style={{ padding: 40, textAlign: 'center' }}>
          No extracted studies found. Go to the Extraction (Meta) step to process papers first.
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
                <th style={{ width: '22%' }}>Study</th>
                <th style={{ width: '20%' }}>Design / Population</th>
                <th style={{ width: '28%' }}>Key Findings</th>
                <th style={{ width: '15%' }}>Bias (RoB)</th>
                <th style={{ width: '15%' }}>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {studies.map(study => {
                const sj = study.study_json || {};
                const authors = study.paper?.authors || sj.authors || sj.first_author || '';
                const year = study.paper?.publication_year || sj.year || '';
                const design = sj.study_design || study.design || 'Not reported';
                const population = sj.population_description || '—';
                
                const findings = Array.isArray(sj.outcomes) && sj.outcomes.length > 0
                  ? sj.outcomes.map((o:any) => o.outcome_name).join(', ')
                  : sj.objective || '—';

                // RoB
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
                    <td style={{ textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                      <input 
                        type="checkbox" 
                        checked={selectedIds.has(study.id)} 
                        onChange={() => toggleSelect(study.id)}
                      />
                    </td>
                    <td>
                      <div style={{ fontWeight: 800, color: '#111827', lineHeight: 1.3, marginBottom: 6 }}>
                        {study.paper_title || study.title || 'Untitled Study'}
                      </div>
                      <div className="rc-row" style={{ gap: 6 }}>
                        {authors && <span className="rc-tag rc-tag--slate" style={{ padding: '2px 8px', fontSize: 11 }}>{authors}</span>}
                        {year && <span className="rc-tag rc-tag--slate" style={{ padding: '2px 8px', fontSize: 11, fontWeight: 700 }}>{year}</span>}
                      </div>
                    </td>
                    <td>
                      <span className="rc-badge rc-tag--primary" style={{ marginBottom: 6 }}>
                        {design}
                      </span>
                      <div style={{ color: 'var(--rc-text-secondary)', lineHeight: 1.5, fontSize: 12 }}>
                        {population.length > 80 ? population.substring(0, 80) + '...' : population}
                      </div>
                      {study.n != null && (
                         <div style={{ fontWeight: 800, marginTop: 4, fontSize: 11, color: 'var(--rc-text)' }}>N = {study.n}</div>
                      )}
                    </td>
                    <td style={{ color: 'var(--rc-text-secondary)', lineHeight: 1.6, fontSize: 13 }}>
                      {findings.length > 140 ? findings.substring(0, 140) + '...' : findings}
                    </td>
                    <td>
                      {robScore !== null ? (
                        <div style={{ paddingRight: 20 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, fontWeight: 700, marginBottom: 2 }}>
                            <span style={{ color: robLevel === 'high' ? 'var(--rc-danger)' : robLevel === 'medium' ? 'var(--rc-warning)' : 'var(--rc-success)' }}>
                              {robLevel === 'low' ? 'Low' : robLevel === 'medium' ? 'Mod' : 'High'}
                            </span>
                            <span style={{ color: 'var(--rc-muted)' }}>{robScore}%</span>
                          </div>
                          <div className="rc-rob-bar">
                            <div className={`rc-rob-fill rc-rob-${robLevel}`} style={{ width: `${robScore}%` }} />
                          </div>
                        </div>
                      ) : (
                        <span className="rc-muted">No data</span>
                      )}
                    </td>
                    <td>
                      {confScore !== null ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{ 
                            width: 32, height: 32, borderRadius: '50%', 
                            background: confScore > 80 ? 'var(--rc-success-bg)' : 'var(--rc-warning-bg)',
                            color: confScore > 80 ? 'var(--rc-success)' : 'var(--rc-warning)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontWeight: 800, fontSize: 11
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
