import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useI18n } from '../i18n';

export default function LoginPage() {
  const login = useAuthStore((s) => s.login);
  const loading = useAuthStore((s) => s.loading);
  const error = useAuthStore((s) => s.error);
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  const { t } = useI18n();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);

  useEffect(() => {
    if (user) navigate('/dashboard');
  }, [user, navigate]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await login(email, password);
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#0f0e1a' }}>
      {/* Left panel */}
      <div className="login-left-panel" style={{
        flex: '0 0 460px',
        background: 'linear-gradient(145deg, #13122a 0%, #1a1040 50%, #0e1628 100%)',
        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
        padding: '48px', borderRight: '1px solid rgba(255,255,255,0.06)',
        position: 'relative', overflow: 'hidden',
      }}>
        <div style={{ position:'absolute',inset:0,opacity:0.6,
          backgroundImage:'radial-gradient(circle at 20% 80%, rgba(99,102,241,0.18) 0%, transparent 60%), radial-gradient(circle at 80% 20%, rgba(139,92,246,0.12) 0%, transparent 50%)',
          pointerEvents:'none' }} />

        {/* Logo */}
        <div style={{ position:'relative',zIndex:1,display:'flex',alignItems:'center',gap:12 }}>
          <div style={{ width:40,height:40,borderRadius:12,
            background:'linear-gradient(135deg,#6366f1,#8b5cf6)',
            display:'flex',alignItems:'center',justifyContent:'center',
            boxShadow:'0 4px 20px rgba(99,102,241,0.4)' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
          </div>
          <span style={{ fontSize:20,fontWeight:800,color:'white',letterSpacing:'-0.03em',fontFamily:'var(--font-display)' }}>PaperFlow</span>
        </div>

        {/* Illustration */}
        <div style={{ position:'relative',zIndex:1 }}>
          <svg width="300" height="240" viewBox="0 0 300 240" fill="none" style={{ display:'block',margin:'0 auto' }}>
            {[[0,0],[0,1],[0,2],[0,3],[0,4],[0,5],[1,0],[1,1],[1,2],[1,3],[1,4],[1,5],[2,0],[2,1],[2,2],[2,3],[2,4],[2,5],[3,0],[3,1],[3,2],[3,3],[3,4],[3,5],[4,0],[4,1],[4,2],[4,3],[4,4],[4,5]].map(([r,c])=>
              <circle key={`${r}-${c}`} cx={c*52+10} cy={r*48+10} r="1.5" fill="rgba(255,255,255,0.08)"/>
            )}
            <rect x="52" y="48" width="110" height="140" rx="10" fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.08)" strokeWidth="1"/>
            <rect x="60" y="40" width="110" height="140" rx="10" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.1)" strokeWidth="1"/>
            <rect x="68" y="32" width="110" height="140" rx="10" fill="rgba(99,102,241,0.12)" stroke="rgba(99,102,241,0.28)" strokeWidth="1"/>
            <line x1="86" y1="64" x2="158" y2="64" stroke="rgba(255,255,255,0.22)" strokeWidth="1.5" strokeLinecap="round"/>
            <line x1="86" y1="79" x2="158" y2="79" stroke="rgba(255,255,255,0.22)" strokeWidth="1.5" strokeLinecap="round"/>
            <line x1="86" y1="94" x2="142" y2="94" stroke="rgba(255,255,255,0.22)" strokeWidth="1.5" strokeLinecap="round"/>
            <line x1="86" y1="115" x2="158" y2="115" stroke="rgba(255,255,255,0.1)" strokeWidth="1" strokeLinecap="round"/>
            <line x1="86" y1="127" x2="158" y2="127" stroke="rgba(255,255,255,0.1)" strokeWidth="1" strokeLinecap="round"/>
            <line x1="86" y1="139" x2="146" y2="139" stroke="rgba(255,255,255,0.1)" strokeWidth="1" strokeLinecap="round"/>
            <circle cx="218" cy="78" r="34" fill="rgba(139,92,246,0.1)" stroke="rgba(139,92,246,0.22)" strokeWidth="1"/>
            <circle cx="218" cy="78" r="20" fill="rgba(139,92,246,0.14)" stroke="rgba(139,92,246,0.32)" strokeWidth="1"/>
            <text x="218" y="84" textAnchor="middle" fill="rgba(167,139,250,0.9)" fontSize="16">✦</text>
            <line x1="194" y1="78" x2="178" y2="88" stroke="rgba(139,92,246,0.3)" strokeWidth="1" strokeDasharray="3 3"/>
            <line x1="218" y1="112" x2="192" y2="138" stroke="rgba(99,102,241,0.3)" strokeWidth="1" strokeDasharray="3 3"/>
            <rect x="80" y="158" width="58" height="16" rx="8" fill="rgba(99,102,241,0.18)" stroke="rgba(99,102,241,0.32)" strokeWidth="1"/>
            <text x="109" y="169" textAnchor="middle" fill="rgba(129,140,248,0.9)" fontSize="8.5" fontWeight="700">READY</text>
            <rect x="146" y="158" width="48" height="16" rx="8" fill="rgba(21,128,61,0.18)" stroke="rgba(21,128,61,0.32)" strokeWidth="1"/>
            <text x="170" y="169" textAnchor="middle" fill="rgba(74,222,128,0.9)" fontSize="8.5" fontWeight="700">CITED</text>
          </svg>
          <div style={{ marginTop:20,textAlign:'center' }}>
            <div style={{ fontSize:21,fontWeight:800,color:'white',letterSpacing:'-0.03em',lineHeight:1.25,fontFamily:'var(--font-display)' }}>
              Your personal<br/>AI research workspace
            </div>
            <div style={{ marginTop:8,fontSize:13,color:'rgba(255,255,255,0.4)',lineHeight:1.6 }}>
              Search, extract, analyze and write<br/>— everything local, nothing in the cloud.
            </div>
          </div>
        </div>

        {/* Features */}
        <div style={{ position:'relative',zIndex:1,display:'flex',flexDirection:'column',gap:8 }}>
          {['AI-powered paper search & reader','Meta-analysis & data extraction','Literature drafts & references'].map(feat=>(
            <div key={feat} style={{ display:'flex',alignItems:'center',gap:10 }}>
              <span style={{ color:'rgba(139,92,246,0.7)',fontSize:8 }}>✦</span>
              <span style={{ fontSize:12,color:'rgba(255,255,255,0.38)',letterSpacing:'0.01em' }}>{feat}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Right panel */}
      <div style={{ flex:1,display:'flex',alignItems:'center',justifyContent:'center',padding:'48px 32px',background:'#f7f6f2' }}>
        <div style={{ width:'100%',maxWidth:380 }}>
          <div style={{ marginBottom:36 }}>
            <div style={{ fontSize:26,fontWeight:850,letterSpacing:'-0.03em',color:'#1a1929',fontFamily:'var(--font-display)' }}>
              Welcome back
            </div>
            <div style={{ marginTop:6,fontSize:14,color:'rgba(26,25,41,0.5)' }}>Sign in to your workspace</div>
          </div>

          <form onSubmit={onSubmit} style={{ display:'flex',flexDirection:'column',gap:16 }}>
            <div>
              <div className="rc-kicker">Email</div>
              <input className="rc-input" type="email" value={email} onChange={e=>setEmail(e.target.value)}
                placeholder="you@example.com" autoComplete="email" autoFocus required style={{ fontSize:14 }}/>
            </div>
            <div>
              <div className="rc-kicker">Password</div>
              <div style={{ position:'relative' }}>
                <input className="rc-input" type={showPw?'text':'password'} value={password}
                  onChange={e=>setPassword(e.target.value)} placeholder="••••••••"
                  autoComplete="current-password" required style={{ fontSize:14,paddingRight:44 }}/>
                <button type="button" onClick={()=>setShowPw(!showPw)} style={{
                  position:'absolute',right:12,top:'50%',transform:'translateY(-50%)',
                  background:'none',border:'none',cursor:'pointer',padding:4,
                  color:'rgba(26,25,41,0.4)',lineHeight:1 }}>
                  {showPw
                    ? <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                    : <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                  }
                </button>
              </div>
            </div>

            {error && (
              <div style={{ padding:'10px 14px',borderRadius:10,background:'rgba(185,28,28,0.08)',border:'1px solid rgba(185,28,28,0.18)',color:'#b91c1c',fontSize:13 }}>
                {error}
              </div>
            )}

            <button type="submit" className="rc-btn rc-btn--primary" disabled={loading||!email||!password}
              style={{ width:'100%',padding:'11px 16px',fontSize:14,marginTop:4,borderRadius:12 }}>
              {loading
                ? <span style={{ display:'flex',alignItems:'center',gap:8,justifyContent:'center' }}>
                    <span className="rc-spinner" style={{ borderTopColor:'white',width:14,height:14 }}/>{t.auth.signingIn}
                  </span>
                : `${t.auth.signIn} →`}
            </button>

            <div style={{ display:'flex',justifyContent:'center',marginTop:10 }}>
              <Link to="/forgot-password" style={{ fontSize:12,color:'var(--rc-primary)' }}>{t.auth.forgotPassword}</Link>
            </div>
          </form>

          <div style={{ marginTop:20,textAlign:'center',fontSize:13,color:'rgba(26,25,41,0.5)' }}>
            {t.auth.noAccount}{' '}
            <Link to="/signup" style={{ fontWeight:700 }}>{t.auth.signUp}</Link>
          </div>

          <div style={{ marginTop:20,paddingTop:20,borderTop:'1px solid rgba(26,25,41,0.1)',textAlign:'center',fontSize:12,color:'rgba(26,25,41,0.3)' }}>
            {t.auth.tagline}
          </div>
        </div>
      </div>

      <style>{`.login-left-panel { display: flex !important; } @media(max-width:780px){.login-left-panel{display:none!important}}`}</style>
    </div>
  );
}
