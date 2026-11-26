import SourceDetails, { DeferredMap, type SourceDetail } from "./SourceDetails";
import { useLocationName, useDistrictName } from "@/features/establishments/registry";
import RegistryOwnership from "@/features/establishments/RegistryOwnership";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, Fingerprint, Link2, Pencil, Printer, RefreshCw } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { Can } from "@/components/Can";
import { PageSection } from "@/components/PageSection";
import { ActionsMenu } from "@/components/public/ActionsMenu";
import { AppDialog } from "@/components/public/AppDialog";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import AppTable from "@/components/public/AppTable";
import AppTitle from "@/components/public/AppTitle";
import { SystemDateTime } from "@/components/public/SystemDateTime";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import EstablishmentForm from "@/features/establishments/EstablishmentForm";
import EstablishmentMappings from "@/features/establishments/EstablishmentMappings";
import { useApiQuery } from "@/features/shared/api";
import { choiceLabel, localizeAddress } from "@/features/shared/labels";
import type { Establishment, Submission, SubmissionGroup } from "@/lib/api";
import { api, errorMessage } from "@/lib/api";
import { notify } from "@/lib/notify";
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

function InspectionStats({ stats }: { stats: Establishment["inspection_stats"] }) {
  const { t } = useTranslation();
  return (
    <dl className="stats-band">
      <div>
        <dt>{t("Total inspections")}</dt>
        <dd>{stats?.total ?? 0}</dd>
      </div>
      <div>
        <dt>{t("Inspections this year")}</dt>
        <dd>{stats?.this_year ?? 0}</dd>
      </div>
      <div>
        <dt>{t("Last inspection")}</dt>
        <dd className="text-base">
          <SystemDateTime value={stats?.last_submitted_at ?? null} />
        </dd>
      </div>
    </dl>
  );
}

export default function EstablishmentDetailPage() {
  const { t } = useTranslation();
  const locationName = useLocationName();
  const districtName = useDistrictName();
  const { id } = useParams();
  const client = useQueryClient();
  const { permissions } = useSession();
  const [edit, setEdit] = useState(false);
  const [identityOpen, setIdentityOpen] = useState(false);
  const [mappingsOpen, setMappingsOpen] = useState(false);
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
  const surveyLink = data.data?.source_links.find((link) => link.source === "survey");
  const survey = useApiQuery<SourceDetail>(
    ["survey-profile", id],
    `/establishments/${id}/sources/survey/`,
    {},
    {
      enabled:
        Boolean(surveyLink) &&
        permissions.includes("establishments.view_sourcelink"),
    },
  );
  const groups = useApiQuery<SubmissionGroup[]>(
    ["establishment-submission-groups", id],
    `/establishments/${id}/collection-groups/`,
  );
  const syncSubmissions = useMutation({
    mutationFn: () => api.post("/integrations/collection/sync/", { establishment_id: id }),
    onSuccess: () => notify.success(t("Submissions synced.")),
    onError: (error) =>
      notify.error(t("Could not complete the action."), {
        description: errorMessage(error),
      }),
    onSettled: () => client.invalidateQueries({ queryKey: ["establishment-submission-groups", id] }),
  });

  if (data.isPending) return <AppLoader label={t("Loading…")} className="py-16" />;
  if (data.error)
    return <AppErrorState message={errorMessage(data.error)} onRetry={() => data.refetch()} />;
  const establishment = data.data!;
  const location =
    establishment.latitude != null && establishment.longitude != null
      ? { latitude: establishment.latitude, longitude: establishment.longitude }
      : null;
  const submissionCount = (groups.data ?? []).reduce((total, group) => total + group.count, 0);

  return (
    <div className="establishment-profile mx-auto w-full max-w-6xl space-y-6">
      <div className="print-only print-profile-head">
        <p className="print-brand">Afghanistan Food and Drug Authority · Monitoring &amp; inspection</p>
        <h1>{establishment.name}</h1>
        <p>
          {t(choiceLabel(establishment.kind))} ·{" "}
          {locationName(establishment.province_name, establishment.province_name_local)}
        </p>
      </div>
      <div className="print:hidden">
        <AppTitle
          title={establishment.name}
          description={`${t(choiceLabel(establishment.kind))} · ${locationName(establishment.province_name, establishment.province_name_local)}`}
          others={
            <ActionsMenu
              label={t("More actions")}
              items={[
                {
                  id: "edit",
                  label: t("Edit details"),
                  icon: Pencil,
                  disabled: !!establishment.primary_source,
                  hidden: !permissions.includes("establishments.change_establishment"),
                  onSelect: () => setEdit(true),
                },
                {
                  id: "print",
                  label: t("Print profile"),
                  icon: Printer,
                  onSelect: () => window.print(),
                },
                {
                  id: "identity",
                  label: t("Registry identity"),
                  icon: Fingerprint,
                  separatorBefore: true,
                  hidden: !permissions.includes("establishments.view_sourcelink"),
                  onSelect: () => setIdentityOpen(true),
                },
                {
                  id: "mappings",
                  label: t("System mappings"),
                  icon: Link2,
                  hidden: !permissions.includes("establishments.view_sourcelink"),
                  onSelect: () => setMappingsOpen(true),
                },
              ]}
            />
          }
        />
      </div>

      <InspectionStats stats={establishment.inspection_stats} />

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="print:hidden">
          <TabsTrigger value="overview">{t("Overview")}</TabsTrigger>
          <TabsTrigger value="checklists">
            {t("Checklists")}
            {submissionCount ? ` (${submissionCount})` : null}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <PageSection
            title={t("Location")}
            description={t("Address and map for this establishment.")}
          >
            <dl className="grid gap-x-8 gap-y-6 sm:grid-cols-2">
              <div>
                <dt className="text-muted-foreground mb-1.5 text-[13px]">{t("Province")}</dt>
                <dd className="text-[15px] break-words" dir="auto">
                  {locationName(
                    establishment.province_name,
                    establishment.province_name_local,
                  ) || "—"}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground mb-1.5 text-[13px]">{t("District")}</dt>
                <dd className="text-[15px] break-words" dir="auto">
                  {districtName(
                    establishment.district_name,
                    establishment.district_name_local,
                  ) || "—"}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-muted-foreground mb-1.5 text-[13px]">{t("Address")}</dt>
                <dd className="text-[15px] leading-relaxed break-words" dir="auto">
                  {localizeAddress(establishment.address) || "—"}
                </dd>
              </div>
            </dl>
            {location && (
              <div className="mt-5">
                <DeferredMap
                  location={location}
                  name={establishment.name}
                  address={establishment.address}
                />
              </div>
            )}
          </PageSection>

          {licensingLink && permissions.includes("establishments.view_sourcelink") ? (
            <PageSection
              title={t("Licensing details")}
              description={t(
                "Establishment identity, license, location, ownership and technical staff from Licensing.",
              )}
              actions={
                <Link
                  className="text-link print:hidden"
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
                <SourceDetails data={licensing.data} stacked showLocationMap={false} />
              ) : null}
            </PageSection>
          ) : null}

          {surveyLink && permissions.includes("establishments.view_sourcelink") ? (
            <PageSection
              title={t("Survey details")}
              description={t(
                "Registration, ownership, staff and location from Survey.",
              )}
              actions={
                <Link
                  className="text-link print:hidden"
                  to={`/establishments/${establishment.id}/sources/survey`}
                >
                  {t("Open full profile")}
                </Link>
              }
            >
              {survey.isPending ? (
                <AppLoader label={t("Loading Survey details…")} className="py-8" />
              ) : survey.error ? (
                <AppErrorState
                  message={errorMessage(survey.error)}
                  onRetry={() => survey.refetch()}
                />
              ) : survey.data ? (
                <SourceDetails data={survey.data} stacked showLocationMap={false} />
              ) : null}
            </PageSection>
          ) : null}
        </TabsContent>

        <TabsContent value="checklists" className="space-y-6">

          <PageSection
            title={t("Checklist submissions")}
            description={t(
              "Every checklist this establishment has submissions for, with its most recent forms.",
            )}
            actions={
              <Can permission="inspections.deploy_checklist">
                <Button
                  variant="outline"
                  className="print:hidden"
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
            {groups.isPending ? (
              <AppLoader label={t("Loading…")} className="py-8" />
            ) : groups.error ? (
              <AppErrorState
                message={errorMessage(groups.error)}
                onRetry={() => groups.refetch()}
              />
            ) : (groups.data ?? []).length === 0 ? (
              <p className="text-muted-foreground py-8 text-center">
                {t("No Collection submissions yet. Press Sync submissions to pull new forms.")}
              </p>
            ) : (
              <div className="space-y-8">
                {(groups.data ?? []).map((group) => (
                  <section key={group.checklist_id} className="space-y-3">
                    <div className="flex flex-wrap items-end justify-between gap-2">
                      <div>
                        <h3 className="text-base font-semibold">
                          <Link
                            className="entity-link"
                            to={`/checklists/${group.checklist_id}`}
                          >
                            {group.checklist_name}
                          </Link>
                        </h3>
                        <p className="text-muted-foreground text-sm">
                          {t("{{count}} submissions", { count: group.count })}
                          {group.last_submitted_at ? (
                            <>
                              {" · "}
                              {t("Last submitted")}{" "}
                              <SystemDateTime value={group.last_submitted_at} includeTime />
                            </>
                          ) : null}
                        </p>
                      </div>
                      <Link
                        className="text-link"
                        to={`/submissions?checklist_id=${group.checklist_id}&establishment_id=${establishment.id}`}
                      >
                        {t("View all submissions")}
                      </Link>
                    </div>
                    <AppTable className="min-w-[520px]">
                      <TableHeader>
                        <TableRow>
                          <TableHead>{t("Submitted")}</TableHead>
                          <TableHead>{t("Score")}</TableHead>
                          <TableHead className="print:hidden">{t("Action")}</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {group.submissions.map((submission) => (
                          <TableRow key={submission.id}>
                            <TableCell>
                              <Link
                                className="entity-link"
                                to={`/submissions/${submission.id}`}
                              >
                                <SystemDateTime
                                  value={submission.submitted_at}
                                  includeTime
                                />
                              </Link>
                            </TableCell>
                            <TableCell>
                              <ScoreBadge percent={submission.scores?.percent} />
                            </TableCell>
                            <TableCell className="print:hidden">
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
                      </TableBody>
                    </AppTable>
                  </section>
                ))}
              </div>
            )}
          </PageSection>
        </TabsContent>
      </Tabs>

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
        open={identityOpen}
        onOpenChange={setIdentityOpen}
        title={t("Registry identity")}
        description={t(
          "Choose which registry owns this establishment's identity, or keep it in Mandi.",
        )}
        size="lg"
      >
        <RegistryOwnership establishment={establishment} />
      </AppDialog>

      <AppDialog
        open={mappingsOpen}
        onOpenChange={setMappingsOpen}
        title={t("System mappings")}
        description={t(
          "Connect this establishment to a record in another system. The system and external ID are stored on the establishment.",
        )}
        size="xl"
        contentClassName="max-h-[90vh] overflow-y-auto"
      >
        <EstablishmentMappings establishment={establishment} embedded />
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
