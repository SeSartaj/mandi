import "@/i18n";
import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router";
import App from "./AppLoader";
import { PageBoundary } from "@/components/public/PageBoundary";
import { Toaster } from "@/components/ui/sonner";
import "./style.css";
const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, staleTime: 15000 } },
});
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <PageBoundary>
          <App />
        </PageBoundary>
        <Toaster closeButton visibleToasts={4} duration={4500} />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
