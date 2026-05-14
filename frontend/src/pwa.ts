export function registerServiceWorker() {
  // Desabilitar Service Worker no Tauri (desktop) — ele cacheia assets e impede atualizações
  if ((window as any).__TAURI_INTERNALS__) return;

  if (!("serviceWorker" in navigator)) return;

  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch(() => {
      // Registro PWA e melhoria progressiva; a aplicacao continua funcionando sem ele.
    });
  });
}
