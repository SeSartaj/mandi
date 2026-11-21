import { useQuery, useQueryClient } from "@tanstack/react-query";
import { lazy, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Route, Routes } from "react-router";

import { Can, PermissionDenied } from "@/components/Can";
import DashboardLayout from "@/components/dashboardLayout/DashboardLayout";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import { Button } from "@/components/ui/button";
import LoginPage from "@/features/auth/LoginPage";
import { isRTL } from "@/config/languages";
import "@/i18n";
import { api, errorMessage } from "@/lib/api";
import type { Session } from "@/lib/api";
import { SessionContext } from "@/lib/session";
import { useThemeStore } from "@/store/theme";

const ChecklistsPage = lazy(() => import("@/features/checklists/ChecklistsPage"));
const ChecklistDetailPage = lazy(() => import("@/features/checklists/ChecklistDetailPage"));
const SubmissionDetailPage = lazy(() => import("@/features/checklists/SubmissionDetailPage"));
const DashboardPage = lazy(() => import("@/features/dashboard/DashboardPage"));
const EmployeesPage = lazy(() => import("@/features/employees/EmployeesPage"));
const EstablishmentDetailPage = lazy(
  () => import("@/features/establishments/EstablishmentDetailPage"),
);
const SourceDetailPage = lazy(() => import("@/features/establishments/SourceDetailPage"));
const EstablishmentsPage = lazy(() => import("@/features/establishments/EstablishmentsPage"));
const SubmissionsPage = lazy(() => import("@/features/submissions/SubmissionsPage"));

export default function App() {
  const { t, i18n } = useTranslation();
  const client = useQueryClient();
  const [sessionExpired, setSessionExpired] = useState(false);
  const [token, setToken] = useState(sessionStorage.getItem("mandi-token"));
  const me = useQuery({
    queryKey: ["session", token],
    enabled: Boolean(token),
    queryFn: async () => (await api.get<Session>("/auth/me/")).data,
    retry: false,
  });

  useEffect(() => {
    document.documentElement.dir = isRTL(i18n.language) ? "rtl" : "ltr";
    document.documentElement.lang = i18n.language;
    localStorage.setItem("mandi-locale", i18n.language);
  }, [i18n.language]);

  useEffect(() => {
    useThemeStore.getState().applyTheme();
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => useThemeStore.getState().applyTheme();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    const expire = () => {
      setSessionExpired(true);
      setToken(null);
      client.clear();
    };
    window.addEventListener("mandi-session-expired", expire);
    return () => window.removeEventListener("mandi-session-expired", expire);
  }, [client]);

  const signout = async () => {
    try {
      await api.post("/auth/logout/");
    } catch {
      // Local sign-out must still complete when the server is unavailable.
    } finally {
      sessionStorage.removeItem("mandi-token");
      setToken(null);
      client.clear();
    }
  };

  if (!token)
    return (
      <LoginPage
        sessionExpired={sessionExpired}
        onLogin={(value) => {
          setSessionExpired(false);
          setToken(value);
        }}
      />
    );
  if (me.isPending) return <AppLoader label={t("Loading…")} className="py-16" />;
  if (me.error || !me.data) {
    return (
      <div className="login-page">
        <AppErrorState message={errorMessage(me.error)} onRetry={() => me.refetch()} />
        <Button onClick={signout}>{t("Sign out")}</Button>
      </div>
    );
  }

  return (
    <SessionContext.Provider value={{ ...me.data, signout }}>
      <Routes>
        <Route element={<DashboardLayout />}>
          <Route
            path="/"
            element={
              <Can permission="establishments.view_establishment" fallback={<PermissionDenied />}>
                <DashboardPage />
              </Can>
            }
          />
          <Route
            path="/establishments"
            element={
              <Can permission="establishments.view_establishment" fallback={<PermissionDenied />}>
                <EstablishmentsPage />
              </Can>
            }
          />
          <Route
            path="/establishments/:id"
            element={
              <Can permission="establishments.view_establishment" fallback={<PermissionDenied />}>
                <EstablishmentDetailPage />
              </Can>
            }
          />
          <Route
            path="/establishments/:id/sources/:source"
            element={
              <Can
                permissions={[
                  "establishments.view_establishment",
                  "establishments.view_sourcelink",
                ]}
                operator="and"
                fallback={<PermissionDenied />}
              >
                <SourceDetailPage />
              </Can>
            }
          />
          <Route
            path="/checklists"
            element={
              <Can permission="inspections.view_checklist" fallback={<PermissionDenied />}>
                <ChecklistsPage />
              </Can>
            }
          />
          <Route
            path="/checklists/:id"
            element={
              <Can permission="inspections.view_checklist" fallback={<PermissionDenied />}>
                <ChecklistDetailPage />
              </Can>
            }
          />
          <Route
            path="/submissions"
            element={
              <Can permission="establishments.view_establishment" fallback={<PermissionDenied />}>
                <SubmissionsPage />
              </Can>
            }
          />
          <Route
            path="/submissions/:id"
            element={
              <Can permission="establishments.view_establishment" fallback={<PermissionDenied />}>
                <SubmissionDetailPage />
              </Can>
            }
          />
          <Route
            path="/employees"
            element={
              <Can permission="accounts.view_user" fallback={<PermissionDenied />}>
                <EmployeesPage />
              </Can>
            }
          />
          <Route
            path="*"
            element={
              <div className="space-y-4 py-12 text-center">
                <h1 className="text-2xl font-semibold">{t("Page not found.")}</h1>
                <Button asChild variant="outline">
                  <Link to="/">{t("Overview")}</Link>
                </Button>
              </div>
            }
          />
        </Route>
      </Routes>
    </SessionContext.Provider>
  );
}
