import { useTranslation } from "react-i18next";

import { PageSection } from "@/components/PageSection";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import AppTitle from "@/components/public/AppTitle";
import {
  InspectionFilters,
  type InspectionFilterValues,
} from "@/features/inspections/InspectionFilters";
import { useState } from "react";
import { useApiQuery } from "@/features/shared/api";
import type { Coverage } from "@/lib/api";
import { errorMessage } from "@/lib/api";

export default function ReportsPage() {
  const { t } = useTranslation();
  const [filters, setFilters] = useState<InspectionFilterValues>({});
  const coverage = useApiQuery<Coverage>(["report-coverage"], "/reports/coverage/", filters);

  return (
    <div className="space-y-6">
      <AppTitle
        title={t("Coverage")}
        description={t("Distinct establishments inspected and approval counts.")}
      />

      <PageSection title={t("Inspection coverage")} contentClassName="space-y-4 pt-4">
        <InspectionFilters onApply={setFilters} />
        {coverage.isPending ? (
          <AppLoader label={t("Loading…")} className="py-8" />
        ) : coverage.error ? (
          <AppErrorState
            message={errorMessage(coverage.error)}
            onRetry={() => coverage.refetch()}
          />
        ) : coverage.data ? (
          <div className="report-strip">
            {[
              ["Establishments", coverage.data.establishments],
              ["Inspected establishments", coverage.data.inspected],
              ["Uninspected establishments", coverage.data.uninspected],
              ["Inspection visits", coverage.data.visits],
              ["Approved", coverage.data.approved],
              ["Unapproved", coverage.data.unapproved],
            ].map(([name, value]) => (
              <div key={String(name)}>
                <span>{t(String(name))}</span>
                <strong>{value}</strong>
              </div>
            ))}
            <div>
              <span>{t("Inspection coverage")}</span>
              <strong>{coverage.data.coverage_percent}%</strong>
            </div>
          </div>
        ) : null}
      </PageSection>
    </div>
  );
}
