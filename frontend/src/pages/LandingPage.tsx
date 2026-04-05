import { Link } from 'react-router-dom';
import { useI18n } from '../i18n';
import type { Locale } from '../i18n';
import './LandingPage.css';

type Localized = Record<Locale, string>;

type Highlight = {
  label: Localized;
  value: Localized;
};

type Feature = {
  kicker: Localized;
  title: Localized;
  body: Localized;
  points: Record<Locale, string[]>;
  example: Localized;
};

type Testimonial = {
  quote: Localized;
  name: string;
  role: Localized;
};

type Faq = {
  question: Localized;
  answer: Localized;
};

const content = {
  nav: {
    product: { en: 'Product', es: 'Producto', pt: 'Produto' },
    workflow: { en: 'Workflow', es: 'Flujo', pt: 'Fluxo' },
    faq: { en: 'FAQ', es: 'FAQ', pt: 'FAQ' },
    login: { en: 'Log in', es: 'Entrar', pt: 'Entrar' },
    cta: { en: 'Start free', es: 'Comenzar gratis', pt: 'Começar grátis' },
  },
  hero: {
    badge: {
      en: 'Local-first research workspace',
      es: 'Workspace de investigación local-first',
      pt: 'Workspace de pesquisa local-first',
    },
    titleLead: {
      en: 'Research with AI,',
      es: 'Investiga con IA,',
      pt: 'Pesquise com IA,',
    },
    titleAccent: {
      en: 'own every step',
      es: 'controla cada paso',
      pt: 'controle cada etapa',
    },
    body: {
      en: 'PaperFlow unifies search, reading, extraction, clinical synthesis and writing in one editorial-grade workspace that runs on your machine.',
      es: 'PaperFlow unifica búsqueda, lectura, extracción, síntesis clínica y redacción en un solo workspace editorial que corre en tu máquina.',
      pt: 'PaperFlow unifica busca, leitura, extração, síntese clínica e escrita em um workspace editorial que roda na sua máquina.',
    },
    ctaPrimary: {
      en: 'Create workspace',
      es: 'Crear workspace',
      pt: 'Criar workspace',
    },
    ctaSecondary: {
      en: 'Live demo',
      es: 'Demo en vivo',
      pt: 'Demo ao vivo',
    },
    trust: {
      en: 'Private by design · No cloud lock-in · Open source',
      es: 'Privado por diseño · Sin lock-in de nube · Open source',
      pt: 'Privado por design · Sem lock-in de nuvem · Open source',
    },
  },
  proofTitle: {
    en: 'Teams and residents building high-stakes evidence with PaperFlow',
    es: 'Equipos y residentes construyendo evidencia clínica con PaperFlow',
    pt: 'Times e residentes produzindo evidência clínica com PaperFlow',
  },
  workflowTitle: {
    en: 'One continuous workflow, not disconnected AI tools',
    es: 'Un flujo continuo, no herramientas IA desconectadas',
    pt: 'Um fluxo contínuo, não ferramentas IA desconectadas',
  },
  workflowBody: {
    en: 'From search query to exportable clinical brief, each stage is traceable and grounded in documents.',
    es: 'Desde la búsqueda hasta la ficha clínica exportable, cada etapa es trazable y fundamentada en documentos.',
    pt: 'Da busca ao brief clínico exportável, cada etapa é rastreável e fundamentada em documentos.',
  },
  testimonialsTitle: {
    en: 'Why clinicians keep coming back',
    es: 'Por qué los clínicos vuelven',
    pt: 'Por que clínicos continuam usando',
  },
  faqTitle: {
    en: 'Frequently asked questions',
    es: 'Preguntas frecuentes',
    pt: 'Perguntas frequentes',
  },
  ctaTitle: {
    en: 'Ready to make your research stack release-grade?',
    es: '¿Listo para llevar tu stack de investigación a nivel release?',
    pt: 'Pronto para elevar seu stack de pesquisa para nível release?',
  },
  ctaBody: {
    en: 'Open your workspace, run your pipeline, and keep every claim linked to evidence.',
    es: 'Abre tu workspace, ejecuta tu pipeline y mantén cada afirmación ligada a evidencia.',
    pt: 'Abra seu workspace, rode seu pipeline e mantenha cada afirmação vinculada à evidência.',
  },
  footer: {
    en: 'Built for evidence-first teams',
    es: 'Construido para equipos evidence-first',
    pt: 'Construído para times evidence-first',
  },
} as const;

const highlights: Highlight[] = [
  {
    label: { en: 'Indexed papers', es: 'Papers indexados', pt: 'Papers indexados' },
    value: { en: '200M+', es: '200M+', pt: '200M+' },
  },
  {
    label: { en: 'Endpoints in platform', es: 'Endpoints en plataforma', pt: 'Endpoints na plataforma' },
    value: { en: '105+', es: '105+', pt: '105+' },
  },
  {
    label: { en: 'Data exported to cloud', es: 'Datos exportados a nube', pt: 'Dados exportados para nuvem' },
    value: { en: '0', es: '0', pt: '0' },
  },
  {
    label: { en: 'Workspace model', es: 'Modelo de workspace', pt: 'Modelo de workspace' },
    value: { en: 'Local-first', es: 'Local-first', pt: 'Local-first' },
  },
];

const features: Feature[] = [
  {
    kicker: { en: '01. Discovery', es: '01. Descubrimiento', pt: '01. Descoberta' },
    title: { en: 'Search and shortlist evidence quickly', es: 'Busca y prioriza evidencia rápido', pt: 'Busque e priorize evidência rápido' },
    body: {
      en: 'Federated search across PubMed and partners with relevance signals, OA traceability and project-scoped save actions.',
      es: 'Búsqueda federada en PubMed y socios con señales de relevancia, trazabilidad OA y guardado por proyecto.',
      pt: 'Busca federada em PubMed e parceiros com sinais de relevância, rastreabilidade OA e salvamento por projeto.',
    },
    points: {
      en: ['Query refinement in-context', 'Batch download traceability', 'Project-aware deduplication'],
      es: ['Refinamiento de query en contexto', 'Trazabilidad de descarga por lotes', 'Deduplicación por proyecto'],
      pt: ['Refino de query no contexto', 'Rastreabilidade de download em lote', 'Deduplicação por projeto'],
    },
    example: { en: 'Search workspace', es: 'Workspace de búsqueda', pt: 'Workspace de busca' },
  },
  {
    kicker: { en: '02. Extraction', es: '02. Extracción', pt: '02. Extração' },
    title: { en: 'From full text to structured data', es: 'De texto completo a datos estructurados', pt: 'Do texto completo a dados estruturados' },
    body: {
      en: 'AI-assisted reading, notes and extraction surfaces keep your outputs grounded and auditable.',
      es: 'Las superficies de lectura, notas y extracción con IA mantienen salidas fundamentadas y auditables.',
      pt: 'Superfícies de leitura, notas e extração com IA mantêm saídas fundamentadas e auditáveis.',
    },
    points: {
      en: ['Reader with grounded chat', 'Structured study extraction', 'Reference sync by project'],
      es: ['Reader con chat grounded', 'Extracción estructurada de estudios', 'Sincronía de referencias por proyecto'],
      pt: ['Reader com chat grounded', 'Extração estruturada de estudos', 'Sincronia de referências por projeto'],
    },
    example: { en: 'Extraction board', es: 'Tablero de extracción', pt: 'Quadro de extração' },
  },
  {
    kicker: { en: '03. Synthesis', es: '03. Síntesis', pt: '03. Síntese' },
    title: { en: 'Produce clinical and writing outputs', es: 'Produce salidas clínicas y de redacción', pt: 'Produza saídas clínicas e de escrita' },
    body: {
      en: 'Generate evidence sheets, draft sections and analysis artifacts in one coherent path.',
      es: 'Genera fichas de evidencia, secciones de borrador y artefactos de análisis en una ruta coherente.',
      pt: 'Gere fichas de evidência, seções de rascunho e artefatos de análise em uma rota coerente.',
    },
    points: {
      en: ['Clinical multi-pass pipeline', 'Meta-analysis export path', 'Writer + citation utilities'],
      es: ['Pipeline clínico multi-pass', 'Ruta de export para meta-análisis', 'Writer + utilidades de citación'],
      pt: ['Pipeline clínico multi-pass', 'Rota de export para meta-análise', 'Writer + utilitários de citação'],
    },
    example: { en: 'Clinical + writing', es: 'Clínica + redacción', pt: 'Clínica + escrita' },
  },
];

const testimonials: Testimonial[] = [
  {
    quote: {
      en: 'The best part is confidence: every summary is linked back to source papers and project context.',
      es: 'La mejor parte es la confianza: cada resumen queda enlazado al paper fuente y al contexto del proyecto.',
      pt: 'A melhor parte é a confiança: cada resumo fica ligado ao paper fonte e ao contexto do projeto.',
    },
    name: 'Dr. Laura Fernández',
    role: {
      en: 'Orthopedic surgeon',
      es: 'Cirujana ortopédica',
      pt: 'Cirurgiã ortopédica',
    },
  },
  {
    quote: {
      en: 'What used to be three disconnected apps is now one flow our team can actually maintain.',
      es: 'Lo que antes eran tres apps desconectadas ahora es un flujo único que el equipo sí puede mantener.',
      pt: 'O que antes eram três apps desconectados agora é um fluxo único que a equipe consegue manter.',
    },
    name: 'Dr. Mateo Silva',
    role: {
      en: 'Clinical researcher',
      es: 'Investigador clínico',
      pt: 'Pesquisador clínico',
    },
  },
  {
    quote: {
      en: 'Having local-first defaults made institutional review and data governance much simpler.',
      es: 'Tener defaults local-first hizo más simple la revisión institucional y la gobernanza de datos.',
      pt: 'Ter defaults local-first simplificou a revisão institucional e a governança de dados.',
    },
    name: 'Dr. Ana Castillo',
    role: {
      en: 'Resident physician',
      es: 'Médica residente',
      pt: 'Médica residente',
    },
  },
];

const faqs: Faq[] = [
  {
    question: {
      en: 'Does PaperFlow require cloud APIs to work?',
      es: '¿PaperFlow requiere APIs cloud para funcionar?',
      pt: 'O PaperFlow precisa de APIs cloud para funcionar?',
    },
    answer: {
      en: 'No. The platform is local-first and can run with local models and local services. External APIs are optional.',
      es: 'No. La plataforma es local-first y puede correr con modelos y servicios locales. Las APIs externas son opcionales.',
      pt: 'Não. A plataforma é local-first e pode rodar com modelos e serviços locais. APIs externas são opcionais.',
    },
  },
  {
    question: {
      en: 'Can I keep workflow traceability for reviewers?',
      es: '¿Puedo mantener trazabilidad para revisores?',
      pt: 'Posso manter rastreabilidade para revisores?',
    },
    answer: {
      en: 'Yes. Search actions, references, extraction status and analysis outputs are linked per project.',
      es: 'Sí. Acciones de búsqueda, referencias, estado de extracción y salidas de análisis se enlazan por proyecto.',
      pt: 'Sim. Ações de busca, referências, status de extração e saídas de análise ficam ligadas por projeto.',
    },
  },
  {
    question: {
      en: 'Is this suitable only for medicine?',
      es: '¿Esto sirve solo para medicina?',
      pt: 'Isso serve só para medicina?',
    },
    answer: {
      en: 'The current product focuses on clinical and biomedical workflows, while keeping general research primitives reusable.',
      es: 'El producto actual se enfoca en flujos clínicos y biomédicos, manteniendo primitivas reutilizables para investigación general.',
      pt: 'O produto atual foca em fluxos clínicos e biomédicos, mantendo primitivas reutilizáveis para pesquisa geral.',
    },
  },
];

const brandLogos = ['ORTHO LAB', 'RESIDENCY HUB', 'EVIDENCE UNIT', 'MED REVIEW TEAM', 'RESEARCH CORE'];

function renderExample(locale: Locale, item: Feature) {
  return (
    <div className="landing-feature-preview" aria-label={item.example[locale]}>
      <div className="landing-feature-preview__header">
        <span>{item.example[locale]}</span>
        <span className="landing-feature-preview__dot" />
      </div>
      <div className="landing-feature-preview__line" />
      <div className="landing-feature-preview__line landing-feature-preview__line--short" />
      <div className="landing-feature-preview__chips">
        {item.points[locale].map((point) => (
          <span key={point}>{point}</span>
        ))}
      </div>
    </div>
  );
}

export default function LandingPage() {
  const { locale } = useI18n();

  return (
    <div className="landing">
      <header className="landing-topbar">
        <div className="landing-brand">
          <div className="landing-brand__logo">PF</div>
          <span>PaperFlow AI</span>
        </div>
        <nav className="landing-topbar__links">
          <a href="#workflow">{content.nav.workflow[locale]}</a>
          <a href="#faq">{content.nav.faq[locale]}</a>
          <a href="https://github.com/idarragaa21-prog/paperflow-ai" target="_blank" rel="noreferrer">GitHub</a>
        </nav>
        <div className="landing-topbar__actions">
          <Link to="/login" className="landing-btn landing-btn--ghost">{content.nav.login[locale]}</Link>
          <Link to="/signup" className="landing-btn landing-btn--primary">{content.nav.cta[locale]}</Link>
        </div>
      </header>

      <main>
        <section className="landing-hero" data-testid="landing-hero">
          <div className="landing-hero__copy">
            <div className="landing-pill">{content.hero.badge[locale]}</div>
            <h1>
              {content.hero.titleLead[locale]}{' '}
              <span>{content.hero.titleAccent[locale]}</span>
            </h1>
            <p>{content.hero.body[locale]}</p>
            <div className="landing-hero__actions">
              <Link to="/signup" className="landing-btn landing-btn--primary">{content.hero.ctaPrimary[locale]}</Link>
              <a
                href="https://idarragaa21-prog.github.io/paperflow-ai/"
                target="_blank"
                rel="noreferrer"
                className="landing-btn landing-btn--outline"
              >
                {content.hero.ctaSecondary[locale]}
              </a>
            </div>
            <div className="landing-hero__trust">{content.hero.trust[locale]}</div>
          </div>
          <div className="landing-preview" aria-label="PaperFlow workspace preview">
            <div className="landing-preview__header">
              <div className="landing-preview__dots">
                <span />
                <span />
                <span />
              </div>
              <div className="landing-preview__path">/projects/research/workspace</div>
            </div>
            <div className="landing-preview__body">
              <div className="landing-preview__panel">
                <h3>Research Queue</h3>
                <p>Rotator cuff augmentation outcomes in revision repairs</p>
                <p>Bioinductive implants comparative studies</p>
                <p>Meta-analysis extraction checklist</p>
              </div>
              <div className="landing-preview__panel">
                <h3>Grounded Writer</h3>
                <p>Claim drafted with citation markers linked to selected sources.</p>
                <div className="landing-preview__chip-row">
                  <span>[1]</span>
                  <span>[4]</span>
                  <span>[8]</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="landing-proof">
          <p>{content.proofTitle[locale]}</p>
          <div className="landing-proof__logos">
            {brandLogos.map((logo) => (
              <span key={logo}>{logo}</span>
            ))}
          </div>
        </section>

        <section className="landing-highlights">
          {highlights.map((item) => (
            <article key={item.label.en}>
              <strong>{item.value[locale]}</strong>
              <span>{item.label[locale]}</span>
            </article>
          ))}
        </section>

        <section id="workflow" className="landing-workflow">
          <div className="landing-section-head">
            <h2>{content.workflowTitle[locale]}</h2>
            <p>{content.workflowBody[locale]}</p>
          </div>
          <div className="landing-feature-list">
            {features.map((item, index) => (
              <article key={item.title.en} className={`landing-feature ${index % 2 === 1 ? 'landing-feature--reverse' : ''}`}>
                <div className="landing-feature__copy">
                  <span>{item.kicker[locale]}</span>
                  <h3>{item.title[locale]}</h3>
                  <p>{item.body[locale]}</p>
                  <ul>
                    {item.points[locale].map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ul>
                </div>
                {renderExample(locale, item)}
              </article>
            ))}
          </div>
        </section>

        <section className="landing-testimonials">
          <div className="landing-section-head">
            <h2>{content.testimonialsTitle[locale]}</h2>
          </div>
          <div className="landing-testimonials__grid">
            {testimonials.map((entry) => (
              <article key={entry.name} className="landing-testimonial">
                <p>"{entry.quote[locale]}"</p>
                <div>
                  <strong>{entry.name}</strong>
                  <span>{entry.role[locale]}</span>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section id="faq" className="landing-faq">
          <div className="landing-section-head">
            <h2>{content.faqTitle[locale]}</h2>
          </div>
          <div className="landing-faq__list">
            {faqs.map((item) => (
              <details key={item.question.en}>
                <summary>{item.question[locale]}</summary>
                <p>{item.answer[locale]}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="landing-final-cta">
          <h2>{content.ctaTitle[locale]}</h2>
          <p>{content.ctaBody[locale]}</p>
          <Link to="/signup" className="landing-btn landing-btn--primary">{content.hero.ctaPrimary[locale]}</Link>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="landing-brand">
          <div className="landing-brand__logo">PF</div>
          <span>PaperFlow AI</span>
        </div>
        <span>{content.footer[locale]}</span>
      </footer>
    </div>
  );
}
