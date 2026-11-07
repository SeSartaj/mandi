import { Activity, Building2, Check, ClipboardCheck, ShieldCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import AppTitle from "@/components/public/AppTitle";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import InspectionTable from "@/features/inspections/InspectionTable";
import { useApiQuery } from "@/features/shared/api";
import type { Coverage, Inspection, Page } from "@/lib/api";
import { errorMessage } from "@/lib/api";

export default function DashboardPage() {
  const { t } = useTranslation();
  const report = useApiQuery<Coverage>(["coverage"], "/reports/coverage/");
  const visits = useApiQuery<Page<Inspection>>(["recent"], "/inspections/", {
    page_size: 5,
  });

  if (report.isPending) return <AppLoader label={t("Loading…")} className="py-16" />;
  if (report.error)
    return <AppErrorState message={errorMessage(report.error)} onRetry={() => report.refetch()} />;
  const coverage = report.data!;

  const stats = [
    { label: "Establishments", value: coverage.establishments, icon: Building2 },
    { label: "Inspected establishments", value: coverage.inspected, icon: ShieldCheck },
    { label: "Uninspected establishments", value: coverage.uninspected, icon: ClipboardCheck },
    { label: "Inspection visits", value: coverage.visits, icon: Activity },
  ];

  return (
    <div className="space-y-6">
      <AppTitle
        title={t("Overview")}
        description={t("See which establishments have been inspected, and what needs attention.")}
        others={
          <Link to="/establishments">
            <Button variant="outline">
              <Building2 />
              {t("Establishments")}
            </Button>
          </Link>
        }
      />

      <div className="stats-grid">
        {stats.map((stat) => (
          <Card className="stat-card" key={stat.label}>
            <div>
              <span>{t(stat.label)}</span>
              <stat.icon size={20} />
            </div>
            <strong>{stat.value.toString().padStart(2, "0")}</strong>
          </Card>
        ))}
      </div>

      <div className="dashboard-middle">
        <Card className="coverage-card">
          <div className="section-top">
            <h2>{t("Inspection coverage")}</h2>
            <span className="muted">{t("All statuses")}</span>
          </div>
          <div className="coverage-body">
            <div
              className="coverage-ring"
              style={{
                background: `conic-gradient(var(--primary) ${coverage.coverage_percent}%,var(--muted) 0)`,
              }}
            >
              <div>
                <strong>{coverage.coverage_percent}%</strong>
                <span>{t("Inspection coverage")}</span>
              </div>
            </div>
            <div className="coverage-legend">
              <p>
                <span className="legend-dot green" />
                {t("Inspected establishments")}
                <strong>{coverage.inspected}</strong>
              </p>
              <p>
                <span className="legend-dot gray" />
                {t("Uninspected establishments")}
                <strong>{coverage.uninspected}</strong>
              </p>
              <div className="legend-note">
                {coverage.inspected} / {coverage.establishments} {t("of establishments inspected")}
              </div>
            </div>
          </div>
        </Card>

        <Card className="queue-card">
          <div className="section-top">
            <h2>{t("Review queue")}</h2>
            <ClipboardCheck size={22} />
          </div>
          <div className="queue-number">{coverage.unapproved.toString().padStart(2, "0")}</div>
          <p>{t("Visits awaiting approval")}</p>
          <div className="queue-footer">
            <span>
              <Check size={15} />
              {coverage.approved} {t("Approved")}
            </span>
            <Link to="/inspections?approved=false">{t("View all")}</Link>
          </div>
        </Card>
      </div>

      {visits.error ? (
        <AppErrorState message={errorMessage(visits.error)} onRetry={() => visits.refetch()} />
      ) : (
        <InspectionTable
          title={t("Recent inspections")}
          rows={visits.data?.results ?? []}
          loading={visits.isPending}
          pageSize={5}
        />
      )}
    </div>
  );
}
