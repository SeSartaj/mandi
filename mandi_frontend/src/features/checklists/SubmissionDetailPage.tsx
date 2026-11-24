import { ArrowLeft, ExternalLink } from "lucide-react";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { PageSection } from "@/components/PageSection";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import AppTable from "@/components/public/AppTable";
import AppTitle from "@/components/public/AppTitle";
import { SystemDateTime } from "@/components/public/SystemDateTime";
import { Badge } from "@/components/ui/badge";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SubmissionMedia } from "@/features/checklists/SubmissionMedia";
import { useApiQuery } from "@/features/shared/api";
import type { SubmissionAnswer, Submission } from "@/lib/api";
import { errorMessage } from "@/lib/api";

function scoreVariant(percent: number | null | undefined) {
  if (percent === null || percent === undefined) return "secondary" as const;
  if (percent >= 85) return "default" as const;
  if (percent >= 60) return "secondary" as const;
  return "destructive" as const;
}

function geoHref(answer: SubmissionAnswer): string | null {
  if (answer.type !== "geopoint") return null;
  const source = Array.isArray(answer.value)
    ? `${answer.value[0]} ${answer.value[1]}`
    : answer.display;
  const [lat, lon] = source.split(",").length > 1 ? source.split(",") : source.split(" ");
  const latitude = Number(String(lat).trim());
  const longitude = Number(String(lon).trim());
  if (
    !String(lat ?? "").trim() ||
    !String(lon ?? "").trim() ||
    !Number.isFinite(latitude) ||
    !Number.isFinite(longitude) ||
    Math.abs(latitude) > 90 ||
    Math.abs(longitude) > 180
  )
    return null;
  return `https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=16/${latitude}/${longitude}`;
}

type AnswerGroup = { label: string; answers: SubmissionAnswer[] };

function groupAnswers(answers: SubmissionAnswer[]): AnswerGroup[] {
  const groups: AnswerGroup[] = [];
  for (const answer of answers) {
    const label = answer.group || "";
    const current = groups[groups.length - 1];
    if (!current || current.label !== label) {
      groups.push({ label, answers: [answer] });
    } else {
      current.answers.push(answer);
    }
  }
  return groups;
}

export default function SubmissionDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const submission = useApiQuery<Submission>(
    ["submission", id],
    `/collection-submissions/${id}/`,
  );

  const answers = useMemo(() => submission.data?.answers ?? [], [submission.data?.answers]);
  const groups = useMemo(() => groupAnswers(answers), [answers]);
  const attachments = submission.data?.attachments ?? [];
  const linkedIndexes = useMemo(
    () => new Set(answers.flatMap((answer) => (answer.media ?? []).map((media) => media.index))),
    [answers],
  );
  const unlinked = attachments.filter((attachment) => !linkedIndexes.has(attachment.index));

  if (submission.isPending) return <AppLoader label={t("Loading…")} className="py-16" />;
  if (submission.error)
    return (
      <AppErrorState
        message={errorMessage(submission.error)}
        onRetry={() => submission.refetch()}
      />
    );

  const data = submission.data!;
  const percent = data.scores?.percent;

  return (
    <div className="space-y-6">
      <Link
        className="back-link"
        to={data.checklist_id ? `/checklists/${data.checklist_id}` : "/checklists"}
      >
        <ArrowLeft size={16} />
        {data.checklist_name ?? t("Checklists")}
      </Link>

      <AppTitle
        title={data.establishment_name ?? t("Submission")}
        description={
          <span className="inline-flex flex-wrap items-center gap-2">
            <span>
              <SystemDateTime value={data.submitted_at} includeTime />
            </span>
            <span>·</span>
            {data.establishment_id ? (
              <Link className="text-link" to={`/establishments/${data.establishment_id}`}>
                {t("Establishment")}
              </Link>
            ) : (
              <span>{t("No establishment")}</span>
            )}
            {data.form_version ? (
              <>
                <span>·</span>
                <span>
                  {t("Form version")} <code>{data.form_version}</code>
                </span>
              </>
            ) : null}
            {percent !== null && percent !== undefined ? (
              <Badge variant={scoreVariant(percent)}>
                {percent}%{data.scores?.max ? ` · ${data.scores.score}/${data.scores.max}` : ""}
              </Badge>
            ) : (
              <Badge variant="secondary">{t("No score")}</Badge>
            )}
          </span>
        }
        others={
          data.form_url ? (
            <a className="text-link" href={data.form_url} target="_blank" rel="noreferrer">
              <ExternalLink className="size-4" />
              {t("Open collection service")}
            </a>
          ) : null
        }
      />

      {(data.scores?.sections ?? []).length > 0 ? (
        <PageSection title={t("Section scores")}>
          <AppTable className="min-w-[480px]">
            <TableHeader>
              <TableRow>
                <TableHead>{t("Section")}</TableHead>
                <TableHead>{t("Score")}</TableHead>
                <TableHead>{t("Percentage")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data.scores?.sections ?? []).map((section) => (
                <TableRow key={section.key}>
                  <TableCell className="whitespace-normal">{section.label}</TableCell>
                  <TableCell>
                    {section.score}
                    {section.max ? ` / ${section.max}` : ""}
                  </TableCell>
                  <TableCell>{section.percent === null ? "—" : `${section.percent}%`}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </AppTable>
        </PageSection>
      ) : null}

      <PageSection title={t("Answers")} description={t("Every field recorded in this submission.")}>
        {answers.length === 0 ? (
          <p className="muted">{t("No answers were recorded.")}</p>
        ) : (
          <div className="space-y-8">
            {groups.map((group, index) => (
              <section key={`${group.label}-${index}`} className="space-y-2">
                {group.label ? <h3 className="text-base font-medium">{group.label}</h3> : null}
                <dl className="divide-border divide-y">
                  {group.answers.map((answer) => {
                    const geo = geoHref(answer);
                    return (
                      <div
                        key={answer.name}
                        className="grid gap-2 py-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] sm:gap-6"
                      >
                        <dt className="text-sm">{answer.label}</dt>
                        <dd className="space-y-2 text-sm break-words">
                          {(answer.media ?? []).length > 0 ? (
                            answer.media.map((media) => (
                              <SubmissionMedia
                                key={media.index}
                                url={media.url}
                                kind={media.kind}
                                filename={media.filename}
                                mimetype={media.mimetype}
                              />
                            ))
                          ) : geo ? (
                            <a className="text-link" target="_blank" rel="noreferrer" href={geo}>
                              {answer.display}
                            </a>
                          ) : (
                            answer.display
                          )}
                        </dd>
                      </div>
                    );
                  })}
                </dl>
              </section>
            ))}
          </div>
        )}
      </PageSection>

      {unlinked.length > 0 ? (
        <PageSection title={t("Files")} description={t("Uploads not attached to a question.")}>
          <div className="grid gap-3 sm:grid-cols-2">
            {unlinked.map((attachment) => (
              <div key={attachment.index} className="space-y-1">
                <p className="text-sm">{attachment.basename}</p>
                <SubmissionMedia
                  url={attachment.url}
                  kind={attachment.kind}
                  filename={attachment.basename}
                  mimetype={attachment.mimetype}
                />
              </div>
            ))}
          </div>
        </PageSection>
      ) : null}

      <PageSection title={t("Raw submission data")}>
        <details>
          <summary className="cursor-pointer text-sm font-medium">{t("Show raw JSON")}</summary>
          <pre
            className="bg-muted mt-2 max-h-[40vh] overflow-auto rounded-md p-4 text-xs"
            dir="ltr"
          >
            {JSON.stringify(data.data, null, 2)}
          </pre>
        </details>
      </PageSection>
    </div>
  );
}
