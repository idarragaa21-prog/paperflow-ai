import { useCallback, useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import type { MembershipRole, ProjectInvitation, ProjectInviteResult, ProjectMember } from '../types/api';

const ROLE_OPTIONS: MembershipRole[] = ['owner', 'editor', 'viewer'];
const ROLE_LABELS: Record<MembershipRole, string> = {
  owner: 'Owner',
  editor: 'Editor',
  viewer: 'Viewer',
};

const ROLE_BADGE_STYLES: Record<MembershipRole, CSSProperties> = {
  owner: { background: 'rgba(239,68,68,0.12)', color: 'rgb(185,28,28)', border: '1px solid rgba(239,68,68,0.18)' },
  editor: { background: 'rgba(59,130,246,0.12)', color: 'rgb(29,78,216)', border: '1px solid rgba(59,130,246,0.18)' },
  viewer: { background: 'rgba(16,185,129,0.12)', color: 'rgb(4,120,87)', border: '1px solid rgba(16,185,129,0.18)' },
};

export default function CollaborationPage() {
  const { projectId } = useParams();
  const user = useAuthStore((state) => state.user);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [invitations, setInvitations] = useState<ProjectInvitation[]>([]);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<MembershipRole>('viewer');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const ownerCount = useMemo(() => members.filter((member) => member.role === 'owner').length, [members]);
  const currentRole = useMemo(() => {
    const membership = members.find((member) => member.user_id === user?.id);
    return membership?.role || null;
  }, [members, user?.id]);
  const canManageMembers = currentRole === 'owner';

  const loadMembers = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(`/projects/${projectId}/members`);
      setMembers(response.data as ProjectMember[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not load project members');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const loadInvitations = useCallback(async () => {
    if (!projectId || !canManageMembers) {
      setInvitations([]);
      return;
    }
    try {
      const response = await api.get(`/projects/${projectId}/invitations`);
      setInvitations(response.data as ProjectInvitation[]);
    } catch (e: any) {
      setInvitations([]);
      setError(e?.response?.data?.detail || 'Could not load pending invitations');
    }
  }, [canManageMembers, projectId]);

  useEffect(() => {
    void loadMembers();
  }, [loadMembers]);

  useEffect(() => {
    void loadInvitations();
  }, [loadInvitations]);

  async function inviteMember() {
    const email = inviteEmail.trim().toLowerCase();
    if (!projectId || !canManageMembers || !email) return;
    if (!email.includes('@')) {
      setError('Enter a valid email address.');
      return;
    }

    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const response = await api.post(`/projects/${projectId}/members`, { email, role: inviteRole });
      const result = response.data as ProjectInviteResult;
      if (result.kind === 'membership') {
        setNotice(`${email} now has ${ROLE_LABELS[inviteRole]} access.`);
      } else {
        const invitationUrl = result.invitation_url || `${window.location.origin}${result.invitation?.accept_path || `/project-invitations/${result.invitation?.token || ''}`}`;
        if (result.delivery_status === 'sent') {
          setNotice(`${email} will receive an invitation email shortly. Backup link: ${invitationUrl}`);
        } else {
          try {
            await navigator.clipboard.writeText(invitationUrl);
            setNotice(`${email} does not have email delivery configured here. Invitation link copied: ${invitationUrl}`);
          } catch {
            setNotice(`${email} does not have email delivery configured here. Share this link manually: ${invitationUrl}`);
          }
        }
      }
      setInviteEmail('');
      setInviteRole('viewer');
      await loadMembers();
      await loadInvitations();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not invite member');
    } finally {
      setSaving(false);
    }
  }

  async function updateRole(member: ProjectMember, role: MembershipRole) {
    if (!projectId || role === member.role || !canManageMembers) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await api.patch(`/projects/${projectId}/members/${member.user_id}`, { role });
      setNotice(`${member.email} is now ${ROLE_LABELS[role]}.`);
      await loadMembers();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not update member role');
    } finally {
      setSaving(false);
    }
  }

  async function removeMember(member: ProjectMember) {
    if (!projectId || !canManageMembers) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await api.delete(`/projects/${projectId}/members/${member.user_id}`);
      setNotice(`${member.email} removed from the project.`);
      await loadMembers();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not remove member');
    } finally {
      setSaving(false);
    }
  }

  async function removeInvitation(invitation: ProjectInvitation) {
    if (!projectId || !canManageMembers) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await api.delete(`/projects/${projectId}/invitations/${invitation.id}`);
      setNotice(`Invitation for ${invitation.email} removed.`);
      await loadInvitations();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not remove invitation');
    } finally {
      setSaving(false);
    }
  }

  async function copyInvitationLink(invitation: ProjectInvitation) {
    const link = `${window.location.origin}${invitation.accept_path}`;
    try {
      await navigator.clipboard.writeText(link);
      setNotice(`Invitation link copied for ${invitation.email}.`);
    } catch {
      setNotice(`Copy this invitation link: ${link}`);
    }
  }

  return (
    <div className="rc-page-enter rc-product-page">
      <div className="rc-product-page__header">
        <div>
          <div className="rc-kicker">Collaboration</div>
          <h2>Project access and team roles</h2>
          <p>
            Invite collaborators by email, audit the active roles and keep the ownership model explicit.
          </p>
        </div>
        <div className="rc-discover-badges">
          <span className="rc-discover-badge">{members.length} members</span>
          <span className="rc-discover-badge">{ownerCount} owners</span>
          {currentRole ? <span className="rc-discover-badge">Your role: {ROLE_LABELS[currentRole]}</span> : null}
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}
      {notice ? <div className="rc-help">{notice}</div> : null}
      {currentRole ? (
        <div className="rc-help">
          Your current role is <b>{ROLE_LABELS[currentRole]}</b>.
          {canManageMembers
            ? ' You can invite members, change roles and remove collaborators.'
            : ' You can review the team, but only owners can change membership.'}
        </div>
      ) : null}

      <div className="rc-product-two-column">
        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Invite by email</div>
              <div className="rc-help">Existing users are added immediately. New emails receive an SMTP email when configured, or a secure fallback link you can copy manually.</div>
            </div>
          </div>

          <div className="rc-product-form-grid rc-product-form-grid--three">
            <label className="rc-discover-filter-field" style={{ gridColumn: 'span 2' }}>
              <span>Email</span>
              <input
                data-testid="member-email-input"
                className="rc-input"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="researcher@example.com"
                disabled={!canManageMembers}
              />
            </label>
            <label className="rc-discover-filter-field">
              <span>Role</span>
              <select
                data-testid="member-role-select"
                className="rc-input"
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value as MembershipRole)}
                disabled={!canManageMembers}
              >
                {ROLE_OPTIONS.map((role) => (
                  <option key={role} value={role}>
                    {ROLE_LABELS[role]}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <button
            data-testid="member-add-button"
            className="rc-btn rc-btn--primary"
            onClick={inviteMember}
            disabled={saving || !inviteEmail.trim() || !canManageMembers}
          >
            {saving ? 'Saving…' : 'Invite member'}
          </button>
        </section>

        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Role policy</div>
              <div className="rc-help">Owners manage access, editors work actively, viewers follow the project in read-only mode.</div>
            </div>
          </div>
          <div className="rc-product-record-list">
            {ROLE_OPTIONS.map((role) => (
              <div key={role} className="rc-product-study-panel">
                <div style={{ fontWeight: 800 }}>{ROLE_LABELS[role]}</div>
                <div className="rc-help" style={{ marginTop: 6 }}>
                  {role === 'owner'
                    ? 'Can invite, remove and reassign other members.'
                    : role === 'editor'
                      ? 'Can contribute across the project modules and collaborate actively.'
                      : 'Read-only access for consultation, monitoring or stakeholder visibility.'}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="rc-product-card">
        <div className="rc-product-card__header">
          <div>
            <div className="rc-card-title">Project members</div>
            <div className="rc-help">Owners are highlighted first, followed by editors and viewers.</div>
          </div>
          <div className="rc-discover-badge">Owners: {ownerCount}</div>
        </div>

        {loading ? <div className="rc-muted">Loading members…</div> : null}
        {!loading && members.length === 0 ? <div className="rc-empty-state">No members found.</div> : null}
        {members.map((member) => (
          <div data-testid={`member-card-${member.user_id}`} key={`${member.user_id}-${member.role}`} className="rc-product-record rc-product-record--soft">
            <div className="rc-product-record__header">
              <div>
                <div style={{ fontWeight: 800 }}>{member.full_name || member.email}</div>
                <div className="rc-help">{member.email}</div>
              </div>
              <span className="rc-discover-badge" style={ROLE_BADGE_STYLES[member.role]}>
                {ROLE_LABELS[member.role]}
              </span>
            </div>
            <div className="rc-product-actions" style={{ marginTop: 12 }}>
              <select
                data-testid={`member-role-${member.user_id}`}
                className="rc-input"
                value={member.role}
                onChange={(e) => updateRole(member, e.target.value as MembershipRole)}
                disabled={!canManageMembers || saving || member.role === 'owner'}
              >
                {ROLE_OPTIONS.map((role) => (
                  <option key={role} value={role}>
                    {ROLE_LABELS[role]}
                  </option>
                ))}
              </select>

              {canManageMembers && member.role !== 'owner' ? (
                <button
                  data-testid={`member-remove-${member.user_id}`}
                  className="rc-btn"
                  onClick={() => removeMember(member)}
                  disabled={saving}
                >
                  Remove
                </button>
              ) : null}

              {member.role === 'owner' ? <span className="rc-help">Owners stay visible and cannot be removed here.</span> : null}
            </div>
          </div>
        ))}
      </section>

      {canManageMembers ? (
        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Pending invitations</div>
              <div className="rc-help">Pending collaborators can accept by secure link. If SMTP is configured, the link is also emailed automatically at invite time.</div>
            </div>
            <div className="rc-discover-badge">{invitations.length} pending</div>
          </div>

          {invitations.length === 0 ? <div className="rc-empty-state">No pending invitations.</div> : null}
          {invitations.map((invitation) => (
            <div key={invitation.id} data-testid={`invitation-card-${invitation.id}`} className="rc-product-record rc-product-record--soft">
              <div className="rc-product-record__header">
                <div>
                  <div style={{ fontWeight: 800 }}>{invitation.email}</div>
                  <div className="rc-help">{window.location.origin}{invitation.accept_path}</div>
                </div>
                <span className="rc-discover-badge" style={ROLE_BADGE_STYLES[invitation.role]}>
                  {ROLE_LABELS[invitation.role]}
                </span>
              </div>
              <div className="rc-product-actions" style={{ marginTop: 12 }}>
                <button className="rc-btn" data-testid={`invitation-copy-${invitation.id}`} onClick={() => copyInvitationLink(invitation)} disabled={saving}>
                  Copy link
                </button>
                <button className="rc-btn" data-testid={`invitation-remove-${invitation.id}`} onClick={() => removeInvitation(invitation)} disabled={saving}>
                  Remove
                </button>
              </div>
            </div>
          ))}
        </section>
      ) : null}
    </div>
  );
}
