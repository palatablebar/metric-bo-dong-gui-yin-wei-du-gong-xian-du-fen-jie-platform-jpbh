/** UI store：toast 队列 + 当前选中指标（跨页保持口径一致）。 */
import { useSyncExternalStore } from 'react';

export interface Toast {
  id: number;
  text: string;
  bad?: boolean;
}

interface UiState {
  toasts: Toast[];
  metric: string;
}

type Listener = () => void;

class UiStore {
  private state: UiState = { toasts: [], metric: 'gmv' };
  private listeners = new Set<Listener>();
  private seq = 0;

  subscribe = (listener: Listener) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  getState = (): UiState => this.state;

  private emit(next: Partial<UiState>) {
    this.state = { ...this.state, ...next };
    this.listeners.forEach((listener) => listener());
  }

  toast(text: string, bad = false) {
    const id = ++this.seq;
    this.emit({ toasts: [...this.state.toasts, { id, text, bad }] });
    window.setTimeout(() => this.dismiss(id), 3600);
  }

  dismiss(id: number) {
    this.emit({ toasts: this.state.toasts.filter((item) => item.id !== id) });
  }

  setMetric(metric: string) {
    this.emit({ metric });
  }
}

export const uiStore = new UiStore();

export function useUi() {
  return useSyncExternalStore(uiStore.subscribe, uiStore.getState);
}
