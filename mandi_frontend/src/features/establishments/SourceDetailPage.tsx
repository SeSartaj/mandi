import { ArrowLeft, RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { PageSection } from "@/components/PageSection";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import AppTitle from "@/components/public/AppTitle";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useApiQuery } from "@/features/shared/api";
import { errorMessage } from "@/lib/api";

type SourceDetail = {
  name: string;
  application_id: string;
  category?: string;
  is_demo: boolean;
  sections: {
    title: string;
    fields: { label: string; value: string | number | boolean | null }[];
  }[];
};

export default function SourceDetailPage() {
  const { id, source } = useParams();
  const { t } = useTranslation();
  const query = useApiQuery<SourceDetail>(
    ["source-detail", id, source],
    `/establishments/${id}/sources/${source}/`,
  );
  if (query.isPending) return <AppLoader label={t("Loading…")} className="py-16" />;
  if (query.error)
    return <AppErrorState message={errorMessage(query.error)} onRetry={() => query.refetch()} />;
  const data = query.data!;
  return (
    <div className="space-y-6">
      <Link className="back-link" to={`/establishments/${id}`}>
        <ArrowLeft className="size-4" />
        {t("Establishment")}
      </Link>
      <AppTitle
        title={data.name}
        description={`${t(source === "licensing" ? "Licensing" : "Source details")} · ${data.application_id}`}
        others={
          <Button
            variant="outline"
            disabled={query.isFetching}
            onClick={() => void query.refetch()}
          >
            <RefreshCw className="size-4" />
            {t("Refresh")}
          </Button>
        }
      />
      <p className="text-muted-foreground text-sm">
        {t(
          "Details are loaded from the linked source. Mandi establishment details remain separate.",
        )}
      </p>
      {data.is_demo && <Badge variant="secondary">{t("Demonstration data")}</Badge>}
      <div className="grid items-start gap-6 lg:grid-cols-2">
        {data.sections.map((section) => (
          <PageSection key={section.title} title={t(section.title)}>
            <dl className="space-y-3">
              {section.fields.map((field) => (
                <div
                  key={field.label}
                  className="grid grid-cols-[minmax(0,1fr)_minmax(0,2fr)] gap-4 border-b pb-3 last:border-0 last:pb-0"
                >
                  <dt className="text-muted-foreground text-sm">{t(field.label)}</dt>
                  <dd className="min-w-0 text-sm font-medium break-words whitespace-pre-wrap">
                    {typeof field.value === "boolean"
                      ? t(field.value ? "Yes" : "No")
                      : (field.value ?? "—")}
                  </dd>
                </div>
              ))}
            </dl>
          </PageSection>
        ))}
      </div>
    </div>
  );
}
