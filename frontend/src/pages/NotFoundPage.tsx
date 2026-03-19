import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      minHeight: '100vh', padding: 32, textAlign: 'center', background: 'var(--rc-bg)',
    }}>
      <div style={{
        width: 80, height: 80, borderRadius: 24, marginBottom: 24,
        background: 'linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.12))',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 36, fontWeight: 900, color: 'var(--rc-primary)',
        fontFamily: 'var(--font-display)',
      }}>404</div>
      <div style={{
        fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 22,
        letterSpacing: '-0.03em', marginBottom: 8,
      }}>Page not found</div>
      <div style={{ color: 'var(--rc-muted)', fontSize: 14, maxWidth: 360, marginBottom: 28 }}>
        The page you're looking for doesn't exist or has been moved.
      </div>
      <Link to="/dashboard" className="rc-btn rc-btn--primary" style={{ textDecoration: 'none' }}>
        Back to Dashboard
      </Link>
    </div>
  );
}
