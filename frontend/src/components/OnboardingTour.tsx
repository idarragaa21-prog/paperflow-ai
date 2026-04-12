import { useCallback, useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import { useNavigate } from 'react-router-dom';
import { useI18n } from '../i18n';

const STORAGE_KEY = 'paperflow_onboarding_done';

type Step = {
  target: string; // CSS selector
  title: Record<string, string>;
  body: Record<string, string>;
  route?: string; // navigate here before showing
  placement?: 'bottom' | 'right' | 'top';
};

const steps: Step[] = [
  {
    target: '.rc-brand',
    title: { en: 'Welcome to PaperFlow AI!', es: '¡Bienvenido a PaperFlow AI!', pt: 'Bem-vindo ao PaperFlow AI!' },
    body: {
      en: 'Your private AI research workspace. Everything runs locally — your data never leaves your machine.',
      es: 'Tu espacio de investigación privado con IA. Todo corre localmente — tus datos nunca salen de tu máquina.',
      pt: 'Seu espaço de pesquisa privado com IA. Tudo roda localmente — seus dados nunca saem da sua máquina.',
    },
    placement: 'right',
  },
  {
    target: 'a[href="/projects"]',
    title: { en: 'Projects', es: 'Proyectos', pt: 'Projetos' },
    body: {
      en: 'Organize your research into projects. Each project has its own papers, notes, references, and meta-analysis.',
      es: 'Organiza tu investigación en proyectos. Cada proyecto tiene sus propios papers, notas, referencias y meta-análisis.',
      pt: 'Organize sua pesquisa em projetos. Cada projeto tem seus próprios papers, notas, referências e meta-análise.',
    },
    route: '/dashboard',
    placement: 'right',
  },
  {
    target: 'a[href="/agent-hub"]',
    title: { en: 'Agent Hub', es: 'Hub de Agentes', pt: 'Hub de Agentes' },
    body: {
      en: 'Launch Clinical Consults and Deep Research from one place while keeping project-first workflow intact.',
      es: 'Lanza Consultas Clínicas e Investigación Profunda desde un solo lugar sin romper el flujo project-first.',
      pt: 'Inicie Consultas Clínicas e Pesquisa Profunda de um único lugar mantendo o fluxo project-first.',
    },
    placement: 'right',
  },
  {
    target: 'a[href="/settings"]',
    title: { en: 'Settings & Language', es: 'Configuración e Idioma', pt: 'Configurações e Idioma' },
    body: {
      en: 'Change your password, check service health, and switch interface language (English, Español, Português).',
      es: 'Cambia tu contraseña, revisa el estado de los servicios y cambia el idioma de la interfaz.',
      pt: 'Altere sua senha, verifique a saúde dos serviços e mude o idioma da interface.',
    },
    placement: 'right',
  },
];

const btnText = {
  en: { next: 'Next', prev: 'Back', finish: 'Get Started!', skip: 'Skip tour', of: 'of' },
  es: { next: 'Siguiente', prev: 'Atrás', finish: '¡Comenzar!', skip: 'Saltar tour', of: 'de' },
  pt: { next: 'Próximo', prev: 'Voltar', finish: 'Começar!', skip: 'Pular tour', of: 'de' },
};

export function useOnboarding() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const done = localStorage.getItem(STORAGE_KEY);
    if (!done) setShow(true);
  }, []);

  const dismiss = useCallback(() => {
    setShow(false);
    localStorage.setItem(STORAGE_KEY, 'true');
  }, []);

  const restart = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setShow(true);
  }, []);

  return { showOnboarding: show, dismissOnboarding: dismiss, restartOnboarding: restart };
}

export default function OnboardingTour({ onDone }: { onDone: () => void }) {
  const { locale } = useI18n();
  const navigate = useNavigate();
  const [current, setCurrent] = useState(0);
  const [tooltipPos, setTooltipPos] = useState<{ top: number; left: number } | null>(null);
  const t = btnText[locale] || btnText.en;
  const step = steps[current];

  useEffect(() => {
    if (step.route) navigate(step.route);
  }, [current, step.route, navigate]);

  useEffect(() => {
    const timer = setTimeout(() => {
      const el = document.querySelector(step.target);
      if (el) {
        const rect = el.getBoundingClientRect();
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });

        const placement = step.placement || 'bottom';
        let top = rect.bottom + 12;
        let left = rect.left;
        if (placement === 'right') {
          top = rect.top;
          left = rect.right + 12;
        } else if (placement === 'top') {
          top = rect.top - 12;
          left = rect.left;
        }
        setTooltipPos({ top, left: Math.min(left, window.innerWidth - 360) });

        (el as HTMLElement).style.position = 'relative';
        (el as HTMLElement).style.zIndex = '10001';
        (el as HTMLElement).style.boxShadow = '0 0 0 4px rgba(99,102,241,0.4)';
        (el as HTMLElement).style.borderRadius = '10px';

        return () => {
          (el as HTMLElement).style.zIndex = '';
          (el as HTMLElement).style.boxShadow = '';
          (el as HTMLElement).style.borderRadius = '';
        };
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [current, step]);

  function next() {
    if (current < steps.length - 1) setCurrent(c => c + 1);
    else finish();
  }

  function prev() {
    if (current > 0) setCurrent(c => c - 1);
  }

  function finish() {
    // Cleanup highlights
    steps.forEach(s => {
      const el = document.querySelector(s.target) as HTMLElement | null;
      if (el) { el.style.zIndex = ''; el.style.boxShadow = ''; el.style.borderRadius = ''; }
    });
    onDone();
  }

  const overlayStyle: CSSProperties = {
    position: 'fixed', inset: 0, zIndex: 10000,
    background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(2px)',
  };

  const tooltipStyle: CSSProperties = {
    position: 'fixed',
    top: tooltipPos?.top ?? 200,
    left: tooltipPos?.left ?? 100,
    zIndex: 10002,
    width: 340, padding: 24,
    borderRadius: 16,
    background: 'var(--rc-surface)',
    boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
    color: 'var(--rc-text)',
  };

  return (
    <>
      <div style={overlayStyle} onClick={finish} />
      <div style={tooltipStyle} role="dialog" aria-modal="true" aria-label={step.title[locale] || step.title.en}>
        {/* Progress */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 14 }}>
          {steps.map((_, i) => (
            <div key={i} style={{
              flex: 1, height: 3, borderRadius: 2,
              background: i <= current ? 'var(--rc-primary)' : 'var(--rc-border)',
              transition: 'background 200ms',
            }} />
          ))}
        </div>

        <div style={{ fontSize: 11, color: 'var(--rc-muted)', marginBottom: 8 }}>
          {current + 1} {t.of} {steps.length}
        </div>

        <div style={{ fontFamily: 'var(--font-display, sans-serif)', fontWeight: 800, fontSize: 17, letterSpacing: '-0.02em', marginBottom: 8 }}>
          {step.title[locale] || step.title.en}
        </div>
        <div style={{ fontSize: 14, color: 'var(--rc-text-secondary)', lineHeight: 1.6, marginBottom: 20 }}>
          {step.body[locale] || step.body.en}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button onClick={finish} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            fontSize: 12, color: 'var(--rc-muted)', padding: 0,
          }}>{t.skip}</button>
          <div style={{ display: 'flex', gap: 8 }}>
            {current > 0 && (
              <button onClick={prev} style={{
                padding: '8px 16px', borderRadius: 10, fontSize: 13, fontWeight: 600,
                background: 'var(--rc-surface-3)', border: 'none', cursor: 'pointer', color: 'var(--rc-text)',
              }}>{t.prev}</button>
            )}
            <button onClick={next} style={{
              padding: '8px 20px', borderRadius: 10, fontSize: 13, fontWeight: 700,
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              border: 'none', cursor: 'pointer', color: 'white',
            }}>
              {current === steps.length - 1 ? t.finish : t.next}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
