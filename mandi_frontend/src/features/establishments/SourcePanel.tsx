import { CancelButton } from "@/components/public/ActionButton";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Link } from "react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Can } from "@/components/Can";
import { AppDialog } from "@/components/public/AppDialog";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { Establishment, SourceLink } from "@/lib/api";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { api, errorMessage } from "@/lib/api";

type Candidate = {
  id: string;
  name: string;
  details: SourceLink["details"];
  is_demo: boolean;
};

export default function SourcePanel({
  establishment,
  source,
  title,
}: {
  establishment: Establishment;
  source: string;
  title: string;
}) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const link = establishment.source_links.find((item) => item.source === source);
  const [disconnecting, setDisconnecting] = useState(false);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const [page, setPage] = useState(1);
  const candidates = useQuery({
    queryKey: ["source", source, establishment.kind, debouncedSearch, page],
    enabled: open,
    queryFn: async ({ signal }) =>
      (
        await api.get<{ results: Candidate[]; is_demo: boolean; has_next: boolean }>(
          `/sources/${source}/`,
          {
            params: { kind: establishment.kind, search: debouncedSearch, page },
            signal,
          },
        )
      ).data,
  });
  const mutation = useMutation({
    mutationFn: async (id: string | null) =>
      id
        ? api.post(`/establishments/${establishment.id}/sources/${source}/`, { external_id: id })
        : api.delete(`/establishments/${establishment.id}/sources/${source}/`),
    onSuccess: () => {
      client.invalidateQueries();
      setOpen(false);
      setDisconnecting(false);
    },
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle className="text-base">{t(title)}</CardTitle>
        {link?.is_demo ? <Badge variant="secondary">{t("Demonstration data")}</Badge> : null}
      </CardHeader>
      <CardContent className="space-y-4">
        {link ? (
          <>
            <Can permission="establishments.view_sourcelink">
              <Link
                className="text-link text-base font-semibold"
                to={`/establishments/${establishment.id}/sources/${source}`}
              >
                {String(link.details.name || establishment.name)} · {t("View details")}
              </Link>
            </Can>
            <dl className="details-list">
              {Object.entries(link.details).map(([key, value]) => (
                <div key={key}>
                  <dt>{key.replaceAll("_", " ")}</dt>
                  <dd>{String(value)}</dd>
                </div>
              ))}
            </dl>
            <small className="muted">ID: {link.external_id}</small>
            <Can permission="establishments.change_sourcelink">
              <Button
                variant="outline"
                disabled={mutation.isPending}
                onClick={() => {
                  mutation.reset();
                  setDisconnecting(true);
                }}
              >
                {t("Disconnect")}
              </Button>
            </Can>
          </>
        ) : (
          <>
            <p className="muted">{t("This source is not linked.")}</p>
            <Can permission="establishments.change_sourcelink">
              <Button variant="outline" onClick={() => setOpen(true)}>
                <Plus />
                {t("Connect")}
              </Button>
            </Can>
          </>
        )}
        {mutation.error ? (
          <AppErrorState message={errorMessage(mutation.error)} className="border-0 shadow-none" />
        ) : null}
      </CardContent>

      <AppDialog
        open={disconnecting}
        onOpenChange={(value) => {
          if (!mutation.isPending) setDisconnecting(value);
        }}
        title={t("Disconnect this source?")}
        description={t(
          "This removes the link from Mandi. The source record will remain available to connect again.",
        )}
        showCloseButton={!mutation.isPending}
        footer={
          <>
            <CancelButton
              variant="secondary"
              disabled={mutation.isPending}
              onClick={() => setDisconnecting(false)}
            />
            <Button
              variant="destructive"
              disabled={mutation.isPending}
              onClick={() => mutation.mutate(null)}
            >
              {t("Disconnect")}
            </Button>
          </>
        }
      >
        <p className="font-medium">{t(title)}</p>
        {mutation.error && (
          <div role="alert" className="error-box">
            {errorMessage(mutation.error)}
          </div>
        )}
      </AppDialog>
      <AppDialog open={open} onOpenChange={setOpen} title={t(title)} size="lg">
        <div className="space-y-4">
          <p className="muted">
            {t("Select a record to connect. Source details remain separate from Mandi details.")}
          </p>
          {candidates.data?.is_demo && <Badge variant="secondary">{t("Demonstration data")}</Badge>}
          <Input
            aria-label={t("Search")}
            placeholder={t("Search")}
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
            <div className="max-h-80 overflow-auto">
              {(candidates.data?.results ?? []).map((record) => (
                <div key={record.id} className="candidate">
                  <div>
                    <strong>{record.name}</strong>
                    <small>{record.id}</small>
                  </div>
                  <Button disabled={mutation.isPending} onClick={() => mutation.mutate(record.id)}>
                    {t("Connect")}
                  </Button>
                </div>
              ))}
              {candidates.data?.results.length === 0 ? (
                <div className="empty">{t("No records found.")}</div>
              ) : null}
            </div>
          )}
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
        </div>
      </AppDialog>
    </Card>
  );
}
