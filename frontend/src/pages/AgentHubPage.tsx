import { Link, useNavigate } from 'react-router-dom';
import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import type { Project } from '../types/api';

type AgentMode = 'clinical' | 'research';

export default function AgentHubPage() {
  const navigate = useNavigate();
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [mode, setMode] = useState<AgentMode>('clinical');

  const projectsQuery = useQuery<Pick<Project, 'id' | 'title' | 'clinical_area'>[]>({
    queryKey: ['agent-hub-projects'],
    queryFn: async () => {
      const response = await api.get('/projects');
      return (response.data as Project[])
        .filter((item) => !item.archived)
        .map((item) => ({ id: item.id, title: item.title, clinical_area: item.clinical_area }));
    },
    staleTime: 60_000,
  });

  const selectedProject = useMemo(
    () => projectsQuery.data?.find((project) => project.id === selectedProjectId) || null,
    [projectsQuery.data, selectedProjectId],
  );

  function openAgent() {
    if (mode === 'clinical') {
      if (selectedProjectId) {
        navigate(`/projects/${selectedProjectId}/clinical-consults`);
        return;
      }
      navigate('/clinical');
      return;
    }
    navigate('/deep-research');
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Agent Hub</h1>
        <div className="rc-subtitle">
          Use specialized agents without leaving the canonical project workflow.
          Clinical consults stay concise and grounded; deep research produces bibliographic synthesis.
        </div>
      </div>

      <section className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div className="rc-card-title">Start an agent flow</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 10 }}>
          <button
            className="rc-btn"
            style={{
              justifyContent: 'flex-start',
              borderColor: mode === 'clinical' ? 'rgba(79,70,229,0.35)' : undefined,
              background: mode === 'clinical' ? 'var(--rc-primary-weak)' : undefined,
            }}
            onClick={() => setMode('clinical')}
          >
            Clinical Consults
          </button>
          <button
            className="rc-btn"
            style={{
              justifyContent: 'flex-start',
              borderColor: mode === 'research' ? 'rgba(79,70,229,0.35)' : undefined,
              background: mode === 'research' ? 'var(--rc-primary-weak)' : undefined,
            }}
            onClick={() => setMode('research')}
          >
            Deep Research
          </button>
        </div>

        <label className="rc-discover-filter-field">
          <span>Project context (optional for global mode)</span>
          <select className="rc-input" value={selectedProjectId} onChange={(event) => setSelectedProjectId(event.target.value)}>
            <option value="">No project selected</option>
            {(projectsQuery.data || []).map((project) => (
              <option key={project.id} value={project.id}>
                {project.title}{project.clinical_area ? ` · ${project.clinical_area}` : ''}
              </option>
            ))}
          </select>
        </label>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button className="rc-btn rc-btn--primary" onClick={openAgent}>
            Open {mode === 'clinical' ? 'Clinical Consults' : 'Deep Research'}
          </button>
          {selectedProject ? (
            <Link className="rc-btn" style={{ textDecoration: 'none' }} to={`/projects/${selectedProject.id}/research`}>
              Open {selectedProject.title}
            </Link>
          ) : null}
        </div>
      </section>

      <section className="rc-card">
        <div className="rc-card-title">Canonical workflow reminder</div>
        <div className="rc-help">
          The default delivery path remains:
          {' '}<b>research</b> → <b>library</b> → <b>reader</b> → <b>extraction</b> → <b>matrix</b> → <b>meta runs</b> →
          {' '}<b>artifacts</b> → <b>references</b> → <b>writing</b> → <b>clinical consults</b>.
        </div>
      </section>
    </div>
  );
}
