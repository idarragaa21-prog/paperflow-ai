import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';

type NoteListRow = {
  id: string;
  title: string;
  note_type: string;
  paper_id?: string | null;
  created_at?: string | null;
};

type NoteDetail = {
  id: string;
  project_id: string;
  paper_id?: string | null;
  title: string;
  content: string;
  note_type: string;
  llm_model?: string | null;
};

export default function NotesPage() {
  const { projectId } = useParams();

  const [notes, setNotes] = useState<NoteListRow[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<NoteDetail | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadList() {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const r = await api.get(`/notes/projects/${projectId}`);
      setNotes(r.data as NoteListRow[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load notes');
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(noteId: string) {
    setError(null);
    try {
      const r = await api.get(`/notes/${noteId}`);
      setSelected(r.data as NoteDetail);
      setSelectedId(noteId);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load note');
    }
  }

  useEffect(() => {
    loadList();
  }, [projectId]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Notes</h1>
        <div className="rc-subtitle">Summaries and generated notes linked to papers in this project.</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: 12 }}>
        <div className="rc-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontWeight: 900 }}>Notes</div>
            <button className="rc-btn" onClick={loadList} disabled={loading}>Refresh</button>
          </div>
          {error ? <div className="rc-error" style={{ marginTop: 8 }}>{String(error)}</div> : null}
          <div style={{ height: 10 }} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {notes.length === 0 ? <div className="rc-muted">No notes yet.</div> : null}
            {notes.map((n) => (
              <button
                key={n.id}
                onClick={() => loadDetail(n.id)}
                className="rc-btn"
                style={{ textAlign: 'left', padding: 12, borderColor: n.id === selectedId ? 'rgba(79,70,229,0.35)' : 'rgba(15,23,42,0.16)', background: n.id === selectedId ? 'rgba(79,70,229,0.08)' : 'white' }}
              >
                <div style={{ fontWeight: 850 }}>{n.title}</div>
                <div className="rc-help">{n.note_type}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="rc-card">
          {selected ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ fontSize: 18, fontWeight: 900, letterSpacing: '-0.02em' }}>{selected.title}</div>
              <div className="rc-help">
                {selected.note_type} {selected.llm_model ? `· ${selected.llm_model}` : ''}
              </div>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', background: 'rgba(2,6,23,0.04)', borderRadius: 12, padding: 12, overflow: 'auto' }}>
                {selected.content}
              </pre>
            </div>
          ) : (
            <div className="rc-muted">Select a note to view it.</div>
          )}
        </div>
      </div>
    </div>
  );
}
