import { Link } from 'react-router-dom';
import { useI18n } from '../i18n';

const features = [
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
    ),
    title: { en: 'AI-Powered Search', es: 'Búsqueda con IA', pt: 'Busca com IA' },
    desc: {
      en: 'Search across PubMed with intelligent queries. Get results ranked by relevance with automatic open-access resolution.',
      es: 'Busca en PubMed con consultas inteligentes. Resultados ordenados por relevancia con resolución automática de acceso abierto.',
      pt: 'Pesquise no PubMed com consultas inteligentes. Resultados classificados por relevância com resolução automática de acesso aberto.',
    },
    color: '#6366f1',
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <path d="M12 18v-6"/><path d="M9 15l3 3 3-3"/>
      </svg>
    ),
    title: { en: 'AI Paper Reader', es: 'Lector de Papers con IA', pt: 'Leitor de Papers com IA' },
    desc: {
      en: 'Chat with your PDFs using AI grounded in the document. Ask questions, extract data, and get cited answers.',
      es: 'Chatea con tus PDFs usando IA fundamentada en el documento. Haz preguntas, extrae datos y obtén respuestas citadas.',
      pt: 'Converse com seus PDFs usando IA fundamentada no documento. Faça perguntas, extraia dados e obtenha respostas citadas.',
    },
    color: '#10b981',
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
        <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
      </svg>
    ),
    title: { en: 'Meta-Analysis Engine', es: 'Motor de Meta-Análisis', pt: 'Motor de Meta-Análise' },
    desc: {
      en: 'Extract data from papers with AI, calculate effect sizes, assess risk of bias, and run statistical analysis with R.',
      es: 'Extrae datos de papers con IA, calcula tamaños de efecto, evalúa riesgo de sesgo y ejecuta análisis estadístico con R.',
      pt: 'Extraia dados de papers com IA, calcule tamanhos de efeito, avalie risco de viés e execute análise estatística com R.',
    },
    color: '#f59e0b',
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10 2v4M8 4h4"/><rect x="3" y="6" width="18" height="14" rx="2"/>
        <path d="M7 10h10M7 14h6"/>
      </svg>
    ),
    title: { en: 'Clinical Evidence Sheets', es: 'Fichas de Evidencia Clínica', pt: 'Fichas de Evidência Clínica' },
    desc: {
      en: 'Generate UpToDate-style clinical summaries using a multi-pass LLM pipeline. Export to DOCX and PDF with full citations.',
      es: 'Genera resúmenes clínicos tipo UpToDate con un pipeline LLM multi-paso. Exporta a DOCX y PDF con citas completas.',
      pt: 'Gere resumos clínicos tipo UpToDate com um pipeline LLM multi-passo. Exporte para DOCX e PDF com citações completas.',
    },
    color: '#ef4444',
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
      </svg>
    ),
    title: { en: 'AI Writer + Drafts', es: 'Escritor IA + Borradores', pt: 'Escritor IA + Rascunhos' },
    desc: {
      en: 'Write scientific papers with AI assistance. Inline editing, automatic citation resolution, and HTML export.',
      es: 'Escribe papers científicos con asistencia de IA. Edición inline, resolución automática de citas y exportación HTML.',
      pt: 'Escreva papers científicos com assistência de IA. Edição inline, resolução automática de citações e exportação HTML.',
    },
    color: '#8b5cf6',
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
      </svg>
    ),
    title: { en: 'Reference Manager', es: 'Gestor de Referencias', pt: 'Gerenciador de Referências' },
    desc: {
      en: 'Import by DOI, export BibTeX, copy APA. Full project-scoped reference management with batch operations.',
      es: 'Importa por DOI, exporta BibTeX, copia APA. Gestión completa de referencias por proyecto con operaciones en lote.',
      pt: 'Importe por DOI, exporte BibTeX, copie APA. Gestão completa de referências por projeto com operações em lote.',
    },
    color: '#0ea5e9',
  },
];

const stats = [
  { value: '200M+', label: { en: 'Papers indexed via PubMed', es: 'Papers indexados vía PubMed', pt: 'Papers indexados via PubMed' } },
  { value: '105+', label: { en: 'API endpoints', es: 'Endpoints de API', pt: 'Endpoints de API' } },
  { value: '100%', label: { en: 'Local & private', es: 'Local y privado', pt: 'Local e privado' } },
  { value: '0', label: { en: 'Data sent to cloud', es: 'Datos enviados a la nube', pt: 'Dados enviados para a nuvem' } },
];

const comparisons = {
  en: [
    { them: 'Cloud-dependent', us: 'Runs 100% on your machine' },
    { them: '$24/month for Pro', us: 'Free and open source' },
    { them: 'No meta-analysis', us: 'Full R-powered stats engine' },
    { them: 'No clinical sheets', us: 'UpToDate-style evidence generator' },
    { them: 'No PRISMA screening', us: 'Built-in screening workflow' },
    { them: 'Your data on their servers', us: 'Your data stays on your disk' },
  ],
  es: [
    { them: 'Depende de la nube', us: 'Corre 100% en tu máquina' },
    { them: '$24/mes por Pro', us: 'Gratis y código abierto' },
    { them: 'Sin meta-análisis', us: 'Motor estadístico con R completo' },
    { them: 'Sin fichas clínicas', us: 'Generador de evidencia tipo UpToDate' },
    { them: 'Sin tamizaje PRISMA', us: 'Flujo de tamizaje integrado' },
    { them: 'Tus datos en sus servidores', us: 'Tus datos se quedan en tu disco' },
  ],
  pt: [
    { them: 'Depende da nuvem', us: 'Roda 100% na sua máquina' },
    { them: '$24/mês pelo Pro', us: 'Grátis e código aberto' },
    { them: 'Sem meta-análise', us: 'Motor estatístico com R completo' },
    { them: 'Sem fichas clínicas', us: 'Gerador de evidência tipo UpToDate' },
    { them: 'Sem triagem PRISMA', us: 'Fluxo de triagem integrado' },
    { them: 'Seus dados nos servidores deles', us: 'Seus dados ficam no seu disco' },
  ],
};

const heroText = {
  en: {
    badge: 'Open source · Local-first · Private by design',
    h1_1: 'Your all-in-one',
    h1_2: 'AI research workspace',
    sub: 'Search, extract, analyze and write academic papers — powered by AI, running entirely on your machine. No subscriptions, no cloud, no data leaving your computer.',
    cta1: 'Get Started Free',
    cta2: 'Live Demo',
    trusted: 'Built for researchers, by a researcher',
  },
  es: {
    badge: 'Código abierto · Local-first · Privado por diseño',
    h1_1: 'Tu todo en uno',
    h1_2: 'Espacio de investigación con IA',
    sub: 'Busca, extrae, analiza y escribe papers académicos — potenciado por IA, corriendo completamente en tu máquina. Sin suscripciones, sin nube, sin datos saliendo de tu computadora.',
    cta1: 'Comenzar Gratis',
    cta2: 'Demo en Vivo',
    trusted: 'Hecho para investigadores, por un investigador',
  },
  pt: {
    badge: 'Código aberto · Local-first · Privado por design',
    h1_1: 'Seu tudo em um',
    h1_2: 'Espaço de pesquisa com IA',
    sub: 'Pesquise, extraia, analise e escreva papers acadêmicos — potencializado por IA, rodando inteiramente na sua máquina. Sem assinaturas, sem nuvem, sem dados saindo do seu computador.',
    cta1: 'Começar Grátis',
    cta2: 'Demo ao Vivo',
    trusted: 'Feito para pesquisadores, por um pesquisador',
  },
};

const sectionTitles = {
  en: { features: 'One guided workflow for research', compare: 'Why PaperFlow?', compareSub: 'vs. cloud-based alternatives', cta: 'Ready to own your research?', ctaSub: 'Free forever. No credit card. No cloud.' },
  es: { features: 'Un flujo guiado para investigar', compare: '¿Por qué PaperFlow?', compareSub: 'vs. alternativas en la nube', cta: '¿Listo para ser dueño de tu investigación?', ctaSub: 'Gratis para siempre. Sin tarjeta de crédito. Sin nube.' },
  pt: { features: 'Um fluxo guiado para pesquisar', compare: 'Por que PaperFlow?', compareSub: 'vs. alternativas na nuvem', cta: 'Pronto para ser dono da sua pesquisa?', ctaSub: 'Grátis para sempre. Sem cartão de crédito. Sem nuvem.' },
};

const workflowSteps = {
  en: [
    { n: '01', title: 'Search', desc: 'Start with federated search and build a shortlist of relevant studies.' },
    { n: '02', title: 'Library', desc: 'Download, process and curate the papers you actually want to use.' },
    { n: '03', title: 'Extract + Write', desc: 'Turn full text into structured evidence and grounded manuscript sections.' },
    { n: '04', title: 'Analyze + Share', desc: 'Run reproducible analysis and export clinical sheets or reports.' },
  ],
  es: [
    { n: '01', title: 'Search', desc: 'Empieza con búsqueda federada y arma una shortlist de estudios relevantes.' },
    { n: '02', title: 'Library', desc: 'Descarga, procesa y organiza los papers que realmente vas a usar.' },
    { n: '03', title: 'Extract + Write', desc: 'Convierte texto completo en evidencia estructurada y secciones redactadas.' },
    { n: '04', title: 'Analyze + Share', desc: 'Ejecuta análisis reproducibles y exporta fichas clínicas o reportes.' },
  ],
  pt: [
    { n: '01', title: 'Search', desc: 'Comece com busca federada e monte uma shortlist de estudos relevantes.' },
    { n: '02', title: 'Library', desc: 'Baixe, processe e organize os papers que você realmente vai usar.' },
    { n: '03', title: 'Extract + Write', desc: 'Transforme texto completo em evidência estruturada e seções redigidas.' },
    { n: '04', title: 'Analyze + Share', desc: 'Execute análises reproduzíveis e exporte fichas clínicas ou relatórios.' },
  ],
};

export default function LandingPage() {
  const { locale } = useI18n();
  const hero = heroText[locale];
  const titles = sectionTitles[locale];
  const comp = comparisons[locale];
  const steps = workflowSteps[locale];

  return (
    <div style={{ background: '#0a0a12', color: 'white', minHeight: '100vh', fontFamily: "'DM Sans', sans-serif" }}>
      {/* NAV */}
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 32px', maxWidth: 1200, margin: '0 auto',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
          </div>
          <span style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.03em' }}>PaperFlow AI</span>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <Link to="/login" style={{ padding: '8px 18px', borderRadius: 10, fontSize: 13, fontWeight: 600, color: 'rgba(255,255,255,0.7)', textDecoration: 'none', border: '1px solid rgba(255,255,255,0.12)' }}>
            Log in
          </Link>
          <Link to="/signup" style={{ padding: '8px 18px', borderRadius: 10, fontSize: 13, fontWeight: 700, color: 'white', textDecoration: 'none', background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
            {hero.cta1}
          </Link>
        </div>
      </nav>

      {/* HERO */}
      <section style={{ textAlign: 'center', padding: '80px 24px 60px', maxWidth: 800, margin: '0 auto', position: 'relative' }}>
        <div style={{ position: 'absolute', top: 0, left: '50%', transform: 'translateX(-50%)', width: 600, height: 600, background: 'radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%)', pointerEvents: 'none' }} />
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 16px',
          borderRadius: 999, border: '1px solid rgba(99,102,241,0.3)', background: 'rgba(99,102,241,0.08)',
          fontSize: 12, fontWeight: 600, color: 'rgba(165,160,255,0.9)', marginBottom: 28,
        }}>{hero.badge}</div>

        <h1 style={{ fontSize: 'clamp(36px, 6vw, 64px)', fontWeight: 900, letterSpacing: '-0.04em', lineHeight: 1.08, margin: '0 0 20px' }}>
          {hero.h1_1}<br />
          <span style={{ background: 'linear-gradient(135deg, #818cf8, #c084fc)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            {hero.h1_2}
          </span>
        </h1>

        <p style={{ fontSize: 17, color: 'rgba(255,255,255,0.5)', lineHeight: 1.7, maxWidth: 580, margin: '0 auto 36px' }}>
          {hero.sub}
        </p>

        <div style={{ display: 'flex', gap: 14, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link to="/signup" style={{
            padding: '14px 32px', borderRadius: 14, fontSize: 15, fontWeight: 700, textDecoration: 'none',
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: 'white',
            boxShadow: '0 4px 24px rgba(99,102,241,0.4)',
          }}>{hero.cta1} →</Link>
          <a href="https://idarragaa21-prog.github.io/paperflow-ai/" target="_blank" rel="noopener" style={{
            padding: '14px 32px', borderRadius: 14, fontSize: 15, fontWeight: 600, textDecoration: 'none',
            border: '1px solid rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.8)',
          }}>{hero.cta2}</a>
        </div>

        <p style={{ marginTop: 40, fontSize: 13, color: 'rgba(255,255,255,0.25)' }}>{hero.trusted}</p>
      </section>

      {/* STATS */}
      <section style={{ maxWidth: 900, margin: '0 auto', padding: '20px 24px 60px' }}>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16,
          padding: '28px 24px', borderRadius: 20, border: '1px solid rgba(255,255,255,0.08)',
          background: 'rgba(255,255,255,0.02)',
        }}>
          {stats.map((s, i) => (
            <div key={i} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 32, fontWeight: 900, letterSpacing: '-0.04em', background: 'linear-gradient(135deg, #818cf8, #c084fc)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                {s.value}
              </div>
              <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>{s.label[locale]}</div>
            </div>
          ))}
        </div>
      </section>

      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '0 24px 72px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 28 }}>
          <h2 style={{ fontSize: 'clamp(24px, 4vw, 40px)', fontWeight: 900, letterSpacing: '-0.03em', margin: 0 }}>
            {titles.features}
          </h2>
          <p style={{ margin: 0, maxWidth: 680, color: 'rgba(255,255,255,0.5)', lineHeight: 1.7 }}>
            PaperFlow works best when it feels like one continuous research workspace, not a menu of disconnected AI tricks.
          </p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
          {steps.map((step) => (
            <div key={step.n} style={{ padding: 22, borderRadius: 18, border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)' }}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'rgba(129,140,248,0.9)', marginBottom: 12 }}>{step.n}</div>
              <div style={{ fontSize: 20, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 8 }}>{step.title}</div>
              <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.5)', lineHeight: 1.65 }}>{step.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* FEATURES */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '40px 24px 80px' }}>
        <h2 style={{ textAlign: 'center', fontSize: 'clamp(22px, 4vw, 34px)', fontWeight: 900, letterSpacing: '-0.03em', marginBottom: 12 }}>
          Supporting capabilities
        </h2>
        <p style={{ textAlign: 'center', color: 'rgba(255,255,255,0.42)', maxWidth: 620, margin: '0 auto 36px', lineHeight: 1.7 }}>
          These are not random tools. They are the specialist surfaces that support the core search-to-writing workflow.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20 }}>
          {features.slice(0, 4).map((f, i) => (
            <div key={i} style={{
              padding: 28, borderRadius: 20, border: '1px solid rgba(255,255,255,0.07)',
              background: 'rgba(255,255,255,0.02)', transition: 'border-color 200ms',
            }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = `${f.color}44`)}
            onMouseLeave={e => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)')}
            >
              <div style={{
                width: 48, height: 48, borderRadius: 14, marginBottom: 16,
                background: `${f.color}15`, border: `1px solid ${f.color}30`,
                display: 'flex', alignItems: 'center', justifyContent: 'center', color: f.color,
              }}>{f.icon}</div>
              <div style={{ fontSize: 17, fontWeight: 750, letterSpacing: '-0.02em', marginBottom: 8 }}>
                {f.title[locale]}
              </div>
              <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.45)', lineHeight: 1.65 }}>
                {f.desc[locale]}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* COMPARISON */}
      <section style={{ maxWidth: 700, margin: '0 auto', padding: '40px 24px 80px' }}>
        <h2 style={{ textAlign: 'center', fontSize: 'clamp(24px, 4vw, 36px)', fontWeight: 900, letterSpacing: '-0.03em', marginBottom: 6 }}>
          {titles.compare}
        </h2>
        <p style={{ textAlign: 'center', fontSize: 14, color: 'rgba(255,255,255,0.35)', marginBottom: 36 }}>
          {titles.compareSub}
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {comp.map((row, i) => (
            <div key={i} style={{
              display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12,
              padding: '14px 20px', borderRadius: 14, background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.06)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'rgba(255,255,255,0.35)' }}>
                <span style={{ color: '#ef4444', fontSize: 14 }}>✗</span> {row.them}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'rgba(255,255,255,0.85)', fontWeight: 600 }}>
                <span style={{ color: '#10b981', fontSize: 14 }}>✓</span> {row.us}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* FINAL CTA */}
      <section style={{ textAlign: 'center', padding: '60px 24px 100px', position: 'relative' }}>
        <div style={{ position: 'absolute', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: 500, height: 400, background: 'radial-gradient(circle, rgba(139,92,246,0.12) 0%, transparent 70%)', pointerEvents: 'none' }} />
        <h2 style={{ fontSize: 'clamp(26px, 4vw, 42px)', fontWeight: 900, letterSpacing: '-0.03em', marginBottom: 10, position: 'relative' }}>
          {titles.cta}
        </h2>
        <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.4)', marginBottom: 32, position: 'relative' }}>
          {titles.ctaSub}
        </p>
        <Link to="/signup" style={{
          display: 'inline-block', padding: '16px 40px', borderRadius: 14, fontSize: 16, fontWeight: 700,
          textDecoration: 'none', background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: 'white',
          boxShadow: '0 4px 24px rgba(99,102,241,0.4)', position: 'relative',
        }}>{hero.cta1} →</Link>
      </section>

      {/* FOOTER */}
      <footer style={{
        borderTop: '1px solid rgba(255,255,255,0.06)', padding: '32px 24px',
        maxWidth: 1100, margin: '0 auto',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 28, height: 28, borderRadius: 8, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          </div>
          <span style={{ fontSize: 14, fontWeight: 700 }}>PaperFlow AI</span>
        </div>
        <div style={{ display: 'flex', gap: 24, fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>
          <a href="https://github.com/idarragaa21-prog/paperflow-ai" target="_blank" rel="noopener" style={{ color: 'inherit', textDecoration: 'none' }}>GitHub</a>
          <Link to="/login" style={{ color: 'inherit', textDecoration: 'none' }}>Log in</Link>
          <Link to="/signup" style={{ color: 'inherit', textDecoration: 'none' }}>Sign up</Link>
        </div>
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.2)' }}>
          © {new Date().getFullYear()} Diego Alejandro Idarraga. MIT License.
        </div>
      </footer>
    </div>
  );
}
