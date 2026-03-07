import type { ClinicalSheetDetail, EvidenceStrength, EvidenceSummary, TocItem } from './types';

export function slugify(s: string) {
  return (s || '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s\-áéíóúüñ]/gi, '')
    .replace(/\s+/g, '-')
    .slice(0, 80);
}

export function deriveToc(sheet: ClinicalSheetDetail | null): TocItem[] {
  if (!sheet) return [];

  if (sheet?.format_version === 'clinical_pro_v1' && sheet?.content_json?.sections) {
    const secs = sheet.content_json.sections as any[];
    return secs
      .filter((s) => s && typeof s.id === 'string' && typeof s.title === 'string')
      .map((s) => ({ text: String(s.title), id: String(s.id) }));
  }

  const md = sheet?.content_markdown || '';
  const lines = md.split('\n');
  const items: TocItem[] = [];
  for (const ln of lines) {
    const m = ln.match(/^##\s+(.+)$/);
    if (m) {
      const text = m[1].trim();
      items.push({ text, id: slugify(text) });
    }
  }
  return items;
}

function safeArray(v: any): any[] {
  return Array.isArray(v) ? v : [];
}

export function deriveEvidenceSummary(sheet: ClinicalSheetDetail | null): EvidenceSummary {
  // v2 will override later; v1 best-effort from sources_used
  const su = sheet?.sources_used || {};

  const papers = safeArray((su as any)?.papers)
    .map((p: any) => ({
      paper_id: String(p.paper_id || p.id || ''),
      title: p.title ?? null,
      pmid: p.pmid ?? null,
      doi: p.doi ?? null,
      year: typeof p.year === 'number' ? p.year : null,
      oa: typeof p.oa === 'boolean' ? p.oa : null,
    }))
    .filter((p) => p.paper_id);

  const online = safeArray((su as any)?.online_sources || (su as any)?.online || (su as any)?.sources)
    .map((x: any) => ({
      label: String(x.label || x.source || x.name || 'Source'),
      url: x.url ? String(x.url) : undefined,
    }));

  // try pull strength/gaps from content_json if present
  let evidenceStrength: EvidenceStrength | undefined = undefined;
  let gaps: string[] = [];
  const q = sheet?.content_json?.quality;
  if (q?.evidence_strength && ['high', 'medium', 'low'].includes(String(q.evidence_strength))) {
    evidenceStrength = String(q.evidence_strength) as EvidenceStrength;
  }
  if (Array.isArray(q?.gaps)) gaps = q.gaps.map((g: any) => String(g));

  const sourcesCount = papers.length + online.length;

  return {
    sourcesCount,
    projectPapers: papers,
    onlineSources: online,
    evidenceStrength: evidenceStrength || 'na',
    gaps,
  };
}
