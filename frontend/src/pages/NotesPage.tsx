import { useEffect, useRef, useState } from 'react';
import type { NoteRow, NoteDetail } from '../types/api';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';
import { useConfirm } from '../ui/Dialog/useConfirm';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';

function timeAgo(iso?: string | null): string {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min}m ago`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

const NOTE_TYPES = ['manual', 'summary', 'key_points', 'critique'];

export default function NotesPage() {
  const { projectId } = useParams();
  const toast = useToast();
  const confirm = useConfirm();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [notes, setNotes] = useState<NoteRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<NoteDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // create / edit form
  const [formOpen, setFormOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [noteType, setNoteType] = useState<string>('manual');
  const [saving, setSaving] = useState(false);

  async function load() {
    if (!projectId) return;
    setLoading(true); setError(null);
    try {
      const r = await api.get('/notes', { params: { project_id: projectId } });
      setNotes(r.data as NoteRow[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load notes');
    } finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [projectId]);

  async function loadDetail(id: string) {
    setDetailLoading(true);
    try {
      const r = await api.get(`/notes/${id}`);
      setDetail(r.data as NoteDetail);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load note');
    } finally { setDetailLoading(false); }
  }

  function selectNote(id: string) {
    setSelectedId(id);
    loadDetail(id);
  }

  function openCreate() {
    setEditId(null);
    setTitle('');
    setContent('');
    setNoteType('manual');
    setFormOpen(true);
    setTimeout(() => textareaRef.current?.focus(), 50);
  }

  function openEdit(n: NoteDetail) {
    setEditId(n.id);
    setTitle(n.title);
    setContent(n.content);
    setNoteType(n.note_type);
    setFormOpen(true);
    setTimeout(() => textareaRef.current?.focus(), 50);
  }

  async function save() {
    if (!projectId || !title.trim()) return;
    setSaving(true); setError(null);
    try {
      if (editId) {
        await api.put(`/notes/${editId}`, { title: title.trim(), content, note_type: noteType });
        toast.success('Saved', 'Note updated.');
        await loadDetail(editId);
      } else {
        const r = await api.post('/notes', { project_id: projectId, title: title.trim(), content, note_type: noteType });
        const created = r.data as NoteRow;
        toast.success('Created', title.trim());
        await load();
        selectNote(created.id);
      }
      setFormOpen(false);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to save note');
    } finally { setSaving(false); }
  }

  async function del(id: string, noteTitle: string) {
    const ok = await confirm({ title: 'Delete note?', body: noteTitle, confirmText: 'Delete', danger: true });
    if (!ok) return;
    try {
      await api.delete(`/notes/${id}`);
      toast.success('Deleted', noteTitle);
      if (selectedId === id) { setSelectedId(null); setDetail(null); }
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Delete failed');
    }
  }

  const selectedNote = notes.find(n => n.id === selectedId);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 10 }}>
        <div>
          <h1 className="rc-page-title">Notes</h1>
          <div className="rc-subtitle">Capture ideas, summaries and critiques linked to this project.</div>
        </div>
        <div className="rc-row">
          <button className="rc-btn" onClick={load} disabled={loading}>{loading ? 'Loading…' : 'Refresh'}</button>
          <button className="rc-btn rc-btn--primary" onClick={openCreate}>+ New Note</button>
        </div>
      </div>

      {error && <div className="rc-error">{error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(200px,280px) 1fr', gap: 14, alignItems: 'start' }}>
        {/* List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {loading && notes.length === 0 && (
            <div className="rc-card" style={{ padding: 12 }}>
              <Skeleton height={13} width="60%" radius={8} />
              <div style={{ height: 8 }} />
              <SkeletonLines lines={4} lineHeight={11} lastLineWidth="40%" />
            </div>
          )}
          {!loading && notes.length === 0 && (
            <div className="rc-card" style={{ textAlign: 'center', padding: '40px 16px' }}>
              <svg width="56" height="56" viewBox="0 0 56 56" fill="none" style={{ margin: '0 auto 12px', display: 'block' }}>
                <rect x="8" y="6" width="34" height="42" rx="5" fill="rgba(99,102,241,0.07)" stroke="rgba(99,102,241,0.2)" strokeWidth="1.5"/>
                <line x1="16" y1="18" x2="34" y2="18" stroke="rgba(99,102,241,0.3)" strokeWidth="1.5" strokeLinecap="round"/>
                <line x1="16" y1="26" x2="34" y2="26" stroke="rgba(99,102,241,0.25)" strokeWidth="1.5" strokeLinecap="round"/>
                <line x1="16" y1="34" x2="26" y2="34" stroke="rgba(99,102,241,0.15)" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              <div style={{ fontWeight: 700, fontSize: 13 }}>No notes yet</div>
              <div style={{ fontSize: 12, color: 'var(--rc-muted)', marginTop: 4 }}>Create your first note</div>
            </div>
          )}
          {notes.map(n => (
            <div
              key={n.id}
              onClick={() => selectNote(n.id)}
              style={{
                padding: '10px 12px',
                borderRadius: 10,
                border: `1px solid ${n.id === selectedId ? 'var(--rc-primary)' : 'var(--rc-border)'}`,
                background: n.id === selectedId ? 'rgba(99,102,241,0.07)' : 'var(--rc-surface)',
                cursor: 'pointer',
                transition: 'border-color 0.15s',
              }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, lineHeight: 1.3, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{n.title}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                <span className="rc-badge" style={{ fontSize: 10 }}>{n.note_type}</span>
                <span style={{ fontSize: 11, color: 'var(--rc-muted)' }}>{timeAgo(n.created_at)}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Detail panel */}
        <div>
          {!selectedId && (
            <div className="rc-card" style={{ textAlign: 'center', padding: '60px 24px' }}>
              <svg width="64" height="64" viewBox="0 0 64 64" fill="none" style={{ margin: '0 auto 14px', display: 'block' }}>
                <rect x="10" y="8" width="40" height="48" rx="6" fill="rgba(99,102,241,0.07)" stroke="rgba(99,102,241,0.18)" strokeWidth="1.5"/>
                <line x1="20" y1="22" x2="44" y2="22" stroke="rgba(99,102,241,0.25)" strokeWidth="1.5" strokeLinecap="round"/>
                <line x1="20" y1="30" x2="44" y2="30" stroke="rgba(99,102,241,0.2)" strokeWidth="1.5" strokeLinecap="round"/>
                <line x1="20" y1="38" x2="34" y2="38" stroke="rgba(99,102,241,0.15)" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              <div style={{ fontWeight: 700, fontSize: 14 }}>Select a note to read</div>
              <div style={{ fontSize: 13, color: 'var(--rc-muted)', marginTop: 5 }}>Or create a new one with the button above</div>
            </div>
          )}
          {selectedId && detailLoading && (
            <div className="rc-card" style={{ padding: 20 }}>
              <Skeleton height={16} width="50%" radius={8} />
              <div style={{ height: 12 }} />
              <SkeletonLines lines={6} lineHeight={13} lastLineWidth="35%" />
            </div>
          )}
          {selectedId && !detailLoading && detail && (
            <div className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
                <div>
                  <div style={{ fontWeight: 800, fontSize: 17, fontFamily: 'var(--font-display)', letterSpacing: '-0.02em', lineHeight: 1.25 }}>{detail.title}</div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 5 }}>
                    <span className="rc-badge" style={{ fontSize: 11 }}>{detail.note_type}</span>
                    {detail.llm_model && <span className="rc-badge" style={{ fontSize: 11, opacity: 0.7 }}>{detail.llm_model}</span>}
                  </div>
                </div>
                <div className="rc-row" style={{ gap: 6, flexShrink: 0 }}>
                  <button className="rc-btn rc-btn--sm" onClick={() => openEdit(detail)}>Edit</button>
                  <button className="rc-btn rc-btn--sm" style={{ color: 'var(--rc-danger)' }} onClick={() => del(detail.id, detail.title)}>Delete</button>
                </div>
              </div>
              <div style={{ borderTop: '1px solid var(--rc-border)', paddingTop: 12, whiteSpace: 'pre-wrap', lineHeight: 1.7, fontSize: 14, color: 'var(--rc-text)' }}>
                {detail.content || <span style={{ color: 'var(--rc-muted)', fontStyle: 'italic' }}>No content.</span>}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create / Edit modal */}
      {formOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20, zIndex: 50 }} onClick={() => setFormOpen(false)}>
          <div className="rc-card" style={{ width: 'min(580px, 96vw)', display: 'flex', flexDirection: 'column', gap: 12 }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontWeight: 800, fontFamily: 'var(--font-display)', fontSize: 15 }}>{editId ? 'Edit note' : 'New note'}</div>
              <button className="rc-btn rc-btn--sm rc-btn--ghost" onClick={() => setFormOpen(false)}>✕</button>
            </div>

            <div>
              <div className="rc-kicker">Title</div>
              <input className="rc-input" value={title} onChange={e => setTitle(e.target.value)} placeholder="Note title…" />
            </div>

            <div>
              <div className="rc-kicker">Type</div>
              <select className="rc-input" value={noteType} onChange={e => setNoteType(e.target.value)}>
                {NOTE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            <div>
              <div className="rc-kicker">Content</div>
              <textarea
                ref={textareaRef}
                className="rc-input"
                value={content}
                onChange={e => setContent(e.target.value)}
                placeholder="Write your note here…"
                style={{ minHeight: 180, width: '100%', resize: 'vertical' }}
              />
            </div>

            <div className="rc-row" style={{ justifyContent: 'flex-end' }}>
              <button className="rc-btn" onClick={() => setFormOpen(false)}>Cancel</button>
              <button className="rc-btn rc-btn--primary" onClick={save} disabled={saving || !title.trim()}>
                {saving ? 'Saving…' : editId ? 'Save changes' : 'Create note'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
