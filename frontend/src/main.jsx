import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import App from "./App.jsx";
import { queryClient } from "./queryClient.js";
import "./index.css";

// Browser error reporting. Loaded only when VITE_SENTRY_DSN was set at build time.
if (import.meta.env.VITE_SENTRY_DSN) {
  import("@sentry/react").then((Sentry) => Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN, environment: import.meta.env.MODE, sendDefaultPii: false,
  }));
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <App />
      </HashRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
