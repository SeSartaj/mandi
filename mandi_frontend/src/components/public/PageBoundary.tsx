import { Component, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { AppErrorState } from "@/components/public/AppErrorState";

class ErrorBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

/** Keep navigation available if a page fails to render or its chunk cannot load. */
export function PageBoundary({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  return (
    <ErrorBoundary
      fallback={
        <AppErrorState
          message={t("This page could not be loaded. Reload the page to try again.")}
          onRetry={() => window.location.reload()}
        />
      }
    >
      {children}
    </ErrorBoundary>
  );
}
