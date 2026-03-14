import { useEffect, useMemo, useState } from 'react';
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

function formatDate(value?: string | null) {
  if (!value) return 'Hora desconocida';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function NotesPage() {
  const { projectId } = useParams();

  const [notes, setNotes] = useState<NoteListRow[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<NoteDetail | null>(null);
  const [filterText, setFilterText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadList() {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const r = await api.get(`/notes/projects/${projectId}`);
      const nextNotes = r.data as NoteListRow[];
      setNotes(nextNotes);
      if (!selectedId && nextNotes[0]) {
        void loadDetail(nextNotes[0].id);
      } else if (selectedId && !nextNotes.some((note) => note.id === selectedId)) {
        if (nextNotes[0]) {
          void loadDetail(nextNotes[0].id);
        } else {
          setSelectedId(null);
          setSelected(null);
        }
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudieron cargar las notas');
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
      setError(e?.response?.data?.detail || 'No se pudo cargar la nota');
    }
  }

  useEffect(() => {
    void loadList();
  }, [projectId]);

  const filteredNotes = useMemo(() => {
    const query = filterText.trim().toLowerCase();
    if (!query) return notes;
    return notes.filter((note) => `${note.title} ${note.note_type}`.toLowerCase().includes(query));
  }, [notes, filterText]);

  return (
    <div className="rc-product-page">
      <div className="rc-product-page__header">
        <div>
          <div className="rc-kicker">Notas</div>
          <h2>Resúmenes, observaciones y notas de trabajo</h2>
          <p>Consulta notas generadas por IA o por el equipo sin salir del flujo principal del proyecto.</p>
        </div>
        <div className="rc-discover-badges">
          <span className="rc-discover-badge">{notes.length} notas</span>
          <span className="rc-discover-badge">{new Set(notes.map((note) => note.note_type)).size || '—'} tipos</span>
          <span className="rc-discover-badge">
            {selected ? selected.content.split(/\s+/).filter(Boolean).length : '—'} palabras
          </span>
        </div>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <div className="rc-product-two-column rc-product-two-column--wide">
        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title" style={{ marginBottom: 4 }}>Notas del proyecto</div>
              <div className="rc-help">Filtra por titulo o tipo de nota y abre cualquier nota en el panel de lectura.</div>
            </div>
            <button className="rc-btn rc-btn--subtle" onClick={() => void loadList()} disabled={loading}>
              {loading ? 'Actualizando...' : 'Actualizar'}
            </button>
          </div>
          <label className="rc-discover-filter-field">
            <span>Filtrar notas</span>
            <input
              className="rc-input"
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              placeholder="Buscar resúmenes, notas de extracción o screening..."
            />
          </label>
          <div className="rc-product-record-list">
            {filteredNotes.length === 0 ? (
              <div className="rc-empty-state">
                <div style={{ fontWeight: 800, marginBottom: 6 }}>{notes.length === 0 ? 'Todavia no hay notas' : 'No hay notas para este filtro'}</div>
                <div className="rc-help">
                  {notes.length === 0
                    ? 'Las notas apareceran cuando los resúmenes, acciones del lector u otros modulos generen comentarios a nivel de proyecto.'
                    : 'Prueba con una busqueda mas amplia por titulo o tipo de nota.'}
                </div>
              </div>
            ) : (
              filteredNotes.map((note) => (
                <button
                  key={note.id}
                  onClick={() => void loadDetail(note.id)}
                  className={`rc-list-button ${note.id === selectedId ? 'rc-list-button--active' : ''}`}
                >
                  <div className="rc-detail-header">
                    <div style={{ fontWeight: 850, lineHeight: 1.3 }}>{note.title}</div>
                    <span className="rc-badge">{note.note_type}</span>
                  </div>
                  <div className="rc-help" style={{ marginTop: 8 }}>
                    {note.paper_id ? `paper ${note.paper_id} · ` : ''}
                    {formatDate(note.created_at)}
                  </div>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="rc-product-card">
          {selected ? (
            <div className="rc-stack">
              <div className="rc-detail-header">
                <div style={{ flex: 1, minWidth: 220 }}>
                  <div style={{ fontSize: 28, fontWeight: 850, letterSpacing: '-0.03em', fontFamily: '"Iowan Old Style", "Palatino Linotype", Georgia, serif' }}>
                    {selected.title}
                  </div>
                  <div className="rc-help" style={{ marginTop: 10 }}>
                    {selected.note_type}
                    {selected.llm_model ? ` · ${selected.llm_model}` : ''}
                    {selected.paper_id ? ` · paper ${selected.paper_id}` : ''}
                  </div>
                </div>
                <span className="rc-badge rc-badge--info">Nota abierta</span>
              </div>

              <pre className="rc-code-block">{selected.content}</pre>
            </div>
          ) : (
            <div className="rc-empty-state">
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Selecciona una nota para leerla</div>
              <div className="rc-help">Elige una nota de la columna izquierda para abrir su contenido completo en una vista de lectura mas tranquila.</div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
