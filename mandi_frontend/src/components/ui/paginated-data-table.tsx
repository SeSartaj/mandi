import type { ReactNode } from "react";

import { DataTable } from "@/components/ui/data-table";
import { AppTablePagination } from "@/components/public/AppTable";
import type { AppTablePaginationProps } from "@/components/public/AppTable";
import { AppLoader } from "@/components/public/AppLoader";

type PaginatedDataTableProps = {
  filters?: ReactNode;
  children: ReactNode;
  hasRows: boolean;
  loading?: boolean;
  loadingContent?: ReactNode;
  paginationSummary?: ReactNode;
  error?: ReactNode;
  empty?: ReactNode;
} & AppTablePaginationProps;

/** Shared table layout with a filter bar, states, and AppTable pagination. */
export function PaginatedDataTable({
  filters,
  children,
  hasRows,
  loading = false,
  loadingContent = "Loading...",
  paginationSummary,
  error,
  empty,
  page,
  totalPages,
  onPageChange,
  pageSize,
  onPageSizeChange,
}: PaginatedDataTableProps) {
  const pagination =
    !loading && !error && (paginationSummary || totalPages > 1)
      ? { page, totalPages, onPageChange, pageSize, onPageSizeChange, summary: paginationSummary }
      : undefined;

  return (
    <div className="space-y-4">
      {filters && <div className="flex flex-wrap items-center gap-3">{filters}</div>}
      {loading ? (
        <AppLoader label={loadingContent} className="py-10" spinnerClassName="size-4" />
      ) : error ? (
        error
      ) : hasRows ? (
        <DataTable pagination={pagination}>{children}</DataTable>
      ) : (
        empty
      )}
      {pagination && !hasRows && <AppTablePagination {...pagination} />}
    </div>
  );
}
