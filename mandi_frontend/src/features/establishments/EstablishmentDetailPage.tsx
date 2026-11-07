import { ArrowLeft } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { Can } from "@/components/Can";
import { PageSection } from "@/components/PageSection";
import { AppDialog } from "@/components/public/AppDialog";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import AppTitle from "@/components/public/AppTitle";
import { Button } from "@/components/ui/button";
import EstablishmentForm from "@/features/establishments/EstablishmentForm";
import SourcePanel from "@/features/establishments/SourcePanel";
import InspectionTable from "@/features/inspections/InspectionTable";
import { useApiQuery } from "@/features/shared/api";
import { choiceLabel, pageCount } from "@/features/shared/labels";
import { useTablePageSize } from "@/hooks/useTablePageSize";
import type { Establishment, Inspection, Page } from "@/lib/api";
import { errorMessage } from "@/lib/api";

export default function EstablishmentDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const [edit, setEdit] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useTablePageSize();
  const data = useApiQuery<Establishment>(["establishment", id], `/establishments/${id}/`);
  const visits = useApiQuery<Page<Inspection>>(["establishment-inspections", id], "/inspections/", {
    establishment_id: id,
    page,
    page_size: pageSize,
  });

  if (data.isPending) return <AppLoader label={t("Loading…")} className="py-16" />;
  if (data.error)
    return <AppErrorState message={errorMessage(data.error)} onRetry={() => data.refetch()} />;
  const establishment = data.data!;
  const visitCount = visits.data?.count ?? 0;

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
