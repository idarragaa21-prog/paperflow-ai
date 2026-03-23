import { useEffect, useRef, useState } from 'react';
import type { NoteRow, NoteDetail } from '../types/api';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';

const NOTE_TYPES = ['summary','methodology','findings','critique','annotation','general'];

function EmptyState() {
  return (
    <div style={{ textAlign:'center',padding:'64px 24px' }}>
      <svg width="80" height="80" viewBox="0 0 80 80" fill="none" style={{ margin:'0 auto 16px',display:'block' }}>
        <rect x="12" y="10" width="46" height="58" rx="6" fill="rgba(139,92,246,0.06)" stroke="rgba(139,92,246,0.2)" strokeWidth="1.5"/>
        <line x1="22" y1="26" x2="48" y2="26" stroke="rgba(139,92,246,0.3)" strokeWidth="1.5" strokeLinecap="round"/>
        <line x1="22" y1="34" x2="48" y2="34" stroke="rgba(139,92,246,0.3)" strokeWidth="1.5" strokeLinecap="round"/>
        <line x1="22" y1="42" x2="38" y2="42" stroke="rgba(139,92,246,0.2)" strokeWidth="1.5" strokeLinecap="round"/>
        <circle cx="60" cy="60" r="16" fill="var(--rc-surface)" stroke="rgba(139,92,246,0.3)" strokeWidth="1.5"/>
        <line x1="60" y1="53" x2="60" y2="67" stroke="rgba(139,92,246,0.6)" strokeWidth="2" strokeLinecap="round"/>
        <line x1="53" y1="60" x2="67" y2="60" stroke="rgba(139,92,246,0.6)" strokeWidth="2" strokeLinecap="round"/>
      </svg>
      <div style={{ fontWeight:700,fontSize:15,fontFamily:'var(--font-display)',letterSpacing:'-0.02em' }}>No notes yet</div>
      <div style={{ fontSize:13,color:'var(--rc-muted)',marginTop:5 }}>Create your first note to start capturing insights</div>
    </div>
  );
}

export default function NotesPage() {
  const { projectId } = useParams();
  const [notes, setNotes] = useState<NoteRow[]>([]);
  const [selected, setSelected] = useState<NoteDetail|null>(null);
  const [selectedId, setSelectedId] = useState<string|null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string|null>(null);
  const [showNew, setShowNew] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newContent, setNewContent] = useState('');
  const [newType, setNewType] = useState('general');
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [editTitle, setEditTitle] = useState('');
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');
  const textRef = useRef<HTMLTextAreaElement>(null);

  async function loadList() {
    if (!projectId) return;
    setLoading(true); setError(null);
    try {
      const r = await api.get(`/notes/projects/${projectId}`);
      setNotes(r.data as NoteRow[]);
    } catch (e: any) { setError(e?.response?.data?.detail || 'Failed to load notes'); }
    finally { setLoading(false); }
  }

  async function loadDetail(noteId: string) {
    setError(null);
    try {
      const r = await api.get(`/notes/${noteId}`);
      const n = r.data as NoteDetail;
      setSelected(n); setSelectedId(noteId);
      setEditTitle(n.title); setEditContent(n.content);
      setEditing(false);
    } catch (e: any) { setError(e?.response?.data?.detail || 'Failed to load note'); }
  }

  async function createNote() {
    if (!projectId || !newTitle.trim()) return;
    setCreating(true); setError(null);
    try {
      await api.post(`/notes`, { project_id: projectId, title: newTitle.trim(), content: newContent.trim(), note_type: newType });
      setNewTitle(''); setNewContent(''); setNewType('general'); setShowNew(false);
      await loadList();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Failed to create note'); }
    finally { setCreating(false); }
  }

  async function saveEdit() {
    if (!selected) return;
    setSaving(true); setError(null);
    try {
      await api.patch(`/notes/${selected.id}`, { title: editTitle.trim(), content: editContent.trim() });
      await loadDetail(selected.id);
      await loadList();
      setEditing(false);
    } catch (e: any) { setError(e?.response?.data?.detail || 'Failed to save note'); }
    finally { setSaving(false); }
  }

  async function deleteNote(id: string) {
    if (!confirm('Delete this note?')) return;
    try {
      await api.delete(`/notes/${id}`);
      if (selectedId === id) { setSelected(null); setSelectedId(null); }
      await loadList();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Failed to delete note'); }
  }

  function copyNote() {
    if (!selected) return;
    navigator.clipboard.writeText(selected.content).then(() => alert('Copied!'));
  }

  useEffect(() => { loadList(); }, [projectId]);
  useEffect(() => { if (editing && textRef.current) textRef.current.focus(); }, [editing]);

  const filtered = notes.filter(n => !search || n.title.toLowerCase().includes(search.toLowerCase()) || n.note_type.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="rc-page-enter" style={{ display:'flex',flexDirection:'column',gap:16 }}>
      <div style={{ display:'flex',alignItems:'center',justifyContent:'space-between',flexWrap:'wrap',gap:10 }}>
        <div>
          <h1 className="rc-page-title">Notes</h1>
          <div className="rc-subtitle">Summaries and notes linked to papers in this project.</div>
        </div>
        <button className="rc-btn rc-btn--primary" onClick={()=>setShowNew(!showNew)}>
          {showNew ? 'Cancel' : '+ New note'}
        </button>
      </div>

      {showNew && (
        <div className="rc-card" style={{ borderColor:'rgba(139,92,246,0.25)',background:'rgba(139,92,246,0.02)' }}>
          <div className="rc-card-title">New note</div>
          <div style={{ display:'flex',flexDirection:'column',gap:12 }}>
            <div style={{ display:'grid',gridTemplateColumns:'1fr auto',gap:10 }}>
              <div>
                <div className="rc-kicker">Title *</div>
                <input className="rc-input" value={newTitle} onChange={e=>setNewTitle(e.target.value)} placeholder="Note title" autoFocus/>
              </div>
              <div>
                <div className="rc-kicker">Type</div>
                <select className="rc-input" value={newType} onChange={e=>setNewType(e.target.value)} style={{ width:'auto',minWidth:120 }}>
                  {NOTE_TYPES.map(t=><option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            </div>
            <div>
              <div className="rc-kicker">Content</div>
              <textarea className="rc-input" value={newContent} onChange={e=>setNewContent(e.target.value)}
                placeholder="Write your note here…" rows={6}/>
            </div>
            <div style={{ display:'flex',gap:10 }}>
              <button className="rc-btn rc-btn--primary" onClick={createNote} disabled={creating||!newTitle.trim()}>
                {creating ? 'Saving…' : 'Save note'}
              </button>
              <button className="rc-btn" onClick={()=>setShowNew(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {error && <div className="rc-error">{error}</div>}

      <div style={{ display:'grid',gridTemplateColumns:'320px 1fr',gap:12,alignItems:'start' }}>
        <div className="rc-card" style={{ padding:0,overflow:'hidden' }}>
          <div style={{ padding:'12px 14px',borderBottom:'1px solid var(--rc-border)' }}>
            <input className="rc-input" value={search} onChange={e=>setSearch(e.target.value)}
              placeholder="Search notes…" style={{ fontSize:13 }}/>
          </div>
          {loading ? (
            <div style={{ padding:14 }}><div className="rc-muted">Loading…</div></div>
          ) : filtered.length === 0 ? (
            <EmptyState/>
          ) : (
            <div style={{ maxHeight:520,overflowY:'auto' }}>
              {filtered.map(n=>(
                <button key={n.id} onClick={()=>loadDetail(n.id)}
                  style={{
                    width:'100%',textAlign:'left',padding:'11px 14px',border:'none',cursor:'pointer',
                    background: n.id===selectedId ? 'rgba(99,102,241,0.08)' : 'transparent',
                    borderLeft: n.id===selectedId ? '3px solid var(--rc-primary)' : '3px solid transparent',
                  }}>
                  <div style={{ fontWeight:650,fontSize:13 }}>{n.title}</div>
                  <div style={{ display:'flex',gap:8,marginTop:4 }}>
                    <span className="rc-badge" style={{ fontSize:10.5 }}>{n.note_type}</span>
                    {n.created_at && <span className="rc-help">{new Date(n.created_at).toLocaleDateString()}</span>}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="rc-card" style={{ minHeight:300 }}>
          {!selected ? (
            <div className="rc-muted" style={{ padding:'48px 24px',textAlign:'center' }}>Select a note to view</div>
          ) : (
            <div style={{ display:'flex',flexDirection:'column',gap:12 }}>
              <div style={{ display:'flex',alignItems:'center',justifyContent:'space-between',gap:10,flexWrap:'wrap' }}>
                {editing ? (
                  <input className="rc-input" value={editTitle} onChange={e=>setEditTitle(e.target.value)}
                    style={{ fontSize:16,fontWeight:800,flex:1 }}/>
                ) : (
                  <div style={{ fontSize:17,fontWeight:800,flex:1 }}>{selected.title}</div>
                )}
                <div style={{ display:'flex',gap:6 }}>
                  {editing ? (
                    <>
                      <button className="rc-btn rc-btn--primary" onClick={saveEdit} disabled={saving}>
                        {saving ? '…' : 'Save'}
                      </button>
                      <button className="rc-btn" onClick={()=>{setEditing(false);setEditContent(selected.content);setEditTitle(selected.title);}}>
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      <button className="rc-btn" onClick={()=>setEditing(true)}>Edit</button>
                      <button className="rc-btn" onClick={copyNote}>Copy</button>
                      <button className="rc-btn" onClick={()=>deleteNote(selected.id)}>Delete</button>
                    </>
                  )}
                </div>
              </div>
              <div style={{ display:'flex',gap:8 }}>
                <span className="rc-badge">{selected.note_type}</span>
                {selected.llm_model && <span className="rc-badge">{selected.llm_model}</span>}
              </div>
              {editing ? (
                <textarea ref={textRef} className="rc-input" value={editContent} onChange={e=>setEditContent(e.target.value)}
                  style={{ minHeight:320,fontSize:13,lineHeight:1.65,resize:'vertical' }}/>
              ) : (
                <pre style={{ margin:0,whiteSpace:'pre-wrap',fontFamily:'inherit',fontSize:13,lineHeight:1.65 }}>
                  {selected.content}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
