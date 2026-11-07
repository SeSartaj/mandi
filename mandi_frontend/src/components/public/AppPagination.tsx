import type { ReactNode } from "react";
import { useSearchParams } from "react-router";

import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { AppSelect } from "@/components/public/AppSelect";
import { useLocale, useTranslations } from "@/i18n/useTranslations";
import { isRTL } from "@/config/languages";
import { cn } from "@/lib/utils";
import { paginationState } from "./pagination-state";
import { TABLE_PAGE_SIZE_OPTIONS } from "@/hooks/useTablePageSize";

type AppPaginationProps = {
  totalItems: number;
  pageSizeOptions?: number[];
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
  page?: number;
  pageSize?: number;
  totalPages?: number;
};

const DEFAULT_PAGE_SIZES = [...TABLE_PAGE_SIZE_OPTIONS];

export default function AppPagination({
  totalItems,
  pageSizeOptions = DEFAULT_PAGE_SIZES,
  onPageChange,
  onPageSizeChange,
  page: controlledPage,
  pageSize: controlledPageSize,
  totalPages: controlledTotalPages,
}: AppPaginationProps) {
  const locale = useLocale();
  const t = useTranslations("Pagination");
  const [params, setParams] = useSearchParams();
  const { page, pageSize, totalPages, options, pages } = paginationState(
    controlledPage ?? params.get("page"),
    controlledPageSize ?? params.get("page_size"),
    totalItems,
    pageSizeOptions,
    controlledTotalPages,
  );
  const set = (values: Record<string, string>) => {
    const next = new URLSearchParams(params);
    Object.entries(values).forEach(([key, value]) => next.set(key, value));
    setParams(next);
  };
  const changePage = (nextPage: number) => {
    if (nextPage < 1 || nextPage > totalPages || nextPage === page) return;
    if (onPageChange) onPageChange(nextPage);
    else set({ page: String(nextPage) });
  };
  const changeSize = (nextSize: number) => {
    if (nextSize === pageSize) return;
    if (onPageSizeChange) onPageSizeChange(nextSize);
    else set({ page: "1", page_size: String(nextSize) });
  };
  const items: ReactNode[] = [];
  for (const [position, index] of pages.entries()) {
    if (position > 0 && index - pages[position - 1] > 1) {
      items.push(
        <PaginationItem key={`ellipsis-${index}`}>
          <PaginationEllipsis />
        </PaginationItem>,
      );
    }
    items.push(
      <PaginationItem key={index}>
        <PaginationLink
          href={`?${new URLSearchParams({ ...Object.fromEntries(params), page: String(index) })}`}
          isActive={index === page}
          onClick={(e) => {
            e.preventDefault();
            changePage(index);
          }}
          className="cursor-pointer px-3"
        >
          {index}
        </PaginationLink>
      </PaginationItem>,
    );
  }
  return (
    <Pagination className="flex justify-end">
      <PaginationContent className="w-full flex-wrap items-center justify-center gap-2 md:justify-between">
        <li>
          <AppSelect
            label={`${pageSize}/${t("page")}`}
            value={pageSize}
            options={options.map((size) => ({ value: size, label: `${size}/${t("page")}` }))}
            onChange={(value) => changeSize(Number(value))}
          />
        </li>
        <li>
          <ul dir={isRTL(locale) ? "rtl" : "ltr"} className="flex items-center">
            <PaginationItem>
              <PaginationPrevious
                href={`?${new URLSearchParams({ ...Object.fromEntries(params), page: String(Math.max(1, page - 1)) })}`}
                tabIndex={page <= 1 ? -1 : undefined}
                title={t("previous")}
                aria-disabled={page <= 1}
                className={cn("cursor-pointer", page <= 1 && "pointer-events-none opacity-50")}
                onClick={(e) => {
                  e.preventDefault();
                  changePage(page - 1);
                }}
              />
            </PaginationItem>
            {items}
            <PaginationItem>
              <PaginationNext
                href={`?${new URLSearchParams({ ...Object.fromEntries(params), page: String(Math.min(totalPages, page + 1)) })}`}
                tabIndex={page >= totalPages ? -1 : undefined}
                title={t("next")}
                aria-disabled={page >= totalPages}
                className={cn(
                  "cursor-pointer",
                  page >= totalPages && "pointer-events-none opacity-50",
                )}
                onClick={(e) => {
                  e.preventDefault();
                  changePage(page + 1);
                }}
              />
            </PaginationItem>
          </ul>
        </li>
        <li className="text-muted-foreground flex items-center gap-2 rounded-md border px-3 py-1 text-sm">
          <span>{t("all")}</span>
          <span className="text-foreground font-medium">{totalItems.toLocaleString(locale)}</span>
        </li>
      </PaginationContent>
    </Pagination>
  );
}
