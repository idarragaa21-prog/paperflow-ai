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
    <div className="rc-product-page">
      <div className="rc-product-page__header">
        <div>
          <div className="rc-kicker">Colaboración</div>
          <h2>Accesos, roles y revisión del proyecto</h2>
          <p>
            Mantén el trabajo coordinado desde una sola vista: altas, cambios de rol y revisión con permisos claros.
          </p>
        </div>
        <div className="rc-discover-badges">
          <span className="rc-discover-badge">{members.length} miembros</span>
          <span className="rc-discover-badge">{ownerCount} dueños</span>
          {currentRole ? <span className="rc-discover-badge">Tu rol: {ROLE_LABELS[currentRole]}</span> : null}
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

      <div className="rc-product-two-column">
        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Agregar miembro</div>
              <div className="rc-help">Añade usuarios por UUID y define el nivel de acceso desde esta misma vista.</div>
            </div>
          </div>

          <div className="rc-product-form-grid rc-product-form-grid--three">
            <label className="rc-discover-filter-field" style={{ gridColumn: 'span 2' }}>
              <span>UUID del usuario</span>
              <input
                data-testid="member-user-id-input"
                className="rc-input"
                value={newUserId}
                onChange={(e) => setNewUserId(e.target.value)}
                placeholder="00000000-0000-0000-0000-000000000000"
              />
            </label>
            <label className="rc-discover-filter-field">
              <span>Rol</span>
              <select
                data-testid="member-role-select"
                className="rc-input"
                value={newRole}
                onChange={(e) => setNewRole(e.target.value as Membership['role'])}
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
            onClick={addMember}
            disabled={saving || !newUserId.trim() || !canManageMembers}
          >
            {saving ? 'Guardando…' : 'Agregar miembro'}
          </button>
        </section>

        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Política de roles</div>
              <div className="rc-help">
                Dueños gestionan miembros, editores modifican contenido, revisores validan flujos y lectores consultan.
              </div>
            </div>
          </div>
          <div className="rc-product-record-list">
            {ROLE_OPTIONS.map((role) => (
              <div key={role} className="rc-product-study-panel">
                <div style={{ fontWeight: 800 }}>{ROLE_LABELS[role]}</div>
                <div className="rc-help" style={{ marginTop: 6 }}>
                  {role === 'owner'
                    ? 'Gestiona membresías, cambios de rol y configuración sensible.'
                    : role === 'editor'
                      ? 'Puede editar contenido del proyecto y operar módulos de trabajo.'
                      : role === 'reviewer'
                        ? 'Puede revisar, comentar y participar en flujos de validación.'
                        : 'Solo lectura para seguimiento o consulta.'}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="rc-product-card">
        <div className="rc-product-card__header">
          <div>
            <div className="rc-card-title">Miembros del proyecto</div>
            <div className="rc-help">Revisa roles activos y cambia permisos solo cuando tu rol lo permita.</div>
          </div>
          <div className="rc-discover-badge">Dueños: {ownerCount}</div>
        </div>

        {loading ? <div className="rc-muted">Cargando miembros…</div> : null}
        {!loading && members.length === 0 ? <div className="rc-empty-state">No se encontraron miembros.</div> : null}
        {members.map((member) => (
          <div data-testid={`member-card-${member.user_id}`} key={member.id} className="rc-product-record rc-product-record--soft">
            <div className="rc-product-record__header">
              <div style={{ fontWeight: 800 }}>{member.user_id}</div>
              <span className="rc-discover-badge">{ROLE_LABELS[member.role]}</span>
            </div>
            <div className="rc-product-actions" style={{ marginTop: 12 }}>
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
      </section>
    </div>
  );
}
