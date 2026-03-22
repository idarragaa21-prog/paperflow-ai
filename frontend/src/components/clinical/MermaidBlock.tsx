import { useEffect, useMemo, useRef, useState } from 'react';

type Props = {
  code: string;
};

let mermaidInitDone = false;

function stripFences(txt: string): string {
  let t = (txt || '').trim();
  if (!t.startsWith('```')) return t;
  const lines = t.split('\n');
  lines.shift();
  if (lines.length && lines[lines.length - 1].trim().startsWith('```')) lines.pop();
  return lines.join('\n').trim();
}

function guessKind(txt: string): 'mindmap' | 'flowchart' {
  const t = txt.toLowerCase();
  if (t.includes('mindmap')) return 'mindmap';
  return 'flowchart';
}

function fallbackCode(kind: 'mindmap' | 'flowchart'): string {
  if (kind === 'mindmap') {
    return 'mindmap\n  root((Tema))\n    Diagnóstico\n    Tratamiento\n    Retorno al deporte\n    Riesgos/complicaciones\n';
  }
  return 'flowchart TD\nA[Inicio]-->B{Sospecha clínica?}\nB-->|No|C[Considerar dx alternativos]\nB-->|Sí|D[Imagen: RM/TC según disponibilidad]\nD-->E{Fractura de estrés confirmada?}\nE-->|No|F[Re-evaluar]\nE-->|Sí|G[Plan de manejo + seguimiento]\n';
}

export default function MermaidBlock({ code }: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [usedFallback, setUsedFallback] = useState(false);

  const normalized = useMemo(() => {
    let txt = stripFences(String(code || '')).replace(/\t/g, '  ');
    txt = txt.replace(/\r\n/g, '\n');

    const lines = txt.split('\n');
    const firstNonEmpty = lines.find((l) => l.trim().length > 0)?.trim() || '';
    const isMindmap = firstNonEmpty.toLowerCase().startsWith('mindmap');

    const cleaned = lines
      .map((l, idx) => {
        let s = l;
        // normalize unicode that can break the parser
        s = s.replace(/[–—]/g, '-');
        s = s.replace(/&/g, 'and');

        if (idx === 0) return s.trim();

        // For flowchart/graph, leading indentation can cause syntax errors.
        if (!isMindmap) s = s.trimStart();

        // Mermaid is picky about trailing spaces in some constructs
        return s.replace(/\s+$/g, '');
      })
      .join('\n')
      .trim();

    return cleaned;
  }, [code]);

  useEffect(() => {
    let alive = true;

    async function renderOnce(mermaid: any, src: string): Promise<string> {
      const id = `mmd_${Math.random().toString(36).slice(2)}`;
      const out = await mermaid.render(id, src);
      return out?.svg || '';
    }

    async function run() {
      setError(null);
      setUsedFallback(false);
      if (!hostRef.current) return;
      hostRef.current.innerHTML = '';
      if (!normalized) return;

      try {
        const mod: any = await import('mermaid');
        const mermaid = mod?.default || mod;
        if (!mermaidInitDone) {
          mermaid.initialize({
            startOnLoad: false,
            theme: 'default',
            securityLevel: 'strict',
            suppressErrorRendering: true,
            logLevel: 'fatal',
          });
          mermaidInitDone = true;
        }

        let svg = '';
        try {
          svg = await renderOnce(mermaid, normalized);
        } catch (err: any) {
          // Mermaid sometimes throws instead of returning an error SVG.
          svg = '';
        }

        if (!alive) return;

        const isBad = !svg.trim() || svg.includes('Syntax error in text') || svg.includes('Parse error');
        if (isBad) {
          const fb = fallbackCode(guessKind(normalized));
          const svg2 = await renderOnce(mermaid, fb);
          if (!alive) return;
          const isBad2 = !svg2.trim() || svg2.includes('Syntax error in text') || svg2.includes('Parse error');
          if (isBad2) {
            setError('Mermaid parse error (fallback also failed).');
            hostRef.current.innerHTML = '';
            return;
          }
          setUsedFallback(true);
          hostRef.current.innerHTML = svg2;
          return;
        }

        hostRef.current.innerHTML = svg;
      } catch (e: any) {
        if (!alive) return;
        setError(String(e?.message || e));
      }
    }

    run();
    return () => {
      alive = false;
    };
  }, [normalized]);

  return (
    <div>
      {usedFallback ? <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>Mermaid: rendered fallback diagram (source had syntax errors).</div> : null}
      {error ? (
        <div className="rc-error" style={{ fontSize: 12 }}>
          Mermaid render failed: {error}
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 11, opacity: 0.85 }}>{normalized}</pre>
        </div>
      ) : null}
      <div ref={hostRef} />
    </div>
  );
}
