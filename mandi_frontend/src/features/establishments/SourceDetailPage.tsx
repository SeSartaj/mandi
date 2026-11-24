import SourceDetails, { type SourceDetail } from "./SourceDetails";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import AppTitle from "@/components/public/AppTitle";
import { PageSection } from "@/components/PageSection";
import { Button } from "@/components/ui/button";
import { useApiQuery } from "@/features/shared/api";
import { errorMessage } from "@/lib/api";

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
        description={t(source === "licensing" ? "Licensing" : "Source details")}
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
      <PageSection
        title={t("Source details")}
        description={t(
          "Details are loaded from the linked source. Mandi establishment details remain separate.",
        )}
      >
        <SourceDetails data={data} />
      </PageSection>
    </div>
  );
}
