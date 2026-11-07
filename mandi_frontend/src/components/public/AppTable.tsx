import * as React from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { useSearchParams } from "react-router";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { DataTablePagination } from "@/components/ui/data-table-pagination";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useLocale, useTranslations } from "@/i18n/useTranslations";
import { isRTL } from "@/config/languages";
import { cn } from "@/lib/utils";
import AppPagination from "@/components/public/AppPagination";
import { AppLoader } from "@/components/public/AppLoader";

export type AppTablePaginationProps = {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  pageSize: number;
  onPageSizeChange: (pageSize: number) => void;
  summary?: React.ReactNode;
  summaryClassName?: string;
  className?: string;
  totalItems?: number;
};

export function AppTablePagination(props: AppTablePaginationProps) {
  return props.totalItems !== undefined ? (
    <AppPagination
      totalItems={props.totalItems}
      page={props.page}
      pageSize={props.pageSize}
      totalPages={props.totalPages}
      onPageChange={props.onPageChange}
      onPageSizeChange={props.onPageSizeChange}
    />
  ) : (
    <DataTablePagination {...props} />
  );
}

export type TableHeaderConfig = {
  id: string;
  label: React.ReactNode;
  sortable?: boolean;
  className?: string;
};

type DataTableModeProps<T> = {
  headers: TableHeaderConfig[];
  data: T[];
  renderRow: (item: T, index: number, data?: T[]) => React.ReactNode;
  cardClassName?: string;
  cardContentClassName?: string;
  tableRowClassName?: string;
  titleIcon?: React.ReactNode;
  title?: string;
  description?: string;
  headerAction?: React.ReactNode;
  firstRow?: React.ReactNode;
  lastRow?: React.ReactNode;
  keyExtractor?: (item: T, index: number) => string | number;
  loading?: boolean;
  showPagination?: boolean;
  emptyMessage?: string;
  footer?: React.ReactNode;
  totalItems?: number;
  pageSizeOptions?: number[];
  wrapRow?: boolean;
};

type AppTableProps<T = unknown> = React.ComponentProps<typeof Table> &
  Partial<DataTableModeProps<T>> & { pagination?: AppTablePaginationProps };

/** Shared table with the original children API and a licensing-compatible data API. */
export default function AppTable<T>({
  children,
  className,
  containerClassName,
  dir,
  pagination,
  headers,
  data,
  renderRow,
  cardClassName,
  cardContentClassName,
  tableRowClassName,
  titleIcon,
  title,
  description,
  headerAction,
  firstRow,
  lastRow,
  keyExtractor,
  loading = false,
  showPagination = true,
  emptyMessage,
  footer,
  totalItems,
  pageSizeOptions,
  wrapRow = true,
  ...props
}: AppTableProps<T>) {
  const locale = useLocale();
  const t = useTranslations("Common");
  const [searchParams, setSearchParams] = useSearchParams();
  const direction = dir ?? (isRTL(locale) ? "rtl" : "ltr");
  const dataDriven = Boolean(headers && data && renderRow);
  const ordering = searchParams.get("ordering");
  const sortField = ordering?.startsWith("-") ? ordering.slice(1) : ordering;
  const descending = ordering?.startsWith("-") ?? false;

  const handleSort = (header: TableHeaderConfig) => {
    if (!header.sortable) return;
    const next = new URLSearchParams(searchParams);
    if (sortField !== header.id) next.set("ordering", header.id);
    else if (!descending) next.set("ordering", `-${header.id}`);
    else next.delete("ordering");
    next.set("page", "1");
    setSearchParams(next);
  };

  const table = (
    <Table
      dir={direction}
      containerClassName={cn("rounded-xl border", containerClassName)}
      className={cn("w-full", className)}
      {...props}
    >
      {dataDriven ? (
        <>
          <TableHeader>
            <TableRow>
              {headers!.map((header) => {
                const active = sortField === header.id;
                return (
                  <TableHead
                    key={header.id}
                    onClick={() => handleSort(header)}
                    className={cn(
                      header.sortable && "hover:bg-muted/80 cursor-pointer select-none",
                      active && "text-foreground font-semibold",
                      header.className,
                    )}
                  >
                    <span className="flex items-center gap-1">
                      <span>{header.label}</span>
                      {header.sortable &&
                        (active ? (
                          descending ? (
                            <ArrowDown className="size-3" />
                          ) : (
                            <ArrowUp className="size-3" />
                          )
                        ) : (
                          <ArrowUpDown className="size-3 opacity-40" />
                        ))}
                    </span>
                  </TableHead>
                );
              })}
            </TableRow>
          </TableHeader>
          <TableBody>
            {firstRow}
            {loading ? (
              <TableRow>
                <TableCell colSpan={headers!.length} className="py-10 text-center">
                  <AppLoader label={t("loading")} />
                </TableCell>
              </TableRow>
            ) : data!.length > 0 ? (
              data!.map((item, index) => {
                const row = renderRow!(item, index, data);
                const key = keyExtractor?.(item, index) ?? index;
                return wrapRow ? (
                  <TableRow key={key} className={tableRowClassName}>
                    {row}
                  </TableRow>
                ) : (
                  <React.Fragment key={key}>{row}</React.Fragment>
                );
              })
            ) : (
              <TableRow>
                <TableCell
                  colSpan={headers!.length}
                  className="text-muted-foreground py-6 text-center"
                >
                  {emptyMessage ?? t("no_data")}
                </TableCell>
              </TableRow>
            )}
            {lastRow}
          </TableBody>
        </>
      ) : (
        children
      )}
    </Table>
  );

  if (!dataDriven)
    return (
      <div className="flex flex-1 flex-col justify-between gap-2">
        {table}
        {pagination && <AppTablePagination {...pagination} />}
      </div>
    );

  return (
    <div className="flex flex-1 flex-col justify-between gap-2">
      <Card className={cardClassName}>
        {(title || description || headerAction) && (
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <div className="flex min-w-0 flex-col gap-1">
                {title && (
                  <CardTitle className="flex items-center gap-2">
                    {titleIcon}
                    {title}
                  </CardTitle>
                )}
                {description && <CardDescription>{description}</CardDescription>}
              </div>
              {headerAction}
            </div>
          </CardHeader>
        )}
        <CardContent className={cardContentClassName}>{table}</CardContent>
        {footer && <CardFooter>{footer}</CardFooter>}
      </Card>
      {showPagination &&
        (totalItems !== undefined ? (
          <AppPagination totalItems={totalItems} pageSizeOptions={pageSizeOptions} />
        ) : (
          pagination && <AppTablePagination {...pagination} />
        ))}
    </div>
  );
}
