import { useState } from "react";
import { Plus, Search } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { Can } from "@/components/Can";
import { PageSection } from "@/components/PageSection";
import { AppDialog } from "@/components/public/AppDialog";
import { AppSelect } from "@/components/public/AppSelect";
import AppTable from "@/components/public/AppTable";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import EstablishmentForm from "@/features/establishments/EstablishmentForm";
import { useApiQuery } from "@/features/shared/api";
import { choiceLabel, establishmentKinds, pageCount } from "@/features/shared/labels";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useTablePageSize } from "@/hooks/useTablePageSize";
import type { Establishment, Page } from "@/lib/api";
import { errorMessage } from "@/lib/api";

export default function EstablishmentsPage() {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const [kind, setKind] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useTablePageSize();
  const [open, setOpen] = useState(false);
  const data = useApiQuery<Page<Establishment>>(["establishments"], "/establishments/", {
    search: debouncedSearch,
    kind,
    page,
    page_size: pageSize,
  });

  const rows = data.data?.results ?? [];
  const count = data.data?.count ?? 0;
  const totalPages = pageCount(count, pageSize);

  return (
    <div className="space-y-6">
      <PageSection
        title={t("Establishments")}
        description={t("Monitoring & inspection registry")}
        actions={
          <Can permission="establishments.add_establishment">
            <Button onClick={() => setOpen(true)}>
              <Plus />
              {t("Add establishment")}
            </Button>
          </Can>
        }
      >
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative min-w-60 flex-1">
              <Search className="text-muted-foreground absolute start-3 top-1/2 size-4 -translate-y-1/2" />
              <Input
                className="ps-9"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(1);
                }}
                aria-label={t("Search establishments")}
                placeholder={t("Search establishments")}
              />
            </div>
            <AppSelect
              label={t("All types")}
              value={kind || "__all__"}
              onChange={(value) => {
                setKind(value === "__all__" ? "" : String(value));
                setPage(1);
              }}
              options={[
                { value: "__all__", label: t("All types") },
                ...establishmentKinds.map((value) => ({
                  value,
                  label: t(choiceLabel(value)),
                })),
              ]}
            />
          </div>

          {data.isPending ? (
            <AppLoader label={t("Loading…")} className="py-10" />
          ) : data.error ? (
            <AppErrorState message={errorMessage(data.error)} onRetry={() => data.refetch()} />
          ) : (
            <AppTable
              className="min-w-[760px]"
              pagination={{
                page,
                pageSize,
                totalPages,
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
                  <TableHead>{t("Name")}</TableHead>
                  <TableHead>{t("Type")}</TableHead>
                  <TableHead>{t("Province")}</TableHead>
                  <TableHead>{t("District")}</TableHead>
                  <TableHead>{t("Details")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((establishment) => (
                  <TableRow key={establishment.id}>
                    <TableCell>
                      <Link className="entity-link" to={`/establishments/${establishment.id}`}>
                        {establishment.name}
                      </Link>
                    </TableCell>
                    <TableCell>{t(choiceLabel(establishment.kind))}</TableCell>
                    <TableCell>{establishment.province}</TableCell>
                    <TableCell>{establishment.district || "—"}</TableCell>
                    <TableCell>
                      <Link to={`/establishments/${establishment.id}`} className="text-link">
                        {t("View")}
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
                {rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-muted-foreground py-8 text-center">
                      {t("No records found.")}
                    </TableCell>
                  </TableRow>
                ) : null}
              </TableBody>
            </AppTable>
          )}
        </div>
      </PageSection>

      <AppDialog
        open={open}
        onOpenChange={setOpen}
        title={t("Add establishment")}
        size="lg"
        contentClassName="max-h-[90vh] overflow-y-auto"
      >
        <EstablishmentForm onClose={() => setOpen(false)} />
      </AppDialog>
    </div>
  );
}
