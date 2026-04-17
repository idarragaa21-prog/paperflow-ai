import { Link } from 'react-router-dom';
import { useI18n } from '../i18n';

function Icon({ children }: { children: React.ReactNode }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      {children}
    </svg>
  );
}

const FEATURES = [
  {
    title: { es: 'Búsqueda con IA', en: 'AI Search', pt: 'Busca com IA' },
    desc: {
      es: 'Pregunta en lenguaje natural y recibe resultados de PubMed con síntesis citada.',
      en: 'Ask in natural language and get PubMed results with a cited synthesis.',
      pt: 'Pergunte em linguagem natural e receba resultados do PubMed com síntese citada.',
    },
    to: '/projects',
    icon: <Icon><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></Icon>,
  },
  {
    title: { es: 'Revisión de literatura', en: 'Literature Review', pt: 'Revisão da literatura' },
    desc: {
      es: 'Extrae datos, compara estudios y construye una matriz versionada en minutos.',
      en: 'Extract data, compare studies, and build a versioned matrix in minutes.',
      pt: 'Extraia dados, compare estudos e construa uma matriz versionada em minutos.',
    },
    to: '/projects',
    icon: <Icon><rect x="3" y="4" width="7" height="7" rx="1" /><rect x="14" y="4" width="7" height="7" rx="1" /><rect x="3" y="13" width="7" height="7" rx="1" /><rect x="14" y="13" width="7" height="7" rx="1" /></Icon>,
  },
  {
    title: { es: 'AI Writer', en: 'AI Writer', pt: 'AI Writer' },
    desc: {
      es: 'Redacta artículos clínicos, revisiones o cartas al editor con citas trazadas.',
      en: 'Draft clinical papers, reviews or letters to the editor with traceable citations.',
      pt: 'Redija artigos clínicos, revisões ou cartas ao editor com citações rastreáveis.',
    },
    to: '/projects',
    icon: <Icon><path d="M4 20h16" /><path d="M14 4l6 6L10 20H4v-6z" /></Icon>,
  },
  {
    title: { es: 'Gestor de referencias', en: 'Reference Manager', pt: 'Gestor de referências' },
    desc: {
      es: 'Importa desde DOI, BibTeX o RIS y exporta APA, Vancouver o AMA.',
      en: 'Import from DOI, BibTeX or RIS and export APA, Vancouver or AMA.',
      pt: 'Importe via DOI, BibTeX ou RIS e exporte em APA, Vancouver ou AMA.',
    },
    to: '/projects',
    icon: <Icon><path d="M4 5a2 2 0 0 1 2-2h10l4 4v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z" /><polyline points="14 3 14 8 19 8" /></Icon>,
  },
  {
    title: { es: 'Deep Research', en: 'Deep Research', pt: 'Deep Research' },
    desc: {
      es: 'Reportes profundos sobre tu pregunta clínica, con tendencias y brechas.',
      en: 'Deep reports on your clinical question, with trends and gaps.',
      pt: 'Relatórios profundos sobre sua pergunta clínica, com tendências e lacunas.',
    },
    to: '/deep-research',
    icon: <Icon><path d="M12 3v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6L5.6 18.4" /></Icon>,
  },
  {
    title: { es: 'Meta-análisis', en: 'Meta-analysis', pt: 'Meta-análise' },
    desc: {
      es: 'Corre efectos aleatorios, heterogeneidad y forest plots con R plumber.',
      en: 'Run random effects, heterogeneity and forest plots with R plumber.',
      pt: 'Execute efeitos aleatórios, heterogeneidade e forest plots com R plumber.',
    },
    to: '/projects',
    icon: <Icon><path d="M3 20V8M9 20V4M15 20v-6M21 20v-10" /></Icon>,
  },
];

const HIGHLIGHTS = [
  {
    title: { es: 'Todo corre en tu máquina', en: 'Everything runs on your machine', pt: 'Tudo roda na sua máquina' },
    desc: {
      es: 'Ollama + Postgres + Qdrant + MinIO + R. Ningún dato sale a la nube a menos que tú lo decidas.',
      en: 'Ollama + Postgres + Qdrant + MinIO + R. No data leaves your machine unless you decide so.',
      pt: 'Ollama + Postgres + Qdrant + MinIO + R. Nenhum dado sai da sua máquina a menos que você decida.',
    },
  },
  {
    title: { es: 'Citas siempre trazadas', en: 'Citations always traceable', pt: 'Citações sempre rastreáveis' },
    desc: {
      es: '[M1] apunta a tu matriz, [R2] a un meta-run, [C3] a una referencia. Puedes auditar cualquier afirmación.',
      en: '[M1] points to your matrix, [R2] to a meta-run, [C3] to a reference. You can audit any claim.',
      pt: '[M1] aponta para sua matriz, [R2] a um meta-run, [C3] a uma referência. Você pode auditar qualquer afirmação.',
    },
  },
  {
    title: { es: 'Exportas como siempre', en: 'Exports you already know', pt: 'Exporta como sempre' },
    desc: {
      es: 'DOCX, PDF y Markdown con bibliografía en APA, Vancouver o AMA listos para enviar.',
      en: 'DOCX, PDF and Markdown with bibliography in APA, Vancouver or AMA ready to send.',
      pt: 'DOCX, PDF e Markdown com bibliografia em APA, Vancouver ou AMA prontos para enviar.',
    },
  },
];

export default function LandingPage() {
  const { locale } = useI18n();
  const L = (o: Record<string, string>) => o[locale] || o.es;

  return (
    <div className="pg-shell">
      <header className="pg-topbar">
        <div className="pg-topbar-inner">
          <Link to="/" className="pg-brand">
            <span className="pg-brand-mark">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
            </span>
            PaperFlow
          </Link>
          <nav className="pg-nav">
            <a href="#features">{L({ es: 'Funciones', en: 'Features', pt: 'Funções' })}</a>
            <a href="#workflow">{L({ es: 'Flujo', en: 'Workflow', pt: 'Fluxo' })}</a>
            <a href="#local">{L({ es: 'Local-first', en: 'Local-first', pt: 'Local-first' })}</a>
          </nav>
          <div className="pg-nav-spacer" />
          <div className="pg-topbar-right">
            <Link to="/login" className="pg-btn pg-btn--ghost">
              {L({ es: 'Iniciar sesión', en: 'Sign in', pt: 'Entrar' })}
            </Link>
            <Link to="/signup" className="pg-btn pg-btn--primary">
              {L({ es: 'Comenzar', en: 'Get started', pt: 'Começar' })}
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="pg-container pg-hero pg-fade-in">
          <span className="pg-hero-eyebrow">
            <svg width="10" height="10" viewBox="0 0 20 20" fill="currentColor"><circle cx="10" cy="10" r="5" /></svg>
            {L({ es: '100 % local · sin nube', en: '100% local · no cloud', pt: '100 % local · sem nuvem' })}
          </span>
          <h1 className="pg-display">
            {L({
              es: 'Tu asistente de investigación, en tu propia máquina',
              en: 'Your research assistant, on your own machine',
              pt: 'Seu assistente de pesquisa, na sua máquina',
            })}
          </h1>
          <p className="pg-lead" style={{ margin: '16px auto 0' }}>
            {L({
              es: 'Busca, lee, extrae, meta-analiza y escribe con IA local (Ollama) o Claude en la nube. Todo trazado, citado y exportable.',
              en: 'Search, read, extract, meta-analyze and write with local AI (Ollama) or Claude in the cloud. Traceable, cited, exportable.',
              pt: 'Pesquise, leia, extraia, meta-analise e escreva com IA local (Ollama) ou Claude na nuvem. Rastreável, citado, exportável.',
            })}
          </p>
          <div className="pg-hero-cta">
            <Link to="/signup" className="pg-btn pg-btn--primary pg-btn--lg">
              {L({ es: 'Empezar gratis', en: 'Start free', pt: 'Começar grátis' })}
            </Link>
            <Link to="/login" className="pg-btn pg-btn--lg">
              {L({ es: 'Ya tengo cuenta', en: 'I already have an account', pt: 'Já tenho conta' })}
            </Link>
          </div>
          <div className="pg-hero-trust">
            {L({
              es: 'Ollama · Postgres · Qdrant · MinIO · R plumber · Grobid',
              en: 'Ollama · Postgres · Qdrant · MinIO · R plumber · Grobid',
              pt: 'Ollama · Postgres · Qdrant · MinIO · R plumber · Grobid',
            })}
          </div>
        </section>

        <section id="features" className="pg-container pg-section">
          <div className="pg-section-header">
            <div>
              <div className="pg-kicker">{L({ es: 'Todo en uno', en: 'All in one', pt: 'Tudo em um' })}</div>
              <h2 className="pg-h1" style={{ marginTop: 6 }}>
                {L({ es: 'Las seis herramientas que usas a diario', en: 'The six tools you use every day', pt: 'As seis ferramentas que você usa todo dia' })}
              </h2>
            </div>
            <p className="pg-muted" style={{ maxWidth: 420 }}>
              {L({
                es: 'De la pregunta clínica al DOCX final, sin cambiar de herramienta.',
                en: 'From clinical question to the final DOCX, without switching tools.',
                pt: 'Da pergunta clínica ao DOCX final, sem trocar de ferramenta.',
              })}
            </p>
          </div>

          <div className="pg-features">
            {FEATURES.map((f) => (
              <Link key={L(f.title)} to={f.to} className="pg-feature">
                <span className="pg-feature-icon">{f.icon}</span>
                <h3 className="pg-feature-title">{L(f.title)}</h3>
                <p className="pg-feature-desc">{L(f.desc)}</p>
                <span className="pg-feature-cta">
                  {L({ es: 'Explorar', en: 'Explore', pt: 'Explorar' })} →
                </span>
              </Link>
            ))}
          </div>
        </section>

        <section id="workflow" className="pg-container pg-section">
          <div className="pg-section-header">
            <div>
              <div className="pg-kicker">{L({ es: 'Un flujo, cinco pasos', en: 'One flow, five steps', pt: 'Um fluxo, cinco passos' })}</div>
              <h2 className="pg-h1" style={{ marginTop: 6 }}>
                {L({ es: 'De la búsqueda al artículo enviado', en: 'From search to submitted paper', pt: 'Da busca ao artigo enviado' })}
              </h2>
            </div>
          </div>
          <div className="pg-grid-2">
            {[
              { n: '1', t: L({ es: 'Crea un proyecto', en: 'Create a project', pt: 'Crie um projeto' }), d: L({ es: 'Una pregunta clínica por proyecto. Todo se agrupa por ahí.', en: 'One clinical question per project. Everything lives there.', pt: 'Uma pergunta clínica por projeto. Tudo fica agrupado ali.' }) },
              { n: '2', t: L({ es: 'Busca y añade a la biblioteca', en: 'Search and add to the library', pt: 'Pesquise e adicione à biblioteca' }), d: L({ es: 'AI Search te da síntesis citada. Añades lo relevante con un clic.', en: 'AI Search gives you cited synthesis. Add the relevant papers in one click.', pt: 'AI Search oferece síntese citada. Adicione o relevante em um clique.' }) },
              { n: '3', t: L({ es: 'Extrae y construye la matriz', en: 'Extract and build the matrix', pt: 'Extraia e construa a matriz' }), d: L({ es: 'El worker extrae campos estructurados. Tú revisas. La matriz queda versionada.', en: 'The worker extracts structured fields. You review. The matrix is versioned.', pt: 'O worker extrai campos estruturados. Você revisa. A matriz fica versionada.' }) },
              { n: '4', t: L({ es: 'Meta-analiza (opcional)', en: 'Meta-analyze (optional)', pt: 'Meta-analise (opcional)' }), d: L({ es: 'Efectos aleatorios, heterogeneidad y forest/funnel plot con R.', en: 'Random effects, heterogeneity and forest/funnel plots with R.', pt: 'Efeitos aleatórios, heterogeneidade e forest/funnel plot com R.' }) },
              { n: '5', t: L({ es: 'Escribe y exporta', en: 'Write and export', pt: 'Escreva e exporte' }), d: L({ es: 'Writing Assistant redacta con citas trazadas. Exporta DOCX, PDF o MD.', en: 'Writing Assistant drafts with traceable citations. Export DOCX, PDF or MD.', pt: 'Writing Assistant redige com citações rastreáveis. Exporte DOCX, PDF ou MD.' }) },
            ].map((s) => (
              <div key={s.n} className="pg-card pg-card--soft">
                <div className="pg-row" style={{ marginBottom: 8 }}>
                  <span className="pg-badge pg-badge--info">Paso {s.n}</span>
                </div>
                <h3 className="pg-h3" style={{ marginBottom: 4 }}>{s.t}</h3>
                <p className="pg-muted" style={{ margin: 0, fontSize: 14 }}>{s.d}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="local" className="pg-container pg-section">
          <div className="pg-section-header">
            <div>
              <div className="pg-kicker">{L({ es: 'Privacidad', en: 'Privacy', pt: 'Privacidade' })}</div>
              <h2 className="pg-h1" style={{ marginTop: 6 }}>
                {L({ es: 'Nada se sube a la nube por defecto', en: 'Nothing goes to the cloud by default', pt: 'Nada sobe para a nuvem por padrão' })}
              </h2>
            </div>
          </div>
          <div className="pg-grid-3">
            {HIGHLIGHTS.map((h) => (
              <div key={L(h.title)} className="pg-card">
                <h3 className="pg-h3" style={{ marginBottom: 6 }}>{L(h.title)}</h3>
                <p className="pg-muted" style={{ margin: 0, fontSize: 14 }}>{L(h.desc)}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="pg-container pg-section">
          <div className="pg-card" style={{ textAlign: 'center', padding: 40 }}>
            <h2 className="pg-h1">
              {L({ es: '¿Listo para empezar?', en: 'Ready to start?', pt: 'Pronto para começar?' })}
            </h2>
            <p className="pg-lead" style={{ margin: '10px auto 20px' }}>
              {L({
                es: 'Crea tu cuenta local en 10 segundos y arranca tu primer proyecto.',
                en: 'Create your local account in 10 seconds and start your first project.',
                pt: 'Crie sua conta local em 10 segundos e comece seu primeiro projeto.',
              })}
            </p>
            <Link to="/signup" className="pg-btn pg-btn--primary pg-btn--lg">
              {L({ es: 'Crear cuenta', en: 'Create account', pt: 'Criar conta' })}
            </Link>
          </div>
        </section>
      </main>

      <footer style={{ borderTop: '1px solid var(--pg-line)', padding: '32px 24px', color: 'var(--pg-soft)', fontSize: 13 }}>
        <div className="pg-container pg-row-between">
          <div>© {new Date().getFullYear()} PaperFlow · local-first research</div>
          <div className="pg-row" style={{ gap: 18 }}>
            <Link to="/login" style={{ color: 'inherit' }}>{L({ es: 'Iniciar sesión', en: 'Sign in', pt: 'Entrar' })}</Link>
            <a href="https://github.com/idarragaa21-prog/paperflow-ai" target="_blank" rel="noreferrer" style={{ color: 'inherit' }}>GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
