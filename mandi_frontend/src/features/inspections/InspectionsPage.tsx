import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";

import { AppErrorState } from "@/components/public/AppErrorState";
import AppTitle from "@/components/public/AppTitle";
import InspectionTable from "@/features/inspections/InspectionTable";
import { InspectionFilters } from "@/features/inspections/InspectionFilters";
import { positiveInteger } from "@/components/public/pagination-state";
import { readInspectionFilters, writeInspectionFilters } from "./filter-state";
import { useApiQuery } from "@/features/shared/api";
import { pageCount } from "@/features/shared/labels";
import { useTablePageSize } from "@/hooks/useTablePageSize";
import type { Inspection, Page } from "@/lib/api";
import { errorMessage } from "@/lib/api";

export default function InspectionsPage() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = positiveInteger(searchParams.get("page"), 1);
  const setPage = (value: number) =>
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous);
      next.set("page", String(value));
      return next;
    });
  const [pageSize, setPageSize] = useTablePageSize();
  const filters = useMemo(() => readInspectionFilters(searchParams), [searchParams]);
  const data = useApiQuery<Page<Inspection>>(["inspections"], "/inspections/", {
    ...filters,
    page,
    page_size: pageSize,
  });

  const count = data.data?.count ?? 0;

  return (
    <div className="space-y-6">
      <AppTitle title={t("Inspections")} description={t("Dates follow the selected calendar.")} />

      <InspectionFilters
        initial={filters}
        onApply={(values) => {
          setSearchParams(writeInspectionFilters(searchParams, values));
        }}
      />

      {data.error ? (
        <AppErrorState message={errorMessage(data.error)} onRetry={() => data.refetch()} />
      ) : (
        <InspectionTable
          rows={data.data?.results ?? []}
          loading={data.isPending}
          page={page}
          pageSize={pageSize}
          totalItems={count}
          totalPages={pageCount(count, pageSize)}
          onPageChange={setPage}
          onPageSizeChange={(size) => {
            setPageSize(size);
            setPage(1);
          }}
          title={t("Inspection records")}
        />
      )}
    </div>
  );
}
