import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { DEMO_MODE, demoProjects, demoCounts } from '../services/demo';
import type { Project, ProjectCounts } from '../types/api';

function StatCard({ label, value, color, icon }: { label: string; value: number; color: string; icon: React.ReactNode }) {
  return (
    <div className="rc-card" style={{ display:'flex',alignItems:'center',gap:14 }}>
      <div style={{ width:44,height:44,borderRadius:12,background:color,display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0 }}>{icon}</div>
      <div>
        <div style={{ fontSize:24,fontWeight:850,letterSpacing:'-0.04em',fontFamily:'var(--font-display)',lineHeight:1 }}>{value}</div>
        <div style={{ fontSize:12,color:'var(--rc-muted)',marginTop:3 }}>{label}</div>
      </div>
    </div>
  );
}

// Quick access icon definitions with real SVGs
const quickLinks = [
  {
    label: 'Books & Scans',
    sub: 'Manage book library',
    to: '/books',
    color: 'rgba(59,130,246,0.1)',
    stroke: 'rgba(59,130,246,0.85)',
    icon: (stroke: string) => (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 3h10a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"/>
        <path d="M8 3v14M12 7h2M12 10h2"/>
      </svg>
    ),
  },
  {
    label: 'Clinical Sheets',
    sub: 'AI-powered clinical summaries',
    to: '/clinical',
    color: 'rgba(16,185,129,0.1)',
    stroke: 'rgba(16,185,129,0.85)',
    icon: (stroke: string) => (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2v4M10 4h4"/>
        <rect x="3" y="6" width="18" height="16" rx="2"/>
        <path d="M8 12h8M8 16h6"/>
      </svg>
    ),
  },
  {
    label: 'Background Jobs',
    sub: 'Processing & downloads',
    to: '/jobs',
    color: 'rgba(245,158,11,0.1)',
    stroke: 'rgba(245,158,11,0.85)',
    icon: (stroke: string) => (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="9"/>
        <path d="M12 7v5l3 3"/>
      </svg>
    ),
  },
  {
    label: 'Deep Research',
    sub: 'Automated literature review',
    to: '/deep-research',
    color: 'rgba(139,92,246,0.1)',
    stroke: 'rgba(139,92,246,0.85)',
    icon: (stroke: string) => (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="10" r="6"/>
        <path d="M20 20l-4-4"/>
        <path d="M8 10h6M11 7v6"/>
      </svg>
    ),
  },
];

export default function DashboardPage() {
  const user = useAuthStore(s => s.user);
  const navigate = useNavigate();
  const firstName = (user?.full_name || user?.email || 'Researcher').split(/[\s@]/)[0];
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

  // ── Projects query ────────────────────────────────────────────────────────
  const { data: projects = [], isLoading } = useQuery<Project[]>({
    queryKey: ['dashboard-projects'],
    queryFn: async () => {
      if (DEMO_MODE) return demoProjects as Project[];
      const r = await api.get('/projects');
      return r.data as Project[];
    },
    staleTime: 60_000,
  });

  // ── Per-project counts (parallel) ────────────────────────────────────────
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

  const totalPapers = Object.values(countsMap).reduce((s, c) => s + c.papers, 0);
  const totalRefs   = Object.values(countsMap).reduce((s, c) => s + c.references, 0);
  const totalNotes  = Object.values(countsMap).reduce((s, c) => s + c.notes, 0);

  return (
    <div className="rc-page-enter" style={{ display:'flex',flexDirection:'column',gap:24 }}>

      {/* ── Hero ───────────────────────────────────────────────────────────── */}
      <div style={{ borderRadius:20,padding:'28px 32px',background:'linear-gradient(135deg,#1a1040 0%,#13122a 100%)',position:'relative',overflow:'hidden' }}>
        <div style={{ position:'absolute',inset:0,opacity:0.5,backgroundImage:'radial-gradient(circle at 80% 50%,rgba(139,92,246,0.18) 0%,transparent 50%)',pointerEvents:'none' }}/>
        <div style={{ position:'relative',zIndex:1 }}>
          <div style={{ fontSize:22,fontWeight:800,color:'white',letterSpacing:'-0.03em',fontFamily:'var(--font-display)' }}>
            {greeting}, {firstName} 👋
          </div>
          <div style={{ fontSize:13,color:'rgba(255,255,255,0.45)',marginTop:6 }}>
            {active.length === 0
              ? 'Create your first research project to get started.'
              : `${active.length} active project${active.length !== 1 ? 's' : ''} · ${totalPapers} paper${totalPapers !== 1 ? 's' : ''} · ${totalRefs} reference${totalRefs !== 1 ? 's' : ''}`}
          </div>
          {DEMO_MODE && (
            <div style={{ marginTop:10,display:'inline-flex',alignItems:'center',gap:6,background:'rgba(245,158,11,0.15)',border:'1px solid rgba(245,158,11,0.3)',borderRadius:8,padding:'4px 10px',fontSize:12,color:'rgba(245,158,11,0.9)' }}>
              <svg width="12" height="12" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><circle cx="10" cy="10" r="8"/><path d="M10 6v4M10 14h.01"/></svg>
              Demo mode — UI preview with mock data
            </div>
          )}
          <div style={{ marginTop:18,display:'flex',gap:10,flexWrap:'wrap' }}>
            <Link to="/projects" className="rc-btn" style={{ textDecoration:'none',background:'rgba(255,255,255,0.12)',border:'1px solid rgba(255,255,255,0.18)',color:'white' }}>
              View Projects
            </Link>
            {active.length > 0 && (
              <Link to="/clinical" className="rc-btn" style={{ textDecoration:'none',background:'rgba(255,255,255,0.06)',border:'1px solid rgba(255,255,255,0.1)',color:'rgba(255,255,255,0.7)' }}>
                Clinical Sheets
              </Link>
            )}
            {active.length === 0 && (
              <Link to="/projects" className="rc-btn rc-btn--primary" style={{ textDecoration:'none' }}>
                Create First Project
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* ── Stats ──────────────────────────────────────────────────────────── */}
      {!isLoading && active.length > 0 && (
        <div style={{ display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(175px,1fr))',gap:12 }}>
          <StatCard label="Active projects" value={active.length} color="rgba(99,102,241,0.12)"
            icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="rgba(99,102,241,0.9)" strokeWidth="2" strokeLinecap="round"><rect x="2" y="3" width="8" height="8" rx="1.5"/><rect x="14" y="3" width="8" height="8" rx="1.5"/><rect x="2" y="13" width="8" height="8" rx="1.5"/><rect x="14" y="13" width="8" height="8" rx="1.5"/></svg>}/>
          <StatCard label="Total papers" value={totalPapers} color="rgba(16,185,129,0.12)"
            icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="rgba(16,185,129,0.9)" strokeWidth="2" strokeLinecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>}/>
          <StatCard label="References" value={totalRefs} color="rgba(245,158,11,0.12)"
            icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="rgba(245,158,11,0.9)" strokeWidth="2" strokeLinecap="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>}/>
          <StatCard label="Notes" value={totalNotes} color="rgba(139,92,246,0.12)"
            icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="rgba(139,92,246,0.9)" strokeWidth="2" strokeLinecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>}/>
        </div>
      )}

      {/* ── Recent projects ────────────────────────────────────────────────── */}
      <div>
        <div style={{ display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12 }}>
          <div style={{ fontFamily:'var(--font-display)',fontWeight:700,fontSize:16,letterSpacing:'-0.02em' }}>Recent projects</div>
          <Link to="/projects" style={{ fontSize:12,color:'var(--rc-primary)',textDecoration:'none' }}>View all →</Link>
        </div>
        {isLoading ? (
          <div style={{ display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))',gap:12 }}>
            {[1,2,3].map(i=><div key={i} className="rc-card rc-skeleton" style={{ height:110 }}/>)}
          </div>
        ) : active.length === 0 ? (
          <div className="rc-card" style={{ textAlign:'center',padding:'48px 24px',color:'var(--rc-muted)' }}>
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" style={{ margin:'0 auto 14px',display:'block' }}>
              <rect x="6" y="10" width="36" height="28" rx="4" stroke="rgba(26,25,41,0.18)" strokeWidth="1.5" fill="none"/>
              <path d="M24 20v8M20 24h8" stroke="rgba(99,102,241,0.5)" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            <div style={{ fontWeight:700,fontSize:14,marginBottom:6 }}>No projects yet</div>
            <div style={{ fontSize:13,marginBottom:16 }}>Create a project to organize your research papers, notes, and analyses.</div>
            <Link to="/projects" className="rc-btn rc-btn--primary" style={{ textDecoration:'none' }}>Create first project</Link>
          </div>
        ) : (
          <div style={{ display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))',gap:12 }}>
            {active.slice(0,6).map(p => {
              const c = countsMap[p.id];
              return (
                <div key={p.id} className="rc-card rc-card--hover" onClick={()=>navigate(`/projects/${p.id}/research`)} style={{ display:'flex',flexDirection:'column',gap:10,cursor:'pointer' }}>
                  <div style={{ display:'flex',alignItems:'flex-start',justifyContent:'space-between',gap:8 }}>
                    <div style={{ fontWeight:750,fontSize:14,letterSpacing:'-0.02em',fontFamily:'var(--font-display)',lineHeight:1.35 }}>{p.title}</div>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--rc-muted)" strokeWidth="2" strokeLinecap="round" style={{ flexShrink:0,marginTop:2 }}><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                  </div>
                  {p.clinical_area && <div className="rc-help">{p.clinical_area}</div>}
                  {c ? (
                    <div style={{ display:'flex',gap:14,marginTop:'auto',paddingTop:8,borderTop:'1px solid var(--rc-border)' }}>
                      {([['Papers',c.papers,'#4f46e5'],['Refs',c.references,'#d97706'],['Notes',c.notes,'#7c3aed']] as [string,number,string][]).map(([l,v,col])=>(
                        <div key={l} style={{ fontSize:12 }}>
                          <span style={{ fontWeight:750,color:col }}>{v}</span>
                          <span style={{ color:'var(--rc-muted)',marginLeft:3 }}>{l}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ marginTop:'auto',paddingTop:8,borderTop:'1px solid var(--rc-border)',height:24,display:'flex',alignItems:'center' }}>
                      <div className="rc-skeleton" style={{ height:10,width:'60%',borderRadius:6 }}/>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Quick access ───────────────────────────────────────────────────── */}
      <div>
        <div style={{ fontFamily:'var(--font-display)',fontWeight:700,fontSize:16,letterSpacing:'-0.02em',marginBottom:12 }}>Quick access</div>
        <div style={{ display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(190px,1fr))',gap:10 }}>
          {quickLinks.map(item=>(
            <Link key={item.to} to={item.to} style={{ textDecoration:'none' }}>
              <div className="rc-card rc-card--hover" style={{ display:'flex',alignItems:'center',gap:12 }}>
                <div style={{ width:38,height:38,borderRadius:10,background:item.color,flexShrink:0,display:'flex',alignItems:'center',justifyContent:'center' }}>
                  {item.icon(item.stroke)}
                </div>
                <div>
                  <div style={{ fontWeight:700,fontSize:13 }}>{item.label}</div>
                  <div className="rc-help">{item.sub}</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
