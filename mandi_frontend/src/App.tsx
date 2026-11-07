import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Route, Routes } from "react-router";

import { Can, PermissionDenied } from "@/components/Can";
import DashboardLayout from "@/components/dashboardLayout/DashboardLayout";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import { Button } from "@/components/ui/button";
import ChecklistsPage from "@/features/checklists/ChecklistsPage";
import LoginPage from "@/features/auth/LoginPage";
import DashboardPage from "@/features/dashboard/DashboardPage";
import EmployeesPage from "@/features/employees/EmployeesPage";
import EstablishmentDetailPage from "@/features/establishments/EstablishmentDetailPage";
import EstablishmentsPage from "@/features/establishments/EstablishmentsPage";
import InspectionDetailPage from "@/features/inspections/InspectionDetailPage";
import InspectionsPage from "@/features/inspections/InspectionsPage";
import ReportsPage from "@/features/reports/ReportsPage";
import { isRTL } from "@/config/languages";
import "@/i18n";
import { api, errorMessage } from "@/lib/api";
import type { Session } from "@/lib/api";
import { SessionContext } from "@/lib/session";
import { useThemeStore } from "@/store/theme";

export default function App() {
  const { t, i18n } = useTranslation();
  const client = useQueryClient();
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

  const signout = async () => {
    try {
      await api.post("/auth/logout/");
    } finally {
      sessionStorage.removeItem("mandi-token");
      setToken(null);
      client.clear();
    }
  };

  if (!token) return <LoginPage onLogin={setToken} />;
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
              <Can permission="inspections.view_inspection" fallback={<PermissionDenied />}>
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
            path="/inspections"
            element={
              <Can permission="inspections.view_inspection" fallback={<PermissionDenied />}>
                <InspectionsPage />
              </Can>
            }
          />
          <Route
            path="/inspections/:id"
            element={
              <Can permission="inspections.view_inspection" fallback={<PermissionDenied />}>
                <InspectionDetailPage />
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
            path="/reports"
            element={
              <Can permission="inspections.view_inspection" fallback={<PermissionDenied />}>
                <ReportsPage />
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
              <div className="empty">
                {t("Page not found.")} <Link to="/">{t("Back")}</Link>
              </div>
            }
          />
        </Route>
      </Routes>
    </SessionContext.Provider>
  );
}
