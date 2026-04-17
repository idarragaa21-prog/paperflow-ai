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
    title: { en: 'Clinical Consults', es: 'Consultas Clínicas Rápidas', pt: 'Consultas Clínicas Rápidas' },
    desc: {
      en: 'Ask focused clinical questions and get concise, actionable answers grounded in project papers and PubMed citations.',
      es: 'Haz preguntas clínicas concretas y recibe respuestas accionables, breves y fundamentadas en papers del proyecto y PubMed.',
      pt: 'Faça perguntas clínicas objetivas e receba respostas acionáveis, curtas e fundamentadas em papers do projeto e PubMed.',
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
    title: { en: 'Scientific Writing Assistant', es: 'Asistente de Redacción Científica', pt: 'Assistente de Redação Científica' },
    desc: {
      en: 'Generate IMRAD sections, abstracts and legends with strict grounding to matrix evidence, R outputs and traceable citations.',
      es: 'Genera secciones IMRAD, abstracts y leyendas con grounding estricto a la matriz, resultados de R y citas trazables.',
      pt: 'Gere seções IMRAD, resumos e legendas com grounding estrito na matriz, resultados de R e citações rastreáveis.',
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
    { them: 'No clinical consults', us: 'Grounded rapid clinical consults' },
    { them: 'Fragmented extraction tables', us: 'Versioned master extraction matrix' },
    { them: 'Your data on their servers', us: 'Your data stays on your disk' },
  ],
  es: [
    { them: 'Depende de la nube', us: 'Corre 100% en tu máquina' },
    { them: '$24/mes por Pro', us: 'Gratis y código abierto' },
    { them: 'Sin meta-análisis', us: 'Motor estadístico con R completo' },
    { them: 'Sin consultas clínicas rápidas', us: 'Consultas clínicas con grounding bibliográfico' },
    { them: 'Tablas de extracción fragmentadas', us: 'Master matrix versionada y trazable' },
    { them: 'Tus datos en sus servidores', us: 'Tus datos se quedan en tu disco' },
  ],
  pt: [
    { them: 'Depende da nuvem', us: 'Roda 100% na sua máquina' },
    { them: '$24/mês pelo Pro', us: 'Grátis e código aberto' },
    { them: 'Sem meta-análise', us: 'Motor estatístico com R completo' },
    { them: 'Sem consultas clínicas rápidas', us: 'Consultas clínicas com grounding bibliográfico' },
    { them: 'Tabelas de extração fragmentadas', us: 'Master matrix versionada e rastreável' },
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
  en: {
    features: 'One guided workflow for research',
    compare: 'Why PaperFlow?',
    compareSub: 'vs. cloud-based alternatives',
    cta: 'Ready to own your research?',
    ctaSub: 'Free forever. No credit card. No cloud.',
    deep: 'Deep Research, in one click',
    deepSub: 'Ask a clinical question. Get a fully cited synthesis with bibliography.',
    deepCta: 'Try Deep Research',
    deepBullets: [
      'Searches PubMed live or your project library',
      'Synthesises evidence into IMRAD-style sections',
      'Builds the bibliography with linked PMIDs and DOIs',
      'Print-ready or one-click hand-off to Writing',
    ],
    voices: 'What researchers say',
  },
  es: {
    features: 'Un flujo guiado para investigar',
    compare: '¿Por qué PaperFlow?',
    compareSub: 'vs. alternativas en la nube',
    cta: '¿Listo para ser dueño de tu investigación?',
    ctaSub: 'Gratis para siempre. Sin tarjeta de crédito. Sin nube.',
    deep: 'Investigación Profunda en un clic',
    deepSub: 'Haz una pregunta clínica. Recibe una síntesis con citas y bibliografía.',
    deepCta: 'Probar Investigación Profunda',
    deepBullets: [
      'Busca en PubMed o en la biblioteca del proyecto',
      'Sintetiza evidencia en secciones tipo IMRAD',
      'Construye la bibliografía con enlaces a PMID y DOI',
      'Listo para imprimir o enviar directo a Writing',
    ],
    voices: 'Lo que dicen los investigadores',
  },
  pt: {
    features: 'Um fluxo guiado para pesquisar',
    compare: 'Por que PaperFlow?',
    compareSub: 'vs. alternativas na nuvem',
    cta: 'Pronto para ser dono da sua pesquisa?',
    ctaSub: 'Grátis para sempre. Sem cartão de crédito. Sem nuvem.',
    deep: 'Deep Research em um clique',
    deepSub: 'Faça uma pergunta clínica. Receba uma síntese citada com bibliografia.',
    deepCta: 'Testar Deep Research',
    deepBullets: [
      'Busca no PubMed ao vivo ou na biblioteca do projeto',
      'Sintetiza evidência em seções no estilo IMRAD',
      'Monta a bibliografia com links de PMID e DOI',
      'Pronto para imprimir ou enviar para Writing',
    ],
    voices: 'O que dizem os pesquisadores',
  },
};

const testimonials = {
  en: [
    {
      quote:
        '"Three weeks of literature review collapsed into an afternoon. I still review every citation, but the scaffolding is finally there from minute one."',
      author: 'Diego I.',
      role: 'Internal Medicine resident — power user',
    },
    {
      quote:
        '"Owning my data was non-negotiable for clinical projects. PaperFlow runs on my laptop and never phones home."',
      author: 'A. García',
      role: 'Clinical research lead',
    },
    {
      quote:
        '"The matrix + Writing handoff is what makes it different — every paragraph traces back to a row, every row to a paper."',
      author: 'M. Rivera',
      role: 'Methodologist, systematic reviews',
    },
  ],
  es: [
    {
      quote:
        '"Tres semanas de revisión bibliográfica colapsaron en una tarde. Sigo revisando cada cita, pero por fin parto de un esqueleto sólido."',
      author: 'Diego I.',
      role: 'Residente de Medicina Interna — power user',
    },
    {
      quote:
        '"Tener mis datos en mi propio equipo era innegociable para proyectos clínicos. PaperFlow corre en mi portátil y nunca sale a internet."',
      author: 'A. García',
      role: 'Líder de investigación clínica',
    },
    {
      quote:
        '"El puente Matrix → Writing es lo diferencial — cada párrafo regresa a una fila y cada fila a un paper."',
      author: 'M. Rivera',
      role: 'Metodólogo, revisiones sistemáticas',
    },
  ],
  pt: [
    {
      quote:
        '"Três semanas de revisão viraram uma tarde. Eu ainda checo cada citação, mas a estrutura inicial vem pronta."',
      author: 'Diego I.',
      role: 'Residente de Clínica Médica — power user',
    },
    {
      quote:
        '"Manter os dados na minha máquina era inegociável. PaperFlow roda no meu notebook e nunca conversa com a nuvem."',
      author: 'A. García',
      role: 'Líder de pesquisa clínica',
    },
    {
      quote:
        '"A ponte Matrix → Writing é o diferencial — cada parágrafo volta a uma linha, e cada linha a um paper."',
      author: 'M. Rivera',
      role: 'Metodólogo de revisões sistemáticas',
    },
  ],
};

const workflowSteps = {
  en: [
    { n: '01', title: 'Search', desc: 'Start with federated search and build a shortlist of relevant studies.' },
    { n: '02', title: 'Library', desc: 'Download, process and curate the papers you actually want to use.' },
    { n: '03', title: 'Extract + Write', desc: 'Turn full text into structured evidence and grounded manuscript sections.' },
    { n: '04', title: 'Analyze + Share', desc: 'Run reproducible analysis and export publication-ready artifacts or reports.' },
  ],
  es: [
    { n: '01', title: 'Search', desc: 'Empieza con búsqueda federada y arma una shortlist de estudios relevantes.' },
    { n: '02', title: 'Library', desc: 'Descarga, procesa y organiza los papers que realmente vas a usar.' },
    { n: '03', title: 'Extract + Write', desc: 'Convierte texto completo en evidencia estructurada y secciones redactadas.' },
    { n: '04', title: 'Analyze + Share', desc: 'Ejecuta análisis reproducibles y exporta artefactos publicables o reportes.' },
  ],
  pt: [
    { n: '01', title: 'Search', desc: 'Comece com busca federada e monte uma shortlist de estudos relevantes.' },
    { n: '02', title: 'Library', desc: 'Baixe, processe e organize os papers que você realmente vai usar.' },
    { n: '03', title: 'Extract + Write', desc: 'Transforme texto completo em evidência estruturada e seções redigidas.' },
    { n: '04', title: 'Analyze + Share', desc: 'Execute análises reproduzíveis e exporte artefatos publicáveis ou relatórios.' },
  ],
};

export default function LandingPage() {
  const { locale } = useI18n();
  const hero = heroText[locale];
  const titles = sectionTitles[locale];
  const comp = comparisons[locale];
  const steps = workflowSteps[locale];
  const heroFeatures = features.slice(0, 3);

  return (
    <div style={{ background: '#0a0a12', color: 'white', minHeight: '100vh', fontFamily: "'DM Sans', sans-serif", overflow: 'hidden' }}>
      {/* NAV */}
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '18px 32px', maxWidth: 1240, margin: '0 auto', position: 'relative', zIndex: 2,
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
      <section style={{ maxWidth: 1240, margin: '0 auto', padding: '54px 24px 56px', position: 'relative' }}>
        <div style={{ position: 'absolute', inset: '-10% auto auto 10%', width: 520, height: 520, background: 'radial-gradient(circle, rgba(99,102,241,0.18) 0%, transparent 70%)', pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', inset: '30% 0 auto auto', width: 460, height: 460, background: 'radial-gradient(circle, rgba(16,185,129,0.12) 0%, transparent 70%)', pointerEvents: 'none' }} />

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 28, alignItems: 'center', position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 16px',
              borderRadius: 999, border: '1px solid rgba(99,102,241,0.3)', background: 'rgba(99,102,241,0.08)',
              fontSize: 12, fontWeight: 600, color: 'rgba(165,160,255,0.9)', alignSelf: 'flex-start',
            }}>{hero.badge}</div>

            <div style={{ fontSize: 12, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.36)', fontWeight: 700 }}>
              Guided workflow for literature review, writing and evidence synthesis
            </div>

            <h1 style={{ fontSize: 'clamp(38px, 6vw, 74px)', fontWeight: 900, letterSpacing: '-0.05em', lineHeight: 0.98, margin: 0, maxWidth: 760 }}>
              {hero.h1_1}{' '}
              <span style={{ background: 'linear-gradient(135deg, #818cf8, #c084fc)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                {hero.h1_2}
              </span>
            </h1>

            <p style={{ fontSize: 17, color: 'rgba(255,255,255,0.58)', lineHeight: 1.75, maxWidth: 620, margin: 0 }}>
              {hero.sub}
            </p>

            <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
              <Link to="/signup" style={{
                padding: '14px 32px', borderRadius: 14, fontSize: 15, fontWeight: 700, textDecoration: 'none',
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: 'white',
                boxShadow: '0 14px 34px rgba(99,102,241,0.32)',
              }}>{hero.cta1} →</Link>
              <a href="https://idarragaa21-prog.github.io/paperflow-ai/" target="_blank" rel="noopener" style={{
                padding: '14px 32px', borderRadius: 14, fontSize: 15, fontWeight: 600, textDecoration: 'none',
                border: '1px solid rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.8)', background: 'rgba(255,255,255,0.03)',
              }}>{hero.cta2}</a>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10, maxWidth: 720 }}>
              {stats.slice(0, 3).map((s, i) => (
                <div key={i} style={{ padding: '14px 16px', borderRadius: 18, border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)' }}>
                  <div style={{ fontSize: 26, fontWeight: 900, letterSpacing: '-0.04em' }}>{s.value}</div>
                  <div style={{ marginTop: 4, fontSize: 11, lineHeight: 1.6, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'rgba(255,255,255,0.38)' }}>{s.label[locale]}</div>
                </div>
              ))}
            </div>

            <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.28)', margin: 0 }}>{hero.trusted}</p>
          </div>

          <div style={{
            padding: 18,
            borderRadius: 28,
            border: '1px solid rgba(255,255,255,0.08)',
            background: 'linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03))',
            boxShadow: '0 24px 60px rgba(0,0,0,0.28)',
            backdropFilter: 'blur(14px)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
              <div>
                <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.12em', color: 'rgba(129,140,248,0.86)', fontWeight: 700 }}>Workflow preview</div>
                <div style={{ fontSize: 20, fontWeight: 800, letterSpacing: '-0.03em', marginTop: 6 }}>Search → Library → Reader → Extract</div>
              </div>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 10px', borderRadius: 999, background: 'rgba(16,185,129,0.12)', color: '#6ee7b7', fontSize: 11, fontWeight: 700 }}>
                Live workspace
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {steps.map((step, index) => (
                <div key={step.n} style={{ display: 'grid', gridTemplateColumns: '50px 1fr auto', gap: 12, alignItems: 'center', padding: '12px 14px', borderRadius: 18, background: index === 1 ? 'rgba(99,102,241,0.12)' : 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                  <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.12em', color: 'rgba(255,255,255,0.34)' }}>{step.n}</div>
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 2 }}>{step.title}</div>
                    <div style={{ fontSize: 12, lineHeight: 1.55, color: 'rgba(255,255,255,0.5)' }}>{step.desc}</div>
                  </div>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: index === 1 ? '#818cf8' : 'rgba(255,255,255,0.18)' }} />
                </div>
              ))}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 10, marginTop: 16 }}>
              {heroFeatures.map((feature, index) => (
                <div key={index} style={{ padding: '12px 10px', borderRadius: 16, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                  <div style={{ color: feature.color, marginBottom: 10 }}>{feature.icon}</div>
                  <div style={{ fontSize: 12, fontWeight: 700, lineHeight: 1.45 }}>{feature.title[locale]}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* STATS */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '8px 24px 64px' }}>
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

      {/* DEEP RESEARCH SPOTLIGHT */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '40px 24px 60px', position: 'relative' }}>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 28,
          padding: 32, borderRadius: 26, position: 'relative', overflow: 'hidden',
          border: '1px solid rgba(99,102,241,0.25)',
          background: 'linear-gradient(135deg, rgba(99,102,241,0.10), rgba(236,72,153,0.06) 60%, rgba(16,185,129,0.06))',
        }}>
          <div style={{ position: 'absolute', inset: 'auto -10% -30% auto', width: 360, height: 360, background: 'radial-gradient(circle, rgba(139,92,246,0.18) 0%, transparent 70%)', pointerEvents: 'none' }} />
          <div>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '5px 12px', borderRadius: 999, background: 'rgba(139,92,246,0.18)', border: '1px solid rgba(139,92,246,0.35)', fontSize: 11, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#c4b5fd', marginBottom: 14 }}>
              ★ Deep Research
            </div>
            <h2 style={{ fontSize: 'clamp(24px, 4vw, 38px)', fontWeight: 900, letterSpacing: '-0.03em', margin: '0 0 12px' }}>
              {titles.deep}
            </h2>
            <p style={{ fontSize: 16, lineHeight: 1.7, color: 'rgba(255,255,255,0.65)', margin: '0 0 18px', maxWidth: 520 }}>
              {titles.deepSub}
            </p>
            <Link to="/deep-research" style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '12px 24px', borderRadius: 12, fontSize: 14, fontWeight: 700, textDecoration: 'none',
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: 'white',
              boxShadow: '0 12px 30px rgba(99,102,241,0.35)',
            }}>
              {titles.deepCta} →
            </Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, position: 'relative' }}>
            {titles.deepBullets.map((bullet, i) => (
              <div key={i} style={{
                display: 'grid', gridTemplateColumns: '28px 1fr', gap: 12, alignItems: 'flex-start',
                padding: '14px 16px', borderRadius: 14,
                background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)',
              }}>
                <div style={{
                  width: 24, height: 24, borderRadius: 8,
                  background: 'rgba(139,92,246,0.22)', color: '#c4b5fd',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontWeight: 800, fontSize: 12,
                }}>
                  {i + 1}
                </div>
                <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.78)', lineHeight: 1.55, fontWeight: 500 }}>
                  {bullet}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TESTIMONIALS */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '20px 24px 80px' }}>
        <h2 style={{ textAlign: 'center', fontSize: 'clamp(22px, 4vw, 32px)', fontWeight: 900, letterSpacing: '-0.03em', marginBottom: 30 }}>
          {titles.voices}
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 18 }}>
          {testimonials[locale].map((t, i) => (
            <figure key={i} style={{
              margin: 0, padding: 22, borderRadius: 18,
              background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
              display: 'flex', flexDirection: 'column', gap: 14, position: 'relative',
            }}>
              <div aria-hidden style={{ fontFamily: 'Georgia, serif', fontSize: 48, lineHeight: 0.6, color: 'rgba(129,140,248,0.45)', height: 16 }}>“</div>
              <blockquote style={{ margin: 0, fontSize: 14.5, lineHeight: 1.7, color: 'rgba(255,255,255,0.78)', fontStyle: 'italic' }}>
                {t.quote}
              </blockquote>
              <figcaption style={{ display: 'flex', flexDirection: 'column', gap: 2, marginTop: 'auto' }}>
                <span style={{ fontSize: 13, fontWeight: 800, color: 'rgba(255,255,255,0.92)' }}>{t.author}</span>
                <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>{t.role}</span>
              </figcaption>
            </figure>
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
