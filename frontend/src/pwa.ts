export function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;

  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch(() => {
      // Registro PWA e melhoria progressiva; a aplicacao continua funcionando sem ele.
    });
  });
}
