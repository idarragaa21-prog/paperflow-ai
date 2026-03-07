export type ToastKind = 'success' | 'error' | 'info';

export type ToastAction = {
  label: string;
  onClick: () => void;
};

export type Toast = {
  id: string;
  kind: ToastKind;
  title: string;
  message?: string;
  action?: ToastAction;
  createdAtMs: number;
};
