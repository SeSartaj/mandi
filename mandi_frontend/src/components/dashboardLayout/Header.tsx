"use client";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { ThemeToggle } from "@/components/ui/custom/ThemeToggle";
import LanguageSwitcher from "@/components/translation/LanguageSwitcher";

import CalendarFormatSelector from "@/components/ui/custom/CalendarFormatSelector";
import { GlobalBreadcrumb } from "@/components/ui/custom/GlobalBreadcrumb";
/* Project-independent header */

function Header() {
  return (
    <header className="bg-card flex h-16 shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-12">
      <div className="flex w-full items-center justify-between gap-2 px-4">
        <div className="flex h-full items-center gap-2">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-2 data-[orientation=vertical]:h-4" />
          <GlobalBreadcrumb />
        </div>
        <div className="flex items-center gap-2">
          <CalendarFormatSelector />
          <ThemeToggle />
          <LanguageSwitcher />
        </div>
      </div>
    </header>
  );
}

export default Header;
