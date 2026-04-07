import { useEffect } from 'react';
import { useUiStore } from '../store/uiStore';
import { useToast } from '../ui/Toast/ToastProvider';

/**
 * Drains the uiStore notification queue into the ToastProvider.
 * Must be rendered inside <ToastProvider>.
 *
 * Axios interceptors push errors to uiStore (outside React), and this bridge
 * forwards them to the toast system (inside React context).
 */
export function GlobalErrorBridge() {
  const toast = useToast();
  const notifications = useUiStore((s) => s.notifications);
  const removeNotification = useUiStore((s) => s.removeNotification);

  useEffect(() => {
    if (notifications.length === 0) return;
    const [n, ...rest] = notifications;
    void rest; // consumed below
    toast.push({ kind: n.kind, title: n.title, message: n.message });
    removeNotification(n.id);
  }, [notifications, toast, removeNotification]);

  return null;
}
