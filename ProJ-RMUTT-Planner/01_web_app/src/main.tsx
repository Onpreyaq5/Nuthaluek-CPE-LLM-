import { copy as uiCopy } from "@/i18n/th";
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import { StateProvider } from "./state";
import "./index.css";

async function bootstrap() {
  if (import.meta.env.VITE_USE_MOCKS !== "false") {
    const { worker } = await import("./mocks/browser");
    await worker.start({
      quiet: true,
      onUnhandledRequest(request, print) {
        if (new URL(request.url).pathname.startsWith("/api/v1")) print.error();
      },
    });
  } else {
    const registrations = await navigator.serviceWorker?.getRegistrations();
    let removed = false;
    for (const r of registrations || [])
      if (r.active?.scriptURL.endsWith("/mockServiceWorker.js")) {
        await r.unregister();
        removed = true;
      }
    if (
      removed &&
      navigator.serviceWorker.controller?.scriptURL.endsWith(
        "/mockServiceWorker.js",
      )
    ) {
      window.location.reload();
      return;
    }
  }
  const cache = new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false, staleTime: 20000 },
      mutations: { retry: false },
    },
  });
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <QueryClientProvider client={cache}>
        <BrowserRouter>
          <StateProvider>
            <App />
          </StateProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </React.StrictMode>,
  );
}
bootstrap().catch((error) => {
  console.error(error);
  const root = document.getElementById("root");
  if (root) root.textContent = uiCopy.main001;
});
