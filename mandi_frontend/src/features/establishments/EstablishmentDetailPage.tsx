import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink, RefreshCw } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { Can } from "@/components/Can";
import { PageSection } from "@/components/PageSection";
import { AppDialog } from "@/components/public/AppDialog";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import AppTable from "@/components/public/AppTable";
import AppTitle from "@/components/public/AppTitle";
import { SystemDateTime } from "@/components/public/SystemDateTime";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import EstablishmentForm from "@/features/establishments/EstablishmentForm";
import SourcePanel from "@/features/establishments/SourcePanel";
import InspectionTable from "@/features/inspections/InspectionTable";
import { useApiQuery } from "@/features/shared/api";
import { choiceLabel, pageCount } from "@/features/shared/labels";
import { useTablePageSize } from "@/hooks/useTablePageSize";
import type { Establishment, Inspection, KoboSubmission, Page } from "@/lib/api";
import { api, errorMessage } from "@/lib/api";

function scoreVariant(percent: number | null | undefined) {
  if (percent === null || percent === undefined) return "secondary" as const;
  if (percent >= 85) return "default" as const;
  if (percent >= 60) return "secondary" as const;
  return "destructive" as const;
}

function ScoreBadge({
  percent,
  score,
  max,
}: {
  percent: number | null | undefined;
  score?: number | null;
  max?: number | null;
}) {
  const { t } = useTranslation();
  if (percent === null || percent === undefined) {
    return <span className="text-muted-foreground">{t("No score")}</span>;
  }
  return (
    <div className="flex flex-col items-start gap-1">
      <Badge variant={scoreVariant(percent)}>{percent}%</Badge>
      {score !== null && score !== undefined && max ? (
        <small className="muted">
          {score} / {max}
        </small>
      ) : null}
    </div>
  );
}

function ScoreBar({ percent }: { percent: number | null }) {
  const width = Math.max(0, Math.min(100, percent ?? 0));
  return (
    <div className="bg-muted h-2 w-full min-w-24 overflow-hidden rounded-full">
      <div
        className={
          width >= 85
            ? "h-full bg-emerald-500"
            : width >= 60
              ? "h-full bg-amber-500"
              : "h-full bg-red-500"
        }
        style={{ width: `${width}%` }}
      />
    </div>
  );
}

export default function EstablishmentDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const client = useQueryClient();
  const [edit, setEdit] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useTablePageSize();
  const [koboPage, setKoboPage] = useState(1);
  const [koboPageSize, setKoboPageSize] = useTablePageSize();
  const [selectedSubmission, setSelectedSubmission] = useState<KoboSubmission | null>(null);
  const data = useApiQuery<Establishment>(["establishment", id], `/establishments/${id}/`);
  const visits = useApiQuery<Page<Inspection>>(["establishment-inspections", id], "/inspections/", {
    establishment_id: id,
    page,
    page_size: pageSize,
  });
  const koboSubmissions = useApiQuery<Page<KoboSubmission>>(
    ["kobo-submissions", id],
    `/establishments/${id}/kobo-submissions/`,
    { page: koboPage, page_size: koboPageSize },
  );
  const syncKobo = useMutation({
    mutationFn: () => api.post("/integrations/kobo/sync/", { establishment_id: id }),
    onSettled: () => client.invalidateQueries({ queryKey: ["kobo-submissions", id] }),
  });

  if (data.isPending) return <AppLoader label={t("Loading…")} className="py-16" />;
  if (data.error)
    return <AppErrorState message={errorMessage(data.error)} onRetry={() => data.refetch()} />;
  const establishment = data.data!;
  const visitCount = visits.data?.count ?? 0;
  const koboCount = koboSubmissions.data?.count ?? 0;

  return (
    <div className="space-y-6">
      <Link className="back-link" to="/establishments">
        <ArrowLeft size={16} />
        {t("Establishments")}
      </Link>
      <AppTitle
        title={establishment.name}
        description={`${t(choiceLabel(establishment.kind))} · ${establishment.province}`}
        others={
          <Can permission="establishments.change_establishment">
            <Button variant="outline" onClick={() => setEdit(true)}>
              {t("Edit details")}
            </Button>
          </Can>
        }
      />

      <PageSection
        title={t("Details")}
        description={<code>{establishment.id}</code>}
        contentClassName="pt-4"
      >
        <dl className="info-grid">
          {["subtype", "province", "district", "address", "phone"].map((key) => (
            <div key={key}>
              <dt>{t(key.charAt(0).toUpperCase() + key.slice(1))}</dt>
              <dd>{(establishment[key as keyof Establishment] as string) || "—"}</dd>
            </div>
          ))}
        </dl>
      </PageSection>

      <h2 className="section-title">{t("Source systems")}</h2>
      <div className="source-grid">
        {[
          ["survey", "Survey system"],
          ["archive", "Archive system"],
          ["licensing", "Licensing system"],
        ].map(([source, title]) => (
          <SourcePanel key={source} establishment={establishment} source={source} title={title} />
        ))}
      </div>

      <InspectionTable
        title={t("Inspection history")}
        rows={visits.data?.results ?? []}
        loading={visits.isPending}
        page={page}
        pageSize={pageSize}
        totalItems={visitCount}
        totalPages={pageCount(visitCount, pageSize)}
        onPageChange={setPage}
        onPageSizeChange={(size) => {
          setPageSize(size);
          setPage(1);
        }}
        emptyMessage={t("No inspections in this selection.")}
      />

      <PageSection
        title={t("KoBo inspections")}
        description={t("Inspection forms submitted through KoBo for this establishment.")}
        actions={
          <Can permission="inspections.add_inspection">
            <Button
              variant="outline"
              disabled={syncKobo.isPending}
              onClick={() => syncKobo.mutate()}
            >
              <RefreshCw />
              {syncKobo.isPending ? t("Syncing…") : t("Sync from KoBo")}
            </Button>
          </Can>
        }
      >
        {syncKobo.error ? (
          <div role="alert" className="error-box">
            {errorMessage(syncKobo.error)}
          </div>
        ) : null}
        {koboSubmissions.isPending ? (
          <AppLoader label={t("Loading…")} className="py-8" />
        ) : koboSubmissions.error ? (
          <AppErrorState
            message={errorMessage(koboSubmissions.error)}
            onRetry={() => koboSubmissions.refetch()}
          />
        ) : (
          <AppTable
            className="min-w-[500px]"
            pagination={{
              page: koboPage,
              pageSize: koboPageSize,
              totalPages: pageCount(koboCount, koboPageSize),
              totalItems: koboCount,
              onPageChange: setKoboPage,
              onPageSizeChange: (size) => {
                setKoboPageSize(size);
                setKoboPage(1);
              },
            }}
          >
            <TableHeader>
              <TableRow>
                <TableHead>{t("Submitted")}</TableHead>
                <TableHead>{t("Checklist")}</TableHead>
                <TableHead>{t("Score")}</TableHead>
                <TableHead>{t("Action")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(koboSubmissions.data?.results ?? []).map((submission) => (
                <TableRow key={submission.id}>
                  <TableCell>
                    <SystemDateTime value={submission.submitted_at} includeTime />
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <span className="block max-w-[170px] truncate">
                        {submission.checklist_name ?? "—"}
                        {submission.checklist_version ? ` · ${submission.checklist_version}` : ""}
                      </span>
                      <small className="muted block">
                        <code>{submission.submission_id}</code>
                      </small>
                    </div>
                  </TableCell>
                  <TableCell>
                    <ScoreBadge percent={submission.scores?.percent} />
                  </TableCell>
                  <TableCell>
                    <div className="inline-actions">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setSelectedSubmission(submission)}
                      >
                        {t("View data")}
                      </Button>
                      {submission.kobo_url ? (
                        <a
                          className="text-link"
                          href={submission.kobo_url}
                          target="_blank"
                          rel="noreferrer"
                          title={t("Open in KoBo")}
                          aria-label={t("Open in KoBo")}
                        >
                          <ExternalLink className="size-4" />
                        </a>
                      ) : null}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {koboCount === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-muted-foreground py-8 text-center">
                    {t("No KoBo submissions yet. Press Sync from KoBo to pull new forms.")}
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </AppTable>
        )}
      </PageSection>

      <AppDialog
        open={selectedSubmission !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedSubmission(null);
        }}
        title={t("KoBo inspection")}
        size="xl"
        contentClassName="max-h-[90vh] overflow-y-auto"
      >
        {selectedSubmission ? (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-3">
              <ScoreBadge
                percent={selectedSubmission.scores?.percent}
                score={selectedSubmission.scores?.score}
                max={selectedSubmission.scores?.max}
              />
              <span className="muted">
                <SystemDateTime value={selectedSubmission.submitted_at} includeTime />
              </span>
              {selectedSubmission.kobo_url ? (
                <a
                  className="text-link"
                  href={selectedSubmission.kobo_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <ExternalLink className="size-4" />
                  {t("Open in KoBo")}
                </a>
              ) : null}
            </div>

            <section className="space-y-2">
              <h3 className="font-medium">{t("Section scores")}</h3>
              {(selectedSubmission.scores?.sections ?? []).length === 0 ? (
                <p className="muted">{t("This form does not calculate section scores.")}</p>
              ) : (
                <AppTable className="min-w-[520px]">
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("Section")}</TableHead>
                      <TableHead>{t("Score")}</TableHead>
                      <TableHead>{t("Percentage")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(selectedSubmission.scores?.sections ?? []).map((section) => (
                      <TableRow key={section.key}>
                        <TableCell className="whitespace-normal">{section.label}</TableCell>
                        <TableCell>
                          {section.score}
                          {section.max ? ` / ${section.max}` : ""}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <ScoreBar percent={section.percent} />
                            <span className="w-14 text-sm">
                              {section.percent === null ? "—" : `${section.percent}%`}
                            </span>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </AppTable>
              )}
            </section>

            <section className="space-y-2">
              <h3 className="font-medium">{t("Answers")}</h3>
              {(selectedSubmission.answers ?? []).length === 0 ? (
                <p className="muted">{t("No answers were recorded.")}</p>
              ) : (
                <dl className="divide-border divide-y">
                  {(selectedSubmission.answers ?? []).map((answer) => (
                    <div
                      key={answer.name}
                      className="grid gap-1 py-2 sm:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] sm:gap-4"
                    >
                      <dt className="text-muted-foreground text-sm">{answer.label}</dt>
                      <dd className="text-sm break-words">{answer.display}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </section>

            <details className="space-y-2">
              <summary className="cursor-pointer text-sm font-medium">
                {t("Raw submission data")}
              </summary>
              <pre
                className="bg-muted mt-2 max-h-[40vh] overflow-auto rounded-md p-4 text-xs"
                dir="ltr"
              >
                {JSON.stringify(selectedSubmission.data, null, 2)}
              </pre>
            </details>
          </div>
        ) : null}
      </AppDialog>

      <AppDialog
        open={edit}
        onOpenChange={setEdit}
        title={t("Edit details")}
        size="lg"
        contentClassName="max-h-[90vh] overflow-y-auto"
      >
        <EstablishmentForm existing={establishment} onClose={() => setEdit(false)} />
      </AppDialog>
    </div>
  );
}
