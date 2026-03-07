import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';

type Membership = {
  id: string;
  project_id: string;
  user_id: string;
  role: 'owner' | 'editor' | 'reviewer' | 'viewer';
};

const ROLE_OPTIONS: Membership['role'][] = ['owner', 'editor', 'reviewer', 'viewer'];

export default function CollaborationPage() {
  const { projectId } = useParams();
  const [members, setMembers] = useState<Membership[]>([]);
  const [newUserId, setNewUserId] = useState('');
  const [newRole, setNewRole] = useState<Membership['role']>('viewer');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const ownerCount = useMemo(() => members.filter((member) => member.role === 'owner').length, [members]);

  async function loadMembers() {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(`/projects/${projectId}/members`);
      setMembers(response.data as Membership[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load memberships');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadMembers();
  }, [projectId]);

  async function addMember() {
    if (!projectId || !newUserId.trim()) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await api.post(`/projects/${projectId}/members`, { user_id: newUserId.trim(), role: newRole });
      setNotice(`Member saved as ${newRole}.`);
      setNewUserId('');
      setNewRole('viewer');
      await loadMembers();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to add member');
    } finally {
      setSaving(false);
    }
  }

  async function updateRole(member: Membership, role: Membership['role']) {
    if (!projectId || role === member.role) return;
    setError(null);
    setNotice(null);
    try {
      await api.patch(`/projects/${projectId}/members/${member.id}`, { role });
      setNotice(`Updated ${member.user_id} to ${role}.`);
      await loadMembers();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to update role');
    }
  }

  async function removeMember(member: Membership) {
    if (!projectId) return;
    setError(null);
    setNotice(null);
    try {
      await api.delete(`/projects/${projectId}/members/${member.id}`);
      setNotice(`Removed ${member.user_id}.`);
      await loadMembers();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to remove member');
    }
  }

  return (
    <div className="rc-section-shell">
      <div className="rc-hero-card">
        <div style={{ maxWidth: 760 }}>
          <div className="rc-pill">Collaboration</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>Project access and review</h1>
          <div className="rc-subtitle">Manage memberships, roles and reviewer workflows from one place.</div>
        </div>
        <div className="rc-metric-grid" style={{ minWidth: 300 }}>
          <div className="rc-metric-tile"><strong>{members.length}</strong><span>Members</span></div>
          <div className="rc-metric-tile"><strong>{ownerCount}</strong><span>Owners</span></div>
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}
      {notice ? <div className="rc-help">{notice}</div> : null}

      <div className="rc-panel-grid" style={{ alignItems: 'start' }}>
        <div className="rc-card">
          <div className="rc-card-title">Add member</div>
          <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ minWidth: 280 }}>
              <div className="rc-kicker">User UUID</div>
              <input data-testid="member-user-id-input" className="rc-input" value={newUserId} onChange={(e) => setNewUserId(e.target.value)} placeholder="00000000-0000-0000-0000-000000000000" />
            </div>
            <div style={{ minWidth: 180 }}>
              <div className="rc-kicker">Role</div>
              <select data-testid="member-role-select" className="rc-input" value={newRole} onChange={(e) => setNewRole(e.target.value as Membership['role'])}>
                {ROLE_OPTIONS.map((role) => (
                  <option key={role} value={role}>{role}</option>
                ))}
              </select>
            </div>
            <button data-testid="member-add-button" className="rc-btn rc-btn--primary" onClick={addMember} disabled={saving || !newUserId.trim()}>
              {saving ? 'Saving…' : 'Add member'}
            </button>
          </div>
        </div>

        <div className="rc-card">
          <div className="rc-card-title">Role policy</div>
          <div className="rc-help">Owners manage memberships, editors change project content, reviewers validate workflows and viewers stay read-only.</div>
        </div>
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Members</div>
        <div className="rc-help" style={{ marginBottom: 10 }}>Owners: {ownerCount}</div>
        {loading ? <div className="rc-muted">Loading members…</div> : null}
        {!loading && members.length === 0 ? <div className="rc-muted">No members found.</div> : null}
        {members.map((member) => (
          <div data-testid={`member-card-${member.user_id}`} key={member.id} className="rc-soft-card" style={{ marginBottom: 10 }}>
            <div style={{ fontWeight: 800 }}>{member.user_id}</div>
            <div className="rc-row" style={{ alignItems: 'center', flexWrap: 'wrap' }}>
              <select data-testid={`member-role-${member.user_id}`} className="rc-input" value={member.role} onChange={(e) => updateRole(member, e.target.value as Membership['role'])}>
                {ROLE_OPTIONS.map((role) => (
                  <option key={role} value={role}>{role}</option>
                ))}
              </select>
              <button
                data-testid={`member-remove-${member.user_id}`}
                className="rc-btn"
                onClick={() => removeMember(member)}
                disabled={member.role === 'owner' && ownerCount <= 1}
              >
                Remove
              </button>
              {member.role === 'owner' && ownerCount <= 1 ? <span className="rc-help">Last owner cannot be removed.</span> : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
