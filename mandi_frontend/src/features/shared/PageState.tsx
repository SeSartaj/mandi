import { useTranslation } from "react-i18next";

import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import { errorMessage } from "@/lib/api";

export function PageLoader({ label }: { label?: string }) {
  const { t } = useTranslation();
  return <AppLoader label={label ?? t("Loading…")} className="py-10" />;
}

export function PageError({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return <AppErrorState message={errorMessage(error)} onRetry={onRetry} className="my-4" />;
}
