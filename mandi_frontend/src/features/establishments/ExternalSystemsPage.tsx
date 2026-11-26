import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ListRestart, RefreshCw } from "lucide-react";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { PageSection } from "@/components/PageSection";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import { SystemDateTime } from "@/components/public/SystemDateTime";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useApiQuery } from "@/features/shared/api";
import { api, errorMessage } from "@/lib/api";
import { notify } from "@/lib/notify";
import { cn } from "@/lib/utils";

type SyncState = {
  kind_id: string;
  next_page: number;
  last_attempt_at: string | null;
  last_success_at: string | null;
  last_error: string;
  counts: Record<string, number>;
};

type FullSync = {
  state: "pending" | "running" | "done" | "failed";
  requested_at: string;
  started_at: string | null;
  finished_at: string | null;
  result: Record<string, number>;
  error: string;
};

type ExternalSystem = {
  code: string;
  name: string;
  adapter: string;
  configured: boolean;
  syncable: boolean;
  can_sync: boolean;
  states: SyncState[];
  full_sync: FullSync | null;
};

type SystemsResponse = {
  enabled: boolean;
  interval: number;
  systems: ExternalSystem[];
};

type SyncResult = { busy?: boolean } & Record<string, number>;

function lastSync(system: ExternalSystem): string | null {
  const times = system.states
    .map((state) => state.last_success_at)
    .filter((value): value is string => Boolean(value));
  if (times.length === 0) return null;
  return times.sort().at(-1) ?? null;
}

function syncError(system: ExternalSystem): string | null {
  return system.states.find((state) => state.last_error)?.last_error ?? null;
}

export default function ExternalSystemsPage() {
  const { t } = useTranslation();
  const client = useQueryClient();
  const query = useApiQuery<SystemsResponse>(
    ["registry-systems"],
    "/registry/systems/",
    {},
    // A queued complete sync is executed by the worker; poll to show progress.
    { refetchInterval: 10000 },
  );
  const sync = useMutation({
    mutationFn: async (code: string) =>
      (await api.post<SyncResult>(`/registry/systems/${code}/sync/`)).data,
    onSuccess: (result, code) => {
      const system = query.data?.systems.find((item) => item.code === code);
      if (result.busy) {
        notify.info(t("Sync already running."), { description: system?.name ?? code });
      } else {
        notify.success(
          t("Sync completed: {{created}} new, {{updated}} updated, {{failed}} failed.", {
            created: result.created ?? 0,
            updated: result.updated ?? 0,
            failed: result.failed ?? 0,
          }),
          { description: system?.name ?? code },
        );
      }
      void client.invalidateQueries({ queryKey: ["registry-systems"] });
      void client.invalidateQueries({ queryKey: ["registry-sync-status"] });
    },
    onError: (error) =>
      notify.error(t("Could not complete the action."), {
        description: errorMessage(error),
      }),
  });
  const fullSync = useMutation({
    mutationFn: async (code: string) =>
      (await api.post<{ state: string; requested_at: string; queued: boolean }>(
        `/registry/systems/${code}/full-sync/`,
      )).data,
    onSuccess: (result, code) => {
      const system = query.data?.systems.find((item) => item.code === code);
      notify.info(
        result.queued
          ? t("Complete sync queued for {{system}}. The registry worker will start it shortly.", {
              system: system?.name ?? code,
            })
          : t("A complete sync is already queued or running."),
      );
      void client.invalidateQueries({ queryKey: ["registry-systems"] });
    },
    onError: (error) =>
      notify.error(t("Could not complete the action."), {
        description: errorMessage(error),
      }),
  });

  // Announce completion once, when the polled request changes state.
  const previousStates = useRef<Record<string, string | undefined>>({});
  useEffect(() => {
    for (const system of query.data?.systems ?? []) {
      const state = system.full_sync?.state;
      const previous = previousStates.current[system.code];
      if (state && previous && state !== previous) {
        if (state === "done") {
          notify.success(
            t(
              "Complete sync finished: {{created}} new, {{updated}} updated, {{failed}} failed.",
              {
                created: system.full_sync?.result.created ?? 0,
                updated: system.full_sync?.result.updated ?? 0,
                failed: system.full_sync?.result.failed ?? 0,
              },
            ),
            { description: system.name },
          );
        } else if (state === "failed") {
          notify.error(t("Complete sync failed."), { description: system.name });
        }
      }
      if (state) previousStates.current[system.code] = state;
    }
  }, [query.data, t]);

  return (
    <div className="space-y-6">
      <PageSection
        headingLevel={1}
        title={t("External systems")}
        description={t("Systems Mandi can pull records from.")}
      >
        {query.isPending ? (
          <AppLoader label={t("Loading…")} className="py-10" />
        ) : query.error ? (
          <AppErrorState message={errorMessage(query.error)} onRetry={() => query.refetch()} />
        ) : (
          <div className="space-y-4">
            <p className="text-muted-foreground text-sm">
              {t("Automatic sync")}: {query.data.enabled ? t("Enabled") : t("Disabled")} ·{" "}
              {query.data.interval}s
            </p>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("System")}</TableHead>
                  <TableHead>{t("Status")}</TableHead>
                  <TableHead>{t("Last sync")}</TableHead>
                  <TableHead className="text-end">{t("Actions")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {query.data.systems.map((system) => {
                  const pending = sync.isPending && sync.variables === system.code;
                  const syncedAt = lastSync(system);
                  const error = syncError(system);
                  const complete = system.full_sync;
                  const completeActive =
                    complete?.state === "pending" || complete?.state === "running";
                  const completePending =
                    fullSync.isPending && fullSync.variables === system.code;
                  const reason = !system.syncable
                    ? t("Direct sync is not available for this source.")
                    : !system.can_sync
                      ? t("You do not have permission to sync this system.")
                      : undefined;
                  return (
                    <TableRow key={system.code}>
                      <TableCell>
                        <span className="font-medium">{system.name}</span>
                        <code className="text-muted-foreground block text-xs">{system.code}</code>
                      </TableCell>
                      <TableCell>
                        <Badge variant={system.configured ? "default" : "secondary"}>
                          {system.configured ? t("Configured") : t("Not configured")}
                        </Badge>
                        {!system.syncable && system.code === "archive" && (
                          <span className="text-muted-foreground mt-1 block text-xs">
                            {t("Derived from Licensing")}
                          </span>
                        )}
                        {error && (
                          <span className="text-destructive mt-1 block text-xs" role="alert">
                            {error}
                          </span>
                        )}
                        {complete?.state === "done" && (
                          <span className="text-muted-foreground mt-1 block text-xs">
                            {t("Full sync: {{created}} created, {{updated}} updated, {{failed}} failed.", {
                              created: complete.result.created ?? 0,
                              updated: complete.result.updated ?? 0,
                              failed: complete.result.failed ?? 0,
                            })}
                          </span>
                        )}
                        {complete?.state === "failed" && (
                          <span className="text-destructive mt-1 block text-xs" role="alert">
                            {t("Full sync failed.")}
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {syncedAt ? (
                          <SystemDateTime value={syncedAt} includeTime />
                        ) : (
                          t("Never")
                        )}
                      </TableCell>
                      <TableCell className="text-end">
                        <div className="flex flex-wrap justify-end gap-2">
                          <Button
                            type="button"
                            variant="secondary"
                            title={reason}
                            aria-busy={pending}
                            disabled={!system.can_sync || sync.isPending || completeActive}
                            onClick={() => sync.mutate(system.code)}
                          >
                            <RefreshCw
                              className={cn("size-4", pending && "animate-spin")}
                              aria-hidden="true"
                            />
                            {pending ? t("Syncing…") : t("Sync now")}
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            title={reason}
                            aria-busy={completeActive || completePending}
                            disabled={
                              !system.can_sync ||
                              completeActive ||
                              completePending ||
                              sync.isPending
                            }
                            onClick={() => fullSync.mutate(system.code)}
                          >
                            <ListRestart
                              className={cn(
                                "size-4",
                                (completeActive || completePending) && "animate-spin",
                              )}
                              aria-hidden="true"
                            />
                            {complete?.state === "pending"
                              ? t("Queued")
                              : complete?.state === "running" || completePending
                                ? t("Running…")
                                : t("Complete sync")}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </PageSection>
    </div>
  );
}
