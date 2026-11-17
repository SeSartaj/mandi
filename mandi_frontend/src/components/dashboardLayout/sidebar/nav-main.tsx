import { useRegistryCatalog } from "@/features/establishments/registry";
// Copied AFDA CMS navigation; bound to Mandi routes and permissions.
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  useSidebar,
} from "@/components/ui/sidebar";
import {
  Activity,
  Building2,
  ClipboardCheck,
  FileSpreadsheet,
  LayoutDashboard,
  Users,
} from "lucide-react";
import { Link, useLocation } from "react-router";
import { useTranslation } from "react-i18next";
import { Can } from "@/components/Can";
const items = [
  ["/", "Overview", LayoutDashboard, "inspections.view_inspection"],
  ["/establishments", "Establishments", Building2, "establishments.view_establishment"],
  ["/inspections", "Inspections", ClipboardCheck, "inspections.view_inspection"],
  ["/checklists", "Checklists", FileSpreadsheet, "inspections.view_checklist"],
  ["/reports", "Coverage", Activity, "inspections.view_inspection"],
  ["/employees", "Employees", Users, "accounts.view_user"],
] as const;
export function NavMain() {
  const { t } = useTranslation();
  const { pathname, search } = useLocation();
  const catalog = useRegistryCatalog();
  const selectedKind = new URLSearchParams(search).get("kind");
  const { setOpenMobile } = useSidebar();
  return (
    <SidebarGroup>
      <SidebarGroupLabel>{t("Workspace")}</SidebarGroupLabel>
      <SidebarMenu>
        {items.map(([url, title, Icon, permission]) => (
          <Can key={url} permission={permission}>
            <SidebarMenuItem>
              <SidebarMenuButton
                asChild
                tooltip={t(title)}
                isActive={pathname === url || (url !== "/" && pathname.startsWith(url + "/"))}
              >
                <Link
                  aria-current={
                    pathname === url || (url !== "/" && pathname.startsWith(url + "/"))
                      ? "page"
                      : undefined
                  }
                  to={url}
                  onClick={() => setOpenMobile(false)}
                >
                  <Icon />
                  <span>{t(title)}</span>
                </Link>
              </SidebarMenuButton>
              {url === "/establishments" && (
                <SidebarMenuSub>
                  {(catalog.data?.types ?? []).map((type) => (
                    <SidebarMenuSubItem key={type.code}>
                      <SidebarMenuSubButton
                        asChild
                        isActive={pathname === "/establishments" && selectedKind === type.code}
                      >
                        <Link
                          to={`/establishments?kind=${encodeURIComponent(type.code)}`}
                          onClick={() => setOpenMobile(false)}
                          aria-current={
                            pathname === "/establishments" && selectedKind === type.code
                              ? "page"
                              : undefined
                          }
                        >
                          {t(type.name)}
                        </Link>
                      </SidebarMenuSubButton>
                    </SidebarMenuSubItem>
                  ))}
                </SidebarMenuSub>
              )}
            </SidebarMenuItem>
          </Can>
        ))}
      </SidebarMenu>
    </SidebarGroup>
  );
}
