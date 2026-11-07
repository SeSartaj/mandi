import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
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
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const candidates = useQuery({
    queryKey: ["source", source, establishment.kind, search],
    enabled: open,
    queryFn: async () =>
      (
        await api.get<{ results: Candidate[] }>(`/sources/${source}/`, {
          params: { kind: establishment.kind, search },
        })
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
                onClick={() => mutation.mutate(null)}
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

      <AppDialog open={open} onOpenChange={setOpen} title={t(title)} size="lg">
        <div className="space-y-4">
          <p className="muted">
            {t("Select a record to connect. Source details remain separate from Mandi details.")}
          </p>
          <Badge variant="secondary">{t("Demonstration data")}</Badge>
          <Input
            aria-label={t("Search")}
            placeholder={t("Search")}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
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
        </div>
      </AppDialog>
    </Card>
  );
}
