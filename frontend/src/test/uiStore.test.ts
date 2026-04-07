import { beforeEach, describe, expect, it } from 'vitest';
import { useUiStore } from '../store/uiStore';

describe('uiStore', () => {
  beforeEach(() => {
    useUiStore.setState({
      notifications: [],
      isGlobalLoading: false,
      openModals: [],
    });
  });

  it('pushes a notification and assigns an id', () => {
    useUiStore.getState().pushNotification({ kind: 'error', title: 'Oops', message: 'Something went wrong' });
    const { notifications } = useUiStore.getState();
    expect(notifications).toHaveLength(1);
    expect(notifications[0].kind).toBe('error');
    expect(notifications[0].title).toBe('Oops');
    expect(notifications[0].id).toBeTruthy();
  });

  it('removes a notification by id', () => {
    useUiStore.getState().pushNotification({ kind: 'info', title: 'Hello' });
    const id = useUiStore.getState().notifications[0].id;
    useUiStore.getState().removeNotification(id);
    expect(useUiStore.getState().notifications).toHaveLength(0);
  });

  it('caps the notification queue at 10', () => {
    for (let i = 0; i < 15; i++) {
      useUiStore.getState().pushNotification({ kind: 'info', title: `Notif ${i}` });
    }
    expect(useUiStore.getState().notifications.length).toBeLessThanOrEqual(10);
  });

  it('sets and clears global loading', () => {
    useUiStore.getState().setGlobalLoading(true);
    expect(useUiStore.getState().isGlobalLoading).toBe(true);
    useUiStore.getState().setGlobalLoading(false);
    expect(useUiStore.getState().isGlobalLoading).toBe(false);
  });

  it('opens and closes modals', () => {
    useUiStore.getState().openModal('confirm-delete');
    expect(useUiStore.getState().isModalOpen('confirm-delete')).toBe(true);
    useUiStore.getState().closeModal('confirm-delete');
    expect(useUiStore.getState().isModalOpen('confirm-delete')).toBe(false);
  });

  it('does not duplicate open modals', () => {
    useUiStore.getState().openModal('my-modal');
    useUiStore.getState().openModal('my-modal');
    expect(useUiStore.getState().openModals).toHaveLength(1);
  });
});
