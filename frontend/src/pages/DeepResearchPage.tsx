import { useState } from 'react';
import type { FormEvent } from 'react';
import { api } from '../services/api';
import { useI18n } from '../i18n';
import { DEMO_MODE } from '../services/demo';

type Section = { key: string; title: string; content: string };
type Paper = { pmid: string; title: string; authors: string; journal: string; year: string; abstract: string };
type Report = {
  id: string;
  query: string;
  status: string;
  sections: Section[];
  papers: Paper[];
  papers_analyzed: number;
  metadata: { duration_seconds: number };
};

const demoReport: Report = {
  id: 'demo',
  query: 'distal radius fracture outcomes in elderly patients',
  status: 'completed',
  papers_analyzed: 12,
  metadata: { duration_seconds: 45.2 },
  papers: [
    { pmid: '38901234', title: 'Functional outcomes after volar locking plate fixation of distal radius fractures in patients over 65', authors: 'Johnson A et al.', journal: 'J Hand Surg', year: '2023', abstract: '' },
    { pmid: '38765432', title: 'Conservative vs surgical management of distal radius fractures: a systematic review', authors: 'Chen X, Rodriguez M', journal: 'Bone Joint J', year: '2022', abstract: '' },
    { pmid: '38654321', title: 'Patient-reported outcomes measures in distal radius fracture treatment', authors: 'Davis K et al.', journal: 'Clin Orthop', year: '2023', abstract: '' },
  ],
  sections: [
    { key: 'overview', title: 'Research Overview', content: 'This deep research report analyzes 12 papers published between 2020-2024 on functional outcomes following distal radius fracture treatment in elderly patients (≥65 years). The literature reveals a growing consensus toward individualized treatment approaches that balance surgical outcomes with patient comorbidities and functional demands. Key themes include the comparison of volar locking plate fixation vs. conservative management, the role of patient-reported outcome measures (PROMs), and the impact of osteoporotic bone quality on treatment decisions.' },
    { key: 'key_findings', title: 'Key Findings', content: 'The most significant findings across the literature include: (1) Volar locking plate fixation demonstrates superior radiographic outcomes but similar functional results at 12 months compared to cast immobilization in patients over 65 [1][2]. (2) Patient-reported outcome measures show that grip strength recovery is the strongest predictor of patient satisfaction, regardless of treatment modality [3]. (3) Complication rates are higher in the surgical group (12-18%) compared to conservative management (5-8%), primarily driven by hardware irritation and CRPS [1][4]. (4) Early mobilization protocols significantly improve outcomes in both treatment groups [5].' },
    { key: 'methodology', title: 'Methodology Trends', content: 'The majority of studies employed retrospective cohort designs (7/12), with 3 randomized controlled trials and 2 systematic reviews. Sample sizes ranged from 45 to 312 patients. The DASH score and grip strength were the most commonly used outcome measures. A notable methodological gap is the lack of standardized follow-up periods, ranging from 6 months to 5 years across studies.' },
    { key: 'consensus', title: 'Consensus & Controversies', content: 'Strong consensus exists around the efficacy of volar locking plates for unstable fracture patterns. However, significant controversy persists regarding treatment of extra-articular fractures with acceptable alignment in elderly patients — approximately half the literature supports conservative management while the other half advocates for surgical fixation to enable earlier mobilization.' },
    { key: 'gaps', title: 'Research Gaps & Future Directions', content: 'Key gaps include: (1) Lack of cost-effectiveness analyses comparing treatment strategies in elderly populations. (2) Insufficient data on outcomes in patients >80 years with multiple comorbidities. (3) Need for standardized PROMs specific to elderly hand/wrist function. Future research should prioritize pragmatic RCTs with patient-centered primary outcomes and long-term follow-up.' },
    { key: 'conclusion', title: 'Conclusion', content: 'The current evidence supports an individualized approach to distal radius fracture management in elderly patients. While surgical fixation offers better radiographic outcomes, functional results are similar to conservative treatment at 12 months for many fracture patterns. Clinicians should weigh patient factors including functional demands, bone quality, and comorbidities when making treatment decisions.' },
  ],
};

const text = {
  en: {
    title: 'Deep Research',
    subtitle: 'AI analyzes papers from PubMed and generates a comprehensive research report with citations.',
    placeholder: 'Enter your research question (e.g. "effect of rehabilitation protocols on ACL reconstruction outcomes")',
    generate: 'Generate Report',
    generating: 'Generating report…',
    duration: 'Generated in',
    seconds: 'seconds',
    papersAnalyzed: 'papers analyzed',
    references: 'Source Papers',
    tipTitle: 'Tips for best results',
    tips: [
      'Be specific: "SGLT2 inhibitors in heart failure with preserved ejection fraction" > "heart drugs"',
      'Include population: "...in elderly patients" or "...in pediatric populations"',
      'Add timeframe if relevant: "...published after 2020"',
    ],
  },
  es: {
    title: 'Investigación Profunda',
    subtitle: 'La IA analiza papers de PubMed y genera un reporte de investigación integral con citas.',
    placeholder: 'Ingresa tu pregunta de investigación (ej. "efecto de protocolos de rehabilitación en resultados de reconstrucción de LCA")',
    generate: 'Generar Reporte',
    generating: 'Generando reporte…',
    duration: 'Generado en',
    seconds: 'segundos',
    papersAnalyzed: 'papers analizados',
    references: 'Papers Fuente',
    tipTitle: 'Consejos para mejores resultados',
    tips: [
      'Sé específico: "inhibidores SGLT2 en insuficiencia cardíaca con fracción de eyección preservada" > "fármacos cardíacos"',
      'Incluye población: "...en pacientes ancianos" o "...en poblaciones pediátricas"',
      'Agrega marco temporal si es relevante: "...publicados después de 2020"',
    ],
  },
  pt: {
    title: 'Pesquisa Profunda',
    subtitle: 'A IA analisa papers do PubMed e gera um relatório de pesquisa abrangente com citações.',
    placeholder: 'Digite sua pergunta de pesquisa (ex. "efeito de protocolos de reabilitação nos resultados de reconstrução do LCA")',
    generate: 'Gerar Relatório',
    generating: 'Gerando relatório…',
    duration: 'Gerado em',
    seconds: 'segundos',
    papersAnalyzed: 'papers analisados',
    references: 'Papers Fonte',
    tipTitle: 'Dicas para melhores resultados',
    tips: [
      'Seja específico: "inibidores SGLT2 na insuficiência cardíaca com fração de ejeção preservada" > "medicamentos cardíacos"',
      'Inclua população: "...em pacientes idosos" ou "...em populações pediátricas"',
      'Adicione período temporal se relevante: "...publicados após 2020"',
    ],
  },
};

export default function DeepResearchPage() {
  const { locale } = useI18n();
  const t = text[locale];
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedPaper, setExpandedPaper] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setError(null);
    setLoading(true);
    setReport(null);
    try {
      if (DEMO_MODE) {
        await new Promise(r => setTimeout(r, 2000));
        setReport({ ...demoReport, query });
      } else {
        const r = await api.post('/research/deep', { query, max_papers: 15 });
        setReport(r.data);
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to generate report');
    } finally { setLoading(false); }
  }

  return (
    <div className="rc-page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 860 }}>
      <div>
        <h1 className="rc-page-title">{t.title}</h1>
        <div className="rc-subtitle">{t.subtitle}</div>
      </div>

      {/* Search form */}
      <form onSubmit={onSubmit} style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <input
          className="rc-input"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder={t.placeholder}
          required
          disabled={loading}
          style={{ flex: 1, minWidth: 300, fontSize: 14 }}
        />
        <button type="submit" className="rc-btn rc-btn--primary" disabled={loading || !query.trim()}
          style={{ padding: '10px 24px', whiteSpace: 'nowrap' }}>
          {loading ? (
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="rc-spinner" style={{ width: 14, height: 14, borderTopColor: 'white' }} />
              {t.generating}
            </span>
          ) : `${t.generate} →`}
        </button>
      </form>

      {error && <div className="rc-error">{error}</div>}

      {/* Tips (show when no report) */}
      {!report && !loading && (
        <div className="rc-card" style={{ padding: 20, background: 'var(--rc-surface-2)' }}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>{t.tipTitle}</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {t.tips.map((tip, i) => (
              <div key={i} style={{ display: 'flex', gap: 8, fontSize: 13, color: 'var(--rc-text-secondary)' }}>
                <span style={{ color: 'var(--rc-primary)', fontWeight: 700, flexShrink: 0 }}>{i + 1}.</span>
                {tip}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Loading animation */}
      {loading && (
        <div className="rc-card" style={{ padding: 40, textAlign: 'center' }}>
          <div className="rc-spinner" style={{ width: 32, height: 32, margin: '0 auto 16px' }} />
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>{t.generating}</div>
          <div style={{ color: 'var(--rc-muted)', fontSize: 13 }}>
            Searching PubMed, analyzing papers, and writing report sections…
          </div>
        </div>
      )}

      {/* Report */}
      {report && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Report header */}
          <div className="rc-card" style={{ padding: 20, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 17, letterSpacing: '-0.02em' }}>
                {report.query}
              </div>
              <div style={{ display: 'flex', gap: 16, marginTop: 6, fontSize: 12, color: 'var(--rc-muted)' }}>
                <span>{report.papers_analyzed} {t.papersAnalyzed}</span>
                <span>{t.duration} {report.metadata.duration_seconds.toFixed(1)} {t.seconds}</span>
              </div>
            </div>
            <div style={{
              padding: '4px 12px', borderRadius: 999, fontSize: 11, fontWeight: 700,
              background: 'var(--rc-success-bg)', color: 'var(--rc-success)', border: '1px solid var(--rc-success-border)',
            }}>✓ {report.status}</div>
          </div>

          {/* Sections */}
          {report.sections.map((section) => (
            <div key={section.key} className="rc-card" style={{ padding: 24 }}>
              <div style={{
                fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 16,
                letterSpacing: '-0.02em', marginBottom: 12,
                paddingBottom: 10, borderBottom: '1px solid var(--rc-border)',
              }}>
                {section.title}
              </div>
              <div style={{ fontSize: 14, lineHeight: 1.75, color: 'var(--rc-text-secondary)', whiteSpace: 'pre-wrap' }}>
                {section.content}
              </div>
            </div>
          ))}

          {/* Source papers */}
          <div className="rc-card" style={{ padding: 20 }}>
            <div style={{
              fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 15,
              marginBottom: 14, letterSpacing: '-0.02em',
            }}>
              {t.references} ({report.papers.length})
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {report.papers.map((p, i) => (
                <div key={p.pmid || i} style={{
                  padding: '10px 14px', borderRadius: 10, background: 'var(--rc-surface-2)',
                  cursor: p.abstract ? 'pointer' : 'default',
                }}
                onClick={() => p.abstract && setExpandedPaper(expandedPaper === p.pmid ? null : p.pmid)}
                >
                  <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                    <span style={{
                      flexShrink: 0, width: 22, height: 22, borderRadius: 6,
                      background: 'var(--rc-primary-weak)', color: 'var(--rc-primary)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 11, fontWeight: 700,
                    }}>{i + 1}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 650, fontSize: 13, lineHeight: 1.4 }}>{p.title}</div>
                      <div style={{ fontSize: 12, color: 'var(--rc-muted)', marginTop: 3 }}>
                        {p.authors} — {p.journal} ({p.year})
                        {p.pmid && (
                          <a href={`https://pubmed.ncbi.nlm.nih.gov/${p.pmid}/`} target="_blank" rel="noopener"
                            style={{ marginLeft: 8, color: 'var(--rc-primary)', fontSize: 11 }}
                            onClick={e => e.stopPropagation()}>
                            PubMed ↗
                          </a>
                        )}
                      </div>
                      {expandedPaper === p.pmid && p.abstract && (
                        <div style={{ marginTop: 8, fontSize: 12, color: 'var(--rc-text-secondary)', lineHeight: 1.6, borderTop: '1px solid var(--rc-border)', paddingTop: 8 }}>
                          {p.abstract}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
