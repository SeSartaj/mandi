import { Suspense, useEffect, useRef } from "react";
import { Outlet, useLocation } from "react-router";
import { useTranslation } from "react-i18next";
import Header from "@/components/dashboardLayout/Header";
import { AppSidebar } from "@/components/dashboardLayout/sidebar/app-sidebar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { PageBoundary } from "@/components/public/PageBoundary";
import { AppLoader } from "@/components/public/AppLoader";
import { useLocale } from "@/i18n/useTranslations";
import { isLTR } from "@/config/languages";

export default function DashboardLayout() {
  const locale = useLocale();
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const main = useRef<HTMLElement>(null);

  useEffect(() => {
    const section = pathname.split("/")[1];
    const titles: Record<string, string> = {
      establishments: "Establishments",
      checklists: "Checklists",
      submissions: "Submissions",
      employees: "Employees",
    };
    document.title = `${t(titles[section] ?? (section ? "Page not found." : "Overview"))} · Mandi`;
  }, [pathname, t]);

  useEffect(() => {
    main.current?.scrollTo({ top: 0 });
    main.current?.focus({ preventScroll: true });
  }, [pathname]);

  return (
    <SidebarProvider dir={isLTR(locale) ? "ltr" : "rtl"}>
      <a href="#main-content" className="skip-link">
        {t("Skip to content")}
      </a>
      <AppSidebar side={isLTR(locale) ? "left" : "right"} />
      <SidebarInset className="flex h-dvh min-h-0 min-w-0 flex-col overflow-hidden">
        <Header />
        <main
          id="main-content"
          ref={main}
          tabIndex={-1}
          className="bg-background m-2 min-h-0 flex-1 overflow-auto rounded-md focus:outline-none"
        >
          <div className="mx-auto w-full max-w-400 p-3 sm:p-5 lg:p-6">
            <PageBoundary key={pathname}>
              <Suspense fallback={<AppLoader label={t("Loading…")} className="py-16" />}>
                <Outlet />
              </Suspense>
            </PageBoundary>
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
