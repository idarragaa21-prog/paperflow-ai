import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';

type Membership = {
  id: string;
  project_id: string;
  user_id: string;
  role: 'owner' | 'editor' | 'reviewer' | 'viewer';
};

const ROLE_OPTIONS: Membership['role'][] = ['owner', 'editor', 'reviewer', 'viewer'];
const ROLE_LABELS: Record<Membership['role'], string> = {
  owner: 'dueno',
  editor: 'editor',
  reviewer: 'revisor',
  viewer: 'lector',
};
export default function CollaborationPage() {
  const { projectId } = useParams();
  const user = useAuthStore((state) => state.user);
  const [members, setMembers] = useState<Membership[]>([]);
  const [newUserId, setNewUserId] = useState('');
  const [newRole, setNewRole] = useState<Membership['role']>('viewer');
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

  async function loadMembers() {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(`/projects/${projectId}/members`);
      setMembers(response.data as Membership[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudieron cargar los miembros');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadMembers();
  }, [projectId]);

  async function addMember() {
    if (!projectId || !newUserId.trim() || !canManageMembers) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await api.post(`/projects/${projectId}/members`, { user_id: newUserId.trim(), role: newRole });
      setNotice(`Miembro guardado como ${ROLE_LABELS[newRole]}.`);
      setNewUserId('');
      setNewRole('viewer');
      await loadMembers();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo agregar el miembro');
    } finally {
      setSaving(false);
    }
  }

  async function updateRole(member: Membership, role: Membership['role']) {
    if (!projectId || role === member.role || !canManageMembers) return;
    setError(null);
    setNotice(null);
    try {
      await api.patch(`/projects/${projectId}/members/${member.id}`, { role });
      setNotice(`Se actualizo ${member.user_id} a ${ROLE_LABELS[role]}.`);
      await loadMembers();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo actualizar el rol');
    }
  }

  async function removeMember(member: Membership) {
    if (!projectId || !canManageMembers) return;
    setError(null);
    setNotice(null);
    try {
      await api.delete(`/projects/${projectId}/members/${member.id}`);
      setNotice(`Se elimino ${member.user_id}.`);
      await loadMembers();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo eliminar el miembro');
    }
  }

  return (
    <div className="rc-section-shell">
      <div className="rc-hero-card">
        <div style={{ maxWidth: 760 }}>
          <div className="rc-pill">Colaboracion</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>Accesos y revision del proyecto</h1>
          <div className="rc-subtitle">Gestiona miembros, roles y flujos de revision desde un solo lugar.</div>
        </div>
        <div className="rc-metric-grid" style={{ minWidth: 300 }}>
          <div className="rc-metric-tile"><strong>{members.length}</strong><span>Miembros</span></div>
          <div className="rc-metric-tile"><strong>{ownerCount}</strong><span>Duenos</span></div>
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}
      {notice ? <div className="rc-help">{notice}</div> : null}
      {currentRole ? (
        <div className="rc-help">
          Tu rol actual es <b>{ROLE_LABELS[currentRole]}</b>.
          {!canManageMembers ? ' Puedes revisar miembros, pero solo un dueno puede cambiarlos.' : ' Puedes gestionar altas, cambios de rol y eliminaciones.'}
        </div>
      ) : null}

      <div className="rc-panel-grid" style={{ alignItems: 'start' }}>
        <div className="rc-card">
          <div className="rc-card-title">Agregar miembro</div>
          <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ minWidth: 280 }}>
              <div className="rc-kicker">UUID del usuario</div>
              <input data-testid="member-user-id-input" className="rc-input" value={newUserId} onChange={(e) => setNewUserId(e.target.value)} placeholder="00000000-0000-0000-0000-000000000000" />
            </div>
            <div style={{ minWidth: 180 }}>
              <div className="rc-kicker">Rol</div>
              <select data-testid="member-role-select" className="rc-input" value={newRole} onChange={(e) => setNewRole(e.target.value as Membership['role'])} disabled={!canManageMembers}>
                {ROLE_OPTIONS.map((role) => (
                  <option key={role} value={role}>{ROLE_LABELS[role]}</option>
                ))}
              </select>
            </div>
            <button data-testid="member-add-button" className="rc-btn rc-btn--primary" onClick={addMember} disabled={saving || !newUserId.trim() || !canManageMembers}>
              {saving ? 'Guardando…' : 'Agregar miembro'}
            </button>
          </div>
        </div>

        <div className="rc-card">
          <div className="rc-card-title">Politica de roles</div>
          <div className="rc-help">Los duenos gestionan miembros, los editores cambian el contenido, los revisores validan flujos y los lectores solo consultan.</div>
        </div>
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Miembros</div>
        <div className="rc-help" style={{ marginBottom: 10 }}>Duenos: {ownerCount}</div>
        {loading ? <div className="rc-muted">Cargando miembros…</div> : null}
        {!loading && members.length === 0 ? <div className="rc-muted">No se encontraron miembros.</div> : null}
        {members.map((member) => (
          <div data-testid={`member-card-${member.user_id}`} key={member.id} className="rc-soft-card" style={{ marginBottom: 10 }}>
            <div style={{ fontWeight: 800 }}>{member.user_id}</div>
            <div className="rc-row" style={{ alignItems: 'center', flexWrap: 'wrap' }}>
              <select
                data-testid={`member-role-${member.user_id}`}
                className="rc-input"
                value={member.role}
                onChange={(e) => updateRole(member, e.target.value as Membership['role'])}
                disabled={!canManageMembers}
              >
                {ROLE_OPTIONS.map((role) => (
                  <option key={role} value={role}>{ROLE_LABELS[role]}</option>
                ))}
              </select>
              <button
                data-testid={`member-remove-${member.user_id}`}
                className="rc-btn"
                onClick={() => removeMember(member)}
                disabled={!canManageMembers || (member.role === 'owner' && ownerCount <= 1)}
              >
                Eliminar
              </button>
              {!canManageMembers ? <span className="rc-help">Solo un dueno puede cambiar miembros.</span> : null}
              {member.role === 'owner' && ownerCount <= 1 ? <span className="rc-help">No se puede eliminar al ultimo dueno.</span> : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
