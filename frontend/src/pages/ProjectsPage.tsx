import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { DEMO_MODE, demoProjects, demoCounts } from '../services/demo';
import { useConfirm } from '../ui/Dialog/useConfirm';
import type { Project, ProjectCounts } from '../types/api';

function EmptyState({ archived }: { archived: boolean }) {
  return (
    <div style={{ textAlign:'center',padding:'80px 24px' }}>
      <svg width="88" height="88" viewBox="0 0 88 88" fill="none" style={{ margin:'0 auto 20px',display:'block' }}>
        <rect x="12" y="22" width="52" height="62" rx="7" fill="rgba(99,102,241,0.06)" stroke="rgba(99,102,241,0.18)" strokeWidth="1.5"/>
        <rect x="20" y="14" width="52" height="62" rx="7" fill="rgba(99,102,241,0.06)" stroke="rgba(99,102,241,0.15)" strokeWidth="1.5"/>
        <rect x="28" y="6" width="52" height="62" rx="7" fill="var(--rc-surface)" stroke="rgba(99,102,241,0.22)" strokeWidth="1.5"/>
        <line x1="40" y1="24" x2="70" y2="24" stroke="rgba(99,102,241,0.25)" strokeWidth="2" strokeLinecap="round"/>
        <line x1="40" y1="34" x2="70" y2="34" stroke="rgba(99,102,241,0.25)" strokeWidth="2" strokeLinecap="round"/>
        <line x1="40" y1="44" x2="60" y2="44" stroke="rgba(99,102,241,0.15)" strokeWidth="2" strokeLinecap="round"/>
        {!archived && <><circle cx="76" cy="76" r="18" fill="var(--rc-surface)" stroke="rgba(99,102,241,0.3)" strokeWidth="1.5"/>
        <line x1="76" y1="68" x2="76" y2="84" stroke="rgba(99,102,241,0.6)" strokeWidth="2.5" strokeLinecap="round"/>
        <line x1="68" y1="76" x2="84" y2="76" stroke="rgba(99,102,241,0.6)" strokeWidth="2.5" strokeLinecap="round"/></>}
      </svg>
      <div style={{ fontWeight:700,fontSize:16,fontFamily:'var(--font-display)',letterSpacing:'-0.02em' }}>
        {archived ? 'No archived projects' : 'No projects yet'}
      </div>
      <div style={{ fontSize:13,color:'var(--rc-muted)',marginTop:5 }}>
        {archived ? 'Archived projects will appear here.' : 'Create your first project to get started.'}
      </div>
    </div>
  );
}

export default function ProjectsPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newArea, setNewArea] = useState('');
  const [search, setSearch] = useState('');
  const [tab, setTab] = useState<'active'|'archived'>('active');
  const [mutError, setMutError] = useState<string|null>(null);

  const projectsKey = ['projects'];

  // ── Projects query ────────────────────────────────────────────────────────
  const { data: projects = [], isLoading } = useQuery<Project[]>({
    queryKey: projectsKey,
    queryFn: async () => {
      if (DEMO_MODE) return demoProjects as Project[];
      const r = await api.get('/projects');
      return r.data as Project[];
    },
    staleTime: 30_000,
  });

  // ── Per-project counts (parallel) ────────────────────────────────────────
  const active = projects.filter(p => !p.archived);
  const { data: countsMap = {} } = useQuery<Record<string, ProjectCounts>>({
    queryKey: ['projects-counts', active.map(p => p.id).join(',')],
    queryFn: async () => {
      if (DEMO_MODE) return demoCounts as Record<string, ProjectCounts>;
      const entries = await Promise.allSettled(
        active.map(p => api.get(`/projects/${p.id}/dashboard`).then(r => [p.id, r.data.counts] as [string, ProjectCounts]))
      );
      const map: Record<string, ProjectCounts> = {};
      entries.forEach(e => { if (e.status === 'fulfilled') map[e.value[0]] = e.value[1]; });
      return map;
    },
    enabled: active.length > 0,
    staleTime: 30_000,
  });

  // ── Create mutation ───────────────────────────────────────────────────────
  const createMut = useMutation({
    mutationFn: () => api.post('/projects', { title: newTitle.trim(), clinical_area: newArea.trim() || null }),
    onSuccess: () => {
      setNewTitle(''); setNewArea(''); setShowCreate(false);
      qc.invalidateQueries({ queryKey: projectsKey });
    },
    onError: (e: any) => setMutError(e?.response?.data?.detail || 'Failed to create'),
  });

  const archiveMut = useMutation({
    mutationFn: (id: string) => api.post(`/projects/${id}/archive`),
    onSuccess: () => qc.invalidateQueries({ queryKey: projectsKey }),
    onError: (e: any) => setMutError(e?.response?.data?.detail || 'Failed to archive'),
  });

  const confirm = useConfirm();

  const filtered = useMemo(() =>
    projects
      .filter(p => tab === 'active' ? !p.archived : p.archived)
      .filter(p => !search || p.title.toLowerCase().includes(search.toLowerCase()) || (p.clinical_area || '').toLowerCase().includes(search.toLowerCase())),
    [projects, tab, search]
  );

  return (
    <div className="rc-page-enter" style={{ display:'flex',flexDirection:'column',gap:20 }}>
      <div style={{ display:'flex',alignItems:'flex-start',justifyContent:'space-between',gap:12,flexWrap:'wrap' }}>
        <div>
          <h1 className="rc-page-title">Projects</h1>
          <div className="rc-subtitle">Organize your research, libraries, extraction and writing by project.</div>
        </div>
        <button className="rc-btn rc-btn--primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : '+ New project'}
        </button>
      </div>

      {showCreate && (
        <div className="rc-card" style={{ borderColor:'rgba(99,102,241,0.25)',background:'rgba(99,102,241,0.02)' }}>
          <div className="rc-card-title">New project</div>
          <div style={{ display:'flex',flexDirection:'column',gap:12 }}>
            <div><div className="rc-kicker">Title *</div>
              <input className="rc-input" value={newTitle} onChange={e=>setNewTitle(e.target.value)} placeholder="e.g. Distal radius fracture outcomes in older adults" autoFocus onKeyDown={e=>e.key==='Enter'&&createMut.mutate()}/></div>
            <div><div className="rc-kicker">Clinical area</div>
              <input className="rc-input" value={newArea} onChange={e=>setNewArea(e.target.value)} placeholder="e.g. Orthopedics"/></div>
            <div style={{ display:'flex',gap:10 }}>
              <button className="rc-btn rc-btn--primary" onClick={() => createMut.mutate()} disabled={createMut.isPending || !newTitle.trim()}>
                {createMut.isPending ? <><span className="rc-spinner" style={{ borderTopColor:'white' }}/> Creating…</> : 'Create project'}
              </button>
              <button className="rc-btn" onClick={() => setShowCreate(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {mutError && <div className="rc-error">{mutError}</div>}

      <div style={{ display:'flex',gap:10,alignItems:'center',flexWrap:'wrap' }}>
        <div style={{ flex:'1 1 220px',position:'relative' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--rc-muted)" strokeWidth="2" strokeLinecap="round" style={{ position:'absolute',left:10,top:'50%',transform:'translateY(-50%)',pointerEvents:'none' }}><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
          <input className="rc-input" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search projects…" style={{ paddingLeft:32 }}/>
        </div>
        <div style={{ display:'flex',gap:2,background:'rgba(26,25,41,0.06)',padding:3,borderRadius:10 }}>
          {(['active','archived'] as const).map(t=>(
            <button key={t} onClick={()=>setTab(t)} style={{ padding:'5px 14px',borderRadius:8,border:'none',cursor:'pointer',fontSize:12,fontWeight:600,background:tab===t?'var(--rc-surface)':'transparent',color:tab===t?'var(--rc-text)':'var(--rc-muted)',boxShadow:tab===t?'var(--rc-shadow-sm)':'none',transition:'all 150ms' }}>
              {t==='active'?`Active (${projects.filter(p=>!p.archived).length})`:`Archived (${projects.filter(p=>p.archived).length})`}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div style={{ display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(300px,1fr))',gap:12 }}>
          {[1,2,3,4].map(i=><div key={i} className="rc-card rc-skeleton" style={{ height:140 }}/>)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rc-card"><EmptyState archived={tab==='archived'}/></div>
      ) : (
        <div style={{ display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(300px,1fr))',gap:12 }}>
          {filtered.map(p => {
            const counts = countsMap[p.id];
            return (
              <div key={p.id} className="rc-card rc-card--hover" style={{ display:'flex',flexDirection:'column',gap:10 }}>
                <div style={{ display:'flex',gap:8,alignItems:'flex-start',justifyContent:'space-between' }}>
                  <div style={{ flex:1,cursor:'pointer' }} onClick={()=>navigate(`/projects/${p.id}/research`)}>
                    <div style={{ fontWeight:750,fontSize:14,letterSpacing:'-0.02em',fontFamily:'var(--font-display)',lineHeight:1.35 }}>{p.title}</div>
                    {p.clinical_area && <div className="rc-help" style={{ marginTop:3 }}>{p.clinical_area}</div>}
                  </div>
                  {!p.archived && !DEMO_MODE && (
                    <button
                      className="rc-btn rc-btn--ghost rc-btn--sm"
                      title="Archive project"
                      style={{ flexShrink: 0, padding: '4px 6px', color: 'var(--rc-muted)' }}
                      onClick={async () => {
                        const ok = await confirm({
                          title: `Archive "${p.title}"?`,
                          body: 'The project and all its content will be archived. You can restore it later from the Archived tab.',
                          confirmText: 'Archive',
                        });
                        if (ok) archiveMut.mutate(p.id);
                      }}
                    >
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>
                    </button>
                  )}
                </div>
                {counts && !p.archived && (
                  <div style={{ display:'flex',gap:12,paddingTop:10,borderTop:'1px solid var(--rc-border)',flexWrap:'wrap' }}>
                    {[['Papers',counts.papers,'#4f46e5'],['Refs',counts.references,'#d97706'],['Notes',counts.notes,'#7c3aed'],['Meta',counts.meta_studies_current,'#059669']].map(([l,v,c])=>(
                      <div key={l as string} style={{ fontSize:12,display:'flex',alignItems:'center',gap:4 }}>
                        <span style={{ fontWeight:750,color:c as string }}>{v}</span>
                        <span style={{ color:'var(--rc-muted)' }}>{l}</span>
                      </div>
                    ))}
                  </div>
                )}
                {!p.archived && (
                  <button className="rc-btn rc-btn--primary rc-btn--sm" onClick={()=>navigate(`/projects/${p.id}/research`)} style={{ alignSelf:'flex-start',marginTop:2 }}>
                    Open →
                  </button>
                )}
                {p.archived && <span className="rc-tag rc-tag--slate" style={{ alignSelf:'flex-start' }}>Archived</span>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
