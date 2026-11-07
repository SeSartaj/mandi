import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { Can } from "@/components/Can";
import { PageSection } from "@/components/PageSection";
import AppTable from "@/components/public/AppTable";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import AppTitle from "@/components/public/AppTitle";
import { SystemDateTime } from "@/components/public/SystemDateTime";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TableCell } from "@/components/ui/table";
import { InspectionStatus } from "@/features/inspections/InspectionTable";
import { useApiQuery } from "@/features/shared/api";
import { choiceLabel } from "@/features/shared/labels";
import type { Inspection } from "@/lib/api";
import { api, errorMessage } from "@/lib/api";

export default function InspectionDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const client = useQueryClient();
  const data = useApiQuery<Inspection>(["inspection", id], `/inspections/${id}/`);
  const approve = useMutation({
    mutationFn: () => api.post(`/inspections/${id}/approve/`),
    onSuccess: () => client.invalidateQueries(),
  });

  if (data.isPending) return <AppLoader label={t("Loading…")} className="py-16" />;
  if (data.error)
    return <AppErrorState message={errorMessage(data.error)} onRetry={() => data.refetch()} />;
  const inspection = data.data!;
  const findings = inspection.summary.findings ?? [];

  return (
    <div className="space-y-6">
      <Link to="/inspections" className="back-link">
        <ArrowLeft size={16} />
        {t("Inspections")}
      </Link>
      <AppTitle
        title={inspection.establishment_name}
        description={
          <>
            {t(choiceLabel(inspection.kind))} · <SystemDateTime value={inspection.inspected_on} />
          </>
        }
        others={
          <div className="inline-actions">
            <InspectionStatus approved={inspection.approved} />
            <Can permission="inspections.approve_inspection">
              {!inspection.approved ? (
                <Button disabled={approve.isPending} onClick={() => approve.mutate()}>
                  <Check />
                  {t("Approve inspection")}
                </Button>
              ) : null}
            </Can>
          </div>
        }
      />

      {approve.error ? <AppErrorState message={errorMessage(approve.error)} /> : null}
      {inspection.is_demo ? (
        <Badge variant="secondary">
          {t("Demonstration data")} ·{" "}
          {t("Local review build · Live integrations are not connected.")}
        </Badge>
      ) : null}

      <PageSection title={t("Details")} contentClassName="pt-4">
        <dl className="info-grid">
          <div>
            <dt>{t("Checklist")}</dt>
            <dd>{inspection.checklist.name}</dd>
          </div>
          <div>
            <dt>{t("Version")}</dt>
            <dd>{inspection.checklist.version}</dd>
          </div>
          <div>
            <dt>{t("Team")}</dt>
            <dd>
              {inspection.team.map((member) => member.display_name || member.username).join(", ")}
            </dd>
          </div>
          <div>
            <dt>{t("Provider")}</dt>
            <dd>{inspection.provider}</dd>
          </div>
          <div>
            <dt>{t("Submission")}</dt>
            <dd>{inspection.submission_id}</dd>
          </div>
          <div>
            <dt>{t("Establishments")}</dt>
            <dd>
              <Link className="text-link" to={`/establishments/${inspection.establishment_id}`}>
                {t("View")}
              </Link>
            </dd>
          </div>
          {inspection.approved_by ? (
            <div>
              <dt>{t("Approved")}</dt>
              <dd>
                {inspection.approved_by.display_name} ·{" "}
                <SystemDateTime value={inspection.approved_at} includeTime />
              </dd>
            </div>
          ) : null}
        </dl>
      </PageSection>

      <PageSection
        title={t("Selected results")}
        actions={
          inspection.summary.overall_percent !== undefined ? (
            <strong className="result-number">{inspection.summary.overall_percent}%</strong>
          ) : null
        }
        contentClassName="pt-4"
      >
        {inspection.summary.sections?.map((section, index) => (
          <div className="score-line" key={index}>
            <span>{section.name}</span>
            <strong>
              {section.earned} / {section.possible}
            </strong>
          </div>
        ))}
        {!inspection.summary.sections?.length ? (
          <p className="muted">{t("No findings returned in this summary.")}</p>
        ) : null}
      </PageSection>

      <AppTable
        title={t("Findings & actions")}
        headers={[
          { id: "finding", label: t("Finding") },
          { id: "action", label: t("Action") },
          { id: "deadline", label: t("Deadline") },
        ]}
        data={findings}
        emptyMessage={t("No findings returned in this summary.")}
        renderRow={(finding) => (
          <>
            <TableCell>{finding.issue}</TableCell>
            <TableCell>{finding.action}</TableCell>
            <TableCell dir="ltr">
              <SystemDateTime value={finding.deadline} />
            </TableCell>
          </>
        )}
      />
    </div>
  );
}
