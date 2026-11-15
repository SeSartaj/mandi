import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink, RefreshCw, Search } from "lucide-react";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { Can } from "@/components/Can";
import { PageSection } from "@/components/PageSection";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import { AppSelect } from "@/components/public/AppSelect";
import AppTable from "@/components/public/AppTable";
import AppTitle from "@/components/public/AppTitle";
import { SystemDateTime } from "@/components/public/SystemDateTime";
import { DeploymentBadge } from "./DeploymentBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { choiceLabel, pageCount } from "@/features/shared/labels";
import { useApiQuery } from "@/features/shared/api";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useListParams } from "@/hooks/useListParams";
import { SimpleDatePicker } from "@/components/ui/custom/CustomDatePickerType";
import { useSystemCalendar } from "@/hooks/use-system-calendar";
import { validDateRange } from "@/features/inspections/filter-state";
import { useTablePageSize } from "@/hooks/useTablePageSize";
import type { Checklist, KoboSubmission, Page } from "@/lib/api";
import { api, errorMessage } from "@/lib/api";
import { useSession } from "@/lib/session";

function scoreVariant(percent: number | null | undefined) {
  if (percent === null || percent === undefined) return "secondary" as const;
  if (percent >= 85) return "default" as const;
  if (percent >= 60) return "secondary" as const;
  return "destructive" as const;
}

export default function ChecklistDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const client = useQueryClient();
  const session = useSession();
  const canSync = (session?.permissions ?? []).includes("inspections.add_inspection");
  const { params, update, page, setPage } = useListParams();
  const calendar = useSystemCalendar();
  const search = params.get("search") ?? "";
  const debouncedSearch = useDebouncedValue(search, 300);
  const establishmentId = params.get("establishment_id") ?? "";
  const dateFrom = params.get("date_from") ?? "";
  const dateTo = params.get("date_to") ?? "";
  const datesValid = validDateRange(dateFrom, dateTo);
  const [pageSize, setPageSize] = useTablePageSize();

  const checklist = useApiQuery<Checklist>(["checklist", id], `/checklists/${id}/`);
  const kind = checklist.data?.establishment_kind;
  const establishments = useQuery({
    queryKey: ["establishment-choices", kind],
    enabled: Boolean(kind) && session.permissions.includes("establishments.view_establishment"),
    queryFn: async () =>
      (
        await api.get<{ name: string; label: string }[]>("/integrations/establishment-choices/", {
          params: { kind },
        })
      ).data,
  });
  const submissions = useApiQuery<Page<KoboSubmission>>(
    ["checklist-submissions", id],
    `/checklists/${id}/submissions/`,
    {
      search: debouncedSearch,
      establishment_id: establishmentId,
      date_from: dateFrom,
      date_to: datesValid ? dateTo : "",
      page,
      page_size: pageSize,
    },
    { enabled: datesValid },
  );

  const sync = useMutation({
    mutationFn: async () =>
      (await api.post("/integrations/kobo/sync/", { checklist_id: Number(id) })).data,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["checklist-submissions", id] });
      client.invalidateQueries({ queryKey: ["checklist", id] });
    },
  });
  const runSync = sync.mutate;
  const autoSynced = useRef<string | undefined>(undefined);
  const deployed = checklist.data?.kobo_deployment_status === "deployed";

  useEffect(() => {
    if (autoSynced.current === id || !canSync || !deployed) return;
    autoSynced.current = id;
    runSync();
  }, [canSync, deployed, runSync, id]);

  if (checklist.isPending) return <AppLoader label={t("Loading…")} className="py-16" />;
  if (checklist.error)
    return (
      <AppErrorState message={errorMessage(checklist.error)} onRetry={() => checklist.refetch()} />
    );

  const data = checklist.data!;
  const rows = submissions.data?.results ?? [];
  const count = submissions.data?.count ?? 0;
  const filtersActive = Boolean(search || establishmentId || dateFrom || dateTo);

  return (
    <div className="space-y-6">
      <Link className="back-link" to="/checklists">
        <ArrowLeft size={16} />
        {t("Checklists")}
      </Link>

      <AppTitle
        title={data.name}
        description={
          <span className="inline-flex flex-wrap items-center gap-2">
            <code>{data.code}</code>
            <span>·</span>
            <span>{data.version}</span>
            <span>·</span>
            <span>{t(choiceLabel(data.establishment_kind))}</span>
            <DeploymentBadge status={data.kobo_deployment_status} />
          </span>
        }
        others={
          <div className="inline-actions">
            {data.kobo_project_url ? (
              <a
                className="text-link"
                href={data.kobo_project_url}
                target="_blank"
                rel="noreferrer"
              >
                <ExternalLink className="size-4" />
                {t("Open in KoBo")}
              </a>
            ) : null}
            <Can permission="inspections.add_inspection">
              <Button
                variant="outline"
                disabled={sync.isPending || !data.kobo_asset_uid}
                onClick={() => runSync()}
              >
                <RefreshCw />
                {sync.isPending ? t("Syncing…") : t("Sync from KoBo")}
              </Button>
            </Can>
          </div>
        }
      />

      {sync.error ? (
        <div role="alert" className="error-box">
          {errorMessage(sync.error)}
        </div>
      ) : null}

      <PageSection
        title={t("Submissions")}
        description={t("Every KoBo submission received for this checklist.")}
      >
        <div className="space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="relative min-w-0 flex-1 basis-60">
              <Search className="text-muted-foreground absolute start-3 top-1/2 size-4 -translate-y-1/2" />
              <Input
                className="ps-9"
                value={search}
                onChange={(event) => {
                  update({ search: event.target.value }, true, true);
                }}
                aria-label={t("Search submissions")}
                placeholder={t("Search by establishment or submission id")}
              />
            </div>
            <AppSelect
              label={t("All establishments")}
              value={establishmentId || "__all__"}
              onChange={(value) => {
                update({ establishment_id: value === "__all__" ? "" : String(value) });
              }}
              options={[
                { value: "__all__", label: t("All establishments") },
                ...(establishments.data ?? []).map((item) => ({
                  value: item.name,
                  label: item.label,
                })),
              ]}
            />
            <SimpleDatePicker
              label={t("From date")}
              value={dateFrom}
              initialCalendar={calendar}
              saveInCalendar="miladi"
              onChange={(value) => update({ date_from: value })}
              containerClassName="w-full sm:w-44"
            />
            <SimpleDatePicker
              label={t("To date")}
              value={dateTo}
              initialCalendar={calendar}
              saveInCalendar="miladi"
              onChange={(value) => update({ date_to: value })}
              error={datesValid ? undefined : t("End date must be on or after start date.")}
              containerClassName="w-full sm:w-44"
            />
            {filtersActive ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  update({ search: "", establishment_id: "", date_from: "", date_to: "" });
                }}
              >
                {t("Clear filters")}
              </Button>
            ) : null}
          </div>

          {!datesValid ? (
            <div role="alert" className="error-box">
              {t("End date must be on or after start date.")}
            </div>
          ) : submissions.isPending ? (
            <AppLoader label={t("Loading…")} className="py-10" />
          ) : submissions.error ? (
            <AppErrorState
              message={errorMessage(submissions.error)}
              onRetry={() => submissions.refetch()}
            />
          ) : (
            <AppTable
              className="min-w-[560px]"
              pagination={{
                page,
                pageSize,
                totalPages: pageCount(count, pageSize),
                totalItems: count,
                onPageChange: setPage,
                onPageSizeChange: (size) => {
                  setPageSize(size);
                  setPage(1);
                },
              }}
            >
              <TableHeader>
                <TableRow>
                  <TableHead>{t("Submitted")}</TableHead>
                  <TableHead>{t("Establishment")}</TableHead>
                  <TableHead>{t("Score")}</TableHead>
                  <TableHead>{t("Files")}</TableHead>
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
                      <Link
                        className="entity-link"
                        to={`/establishments/${submission.establishment_id}`}
                      >
                        {submission.establishment_name ?? "—"}
                      </Link>
                    </TableCell>
                    <TableCell>
                      {submission.scores?.percent === null ||
                      submission.scores?.percent === undefined ? (
                        <span className="text-muted-foreground">{t("No score")}</span>
                      ) : (
                        <Badge variant={scoreVariant(submission.scores.percent)}>
                          {submission.scores.percent}%
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>{submission.attachments?.length ?? 0}</TableCell>
                  </TableRow>
                ))}
                {rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-muted-foreground py-8 text-center">
                      {filtersActive
                        ? t("No submissions match these filters.")
                        : t("No submissions yet. Press Sync from KoBo to pull new forms.")}
                    </TableCell>
                  </TableRow>
                ) : null}
              </TableBody>
            </AppTable>
          )}
        </div>
      </PageSection>
    </div>
  );
}
