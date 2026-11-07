"use client";

import { Fragment, useMemo } from "react";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Link, useLocation } from "react-router";
import { useLocale, useTranslations } from "@/i18n/useTranslations";
import { isLTR } from "@/config/languages";
import { ChevronLeft, ChevronRight } from "lucide-react";

type DynamicBreadcrumbProps = {
  homeHref?: string;
  homeLabel?: string;
  labels?: Record<string, string>;
  hiddenSegments?: string[];
};

const isIdLike = (segment: string) => {
  return /^\d+$/.test(segment) || /^[0-9a-fA-F-]{8,}$/.test(segment);
};

const formatSegmentLabel = (segment: string) => {
  return decodeURIComponent(segment).replace(/[-_]/g, " ").trim();
};

export default function AppBreadcrumb({
  homeHref = "/",
  homeLabel,
  labels = {},
  hiddenSegments = [],
}: DynamicBreadcrumbProps) {
  const { pathname } = useLocation();
  const locale = useLocale();
  const t = useTranslations("Sidebar");

  const finalHomeLabel = homeLabel ?? t("dashboard");

  const items = useMemo(() => {
    const rawSegments = pathname.split("/").filter(Boolean);

    const segments = rawSegments[0] === locale ? rawSegments.slice(1) : rawSegments;

    return segments
      .filter((segment) => !hiddenSegments.includes(segment))
      .map((segment, index) => {
        const href = `/${segments.slice(0, index + 1).join("/")}`;
        const label =
          labels[segment] ?? (isIdLike(segment) ? `#${segment}` : formatSegmentLabel(segment));

        return { href, label };
      });
  }, [pathname, locale, labels, hiddenSegments]);

  return (
    <Breadcrumb dir={isLTR(locale) ? "ltr" : "rtl"} className="w-full overflow-hidden">
      <BreadcrumbList className="flex-nowrap items-center overflow-x-auto overflow-y-hidden whitespace-nowrap">
        <BreadcrumbItem className="shrink-0 select-none">
          {items.length === 0 ? (
            <BreadcrumbPage>{finalHomeLabel}</BreadcrumbPage>
          ) : (
            <BreadcrumbLink asChild>
              <Link to={homeHref}>{finalHomeLabel}</Link>
            </BreadcrumbLink>
          )}
        </BreadcrumbItem>

        {items.map((item, index) => {
          const isLast = index === items.length - 1;

          return (
            <Fragment key={item.href}>
              <BreadcrumbSeparator className="text-muted-foreground shrink-0 select-none">
                {isLTR(locale) ? <ChevronRight /> : <ChevronLeft />}
              </BreadcrumbSeparator>

              <BreadcrumbItem className="shrink-0">
                {isLast ? (
                  <BreadcrumbPage>{item.label}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink asChild>
                    <Link to={item.href}>{item.label}</Link>
                  </BreadcrumbLink>
                )}
              </BreadcrumbItem>
            </Fragment>
          );
        })}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
