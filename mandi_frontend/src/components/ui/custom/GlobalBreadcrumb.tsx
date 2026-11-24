import { Fragment } from "react";
import { Link, useLocation } from "react-router";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { isRTL } from "@/config/languages";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";

/** Only show navigable parents: IDs and intermediate API segments are not pages. */
export function GlobalBreadcrumb() {
  const { pathname } = useLocation();
  const { t, i18n } = useTranslation();
  const [section, id, child, source] = pathname.split("/").filter(Boolean);
  const labels: Record<string, string> = {
    establishments: "Establishments",
    "external-systems": "External systems",
    checklists: "Checklists",
    submissions: "Submissions",
    employees: "Employees",
  };
  const items: { label: string; href?: string }[] = [
    { label: "Overview", href: section ? "/" : undefined },
  ];
  if (section === "submissions") {
    items.push({ label: "Submissions", href: id ? "/submissions" : undefined });
  } else if (section) {
    items.push({
      label: labels[section] ?? "Page not found.",
      href: id && labels[section] ? `/${section}` : undefined,
    });
    if (id)
      items.push({
        label: "Details",
        href: child === "sources" ? `/establishments/${id}` : undefined,
      });
    if (child === "sources")
      items.push({
        label:
          (
            { licensing: "Licensing", survey: "Survey", archive: "Archive" } as Record<
              string,
              string
            >
          )[source] ?? "Details",
      });
  }
  const SeparatorIcon = isRTL(i18n.language) ? ChevronLeft : ChevronRight;
  return (
    <Breadcrumb aria-label={t("Breadcrumb")} className="min-w-0">
      <BreadcrumbList className="gap-1.5 text-xs lg:text-sm">
        {items.map((item, index) => (
          <Fragment key={index}>
            {index > 0 && (
              <BreadcrumbSeparator>
                <SeparatorIcon aria-hidden="true" />
              </BreadcrumbSeparator>
            )}
            <BreadcrumbItem>
              {item.href ? (
                <BreadcrumbLink asChild>
                  <Link to={item.href}>{t(item.label)}</Link>
                </BreadcrumbLink>
              ) : (
                <BreadcrumbPage>{t(item.label)}</BreadcrumbPage>
              )}
            </BreadcrumbItem>
          </Fragment>
        ))}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
