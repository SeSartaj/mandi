import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link2, Plus, Unlink } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { Can } from "@/components/Can";
import { PageSection } from "@/components/PageSection";
import { AppDialog } from "@/components/public/AppDialog";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import { AppSelect } from "@/components/public/AppSelect";
import { SystemDateTime } from "@/components/public/SystemDateTime";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import type { Establishment, SourceLink } from "@/lib/api";
import { api, errorMessage } from "@/lib/api";
import { notify } from "@/lib/notify";
import { useRegistryCatalog } from "./registry";

type Candidate = {
  id: string;
  name: string;
  details: SourceLink["details"];
};

export default function EstablishmentMappings({
  establishment,
}: {
  establishment: Establishment;
}) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const catalog = useRegistryCatalog();
  const systems = catalog.data?.systems ?? [];
  const available = systems.filter((system) => system.searchable);
  const systemName = (code: string) =>
    systems.find((system) => system.code === code)?.name ?? code;

  const [open, setOpen] = useState(false);
  const [source, setSource] = useState("");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const [page, setPage] = useState(1);
  const [disconnecting, setDisconnecting] = useState<SourceLink | null>(null);

  const existing = establishment.source_links.find((link) => link.source === source);

  const candidates = useQuery({
    queryKey: ["mapping-search", source, establishment.kind, debouncedSearch, page],
    enabled: open && Boolean(source),
    queryFn: async ({ signal }) =>
      (
        await api.get<{ results: Candidate[]; has_next: boolean }>(`/sources/${source}/`, {
          params: { kind: establishment.kind, search: debouncedSearch, page },
          signal,
        })
      ).data,
  });

  const connect = useMutation({
    mutationFn: async (externalId: string) =>
      api.post(`/establishments/${establishment.id}/sources/${source}/`, {
        external_id: externalId,
      }),
    onSuccess: () => {
      notify.success(t("{{entity}} connected.", { entity: t("Source link") }));
      client.invalidateQueries({ queryKey: ["establishment", establishment.id] });
      client.invalidateQueries({ queryKey: ["registry"] });
      setOpen(false);
    },
    onError: (error) =>
      notify.error(t("Could not complete the action."), {
        description: errorMessage(error),
      }),
  });

  const disconnect = useMutation({
    mutationFn: async (link: SourceLink) =>
      api.delete(`/establishments/${establishment.id}/sources/${link.source}/`),
    onSuccess: () => {
      notify.success(t("{{entity}} disconnected.", { entity: t("Source link") }));
      client.invalidateQueries({ queryKey: ["establishment", establishment.id] });
      setDisconnecting(null);
    },
    onError: (error) =>
      notify.error(t("Could not complete the action."), {
        description: errorMessage(error),
      }),
  });

  const openDialog = () => {
    const first = available[0]?.code ?? "";
    setSource(first);
    setSearch("");
    setPage(1);
    connect.reset();
    setOpen(true);
  };

  return (
    <PageSection
      title={t("System mappings")}
      description={t(
        "Connect this establishment to a record in another system. The system and external ID are stored on the establishment.",
      )}
      actions={
        <Can permission="establishments.change_sourcelink">
          <Button onClick={openDialog} disabled={!available.length}>
            <Plus />
            {t("Map to another system")}
          </Button>
        </Can>
      }
    >
      {establishment.source_links.length ? (
        <div className="space-y-3">
          {establishment.source_links.map((link) => (
            <div
              key={link.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3"
            >
              <div className="min-w-0 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Link2 className="size-4" />
                  <strong>{t(systemName(link.source))}</strong>
                  <code className="text-xs">{link.external_id}</code>
                  {link.is_primary ? (
                    <Badge variant="secondary">{t("Primary")}</Badge>
                  ) : null}
                </div>
                <small className="text-muted-foreground block">
                  {String(link.details.name || establishment.name)}
                  {link.last_synced_at ? (
                    <>
                      {" · "}
                      {t("Synced")} <SystemDateTime value={link.last_synced_at} includeTime />
                    </>
                  ) : null}
                </small>
              </div>
              <div className="inline-actions">
                <Can permission="establishments.view_sourcelink">
                  <Button size="sm" variant="outline" asChild>
                    <Link to={`/establishments/${establishment.id}/sources/${link.source}`}>
                      {t("View details")}
                    </Link>
                  </Button>
                </Can>
                <Can permission="establishments.change_sourcelink">
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={link.is_primary}
                    title={
                      link.is_primary
                        ? t("Transfer ownership before disconnecting the primary mapping.")
                        : undefined
                    }
                    onClick={() => {
                      disconnect.reset();
                      setDisconnecting(link);
                    }}
                  >
                    <Unlink />
                    {t("Disconnect")}
                  </Button>
                </Can>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-muted-foreground text-sm">
          {t("This establishment is not mapped to any external system yet.")}
        </p>
      )}

      <AppDialog open={open} onOpenChange={setOpen} title={t("Map to another system")} size="lg">
        <div className="space-y-4">
          {!available.length ? (
            <p className="text-muted-foreground text-sm">
              {t("No configured system adapters are available.")}
            </p>
          ) : (
            <>
              <AppSelect
                label={t("System")}
                value={source}
                onChange={(value) => {
                  setSource(String(value));
                  setSearch("");
                  setPage(1);
                  connect.reset();
                }}
                options={available.map((system) => ({
                  value: system.code,
                  label: system.name,
                }))}
              />
              {existing ? (
                <p className="text-muted-foreground text-sm">
                  {t(
                    "This establishment is already mapped to this system. Selecting a record will replace the existing mapping.",
                  )}
                </p>
              ) : null}
              <Input
                aria-label={t("Search")}
                placeholder={t("Search by name or ID")}
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(1);
                }}
              />
              {candidates.isPending ? (
                <AppLoader label={t("Loading…")} className="py-8" />
              ) : candidates.error ? (
                <AppErrorState
                  message={errorMessage(candidates.error)}
                  onRetry={() => candidates.refetch()}
                />
              ) : (
                <div className="max-h-80 space-y-2 overflow-auto">
                  {(candidates.data?.results ?? []).map((record) => (
                    <div
                      key={record.id}
                      className="flex flex-wrap items-center justify-between gap-3 rounded border p-3"
                    >
                      <div className="min-w-0">
                        <strong className="block">{record.name}</strong>
                        <code className="text-xs">{record.id}</code>
                      </div>
                      <Button disabled={connect.isPending} onClick={() => connect.mutate(record.id)}>
                        {existing ? t("Replace mapping") : t("Map")}
                      </Button>
                    </div>
                  ))}
                  {candidates.data?.results.length === 0 ? (
                    <p className="text-muted-foreground py-6 text-center text-sm">
                      {t("No records found.")}
                    </p>
                  ) : null}
                </div>
              )}
              {connect.error ? (
                <div role="alert" className="error-box">
                  {errorMessage(connect.error)}
                </div>
              ) : null}
              <div className="flex items-center justify-between gap-2">
                <Button
                  variant="outline"
                  disabled={page === 1 || candidates.isFetching}
                  onClick={() => setPage(page - 1)}
                >
                  {t("Previous")}
                </Button>
                <span>{page}</span>
                <Button
                  variant="outline"
                  disabled={!candidates.data?.has_next || candidates.isFetching}
                  onClick={() => setPage(page + 1)}
                >
                  {t("Next")}
                </Button>
              </div>
            </>
          )}
        </div>
      </AppDialog>

      <AppDialog
        open={Boolean(disconnecting)}
        onOpenChange={(value) => {
          if (!disconnect.isPending && !value) setDisconnecting(null);
        }}
        title={t("Disconnect this mapping?")}
        description={t(
          "This removes the external link from Mandi. The external record remains available for mapping again.",
        )}
        showCloseButton={!disconnect.isPending}
        footer={
          <>
            <Button
              variant="secondary"
              disabled={disconnect.isPending}
              onClick={() => setDisconnecting(null)}
            >
              {t("Cancel")}
            </Button>
            <Button
              variant="destructive"
              disabled={disconnect.isPending}
              onClick={() => disconnecting && disconnect.mutate(disconnecting)}
            >
              {t("Disconnect")}
            </Button>
          </>
        }
      >
        {disconnecting ? (
          <p>
            <strong>{t(systemName(disconnecting.source))}</strong> ·{" "}
            <code>{disconnecting.external_id}</code>
          </p>
        ) : null}
        {disconnect.error ? (
          <div role="alert" className="error-box">
            {errorMessage(disconnect.error)}
          </div>
        ) : null}
      </AppDialog>
    </PageSection>
  );
}
