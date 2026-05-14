/// <reference types="vite/client" />

interface Window {
  __TAURI_INTERNALS__?: {
    invoke<T = unknown>(command: string, args?: Record<string, unknown>): Promise<T>;
  };
}
