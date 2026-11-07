import Header from "@/components/dashboardLayout/Header";
import { AppSidebar } from "@/components/dashboardLayout/sidebar/app-sidebar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { Outlet } from "react-router";
import { useLocale } from "@/i18n/useTranslations";
import { isLTR } from "@/config/languages";

export default function DashboardLayout() {
  const locale = useLocale();
  return (
    <SidebarProvider dir={isLTR(locale) ? "ltr" : "rtl"}>
      <AppSidebar side={isLTR(locale) ? "left" : "right"} />
      <SidebarInset className="flex h-screen min-h-0 flex-col overflow-hidden">
        <Header />
        <div className="bg-background m-2 min-h-0 flex-1 overflow-auto rounded-md">
          <div className="mx-auto w-full max-w-400 p-5">
            <Outlet />
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
