import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { PageSection } from "@/components/PageSection";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import { AppSelect } from "@/components/public/AppSelect";
import AppTable from "@/components/public/AppTable";
import AppTitle from "@/components/public/AppTitle";
import { SystemDateTime } from "@/components/public/SystemDateTime";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SimpleDatePicker } from "@/components/ui/custom/CustomDatePickerType";
import { useEstablishmentKinds } from "@/features/establishments/registry";
import { useApiQuery } from "@/features/shared/api";
import { validDateRange } from "@/features/shared/dates";
import { choiceLabel, pageCount } from "@/features/shared/labels";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useListParams } from "@/hooks/useListParams";
import { useSystemCalendar } from "@/hooks/use-system-calendar";
import { useTablePageSize } from "@/hooks/useTablePageSize";
import { api, errorMessage, type Checklist, type Page, type Submission } from "@/lib/api";

function scoreVariant(percent: number | null | undefined) {
  if (percent === null || percent === undefined) return "secondary" as const;
  if (percent >= 85) return "default" as const;
  if (percent >= 60) return "secondary" as const;
  return "destructive" as const;
}

export default function SubmissionsPage() {
  const { t } = useTranslation();
  const kinds = useEstablishmentKinds();
  const calendar = useSystemCalendar();
  const { params, update, page, setPage } = useListParams();
  const [pageSize, setPageSize] = useTablePageSize();
  const search = params.get("search") ?? "";
  const debouncedSearch = useDebouncedValue(search, 300);
  const kind = params.get("establishment_kind") ?? "";
  const establishmentId = params.get("establishment_id") ?? "";
  const checklistId = params.get("checklist_id") ?? "";
  const dateFrom = params.get("date_from") ?? "";
  const dateTo = params.get("date_to") ?? "";
  const datesValid = validDateRange(dateFrom, dateTo);

  const establishments = useQuery({
    queryKey: ["submission-establishment-choices", kind],
    enabled: Boolean(kind),
    queryFn: async () =>
      (
        await api.get<{ name: string; label: string }[]>(
          "/integrations/establishment-choices/",
          { params: { kind } },
        )
      ).data,
  });
  const checklists = useApiQuery<Checklist[]>(["checklists"], "/checklists/");
  const submissions = useApiQuery<Page<Submission>>(
    ["submissions"],
    "/submissions/",
    {
      search: debouncedSearch,
      establishment_kind: kind,
      establishment_id: establishmentId,
      checklist_id: checklistId,
      date_from: dateFrom,
      date_to: datesValid ? dateTo : "",
      page,
      page_size: pageSize,
    },
    { enabled: datesValid },
  );

  const rows = submissions.data?.results ?? [];
  const count = submissions.data?.count ?? 0;
  const filtersActive = Boolean(
    search || kind || establishmentId || checklistId || dateFrom || dateTo,
  );

  return (
    <div className="space-y-6">
      <AppTitle
        title={t("Submissions")}
        description={t("All collected forms. Filter by establishment type, establishment, or checklist.")}
      />

      <PageSection>
        <div className="space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="relative min-w-0 flex-1 basis-60">
              <Search className="text-muted-foreground absolute start-3 top-1/2 size-4 -translate-y-1/2" />
              <Input
                className="ps-9"
                value={search}
                onChange={(event) => update({ search: event.target.value }, true, true)}
                aria-label={t("Search submissions")}
                placeholder={t("Search by establishment or submission id")}
              />
            </div>
            <AppSelect
              label={t("Establishment type")}
              value={kind || "__all__"}
              onChange={(value) => {
                update({
                  establishment_kind: value === "__all__" ? "" : String(value),
                  establishment_id: "",
                });
              }}
              options={[
                { value: "__all__", label: t("All types") },
                ...kinds.map((value) => ({ value, label: t(choiceLabel(value)) })),
              ]}
            />
            <AppSelect
              label={t("Establishment")}
              value={establishmentId || "__all__"}
              onChange={(value) => {
                update({ establishment_id: value === "__all__" ? "" : String(value) });
              }}
              options={[
                { value: "__all__", label: kind ? t("All establishments") : t("Select a type first") },
                ...(establishments.data ?? []).map((item) => ({
                  value: item.name,
                  label: item.label,
                })),
              ]}
            />
            <AppSelect
              label={t("Checklist")}
              value={checklistId || "__all__"}
              onChange={(value) => {
                update({ checklist_id: value === "__all__" ? "" : String(value) });
              }}
              options={[
                { value: "__all__", label: t("All checklists") },
                ...(checklists.data ?? []).map((item) => ({
                  value: String(item.id),
                  label: item.name,
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
                onClick={() =>
                  update({
                    search: "",
                    establishment_kind: "",
                    establishment_id: "",
                    checklist_id: "",
                    date_from: "",
                    date_to: "",
                  })
                }
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
              className="min-w-[760px]"
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
                  <TableHead>{t("Type")}</TableHead>
                  <TableHead>{t("Checklist")}</TableHead>
                  <TableHead>{t("Form version")}</TableHead>
                  <TableHead>{t("Score")}</TableHead>
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
                    <TableCell>
                      {submission.establishment_kind
                        ? t(choiceLabel(submission.establishment_kind))
                        : "—"}
                    </TableCell>
                    <TableCell>{submission.checklist_name ?? "—"}</TableCell>
                    <TableCell>
                      {submission.form_version ? (
                        <code>{submission.form_version}</code>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
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
                  </TableRow>
                ))}
                {rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-muted-foreground py-8 text-center">
                      {filtersActive
                        ? t("No submissions match these filters.")
                        : t("No submissions yet. Press Sync submissions to pull new forms.")}
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
