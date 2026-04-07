import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useI18n } from '../i18n';

export default function LoginPage() {
  const login = useAuthStore((s) => s.login);
  const loading = useAuthStore((s) => s.loading);
  const error = useAuthStore((s) => s.error);
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { t } = useI18n();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const invitationToken = searchParams.get('invitation_token');
  const invitationEmail = searchParams.get('email');
  const invitedAfterSignup = searchParams.get('invited') === '1';
  const acceptedProjectId = searchParams.get('accepted_project_id');
  const hasInvitationContext = Boolean(invitationToken || invitedAfterSignup || acceptedProjectId);

  useEffect(() => {
    if (invitationEmail && !email) {
      setEmail(invitationEmail);
    }
  }, [email, invitationEmail]);

  useEffect(() => {
    if (!user) return;
    if (acceptedProjectId) {
      navigate(`/projects/${acceptedProjectId}/research`, { replace: true });
      return;
    }
    if (invitationToken) {
      navigate(`/project-invitations/${invitationToken}`, { replace: true });
      return;
    }
    navigate('/dashboard');
  }, [acceptedProjectId, user, invitationToken, navigate]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await login(email, password);
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--rc-bg)', fontFamily: 'var(--font-sans)' }}>
      {/* Left panel */}
      <div className="login-left-panel" style={{
        flex: '0 0 45%',
        maxWidth: '560px',
        background: 'linear-gradient(145deg, var(--rc-surface-2) 0%, var(--rc-bg) 100%)',
        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
        padding: '64px', borderRight: '1px solid var(--rc-surface-3)',
        position: 'relative', overflow: 'hidden',
      }}>
        {/* Decorative background glow */}
        <div style={{ position:'absolute',inset:0,opacity:0.8,
          backgroundImage:'radial-gradient(circle at 10% 90%, rgba(79, 70, 229, 0.15) 0%, transparent 50%), radial-gradient(circle at 90% 10%, rgba(139, 92, 246, 0.1) 0%, transparent 50%)',
          pointerEvents:'none' }} />

        {/* Logo */}
        <div style={{ position:'relative',zIndex:1,display:'flex',alignItems:'center',gap:16 }}>
          <div style={{ width:48,height:48,borderRadius:14,
            background:'linear-gradient(135deg, var(--rc-primary) 0%, var(--rc-primary-hover) 100%)',
            display:'flex',alignItems:'center',justifyContent:'center',
            boxShadow:'0 8px 30px var(--rc-primary-weak)' }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
          </div>
          <span style={{ fontSize:26,fontWeight:900,color:'var(--rc-text)',letterSpacing:'-0.03em',fontFamily:'var(--font-display)' }}>PaperFlow</span>
        </div>

        {/* Illustration & Value Prop */}
        <div style={{ position:'relative',zIndex:1, marginTop: '20vh' }}>
          <div style={{ fontSize:36,fontWeight:900,color:'var(--rc-text)',letterSpacing:'-0.04em',lineHeight:1.15,fontFamily:'var(--font-display)' }}>
            Your personal <br/>
            <span style={{ color: 'var(--rc-primary)' }}>AI research workspace</span>
          </div>
          <p style={{ marginTop:16,fontSize:16,color:'var(--rc-muted)',lineHeight:1.6, maxWidth: 360 }}>
            Search, extract, analyze, and draft your scientific manuscripts in one cohesive, secure environment.
          </p>

          {/* Feature Badges */}
          <div style={{ display:'flex',flexDirection:'column',gap:14, marginTop: 40 }}>
            {[
              { icon: '🔍', text: 'AI-powered Literature Search' },
              { icon: '📊', text: 'Automated Matrix Extraction' },
              { icon: '📝', text: 'Evidence-grounded Drafting Canvas' }
            ].map((feat, i) =>(
              <div key={i} style={{ display:'flex',alignItems:'center',gap:12, padding: '12px 16px', background: 'var(--rc-surface-2)', borderRadius: 12, border: '1px solid var(--rc-border)', width: 'fit-content', boxShadow: '0 4px 12px rgba(0,0,0,0.02)' }}>
                <span style={{ fontSize:18 }}>{feat.icon}</span>
                <span style={{ fontSize:14,color:'var(--rc-text-secondary)',fontWeight:600 }}>{feat.text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer info left panel */}
        <div style={{ position:'relative',zIndex:1, fontSize: 13, color:'var(--rc-muted)', fontWeight:500 }}>
          © {new Date().getFullYear()} PaperFlow AI. All rights reserved.
        </div>
      </div>

      {/* Right panel */}
      <div style={{ flex:1,display:'flex',alignItems:'center',justifyContent:'center',padding:'48px 32px',background:'var(--rc-bg)' }}>
        
        <div className="rc-card rc-glass" style={{ width:'100%',maxWidth:420, padding: '48px', border: '1px solid rgba(79, 70, 229, 0.1)', boxShadow: '0 20px 40px rgba(0,0,0,0.05)', borderRadius: 24, position: 'relative', overflow: 'hidden' }}>
          {/* Subtle glow inside card */}
          <div style={{ position:'absolute', top: -50, right: -50, width: 150, height: 150, background: 'var(--rc-primary-weak)', filter: 'blur(60px)', borderRadius: '50%', pointerEvents:'none' }} />

          <div style={{ marginBottom:40 }}>
            <h1 style={{ fontSize:32,fontWeight:900,letterSpacing:'-0.03em',color:'var(--rc-text)',fontFamily:'var(--font-display)', margin: 0 }}>
              Welcome back
            </h1>
            <p style={{ marginTop:8,fontSize:15,color:'var(--rc-text-secondary)' }}>Sign in to continue your research.</p>
          </div>

          <form onSubmit={onSubmit} style={{ display:'flex',flexDirection:'column',gap:24, position: 'relative', zIndex: 1 }}>
            {hasInvitationContext ? (
              <div style={{ padding:'14px 16px',borderRadius:12,background:'rgba(99,102,241,0.08)',border:'1px solid rgba(99,102,241,0.2)',color:'#4f46e5',fontSize:14, fontWeight:600 }}>
                {invitedAfterSignup
                  ? acceptedProjectId
                    ? 'Account created. Sign in to open your shared project.'
                    : 'Account created. Sign in to accept your project invitation.'
                  : 'Sign in with the invited email to accept this project invitation.'}
              </div>
            ) : null}
            
            <div style={{ display:'flex',flexDirection:'column',gap:8 }}>
              <label htmlFor="login-email" style={{ fontSize:13, fontWeight:700, color:'var(--rc-text)', letterSpacing:'0.02em', textTransform:'uppercase' }}>Email address</label>
              <input id="login-email" className="rc-input" type="email" value={email} onChange={e=>setEmail(e.target.value)}
                placeholder="you@example.com" autoComplete="email" autoFocus required 
                style={{ fontSize:15, padding: '14px 16px', borderRadius: 12, backgroundColor: 'var(--rc-surface-2)', border: '1px solid var(--rc-border)', transition: 'all 0.2s', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.02)' }}
              />
            </div>
            
            <div style={{ display:'flex',flexDirection:'column',gap:8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label htmlFor="login-password" style={{ fontSize:13, fontWeight:700, color:'var(--rc-text)', letterSpacing:'0.02em', textTransform:'uppercase' }}>Password</label>
                <Link to="/forgot-password" style={{ fontSize:13,color:'var(--rc-primary)', fontWeight:600 }}>Forgot password?</Link>
              </div>
              <div style={{ position:'relative' }}>
                <input id="login-password" className="rc-input" type={showPw?'text':'password'} value={password}
                  onChange={e=>setPassword(e.target.value)} placeholder="••••••••"
                  autoComplete="current-password" required 
                  style={{ fontSize:15, padding: '14px 16px', paddingRight:48, borderRadius: 12, backgroundColor: 'var(--rc-surface-2)', border: '1px solid var(--rc-border)', width: '100%', transition: 'all 0.2s', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.02)' }}
                />
                <button type="button" onClick={()=>setShowPw(!showPw)}
                  aria-label={showPw ? 'Hide password' : 'Show password'}
                  title={showPw ? 'Hide password' : 'Show password'}
                  style={{
                  position:'absolute',right:14,top:'50%',transform:'translateY(-50%)',
                  background:'none',border:'none',cursor:'pointer',padding:4,
                  color:'var(--rc-muted)',lineHeight:1, transition: 'color 0.2s' }}>
                  {showPw
                    ? <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                    : <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                  }
                </button>
              </div>
            </div>

            {error && (
              <div style={{ padding:'12px 16px',borderRadius:12,background:'rgba(239, 68, 68,0.08)',border:'1px solid rgba(239, 68, 68,0.2)',color:'#dc2626',fontSize:14, fontWeight:500 }}>
                {error}
              </div>
            )}

            <button type="submit" className="rc-btn rc-btn--primary" disabled={loading||!email||!password}
              style={{ width:'100%',padding:'14px 16px',fontSize:15,marginTop:8,borderRadius:12, fontWeight:800, letterSpacing: '0.01em', boxShadow: '0 4px 14px var(--rc-primary-weak)', border: 'none' }}>
              {loading
                ? <span style={{ display:'flex',alignItems:'center',gap:10,justifyContent:'center' }}>
                    <span className="rc-spinner" style={{ borderTopColor:'white',width:16,height:16 }}/>{t.auth.signingIn}
                  </span>
                : `Sign In to Workspace`}
            </button>
          </form>

          <div style={{ marginTop:32,textAlign:'center',fontSize:14,color:'var(--rc-text-secondary)', position: 'relative', zIndex: 1 }}>
            {t.auth.noAccount}{' '}
            <Link
              to={invitationToken ? `/signup?invitation_token=${encodeURIComponent(invitationToken)}${invitationEmail ? `&email=${encodeURIComponent(invitationEmail)}` : ''}` : '/signup'}
              style={{ fontWeight:800, color: 'var(--rc-text)', position: 'relative' }}
              className="rc-link-highlight"
            >
              {t.auth.signUp}
            </Link>
          </div>
        </div>
      </div>

      <style>{`
        .login-left-panel { display: flex !important; } 
        @media(max-width:960px){.login-left-panel{display:none!important}}
        .rc-input:focus { border-color: var(--rc-primary) !important; box-shadow: 0 0 0 3px rgba(79,70,229,0.15) !important; }
        .rc-link-highlight:hover { color: var(--rc-primary) !important; text-decoration: underline; }
      `}</style>
    </div>
  );
}
