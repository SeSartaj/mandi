import { useTranslation } from "react-i18next";
import { AppLoader as LoadingState } from "@/components/public/AppLoader";
import { lazy, Suspense } from "react";
const App = lazy(() => import("./App"));
export default function AppLoader() {
  const { t } = useTranslation();
  return (
    <Suspense fallback={<LoadingState label={t("Loading…")} className="min-h-dvh" />}>
      <App />
    </Suspense>
  );
}
