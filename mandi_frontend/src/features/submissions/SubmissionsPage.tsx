import { useQuery } from "@tanstack/react-query";
import { Filter, Search, SlidersHorizontal } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
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
import { DataTableColumnSettings } from "@/components/ui/data-table-column-settings";
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
import {
  api,
  errorMessage,
  type Checklist,
  type ChecklistQuestion,
  type Page,
  type Submission,
} from "@/lib/api";

const BASE_COLUMNS = [
  "__submitted",
  "__establishment",
  "__kind",
  "__checklist",
  "__form_version",
  "__score",
] as const;

type BaseColumn = (typeof BASE_COLUMNS)[number];

function questionKey(name: string) {
  return `q:${name}`;
}

function answerName(key: string) {
  return key.startsWith("q:") ? key.slice(2) : "";
}

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
  const [visible, setVisible] = useState<string[]>([...BASE_COLUMNS]);
  const [answerFilters, setAnswerFilters] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const initializedFor = useRef<string | null>(null);

  const establishments = useQuery({
    queryKey: ["submission-establishment-choices", kind, checklistId],
    enabled: Boolean(kind || checklistId),
    queryFn: async () =>
      (
        await api.get<{ name: string; label: string }[]>(
          "/integrations/establishment-choices/",
          { params: { kind, checklist_id: checklistId || undefined } },
        )
      ).data,
  });
  const checklists = useApiQuery<Checklist[]>(["checklists"], "/checklists/");
  const questions = useApiQuery<ChecklistQuestion[]>(
    ["checklist-questions", checklistId],
    `/checklists/${checklistId}/questions/`,
    {},
    { enabled: Boolean(checklistId) },
  );
  const questionList = useMemo(() => questions.data ?? [], [questions.data]);
  const questionKeys = useMemo(
    () => questionList.map((question) => questionKey(question.name)),
    [questionList],
  );
  const storageKey = `mandi-submissions-columns-${checklistId || "all"}`;
  const answerParams = useMemo(() => {
    const entries: Record<string, string> = {};
    params.forEach((value, key) => {
      if (key.startsWith("answer.") && value) entries[key] = value;
    });
    return entries;
  }, [params]);

  useEffect(() => {
    const current = checklistId || "__all__";
    if (initializedFor.current === current) return;
    if (checklistId && questions.isPending) return;
    initializedFor.current = current;
    const allowed = new Set<string>([...BASE_COLUMNS, ...questionKeys]);
    const stored = localStorage.getItem(storageKey);
    let next: string[] | null = null;
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          next = parsed.filter(
            (key): key is string => typeof key === "string" && allowed.has(key),
          );
        }
      } catch {
        next = null;
      }
    }
    setVisible(next && next.length ? next : [...BASE_COLUMNS, ...questionKeys]);
  }, [checklistId, questionKeys, questions.isPending, storageKey]);

  useEffect(() => {
    if (initializedFor.current !== (checklistId || "__all__")) return;
    localStorage.setItem(storageKey, JSON.stringify(visible));
  }, [checklistId, storageKey, visible]);

  useEffect(() => {
    const next: Record<string, string> = {};
    for (const [key, value] of Object.entries(answerParams)) {
      next[key.slice("answer.".length)] = value;
    }
    setAnswerFilters(next);
  }, [answerParams]);

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
      ...answerParams,
      page,
      page_size: pageSize,
    },
    { enabled: datesValid },
  );

  const rows = submissions.data?.results ?? [];
  const count = submissions.data?.count ?? 0;
  const activeAnswerFilters = Object.keys(answerParams).length;
  const filtersActive = Boolean(
    search ||
      kind ||
      establishmentId ||
      checklistId ||
      dateFrom ||
      dateTo ||
      activeAnswerFilters,
  );

  const columnOptions = [
    { key: "__submitted", label: t("Submitted") },
    { key: "__establishment", label: t("Establishment") },
    { key: "__kind", label: t("Type") },
    { key: "__checklist", label: t("Checklist") },
    { key: "__form_version", label: t("Form version") },
    { key: "__score", label: t("Score") },
    ...questionList.map((question) => ({
      key: questionKey(question.name),
      label: question.label || question.name,
    })),
  ];
  const defaultColumns = [...BASE_COLUMNS, ...questionKeys];
  const columns = visible.filter((key) =>
    columnOptions.some((option) => option.key === key),
  );

  const applyAnswerFilters = () => {
    const values: Record<string, string> = {};
    for (const question of questionList) {
      values[`answer.${question.name}`] = answerFilters[question.name] ?? "";
    }
    update(values);
  };

  const clearAnswerFilters = () => {
    const values: Record<string, string> = {};
    for (const key of Object.keys(answerParams)) {
      values[key] = "";
    }
    setAnswerFilters({});
    update(values);
  };

  const questionValue = (submission: Submission, name: string) =>
    submission.answers?.find((answer) => answer.name === name)?.display ?? "—";

  const baseCell = (key: BaseColumn, submission: Submission) => {
    switch (key) {
      case "__submitted":
        return (
          <Link className="entity-link" to={`/submissions/${submission.id}`}>
            <SystemDateTime value={submission.submitted_at} includeTime />
          </Link>
        );
      case "__establishment":
        return submission.establishment_id ? (
          <Link className="entity-link" to={`/establishments/${submission.establishment_id}`}>
            {submission.establishment_name ?? "—"}
          </Link>
        ) : (
          <span className="text-muted-foreground">{t("No establishment")}</span>
        );
      case "__kind":
        return submission.establishment_kind
          ? t(choiceLabel(submission.establishment_kind))
          : "—";
      case "__checklist":
        return submission.checklist_name ?? "—";
      case "__form_version":
        return submission.form_version ? (
          <code>{submission.form_version}</code>
        ) : (
          <span className="text-muted-foreground">—</span>
        );
      case "__score":
        return submission.scores?.percent === null ||
          submission.scores?.percent === undefined ? (
          <span className="text-muted-foreground">{t("No score")}</span>
        ) : (
          <Badge variant={scoreVariant(submission.scores.percent)}>
            {submission.scores.percent}%
          </Badge>
        );
      default:
        return null;
    }
  };


  return (
    <div className="space-y-6">
      <AppTitle
        title={t("Submissions")}
        description={
          checklistId
            ? t(
                "Each question is a column. Choose columns, filter by answers, or narrow to one establishment.",
              )
            : t("All collected forms. Choose a checklist to show one column per question.")
        }
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
                {
                  value: "__all__",
                  label: kind || checklistId ? t("All establishments") : t("Select a type first"),
                },
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
                const next: Record<string, string> = {
                  checklist_id: value === "__all__" ? "" : String(value),
                  establishment_id: "",
                };
                for (const key of Object.keys(answerParams)) next[key] = "";
                update(next);
              }}
              options={[
                { value: "__all__", label: t("All checklists") },
                ...(checklists.data ?? []).map((item) => ({
                  value: String(item.id),
                  label: item.name,
                })),
              ]}
            />
            <Button
              variant="outline"
              aria-expanded={filtersOpen}
              onClick={() => setFiltersOpen((value) => !value)}
              disabled={!questionList.length}
            >
              <SlidersHorizontal />
              {t("Column filters")}
              {activeAnswerFilters ? ` (${activeAnswerFilters})` : null}
            </Button>
            <DataTableColumnSettings
              columns={columnOptions}
              visibleColumns={visible}
              onChange={setVisible}
              onReset={() => setVisible(defaultColumns)}
              labels={{
                button: t("Columns"),
                title: t("Choose columns"),
                reset: t("Show all columns"),
                moveUp: t("Move column up"),
                moveDown: t("Move column down"),
              }}
              idPrefix="submission-column"
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
                  const next: Record<string, string> = {
                    search: "",
                    establishment_kind: "",
                    establishment_id: "",
                    checklist_id: "",
                    date_from: "",
                    date_to: "",
                  };
                  for (const key of Object.keys(answerParams)) next[key] = "";
                  setAnswerFilters({});
                  update(next);
                }}
              >
                {t("Clear filters")}
              </Button>
            ) : null}
          </div>

          {filtersOpen && questionList.length ? (
            <div className="bg-muted/20 space-y-3 rounded-lg border p-4">
              <p className="text-muted-foreground text-sm">
                {t("Filter submissions by the answers in each column.")}
              </p>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {questionList.map((question) => (
                  <div key={question.name} className="space-y-1.5">
                    <label
                      className="block text-xs font-medium"
                      htmlFor={`answer-filter-${question.name}`}
                    >
                      {question.label || question.name}
                      {question.group ? (
                        <span className="text-muted-foreground"> · {question.group}</span>
                      ) : null}
                    </label>
                    <Input
                      id={`answer-filter-${question.name}`}
                      value={answerFilters[question.name] ?? ""}
                      onChange={(event) =>
                        setAnswerFilters((previous) => ({
                          ...previous,
                          [question.name]: event.target.value,
                        }))
                      }
                      onKeyDown={(event) => {
                        if (event.key === "Enter") applyAnswerFilters();
                      }}
                      placeholder={t("Filter by answer")}
                    />
                  </div>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" onClick={applyAnswerFilters}>
                  <Filter />
                  {t("Apply column filters")}
                </Button>
                <Button size="sm" variant="ghost" onClick={clearAnswerFilters}>
                  {t("Clear column filters")}
                </Button>
              </div>
            </div>
          ) : null}

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
              className={questionList.length ? "min-w-max" : "min-w-[760px]"}
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
                  {columns.map((key) => (
                    <TableHead key={key} className="whitespace-nowrap">
                      {columnOptions.find((option) => option.key === key)?.label ?? key}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((submission) => (
                  <TableRow key={submission.id}>
                    {columns.map((key) =>
                      key.startsWith("q:") ? (
                        <TableCell
                          key={key}
                          className="max-w-[240px] align-top break-words whitespace-normal"
                        >
                          {questionValue(submission, answerName(key))}
                        </TableCell>
                      ) : (
                        <TableCell key={key}>{baseCell(key as BaseColumn, submission)}</TableCell>
                      ),
                    )}
                  </TableRow>
                ))}
                {rows.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={Math.max(columns.length, 1)}
                      className="text-muted-foreground py-8 text-center"
                    >
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
