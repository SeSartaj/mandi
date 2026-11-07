"use client";

import { Fragment } from "react";
import { Link, useLocation } from "react-router";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { isRTL } from "@/config/languages";
import { useLocale, useTranslations } from "@/i18n/useTranslations";
import {
  Breadcrumb,
  BreadcrumbEllipsis,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const routeLabelKeys: Record<string, string> = {
  establishments: "establishments",
  inspections: "inspections",
  reports: "reports",
  activity: "activity",
  dashboard: "dashboard",
  "new-ticket": "new_ticket",
  organization: "organization",
  "org-chart": "organization_chart",
  analytics: "analytics",
  employees: "employees",
  customers: "customers",
  "external-organizations": "external_organizations",
  tickets: "tickets",
  "ticket-search": "ticket_search",
  archive: "archive",
  cabinets: "cabinets",
  drawers: "drawers",
  "blue-files": "blue_files",
  documents: "documents",
  audit: "audit",
  components: "components",
  settings: "settings",
  attachments: "attachments",
  chart: "organization_chart",
};

const MAX_VISIBLE = 3;

export function GlobalBreadcrumb() {
  const location = useLocation();
  const locale = useLocale();
  const t = useTranslations("Breadcrumb");
  const rtl = isRTL(locale);
  const direction = rtl ? "rtl" : "ltr";
  const segments = location.pathname.split("/").filter(Boolean);

  if (segments.length === 0) return null;

  const showDropdown = segments.length > MAX_VISIBLE;
  const first = segments[0];
  const last = segments[segments.length - 1];
  const middle = segments.slice(1, -1);

  const separator = (
    <BreadcrumbSeparator>
      {rtl ? <ChevronLeft aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}
    </BreadcrumbSeparator>
  );

  return (
    <Breadcrumb aria-label={t("label")} dir={direction} className="mb-0 min-w-0">
      <BreadcrumbList>
        <BreadcrumbItem>
          <BreadcrumbLink asChild>
            <Link to="/">{t("home")}</Link>
          </BreadcrumbLink>
        </BreadcrumbItem>

        {separator}

        {showDropdown ? (
          <>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link to={`/${first}`}>{getLabel(first, 0, segments, t)}</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>

            {separator}

            <BreadcrumbItem>
              <DropdownMenu dir={direction}>
                <DropdownMenuTrigger className="flex items-center gap-1">
                  <BreadcrumbEllipsis className="size-4" />
                  <span className="sr-only">{t("more")}</span>
                </DropdownMenuTrigger>
                <DropdownMenuContent align={rtl ? "end" : "start"} style={{ direction }}>
                  {middle.map((segment, index) => {
                    const href = "/" + segments.slice(0, index + 2).join("/");
                    return (
                      <DropdownMenuItem key={href} asChild>
                        <Link to={href}>{getLabel(segment, index + 1, segments, t)}</Link>
                      </DropdownMenuItem>
                    );
                  })}
                </DropdownMenuContent>
              </DropdownMenu>
            </BreadcrumbItem>

            {separator}

            <BreadcrumbItem>
              <BreadcrumbPage>{getLabel(last, segments.length - 1, segments, t)}</BreadcrumbPage>
            </BreadcrumbItem>
          </>
        ) : (
          segments.map((segment, index) => {
            const href = "/" + segments.slice(0, index + 1).join("/");
            const isLast = index === segments.length - 1;

            return (
              <Fragment key={href}>
                {index > 0 && separator}
                <BreadcrumbItem>
                  {isLast ? (
                    <BreadcrumbPage>{getLabel(segment, index, segments, t)}</BreadcrumbPage>
                  ) : (
                    <BreadcrumbLink asChild>
                      <Link to={href}>{getLabel(segment, index, segments, t)}</Link>
                    </BreadcrumbLink>
                  )}
                </BreadcrumbItem>
              </Fragment>
            );
          })
        )}
      </BreadcrumbList>
    </Breadcrumb>
  );
}

function getLabel(segment: string, index: number, segments: string[], t: (key: string) => string) {
  const key = getRouteLabelKey(segment, index, segments);
  const translated = t(key);

  return translated === key ? formatSegment(segment) : translated;
}

function getRouteLabelKey(segment: string, index: number, segments: string[]) {
  const previous = segments[index - 1];
  const beforePrevious = segments[index - 2];

  if (segment === "new") {
    if (previous === "establishments") return "establishment_details";
    if (previous === "inspections") return "inspection_details";
    if (previous === "employees") return "add_employee";
    if (previous === "customers") return "add_customer";
    if (previous === "tickets") return "new_ticket";
  }

  if (segment === "edit" && beforePrevious === "customers") return "edit_customer";
  if (segment === "print" && beforePrevious === "attachments") return "print";
  if (segment === "chart" && (previous === "organization" || previous === "org-chart")) {
    return "organization_chart";
  }

  if (previous === "cabinets") return "cabinet_details";
  if (previous === "drawers") return "drawer_details";
  if (previous === "blue-files") return "blue_file_details";
  if (previous === "documents") return "document_details";

  if (previous === "establishments") return "establishment_details";
  if (previous === "inspections") return "inspection_details";
  if (previous === "employees") return "employee_details";
  if (previous === "customers") return "customer_details";
  if (previous === "external-organizations") return "external_organization_details";
  if (previous === "tickets") return "ticket_details";
  if (previous === "attachments") return "attachment_details";
  if (previous === "chart" && segments[0] === "organization") return "unit_details";
  if (previous === "org-chart") return "unit_details";

  return routeLabelKeys[segment] ?? segment;
}

function formatSegment(segment: string) {
  return segment.replace(/[-_]/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}
