"use client";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { ThemeToggle } from "@/components/ui/custom/ThemeToggle";
import LanguageSwitcher from "@/components/translation/LanguageSwitcher";

import WorkspaceHelp from "./WorkspaceHelp";
import CalendarFormatSelector from "@/components/ui/custom/CalendarFormatSelector";
import { GlobalBreadcrumb } from "@/components/ui/custom/GlobalBreadcrumb";
/* Project-independent header */

function Header() {
  return (
    <header className="bg-card flex h-16 shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-12">
      <div className="flex w-full min-w-0 items-center justify-between gap-2 px-3 sm:px-4">
        <div className="flex h-full min-w-0 items-center gap-2">
          <SidebarTrigger className="-ms-1" />
          <Separator
            orientation="vertical"
            className="me-2 hidden data-[orientation=vertical]:h-4 sm:block"
          />
          <div className="hidden min-w-0 md:block">
            <GlobalBreadcrumb />
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1 sm:gap-2">
          <WorkspaceHelp />
          <CalendarFormatSelector />
          <ThemeToggle />
          <LanguageSwitcher />
        </div>
      </div>
    </header>
  );
}

export default Header;
