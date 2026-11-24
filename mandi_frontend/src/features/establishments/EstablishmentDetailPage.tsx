import SourceDetails, { DeferredMap, type SourceDetail } from "./SourceDetails";
import { useLocationName } from "@/features/establishments/registry";
import RegistryOwnership from "@/features/establishments/RegistryOwnership";
import { EditButton } from "@/components/public/ActionButton";
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
import EstablishmentMappings from "@/features/establishments/EstablishmentMappings";
import { useApiQuery } from "@/features/shared/api";
import { choiceLabel, pageCount } from "@/features/shared/labels";
import { useTablePageSize } from "@/hooks/useTablePageSize";
import type { Establishment, Page, Submission } from "@/lib/api";
import { api, errorMessage } from "@/lib/api";
import { useSession } from "@/lib/session";

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
  const locationName = useLocationName();
  const { id } = useParams();
  const client = useQueryClient();
  const { permissions } = useSession();
  const [edit, setEdit] = useState(false);
  const [submissionPage, setSubmissionPage] = useState(1);
  const [submissionPageSize, setSubmissionPageSize] = useTablePageSize();
  const [selectedSubmission, setSelectedSubmission] = useState<Submission | null>(null);
  const data = useApiQuery<Establishment>(["establishment", id], `/establishments/${id}/`);
  const licensingLink = data.data?.source_links.find((link) => link.source === "licensing");
  const licensing = useApiQuery<SourceDetail>(
    ["licensing-profile", id],
    `/establishments/${id}/sources/licensing/`,
    {},
    {
      enabled:
        Boolean(licensingLink) &&
        permissions.includes("establishments.view_sourcelink"),
    },
  );
  const submissions = useApiQuery<Page<Submission>>(
    ["collection-submissions", id],
    `/establishments/${id}/collection-submissions/`,
    { page: submissionPage, page_size: submissionPageSize },
  );
  const syncSubmissions = useMutation({
    mutationFn: () => api.post("/integrations/collection/sync/", { establishment_id: id }),
    onSettled: () => client.invalidateQueries({ queryKey: ["collection-submissions", id] }),
  });

  if (data.isPending) return <AppLoader label={t("Loading…")} className="py-16" />;
  if (data.error)
    return <AppErrorState message={errorMessage(data.error)} onRetry={() => data.refetch()} />;
  const establishment = data.data!;
  const location =
    establishment.latitude != null && establishment.longitude != null
      ? { latitude: establishment.latitude, longitude: establishment.longitude }
      : null;
  const submissionCount = submissions.data?.count ?? 0;

  return (
    <div className="space-y-6">
      <Link className="back-link" to={`/establishments?kind=${establishment.kind}`}>
        <ArrowLeft size={16} />
        {t("Establishments")}
      </Link>
      <AppTitle
        title={establishment.name}
        description={`${t(choiceLabel(establishment.kind))} · ${locationName(establishment.province_name, establishment.province_name_local)}`}
        others={
          <Can permission="establishments.change_establishment">
            <EditButton
              variant="secondary"
              disabled={!!establishment.primary_source}
              onClick={() => setEdit(true)}
              label={t("Edit details")}
            />
          </Can>
        }
      />

      <PageSection
        title={t("Establishment overview")}
        description={t(
          establishment.primary_source
            ? "Identity synced from Licensing. Source details are shown below."
            : "Identity managed in Mandi.",
        )}
        contentClassName="pt-4"
      >
        <dl className="info-grid">
          {([
            ["Province", locationName(establishment.province_name, establishment.province_name_local)],
            ["District", locationName(establishment.district_name, establishment.district_name_local)],
            ["Address", establishment.address],
            ["Latitude", establishment.latitude],
            ["Longitude", establishment.longitude],
          ] as [string, string | number | null][]).map(([label, value]) => (
            <div key={label}>
              <dt>{t(label)}</dt>
              <dd>{value ?? "—"}</dd>
            </div>
          ))}
        </dl>
        {location && (
          <div className="mt-4">
            <DeferredMap location={location} />
          </div>
        )}
        <details className="mt-4 border-t pt-4">
          <summary className="cursor-pointer text-sm">
            {t("Identity and source management")}
          </summary>
          <div className="mt-3">
            <RegistryOwnership establishment={establishment} />
          </div>
        </details>
      </PageSection>

      {licensingLink && permissions.includes("establishments.view_sourcelink") ? (
        <PageSection
          title={t("Licensing details")}
          description={t(
            "Establishment identity, license, location, ownership and technical staff from Licensing.",
          )}
          actions={
            <Link
              className="text-link"
              to={`/establishments/${establishment.id}/sources/licensing`}
            >
              {t("Open full profile")}
            </Link>
          }
        >
          {licensing.isPending ? (
            <AppLoader label={t("Loading Licensing details…")} className="py-8" />
          ) : licensing.error ? (
            <AppErrorState
              message={errorMessage(licensing.error)}
              onRetry={() => licensing.refetch()}
            />
          ) : licensing.data ? (
            <SourceDetails data={licensing.data} stacked />
          ) : null}
        </PageSection>
      ) : null}

      <Can permission="establishments.view_sourcelink">
        <EstablishmentMappings establishment={establishment} />
      </Can>

      <PageSection
        title={t("Collection submissions")}
        description={t(
          "Forms submitted for this establishment through the configured collection service.",
        )}
        actions={
          <Can permission="inspections.deploy_checklist">
            <Button
              variant="outline"
              disabled={syncSubmissions.isPending}
              onClick={() => syncSubmissions.mutate()}
            >
              <RefreshCw />
              {syncSubmissions.isPending ? t("Syncing…") : t("Sync submissions")}
            </Button>
          </Can>
        }
      >
        {syncSubmissions.error ? (
          <div role="alert" className="error-box">
            {errorMessage(syncSubmissions.error)}
          </div>
        ) : null}
        {submissions.isPending ? (
          <AppLoader label={t("Loading…")} className="py-8" />
        ) : submissions.error ? (
          <AppErrorState
            message={errorMessage(submissions.error)}
            onRetry={() => submissions.refetch()}
          />
        ) : (
          <AppTable
            className="min-w-[500px]"
            pagination={{
              page: submissionPage,
              pageSize: submissionPageSize,
              totalPages: pageCount(submissionCount, submissionPageSize),
              totalItems: submissionCount,
              onPageChange: setSubmissionPage,
              onPageSizeChange: (size) => {
                setSubmissionPageSize(size);
                setSubmissionPage(1);
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
              {(submissions.data?.results ?? []).map((submission) => (
                <TableRow key={submission.id}>
                  <TableCell>
                    <SystemDateTime value={submission.submitted_at} includeTime />
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <span className="block max-w-[170px] truncate">
                        {submission.checklist_name ?? "—"}
                        {submission.form_version ? ` · ${submission.form_version}` : ""}
                      </span>
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
                      {submission.form_url ? (
                        <a
                          className="text-link"
                          href={submission.form_url}
                          target="_blank"
                          rel="noreferrer"
                          title={t("Open collection service")}
                          aria-label={t("Open collection service")}
                        >
                          <ExternalLink className="size-4" />
                        </a>
                      ) : null}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {submissionCount === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-muted-foreground py-8 text-center">
                    {t("No Collection submissions yet. Press Sync submissions to pull new forms.")}
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
        title={t("Submission")}
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
              {selectedSubmission.form_url ? (
                <a
                  className="text-link"
                  href={selectedSubmission.form_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <ExternalLink className="size-4" />
                  {t("Open collection service")}
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
