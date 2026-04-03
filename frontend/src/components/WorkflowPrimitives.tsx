import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import type { ProjectCounts } from '../types/api';

export type WorkflowStageKey = 'research' | 'library' | 'reader' | 'extract' | 'write' | 'analysis';
type StageState = 'complete' | 'ready' | 'active' | 'pending';

type WorkflowStage = {
  key: WorkflowStageKey;
  label: string;
  shortLabel: string;
  description: string;
  to: string;
  state: StageState;
  metricLabel: string;
  metricValue: string;
};

type WorkflowCounts = Pick<ProjectCounts, 'papers' | 'notes' | 'references' | 'meta_studies_current' | 'presentations'>;

type PageHeroMetric = {
  label: string;
  value: string | number;
  tone?: 'primary' | 'success' | 'warning' | 'neutral';
};

type PageHeroProps = {
  eyebrow?: string;
  title: string;
  subtitle: string;
  metrics?: PageHeroMetric[];
  actions?: ReactNode;
  aside?: ReactNode;
};

type WorkflowRailProps = {
  projectId: string;
  counts?: Partial<WorkflowCounts> | null;
  current?: WorkflowStageKey;
};

type InsightCardProps = {
  eyebrow?: string;
  title: string;
  body: string;
  action?: ReactNode;
  tone?: 'primary' | 'success' | 'warning' | 'neutral';
};

const TONE_CLASS: Record<NonNullable<PageHeroMetric['tone']>, string> = {
  primary: 'rc-metric-card--primary',
  success: 'rc-metric-card--success',
  warning: 'rc-metric-card--warning',
  neutral: 'rc-metric-card--neutral',
};

function normalizeCounts(counts?: Partial<WorkflowCounts> | null): WorkflowCounts {
  return {
    papers: counts?.papers ?? 0,
    notes: counts?.notes ?? 0,
    references: counts?.references ?? 0,
    meta_studies_current: counts?.meta_studies_current ?? 0,
    presentations: counts?.presentations ?? 0,
  };
}

function stageState(key: WorkflowStageKey, counts: WorkflowCounts, current?: WorkflowStageKey): StageState {
  if (current === key) return 'active';

  if (key === 'research') return counts.papers > 0 ? 'complete' : 'ready';
  if (key === 'library') return counts.papers > 0 ? 'complete' : 'pending';
  if (key === 'reader') {
    if (counts.notes > 0) return 'complete';
    return counts.papers > 0 ? 'ready' : 'pending';
  }
  if (key === 'extract') {
    if (counts.meta_studies_current > 0) return 'complete';
    return counts.papers > 0 ? 'ready' : 'pending';
  }
  if (key === 'write') {
    if (counts.references > 0 || counts.notes > 0) return 'complete';
    return counts.meta_studies_current > 0 ? 'ready' : 'pending';
  }
  if (counts.presentations > 0) return 'complete';
  return counts.meta_studies_current > 0 ? 'ready' : 'pending';
}

export function getWorkflowStages(
  projectId: string,
  counts?: Partial<WorkflowCounts> | null,
  current?: WorkflowStageKey,
): WorkflowStage[] {
  const normalized = normalizeCounts(counts);
  return [
    {
      key: 'research',
      label: 'Research',
      shortLabel: 'Search',
      description: 'Find the right evidence and build your shortlist.',
      to: `/projects/${projectId}/research`,
      state: stageState('research', normalized, current),
      metricLabel: 'papers found',
      metricValue: normalized.papers > 0 ? String(normalized.papers) : 'Start',
    },
    {
      key: 'library',
      label: 'Library',
      shortLabel: 'Library',
      description: 'Ingest, deduplicate and process the papers you will use.',
      to: `/projects/${projectId}/library`,
      state: stageState('library', normalized, current),
      metricLabel: 'files ready',
      metricValue: normalized.papers ? String(normalized.papers) : '0',
    },
    {
      key: 'reader',
      label: 'Reader',
      shortLabel: 'Reader',
      description: 'Read with AI assistance and keep grounded notes.',
      to: `/projects/${projectId}/reader`,
      state: stageState('reader', normalized, current),
      metricLabel: 'notes saved',
      metricValue: normalized.notes ? String(normalized.notes) : 'Ask',
    },
    {
      key: 'extract',
      label: 'Extraction',
      shortLabel: 'Extract',
      description: 'Turn full text into structured studies and review tables.',
      to: `/projects/${projectId}/meta`,
      state: stageState('extract', normalized, current),
      metricLabel: 'studies extracted',
      metricValue: normalized.meta_studies_current ? String(normalized.meta_studies_current) : 'Review',
    },
    {
      key: 'write',
      label: 'Writing',
      shortLabel: 'Write',
      description: 'Draft grounded prose with evidence and citations attached.',
      to: `/projects/${projectId}/drafts`,
      state: stageState('write', normalized, current),
      metricLabel: 'writing assets',
      metricValue: normalized.references || normalized.notes ? String(normalized.references + normalized.notes) : 'Draft',
    },
    {
      key: 'analysis',
      label: 'Analysis',
      shortLabel: 'Analyze',
      description: 'Run reproducible analyses and export final outputs.',
      to: `/projects/${projectId}/analysis`,
      state: stageState('analysis', normalized, current),
      metricLabel: 'analysis ready',
      metricValue: normalized.meta_studies_current ? 'Run' : 'Later',
    },
  ];
}

export function getProjectNextAction(
  projectId: string,
  counts?: Partial<WorkflowCounts> | null,
): { label: string; description: string; to: string } {
  const normalized = normalizeCounts(counts);

  if (normalized.papers === 0) {
    return {
      label: 'Start with Research',
      description: 'Search PubMed and build the first evidence set for this project.',
      to: `/projects/${projectId}/research`,
    };
  }
  if (normalized.notes === 0) {
    return {
      label: 'Review in Reader',
      description: 'Ask focused questions and capture grounded notes before extraction.',
      to: `/projects/${projectId}/reader`,
    };
  }
  if (normalized.meta_studies_current === 0) {
    return {
      label: 'Run Extraction',
      description: 'Extract structured studies and effect-size data from the papers you selected.',
      to: `/projects/${projectId}/meta`,
    };
  }
  if (normalized.references === 0) {
    return {
      label: 'Draft the Manuscript',
      description: 'Use extracted evidence to start writing a grounded draft.',
      to: `/projects/${projectId}/drafts`,
    };
  }
  return {
    label: 'Launch Analysis',
    description: 'Create a dataset, validate it and run the final reproducible analysis.',
    to: `/projects/${projectId}/analysis`,
  };
}

export function getWorkflowCompletion(counts?: Partial<WorkflowCounts> | null) {
  const normalized = normalizeCounts(counts);
  const completed = [
    normalized.papers > 0,
    normalized.papers > 0,
    normalized.notes > 0,
    normalized.meta_studies_current > 0,
    normalized.references > 0 || normalized.notes > 0,
    normalized.meta_studies_current > 0,
  ].filter(Boolean).length;
  return Math.round((completed / 6) * 100);
}

function stateLabel(state: StageState) {
  if (state === 'complete') return 'Complete';
  if (state === 'ready') return 'Ready';
  if (state === 'active') return 'Current';
  return 'Locked';
}

export function PageHero({ eyebrow, title, subtitle, metrics = [], actions, aside }: PageHeroProps) {
  return (
    <section className="rc-page-hero">
      <div className="rc-page-hero__main">
        {eyebrow ? <div className="rc-page-hero__eyebrow">{eyebrow}</div> : null}
        <h1 className="rc-page-hero__title">{title}</h1>
        <p className="rc-page-hero__subtitle">{subtitle}</p>
        {actions ? <div className="rc-page-hero__actions">{actions}</div> : null}
      </div>
      <div className="rc-page-hero__side">
        {metrics.length > 0 ? (
          <div className="rc-metric-grid">
            {metrics.map((metric) => (
              <div key={metric.label} className={`rc-metric-card ${TONE_CLASS[metric.tone || 'neutral']}`}>
                <div className="rc-metric-card__value">{metric.value}</div>
                <div className="rc-metric-card__label">{metric.label}</div>
              </div>
            ))}
          </div>
        ) : null}
        {aside}
      </div>
    </section>
  );
}

export function ProjectWorkflowRail({ projectId, counts, current }: WorkflowRailProps) {
  const stages = getWorkflowStages(projectId, counts, current);
  return (
    <section className="rc-stage-rail" data-testid="workflow-rail">
      {stages.map((stage) => (
        <Link
          key={stage.key}
          to={stage.to}
          className={`rc-stage-card rc-stage-card--${stage.state}`}
        >
          <div className="rc-stage-card__top">
            <span className="rc-stage-card__name">{stage.shortLabel}</span>
            <span className={`rc-stage-card__status rc-stage-card__status--${stage.state}`}>
              {stateLabel(stage.state)}
            </span>
          </div>
          <div className="rc-stage-card__title">{stage.label}</div>
          <div className="rc-stage-card__body">{stage.description}</div>
          <div className="rc-stage-card__metric">
            <strong>{stage.metricValue}</strong>
            <span>{stage.metricLabel}</span>
          </div>
        </Link>
      ))}
    </section>
  );
}

export function InsightCard({ eyebrow, title, body, action, tone = 'neutral' }: InsightCardProps) {
  return (
    <div className={`rc-insight-card rc-insight-card--${tone}`}>
      {eyebrow ? <div className="rc-insight-card__eyebrow">{eyebrow}</div> : null}
      <div className="rc-insight-card__title">{title}</div>
      <div className="rc-insight-card__body">{body}</div>
      {action ? <div className="rc-insight-card__action">{action}</div> : null}
    </div>
  );
}
