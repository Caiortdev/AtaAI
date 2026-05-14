import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import { registerServiceWorker } from "./pwa";
import "./styles.css";

const queryClient = new QueryClient();

// Unregister stale service workers before registering the current one
if ("serviceWorker" in navigator) {
  navigator.serviceWorker
    .getRegistrations()
    .then((registrations) => {
      for (const registration of registrations) {
        registration.unregister();
      }
    })
    .then(() => registerServiceWorker());
} else {
  registerServiceWorker();
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
