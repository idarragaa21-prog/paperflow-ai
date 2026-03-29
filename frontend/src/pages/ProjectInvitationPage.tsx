import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import type { ProjectInvitationLookup } from '../types/api';

const ROLE_LABELS: Record<string, string> = {
  owner: 'Owner',
  editor: 'Editor',
  viewer: 'Viewer',
};

export default function ProjectInvitationPage() {
  const { token = '' } = useParams();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);

  const [invitation, setInvitation] = useState<ProjectInvitationLookup | null>(null);
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadInvitation() {
      setLoading(true);
      setError(null);
      try {
        const response = await api.get(`/projects/invitations/${token}`);
        if (!cancelled) {
          setInvitation(response.data as ProjectInvitationLookup);
        }
      } catch (e: any) {
        if (!cancelled) {
          setInvitation(null);
          setError(e?.response?.data?.detail || 'Invitation not found');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void loadInvitation();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function acceptInvitation() {
    if (!invitation) return;
    setAccepting(true);
    setError(null);
    setNotice(null);
    try {
      const response = await api.post(`/projects/invitations/${token}/accept`);
      const projectId = (response.data as { project_id?: string })?.project_id;
      setNotice(`Invitation accepted. Redirecting to ${invitation.project_title}…`);
      if (projectId) {
        navigate(`/projects/${projectId}/research`, { replace: true });
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not accept invitation');
    } finally {
      setAccepting(false);
    }
  }

  const canAccept = Boolean(
    invitation &&
      user &&
      user.email.toLowerCase() === invitation.email.toLowerCase() &&
      invitation.status === 'pending',
  );
  const canOpenAcceptedProject = Boolean(
    invitation &&
      user &&
      user.email.toLowerCase() === invitation.email.toLowerCase() &&
      invitation.status === 'accepted',
  );

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f7f6f2', padding: 24 }}>
      <div className="rc-card" style={{ width: '100%', maxWidth: 560, padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <div className="rc-kicker">Project invitation</div>
          <h1 className="rc-page-title" style={{ marginBottom: 6 }}>Join a shared PaperFlow project</h1>
          <div className="rc-subtitle">Review the invitation details, then sign in or create an account with the invited email.</div>
        </div>

        {loading ? <div className="rc-muted">Loading invitation…</div> : null}
        {error ? <div className="rc-error">{error}</div> : null}
        {notice ? <div className="rc-help">{notice}</div> : null}

        {invitation ? (
          <>
            <div className="rc-product-record rc-product-record--soft">
              <div className="rc-product-record__header">
                <div>
                  <div style={{ fontWeight: 800 }}>{invitation.project_title}</div>
                  <div className="rc-help">{invitation.email}</div>
                </div>
                <span className="rc-discover-badge">{ROLE_LABELS[invitation.role] || invitation.role}</span>
              </div>
              <div className="rc-help" style={{ marginTop: 10 }}>
                Status: <b>{invitation.status}</b>
              </div>
            </div>

            {!user ? (
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <Link
                  className="rc-btn rc-btn--primary"
                  data-testid="invitation-create-account-link"
                  to={`/signup?invitation_token=${encodeURIComponent(token)}&email=${encodeURIComponent(invitation.email)}`}
                >
                  Create account
                </Link>
                <Link
                  className="rc-btn"
                  data-testid="invitation-sign-in-link"
                  to={`/login?invitation_token=${encodeURIComponent(token)}&email=${encodeURIComponent(invitation.email)}`}
                >
                  Sign in
                </Link>
              </div>
            ) : null}

            {!user && invitation.status === 'accepted' ? (
              <div className="rc-help">
                This invitation is already linked to {invitation.email}. Sign in with that account to open the project.
              </div>
            ) : null}

            {user && user.email.toLowerCase() !== invitation.email.toLowerCase() ? (
              <div className="rc-error">
                Signed in as {user.email}. This invitation was sent to {invitation.email}. Use the invited email to accept it.
              </div>
            ) : null}

            {canAccept ? (
              <button
                className="rc-btn rc-btn--primary"
                data-testid="invitation-accept-button"
                onClick={acceptInvitation}
                disabled={accepting}
              >
                {accepting ? 'Accepting…' : 'Accept invitation'}
              </button>
            ) : null}

            {canOpenAcceptedProject ? (
              <button
                className="rc-btn rc-btn--primary"
                data-testid="invitation-open-project-button"
                onClick={() => navigate(`/projects/${invitation.project_id}/research`, { replace: true })}
              >
                Open project
              </button>
            ) : null}

            {invitation.status === 'revoked' ? (
              <div className="rc-help">
                This invitation was revoked. Ask the project owner to send you a new access link.
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}
