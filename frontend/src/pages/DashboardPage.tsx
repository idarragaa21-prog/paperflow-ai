import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { DEMO_MODE, demoProjects, demoCounts } from '../services/demo';
import type { Project, ProjectCounts } from '../types/api';

function NewProjectModal({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
  const [title, setTitle] = useState('');
  const [area, setArea] = useState('');
  const qc = useQueryClient();

  const createMut = useMutation({
    mutationFn: async () => {
      const r = await api.post('/projects', { title: title.trim(), clinical_area: area.trim() || null });
      return r.data as { id: string };
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['dashboard-projects'] });
      onCreated(data.id);
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
            placeholder="e.g. ACL Reconstruction Outcomes"
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
            placeholder="e.g. Orthopedic Surgery"
          />
        </div>
        {createMut.error && (
          <div style={{ padding: '10px 12px', borderRadius: 10, background: '#FEF2F2', border: '1px solid #FECACA', color: '#B91C1C', fontSize: 13 }}>
            {(createMut.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Create failed'}
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

export default function DashboardPage() {
  const user = useAuthStore(s => s.user);
  const navigate = useNavigate();
  const [showNewProject, setShowNewProject] = useState(false);
  const [query, setQuery] = useState('');

  const firstName = (user?.full_name || user?.email || 'Researcher').split(/[\s@]/)[0];
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Buenos días' : hour < 18 ? 'Buenas tardes' : 'Buenas noches';

  const { data: projects = [], isLoading } = useQuery<Project[]>({
    queryKey: ['dashboard-projects'],
    queryFn: async () => {
      if (DEMO_MODE) return demoProjects as Project[];
      const r = await api.get('/projects');
      return r.data as Project[];
    },
    staleTime: 60_000,
  });

  const active = projects.filter(p => !p.archived);

  const { data: countsMap = {} } = useQuery<Record<string, ProjectCounts>>({
    queryKey: ['dashboard-counts', active.map(p => p.id).join(',')],
    queryFn: async () => {
      if (DEMO_MODE) return demoCounts as Record<string, ProjectCounts>;
      const entries = await Promise.allSettled(
        active.slice(0, 6).map(p =>
          api.get(`/projects/${p.id}/dashboard`).then(r => [p.id, r.data.counts] as [string, ProjectCounts])
        )
      );
      const map: Record<string, ProjectCounts> = {};
      entries.forEach(e => { if (e.status === 'fulfilled') map[e.value[0]] = e.value[1]; });
      return map;
    },
    enabled: active.length > 0,
    staleTime: 60_000,
  });

  function onSearch(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    navigate(`/deep-research?q=${encodeURIComponent(q)}`);
  }

  return (
    <div className="pg-fade-in pg-stack-lg">
      {showNewProject && (
        <NewProjectModal
          onClose={() => setShowNewProject(false)}
          onCreated={(id) => { setShowNewProject(false); navigate(`/projects/${id}/research`); }}
        />
      )}

      {DEMO_MODE && (
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'rgba(217,119,6,0.10)', border: '1px solid rgba(217,119,6,0.28)', borderRadius: 999, padding: '4px 10px', fontSize: 12, color: '#B45309', alignSelf: 'flex-start' }}>
          Demo mode — vista previa con datos simulados
        </div>
      )}

      <section className="pg-ask">
        <div className="pg-kicker" style={{ marginBottom: 10 }}>{greeting}, {firstName}</div>
        <h1 className="pg-ask-title">¿Qué vamos a investigar hoy?</h1>
        <p className="pg-ask-sub">
          Escribe tu pregunta clínica y dejaremos que la IA busque, sintetice y cite. O abre un proyecto para continuar.
        </p>
        <form className="pg-ask-box" onSubmit={onSearch}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--pg-soft)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ marginLeft: 8 }}>
            <circle cx="11" cy="11" r="7" />
            <line x1="16.5" y1="16.5" x2="21" y2="21" />
          </svg>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="ej. Eficacia de anticoagulantes orales directos en fibrilación auricular"
            aria-label="Pregunta de investigación"
          />
          <button type="submit" className="pg-btn pg-btn--primary" disabled={!query.trim()}>
            Buscar
          </button>
        </form>
        <div className="pg-chips">
          <button type="button" className="pg-chip" onClick={() => setShowNewProject(true)}>
            + Nuevo proyecto
          </button>
          <Link to="/deep-research" className="pg-chip">Deep Research</Link>
          <Link to="/clinical" className="pg-chip">Consulta clínica</Link>
          <Link to="/projects" className="pg-chip">Ver proyectos</Link>
        </div>
      </section>

      <section>
        <div className="pg-section-head">
          <h2>Proyectos recientes</h2>
          <Link to="/projects" className="pg-link">Ver todos →</Link>
        </div>
        {isLoading ? (
          <div className="pg-tile-grid">
            {[1, 2, 3].map(i => (
              <div key={i} className="pg-tile" style={{ height: 132, background: 'var(--pg-surface)' }} />
            ))}
          </div>
        ) : active.length === 0 ? (
          <div className="pg-card" style={{ textAlign: 'center', padding: '48px 24px' }}>
            <h3 className="pg-h3" style={{ marginBottom: 6 }}>Aún no tienes proyectos</h3>
            <p className="pg-muted" style={{ maxWidth: 440, margin: '0 auto 20px', fontSize: 14 }}>
              Un proyecto agrupa tu pregunta, biblioteca, matriz de extracción y escritura final.
            </p>
            <button className="pg-btn pg-btn--primary" onClick={() => setShowNewProject(true)}>
              Crear tu primer proyecto
            </button>
          </div>
        ) : (
          <div className="pg-tile-grid">
            {active.slice(0, 6).map(p => {
              const c = countsMap[p.id];
              return (
                <Link key={p.id} to={`/projects/${p.id}/research`} className="pg-tile">
                  <div className="pg-tile-title">{p.title}</div>
                  <div className="pg-tile-sub">{p.clinical_area || 'Sin área clínica'}</div>
                  <div className="pg-tile-stats">
                    <span><strong>{c?.papers ?? 0}</strong>papers</span>
                    <span><strong>{c?.references ?? 0}</strong>refs</span>
                    <span><strong>{c?.notes ?? 0}</strong>notas</span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
