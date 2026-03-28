export const PROJECT_CONTENT_CHANGED_EVENT = 'paperflow:project-content-changed';

export type ProjectContentChangedReason =
  | 'paper-downloaded'
  | 'batch-download'
  | 'manual-refresh';

export type ProjectContentChangedDetail = {
  projectId: string;
  reason: ProjectContentChangedReason;
};

export function emitProjectContentChanged(
  projectId: string,
  reason: ProjectContentChangedReason,
): void {
  window.dispatchEvent(
    new CustomEvent<ProjectContentChangedDetail>(PROJECT_CONTENT_CHANGED_EVENT, {
      detail: { projectId, reason },
    }),
  );
}
