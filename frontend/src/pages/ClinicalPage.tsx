import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Breadcrumb } from '../components/Breadcrumb';
import type { Project } from '../types/api';

type ConsultMode = 'brief' | 'standard' | 'deep';

type ClinicalConsult = {
  id: string;
  project_id: string | null;
  question: string;
  mode: ConsultMode;
  status: string;
  answer_markdown: string;
  uncertainty_text: string | null;
  limitations_text: string | null;
  used_project_library: boolean;
  used_pubmed: boolean;
  created_at?: string | null;
  sources: Array<{
    id: string;
    source_kind: string;
    title: string | null;
    pmid: string | null;
    doi: string | null;
    year: number | null;
    excerpt: string | null;
    confidence: number | null;
  }>;
  claims: Array<{
    id: string;
    claim_text: string;
    confidence: number | null;
    support_level: string | null;
  }>;
};

function toIsoDate(value?: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString();
}

export default function ClinicalPage() {
  const { projectId: projectRouteId } = useParams();
  const qc = useQueryClient();
  const defaultProjectId = projectRouteId || '';
  const [projectId, setProjectId] = useState(defaultProjectId);
  const [question, setQuestion] = useState('');
  const [mode, setMode] = useState<ConsultMode>('standard');
  const [patient, setPatient] = useState('');
  const [intervention, setIntervention] = useState('');
  const [comparator, setComparator] = useState('');
  const [outcome, setOutcome] = useState('');
  const [useProjectLibrary, setUseProjectLibrary] = useState(true);
  const [usePubmed, setUsePubmed] = useState(true);
  const [selectedConsultId, setSelectedConsultId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canCreate = question.trim().length >= 3;
  const consultsQueryKey = useMemo(() => ['clinical-consults', projectId || 'all'], [projectId]);

  const projectsQuery = useQuery<Pick<Project, 'id' | 'title' | 'clinical_area'>[]>({
    queryKey: ['projects-list-clinical'],
    queryFn: async () => {
      const response = await api.get('/projects');
      return (response.data as Project[])
        .filter((item) => !item.archived)
        .map((item) => ({ id: item.id, title: item.title, clinical_area: item.clinical_area }));
    },
    staleTime: 60_000,
  });

  const consultsQuery = useQuery<ClinicalConsult[]>({
    queryKey: consultsQueryKey,
    queryFn: async () => {
      const params = projectId ? { project_id: projectId } : undefined;
      const response = await api.get('/clinical/consults', { params });
      return response.data as ClinicalConsult[];
    },
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const pico = {
        patient: patient.trim() || null,
        intervention: intervention.trim() || null,
        comparator: comparator.trim() || null,
        outcome: outcome.trim() || null,
      };
      const response = await api.post('/clinical/consults', {
        project_id: projectId || null,
        question: question.trim(),
        mode,
        pico,
        use_project_library: useProjectLibrary,
        use_pubmed: usePubmed,
      });
      return response.data as ClinicalConsult;
    },
    onSuccess: async (consult) => {
      setSelectedConsultId(consult.id);
      setError(null);
      await qc.invalidateQueries({ queryKey: consultsQueryKey });
    },
    onError: (e: unknown) => {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Could not create consult');
    },
  });

  const selectedConsult = useMemo(
    () => consultsQuery.data?.find((item) => item.id === selectedConsultId) || consultsQuery.data?.[0] || null,
    [consultsQuery.data, selectedConsultId],
  );

  const selectedProject = projectsQuery.data?.find((item) => item.id === projectId);
  const breadcrumbItems = projectRouteId && selectedProject
    ? [
        { label: 'Projects', to: '/projects' },
        { label: selectedProject.title, to: `/projects/${projectRouteId}/research` },
        { label: 'Clinical Consults' },
      ]
    : [{ label: 'Clinical Consults' }];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <Breadcrumb items={breadcrumbItems} />

      <div>
        <h1 className="rc-page-title">Clinical Consults</h1>
        <div className="rc-subtitle">
          Quick, grounded clinical answers with traceable sources from your project library and PubMed.
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}

      <div className="rc-card">
        <div className="rc-card-title">New consult</div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10, marginBottom: 10 }}>
          <label className="rc-discover-filter-field">
            <span>Project scope (optional)</span>
            <select className="rc-input" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">All accessible evidence</option>
              {(projectsQuery.data || []).map((project) => (
                <option key={project.id} value={project.id}>
                  {project.title}{project.clinical_area ? ` · ${project.clinical_area}` : ''}
                </option>
              ))}
            </select>
          </label>

          <label className="rc-discover-filter-field">
            <span>Response mode</span>
            <select className="rc-input" value={mode} onChange={(e) => setMode(e.target.value as ConsultMode)}>
              <option value="brief">brief</option>
              <option value="standard">standard</option>
              <option value="deep">deep</option>
            </select>
          </label>
        </div>

        <label className="rc-discover-filter-field" style={{ marginBottom: 10 }}>
          <span>Clinical question</span>
          <textarea
            className="rc-textarea"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. Should aspirin be used for secondary prevention after ischemic stroke?"
            style={{ minHeight: 86 }}
          />
        </label>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10, marginBottom: 10 }}>
          <label className="rc-discover-filter-field">
            <span>PICO - Patient</span>
            <input className="rc-input" value={patient} onChange={(e) => setPatient(e.target.value)} placeholder="population" />
          </label>
          <label className="rc-discover-filter-field">
            <span>PICO - Intervention</span>
            <input className="rc-input" value={intervention} onChange={(e) => setIntervention(e.target.value)} placeholder="intervention" />
          </label>
          <label className="rc-discover-filter-field">
            <span>PICO - Comparator</span>
            <input className="rc-input" value={comparator} onChange={(e) => setComparator(e.target.value)} placeholder="comparator" />
          </label>
          <label className="rc-discover-filter-field">
            <span>PICO - Outcome</span>
            <input className="rc-input" value={outcome} onChange={(e) => setOutcome(e.target.value)} placeholder="outcome" />
          </label>
        </div>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}>
            <input type="checkbox" checked={useProjectLibrary} onChange={(e) => setUseProjectLibrary(e.target.checked)} />
            Use project library first
          </label>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}>
            <input type="checkbox" checked={usePubmed} onChange={(e) => setUsePubmed(e.target.checked)} />
            Fallback to PubMed
          </label>
        </div>

        <div style={{ marginTop: 12 }}>
          <button
            className="rc-btn rc-btn--primary"
            onClick={() => createMutation.mutate()}
            disabled={!canCreate || createMutation.isPending}
          >
            {createMutation.isPending ? 'Generating consult…' : 'Generate consult'}
          </button>
        </div>
      </div>

      <div className="rc-workspace-grid" style={{ gridTemplateColumns: 'minmax(260px, 360px) minmax(0, 1fr)' }}>
        <section className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="rc-card-title" style={{ margin: 0 }}>Recent consults</div>
            <button className="rc-btn rc-btn--sm rc-btn--ghost" aria-label="Refresh" title="Refresh" onClick={() => consultsQuery.refetch()} disabled={consultsQuery.isFetching}>
              {consultsQuery.isFetching ? '…' : '↻'}
            </button>
          </div>

          {(consultsQuery.data || []).length === 0 && !consultsQuery.isFetching ? (
            <div className="rc-muted">No consults yet.</div>
          ) : null}

          {(consultsQuery.data || []).map((consult) => (
            <button
              key={consult.id}
              className="rc-btn"
              style={{
                width: '100%',
                justifyContent: 'flex-start',
                textAlign: 'left',
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: 4,
                borderColor: selectedConsult?.id === consult.id ? 'rgba(79,70,229,0.35)' : undefined,
                background: selectedConsult?.id === consult.id ? 'var(--rc-primary-weak)' : undefined,
              }}
              onClick={() => setSelectedConsultId(consult.id)}
            >
              <div style={{ fontWeight: 700, fontSize: 13 }}>{consult.question}</div>
              <div className="rc-help">{consult.mode} · {toIsoDate(consult.created_at)}</div>
            </button>
          ))}
        </section>

        <section className="rc-card">
          <div className="rc-card-title">Consult response</div>
          {!selectedConsult ? <div className="rc-muted">Select a consult to inspect grounded claims and sources.</div> : null}

          {selectedConsult ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div className="rc-help">
                Mode: <b>{selectedConsult.mode}</b> · Status: <b>{selectedConsult.status}</b> ·
                Sources: <b>{selectedConsult.sources.length}</b> · Claims: <b>{selectedConsult.claims.length}</b>
              </div>

              <div className="rc-card" style={{ padding: 12, background: 'rgba(79,70,229,0.04)' }}>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 13, lineHeight: 1.6 }}>
                  {selectedConsult.answer_markdown || 'No answer content'}
                </pre>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 10 }}>
                <div className="rc-card" style={{ padding: 12 }}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Uncertainty</div>
                  <div className="rc-help">
                    {selectedConsult.uncertainty_text || 'Not explicitly reported for this consult.'}
                  </div>
                </div>
                <div className="rc-card" style={{ padding: 12 }}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Limitations</div>
                  <div className="rc-help">
                    {selectedConsult.limitations_text || 'No limitations summary available.'}
                  </div>
                </div>
              </div>

              <div className="rc-help">
                Evidence scope:
                {' '}
                {selectedConsult.used_project_library ? 'project library' : 'project library disabled'}
                {' + '}
                {selectedConsult.used_pubmed ? 'PubMed fallback enabled' : 'PubMed fallback disabled'}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 10 }}>
                <div className="rc-card" style={{ padding: 12 }}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Grounded claims</div>
                  {selectedConsult.claims.length === 0 ? <div className="rc-muted">No claims.</div> : null}
                  {selectedConsult.claims.map((claim) => (
                    <div key={claim.id} style={{ marginBottom: 8 }}>
                      <div style={{ fontSize: 13 }}>{claim.claim_text}</div>
                      <div className="rc-help">
                        confidence {Number(claim.confidence || 0).toFixed(2)} · {claim.support_level || 'unknown'}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="rc-card" style={{ padding: 12 }}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Sources</div>
                  {selectedConsult.sources.length === 0 ? <div className="rc-muted">No sources.</div> : null}
                  {selectedConsult.sources.map((source) => (
                    <div key={source.id} style={{ marginBottom: 8 }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{source.title || 'Untitled source'}</div>
                      <div className="rc-help">
                        {source.source_kind}
                        {source.year ? ` · ${source.year}` : ''}
                        {source.pmid ? ` · PMID ${source.pmid}` : ''}
                        {source.doi ? ` · DOI ${source.doi}` : ''}
                      </div>
                      {source.excerpt ? <div className="rc-help" style={{ marginTop: 4 }}>{source.excerpt}</div> : null}
                    </div>
                  ))}
                </div>
              </div>

              {selectedConsult.project_id ? (
                <div className="rc-help">
                  Linked project evidence scope is active. You can continue in{' '}
                  <Link to={`/projects/${selectedConsult.project_id}/library`}>Library</Link> or{' '}
                  <Link to={`/projects/${selectedConsult.project_id}/writing`}>Writing</Link>.
                </div>
              ) : null}
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
