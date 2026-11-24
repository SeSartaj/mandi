import RegistrySyncStatus from "./RegistrySyncStatus";
import RegistryImport from "./RegistryImport";
import {
  useEstablishmentKinds,
  useLocationName,
  useLocations,
} from "@/features/establishments/registry";
import { CreateButton } from "@/components/public/ActionButton";
import { useMemo, useState } from "react";
import { ChevronDown, Search, SlidersHorizontal, Tags } from "lucide-react";
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
import EstablishmentTypesDialog from "@/features/establishments/EstablishmentTypesDialog";
import { useApiQuery } from "@/features/shared/api";
import { choiceLabel, pageCount } from "@/features/shared/labels";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useListParams } from "@/hooks/useListParams";
import { useTablePageSize } from "@/hooks/useTablePageSize";
import type { Establishment, Page } from "@/lib/api";
import { errorMessage } from "@/lib/api";

export default function EstablishmentsPage() {
  const { t } = useTranslation();
  const establishmentKinds = useEstablishmentKinds();
  const locationName = useLocationName();
  const { provinces, districts } = useLocations();
  const { params, update, page, setPage } = useListParams();
  const search = params.get("search") ?? "";
  const debouncedSearch = useDebouncedValue(search, 300);
  const kind = params.get("kind") ?? "";
  const province = params.get("province") ?? "";
  const district = params.get("district") ?? "";
  const [advanced, setAdvanced] = useState(Boolean(province || district));
  const [pageSize, setPageSize] = useTablePageSize();
  const [open, setOpen] = useState(false);
  const [typesOpen, setTypesOpen] = useState(false);
  const data = useApiQuery<Page<Establishment>>(["establishments"], "/establishments/", {
    search: debouncedSearch,
    kind,
    province,
    district,
    page,
    page_size: pageSize,
  });

  const districtOptions = useMemo(
    () => districts.filter((item) => !province || String(item.province_id) === province),
    [districts, province],
  );
  const advancedCount = [province, district].filter(Boolean).length;
  const hasFilters = Boolean(search || kind || province || district);

  const rows = data.data?.results ?? [];
  const count = data.data?.count ?? 0;
  const totalPages = pageCount(count, pageSize);

  return (
    <div className="space-y-6">
      <RegistrySyncStatus />
      <PageSection
        headingLevel={1}
        title={kind ? `${t(choiceLabel(kind))} · ${t("Establishments")}` : t("Establishments")}
        description={t("Monitoring & inspection registry")}
        actions={
          <div className="flex flex-wrap gap-2">
            <Can permission="establishments.change_establishment">
              <Button variant="outline" onClick={() => setTypesOpen(true)}>
                <Tags />
                {t("Establishment types")}
              </Button>
            </Can>
            <Can permission="establishments.add_establishment">
              <RegistryImport />
              <CreateButton onClick={() => setOpen(true)} label={t("Add establishment")} />
            </Can>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative min-w-0 flex-1 basis-60">
              <Search className="text-muted-foreground absolute start-3 top-1/2 size-4 -translate-y-1/2" />
              <Input
                className="ps-9"
                value={search}
                onChange={(event) => {
                  update({ search: event.target.value }, true, true);
                }}
                aria-label={t("Search establishments")}
                placeholder={t("Search establishments")}
              />
            </div>
            <AppSelect
              label={t("All types")}
              value={kind || "__all__"}
              onChange={(value) => {
                update({ kind: value === "__all__" ? "" : String(value) });
              }}
              options={[
                { value: "__all__", label: t("All types") },
                ...establishmentKinds.map((value) => ({
                  value,
                  label: t(choiceLabel(value)),
                })),
              ]}
            />
            <Button
              variant="outline"
              aria-expanded={advanced}
              aria-controls="establishment-advanced-filters"
              onClick={() => setAdvanced((value) => !value)}
            >
              <SlidersHorizontal />
              {t("Advanced filters")}
              {advancedCount ? ` (${advancedCount})` : null}
              <ChevronDown
                className={advanced ? "size-4 rotate-180 transition-transform" : "size-4 transition-transform"}
              />
            </Button>
            {hasFilters && (
              <Button
                variant="ghost"
                onClick={() => update({ search: "", kind: "", province: "", district: "" })}
              >
                {t("Clear filters")}
              </Button>
            )}
          </div>

          {advanced && (
            <div
              id="establishment-advanced-filters"
              className="bg-muted/20 grid gap-4 rounded-lg border p-4 sm:grid-cols-2 lg:grid-cols-3"
            >
              <div className="space-y-1.5">
                <span className="text-muted-foreground block text-xs font-medium">
                  {t("Province")}
                </span>
                <AppSelect
                  label={t("All provinces")}
                  className="w-full"
                  value={province || "__all__"}
                  onChange={(value) =>
                    update({ province: value === "__all__" ? "" : String(value), district: "" })
                  }
                  options={[
                    { value: "__all__", label: t("All provinces") },
                    ...provinces.map((item) => ({
                      value: String(item.id),
                      label: locationName(item.name, item.name_local),
                    })),
                  ]}
                />
              </div>
              <div className="space-y-1.5">
                <span className="text-muted-foreground block text-xs font-medium">
                  {t("District")}
                </span>
                <AppSelect
                  label={t("All districts")}
                  className="w-full"
                  value={district || "__all__"}
                  onChange={(value) =>
                    update({ district: value === "__all__" ? "" : String(value) })
                  }
                  options={[
                    { value: "__all__", label: t("All districts") },
                    ...districtOptions.map((item) => ({
                      value: String(item.id),
                      label: locationName(item.name, item.name_local),
                    })),
                  ]}
                />
              </div>
            </div>
          )}

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
                    <TableCell>
                      {locationName(
                        establishment.province_name,
                        establishment.province_name_local,
                      ) || "—"}
                    </TableCell>
                    <TableCell>
                      {locationName(
                        establishment.district_name,
                        establishment.district_name_local,
                      ) || "—"}
                    </TableCell>
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

      <EstablishmentTypesDialog open={typesOpen} onOpenChange={setTypesOpen} />
    </div>
  );
}
