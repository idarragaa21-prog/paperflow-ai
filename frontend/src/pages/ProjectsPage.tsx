import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { DEMO_MODE, demoProjects, demoCounts } from '../services/demo';
import { useConfirm } from '../ui/Dialog/useConfirm';
import type { Project, ProjectCounts } from '../types/api';

type ApiError = { response?: { data?: { detail?: string } } };

function NewProjectModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [title, setTitle] = useState('');
  const [area, setArea] = useState('');
  const qc = useQueryClient();

  const createMut = useMutation({
    mutationFn: async () => {
      await api.post('/projects', { title: title.trim(), clinical_area: area.trim() || null });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects'] });
      onCreated();
    },
  });

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(10,31,58,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20, zIndex: 60 }}
      onClick={onClose}
    >
      <div className="pg-card" style={{ width: 'min(480px, 96vw)', padding: 24, display: 'flex', flexDirection: 'column', gap: 14 }} onClick={e => e.stopPropagation()}>
        <h2 className="pg-h2">Nuevo proyecto</h2>
        <div>
          <label className="pg-label">Título *</label>
          <input
            className="pg-input"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="e.g. Distal radius fracture outcomes"
            autoFocus
            onKeyDown={e => { if (e.key === 'Enter' && title.trim()) createMut.mutate(); }}
          />
        </div>
        <div>
          <label className="pg-label">Área clínica</label>
          <input
            className="pg-input"
            value={area}
            onChange={e => setArea(e.target.value)}
            placeholder="e.g. Orthopedics"
          />
        </div>
        {createMut.error && (
          <div style={{ padding: '10px 12px', borderRadius: 10, background: '#FEF2F2', border: '1px solid #FECACA', color: '#B91C1C', fontSize: 13 }}>
            {(createMut.error as ApiError)?.response?.data?.detail || 'Create failed'}
          </div>
        )}
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 4 }}>
          <button className="pg-btn pg-btn--ghost" onClick={onClose}>Cancelar</button>
          <button
            className="pg-btn pg-btn--primary"
            disabled={!title.trim() || createMut.isPending}
            onClick={() => createMut.mutate()}
          >
            {createMut.isPending ? 'Creando…' : 'Crear proyecto'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ProjectsPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState('');
  const [showArchived, setShowArchived] = useState(false);
  const [mutError, setMutError] = useState<string | null>(null);

  const { data: projects = [], isLoading } = useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: async () => {
      if (DEMO_MODE) return demoProjects as Project[];
      const r = await api.get('/projects');
      return r.data as Project[];
    },
    staleTime: 30_000,
  });

  const visibleSource = projects.filter(p => (showArchived ? p.archived : !p.archived));

  const { data: countsMap = {} } = useQuery<Record<string, ProjectCounts>>({
    queryKey: ['projects-counts', visibleSource.map(p => p.id).join(',')],
    queryFn: async () => {
      if (DEMO_MODE) return demoCounts as Record<string, ProjectCounts>;
      const entries = await Promise.allSettled(
        visibleSource.map(p => api.get(`/projects/${p.id}/dashboard`).then(r => [p.id, r.data.counts] as [string, ProjectCounts]))
      );
      const map: Record<string, ProjectCounts> = {};
      entries.forEach(e => { if (e.status === 'fulfilled') map[e.value[0]] = e.value[1]; });
      return map;
    },
    enabled: visibleSource.length > 0,
    staleTime: 30_000,
  });

  const archiveMut = useMutation({
    mutationFn: (id: string) => api.post(`/projects/${id}/archive`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
    onError: (e: unknown) => setMutError((e as ApiError)?.response?.data?.detail || 'Failed to archive'),
  });

  const filtered = useMemo(
    () => visibleSource.filter(
      p => !search
        || p.title.toLowerCase().includes(search.toLowerCase())
        || (p.clinical_area || '').toLowerCase().includes(search.toLowerCase())
    ),
    [visibleSource, search]
  );

  const activeCount = projects.filter(p => !p.archived).length;
  const archivedCount = projects.filter(p => p.archived).length;

  return (
    <div className="pg-fade-in pg-stack-lg" role="main">
      {showCreate && (
        <NewProjectModal onClose={() => setShowCreate(false)} onCreated={() => setShowCreate(false)} />
      )}

      <div className="pg-row-between">
        <div>
          <h1 className="pg-h1">Proyectos</h1>
          <p className="pg-muted" style={{ marginTop: 4, fontSize: 14 }}>
            {activeCount} activos · {archivedCount} archivados
          </p>
        </div>
        <div className="pg-row">
          <button className="pg-btn pg-btn--primary" onClick={() => setShowCreate(true)}>
            + Nuevo proyecto
          </button>
        </div>
      </div>

      <div className="pg-row" style={{ gap: 10 }}>
        <div style={{ flex: '1 1 260px', position: 'relative' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--pg-soft)" strokeWidth="1.8" strokeLinecap="round"
            style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}>
            <circle cx="11" cy="11" r="7" /><line x1="16.5" y1="16.5" x2="21" y2="21" />
          </svg>
          <input
            className="pg-input"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar proyectos…"
            style={{ paddingLeft: 36 }}
          />
        </div>
        <div className="pg-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            className={`pg-tab${!showArchived ? ' active' : ''}`}
            onClick={() => setShowArchived(false)}
          >
            Activos ({activeCount})
          </button>
          <button
            type="button"
            role="tab"
            className={`pg-tab${showArchived ? ' active' : ''}`}
            onClick={() => setShowArchived(true)}
          >
            Archivados ({archivedCount})
          </button>
        </div>
      </div>

      {mutError && (
        <div style={{ padding: '10px 12px', borderRadius: 10, background: '#FEF2F2', border: '1px solid #FECACA', color: '#B91C1C', fontSize: 13 }}>
          {mutError}
        </div>
      )}

      {isLoading ? (
        <div className="pg-tile-grid">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="pg-tile" style={{ height: 140, background: 'var(--pg-surface)' }} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="pg-card" style={{ textAlign: 'center', padding: '56px 24px' }}>
          <h3 className="pg-h3" style={{ marginBottom: 6 }}>
            {showArchived ? 'Sin proyectos archivados' : 'Aún no tienes proyectos'}
          </h3>
          <p className="pg-muted" style={{ maxWidth: 440, margin: '0 auto 20px', fontSize: 14 }}>
            {showArchived
              ? 'Los proyectos archivados aparecerán aquí.'
              : 'Crea tu primer proyecto para empezar a organizar tu investigación.'}
          </p>
          {!showArchived && (
            <button className="pg-btn pg-btn--primary" onClick={() => setShowCreate(true)}>
              Crear proyecto
            </button>
          )}
        </div>
      ) : (
        <div className="pg-tile-grid">
          {filtered.map(p => {
            const counts = countsMap[p.id];
            return (
              <div key={p.id} className="pg-tile" style={{ display: 'flex', flexDirection: 'column', gap: 10, cursor: 'default' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  <button
                    type="button"
                    onClick={() => navigate(`/projects/${p.id}/research`)}
                    style={{ flex: 1, background: 'transparent', border: 'none', textAlign: 'left', padding: 0, cursor: 'pointer' }}
                  >
                    <div className="pg-tile-title">{p.title}</div>
                    <div className="pg-tile-sub">{p.clinical_area || 'Sin área clínica'}</div>
                  </button>
                  {!p.archived && !DEMO_MODE && (
                    <button
                      type="button"
                      className="pg-btn pg-btn--ghost pg-btn--sm"
                      title="Archivar"
                      aria-label="Archivar proyecto"
                      style={{ flexShrink: 0, padding: '4px 8px', color: 'var(--pg-soft)' }}
                      onClick={async () => {
                        const ok = await confirm({
                          title: `¿Archivar "${p.title}"?`,
                          body: 'El proyecto y su contenido se archivarán. Puedes restaurarlo desde la pestaña Archivados.',
                          confirmText: 'Archivar',
                        });
                        if (ok) archiveMut.mutate(p.id);
                      }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                        <polyline points="21 8 21 21 3 21 3 8" />
                        <rect x="1" y="3" width="22" height="5" />
                        <line x1="10" y1="12" x2="14" y2="12" />
                      </svg>
                    </button>
                  )}
                </div>
                {counts && (
                  <div className="pg-tile-stats" style={{ marginTop: 'auto' }}>
                    <span><strong>{counts.papers}</strong>papers</span>
                    <span><strong>{counts.references}</strong>refs</span>
                    <span><strong>{counts.notes}</strong>notas</span>
                  </div>
                )}
                {p.archived && (
                  <span className="pg-badge" style={{ alignSelf: 'flex-start' }}>Archivado</span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
