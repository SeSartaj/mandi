import { Building2, ClipboardCheck, FileSpreadsheet } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { Can } from "@/components/Can";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import AppTitle from "@/components/public/AppTitle";
import { SystemDateTime } from "@/components/public/SystemDateTime";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import AppTable from "@/components/public/AppTable";
import { useApiQuery } from "@/features/shared/api";
import type { Checklist, Establishment, Page, Submission } from "@/lib/api";
import { errorMessage } from "@/lib/api";

export default function DashboardPage() {
  const { t } = useTranslation();
  const establishments = useApiQuery<Page<Establishment>>(
    ["dashboard-establishments"],
    "/establishments/",
    { page_size: 1 },
  );
  const submissions = useApiQuery<Page<Submission>>(
    ["dashboard-submissions"],
    "/submissions/",
    { page_size: 5 },
  );
  const checklists = useApiQuery<Checklist[]>(["dashboard-checklists"], "/checklists/");

  if (establishments.isPending || submissions.isPending || checklists.isPending)
    return <AppLoader label={t("Loading…")} className="py-16" />;
  const error = establishments.error ?? submissions.error ?? checklists.error;
  if (error)
    return (
      <AppErrorState
        message={errorMessage(error)}
        onRetry={() => {
          establishments.refetch();
          submissions.refetch();
          checklists.refetch();
        }}
      />
    );

  const stats = [
    {
      label: "Establishments",
      value: establishments.data?.count ?? 0,
      icon: Building2,
      to: "/establishments",
    },
    {
      label: "Submissions",
      value: submissions.data?.count ?? 0,
      icon: ClipboardCheck,
      to: "/submissions",
    },
    {
      label: "Checklists",
      value: checklists.data?.length ?? 0,
      icon: FileSpreadsheet,
      to: "/checklists",
    },
  ];
  const rows = submissions.data?.results ?? [];

  return (
    <div className="space-y-6">
      <AppTitle
        title={t("Overview")}
        description={t("See the latest submissions and jump into the registry.")}
        others={
          <Can permission="establishments.view_establishment">
            <Button variant="outline" asChild>
              <Link to="/submissions">
                <ClipboardCheck />
                {t("Submissions")}
              </Link>
            </Button>
          </Can>
        }
      />

      <div className="stats-grid">
        {stats.map((stat) => (
          <Card className="stat-card" key={stat.label}>
            <div>
              <span>{t(stat.label)}</span>
              <stat.icon size={20} />
            </div>
            <strong>{stat.value.toLocaleString()}</strong>
          </Card>
        ))}
      </div>

      <Card className="p-4">
        <div className="section-top mb-3">
          <h2>{t("Recent submissions")}</h2>
          <Link className="text-link" to="/submissions">
            {t("View all")}
          </Link>
        </div>
        <AppTable className="min-w-[560px]">
          <TableHeader>
            <TableRow>
              <TableHead>{t("Submitted")}</TableHead>
              <TableHead>{t("Establishment")}</TableHead>
              <TableHead>{t("Checklist")}</TableHead>
              <TableHead>{t("Form version")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((submission) => (
              <TableRow key={submission.id}>
                <TableCell>
                  <Link className="entity-link" to={`/submissions/${submission.id}`}>
                    <SystemDateTime value={submission.submitted_at} includeTime />
                  </Link>
                </TableCell>
                <TableCell>
                  {submission.establishment_id ? (
                    <Link
                      className="entity-link"
                      to={`/establishments/${submission.establishment_id}`}
                    >
                      {submission.establishment_name ?? "—"}
                    </Link>
                  ) : (
                    <span className="text-muted-foreground">{t("No establishment")}</span>
                  )}
                </TableCell>
                <TableCell>{submission.checklist_name ?? "—"}</TableCell>
                <TableCell>
                  {submission.form_version ? <code>{submission.form_version}</code> : "—"}
                </TableCell>
              </TableRow>
            ))}
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-muted-foreground py-8 text-center">
                  {t("No submissions yet.")}
                </TableCell>
              </TableRow>
            ) : null}
          </TableBody>
        </AppTable>
      </Card>
    </div>
  );
}
