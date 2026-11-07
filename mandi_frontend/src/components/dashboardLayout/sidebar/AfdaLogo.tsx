// Copied AFDA CMS sidebar identity; Mandi has no active-position switcher.
import { SidebarMenu, SidebarMenuButton, SidebarMenuItem } from "@/components/ui/sidebar";
import { Link } from "react-router";
import { useTranslation } from "react-i18next";
export function AfdaLogo() {
  const { t } = useTranslation();
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton size="lg" asChild>
          <Link to="/">
            <img src="/afda_logo.png" alt="AFDA" className="size-8 rounded-md object-contain" />
            <div className="grid min-w-0 flex-1 text-start text-sm leading-tight">
              <span className="truncate font-medium">Mandi</span>
              <span className="text-muted-foreground truncate text-xs">
                {t("Monitoring & inspection")}
              </span>
            </div>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
