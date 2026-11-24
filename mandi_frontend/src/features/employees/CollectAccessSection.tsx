import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { KeyRound, QrCode, RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";

import { PageSection } from "@/components/PageSection";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useApiQuery } from "@/features/shared/api";
import { api, errorMessage } from "@/lib/api";
import { notify } from "@/lib/notify";
import type {
  Checklist,
  CollectionProjectDirectory,
  CollectorCredential,
  EmployeeDetail,
  GrantSummary,
  NewCollectorCredential,
  ProvisionResult,
} from "@/lib/api";

type Props = {
  employee: EmployeeDetail;
  checklists: Checklist[];
  projectNames: Map<number, string>;
  projectDirectory?: CollectionProjectDirectory;
};

function groupDeployedChecklists(checklists: Checklist[]) {
  const groups = new Map<number, Checklist[]>();
  for (const checklist of checklists) {
    if (checklist.collection.provider !== "odk" || checklist.collection.status !== "deployed")
      continue;
    const projectId = checklist.collection.project_id;
    if (projectId === null) continue;
    groups.set(projectId, [...(groups.get(projectId) ?? []), checklist]);
  }
  return [...groups.entries()].sort(([left], [right]) => left - right);
}

export function CollectAccessSection({
  employee,
  checklists,
  projectNames,
  projectDirectory,
}: Props) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const [selected, setSelected] = useState<number[]>([]);
  const [newCredentials, setNewCredentials] = useState<NewCollectorCredential[]>([]);
  const [added, setAdded] = useState<GrantSummary[]>([]);
  const [unchanged, setUnchanged] = useState<GrantSummary[]>([]);

  const grants = useApiQuery<CollectorCredential[]>(
    ["collector-access", employee.id],
    `/employees/${employee.id}/collection-access/`,
  );

  const provision = useMutation({
    mutationFn: async () =>
      (
        await api.post<ProvisionResult>(
          `/employees/${employee.id}/collection-access/`,
          { checklist_ids: selected },
        )
      ).data,
    onSuccess: (data) => {
      notify.success(t("Collection access issued."));
      setNewCredentials(data.credentials);
      setAdded(data.added);
      setUnchanged(data.unchanged);
      setSelected([]);
      client.invalidateQueries({ queryKey: ["collector-access", employee.id] });
    },
    onError: (error) =>
      notify.error(t("Could not complete the action."), {
        description: errorMessage(error),
      }),
  });

  const revoke = useMutation({
    mutationFn: (grantId: number) =>
      api.delete(`/employees/${employee.id}/collection-access/`, {
        data: { grant_id: grantId },
      }),
    onSuccess: () => {
      notify.success(t("Collection access revoked."));
      setNewCredentials([]);
      setAdded([]);
      setUnchanged([]);
      client.invalidateQueries({ queryKey: ["collector-access", employee.id] });
    },
    onError: (error) =>
      notify.error(t("Could not complete the action."), {
        description: errorMessage(error),
      }),
  });

  const grouped = useMemo(() => groupDeployedChecklists(checklists), [checklists]);
  const error = grants.error ?? provision.error ?? revoke.error;

  const projectName = (projectId: number) =>
    projectNames.get(projectId) ?? t("ODK project {{id}}", { id: projectId });

  const toggle = (id: number) =>
    setSelected((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );

  return (
    <PageSection
      title={t("ODK Collect access")}
      description={t(
        "Employees receive one ODK credential per project. The credential is shown once when it is created.",
      )}
    >
      <div className="space-y-6">
        {projectDirectory && !projectDirectory.available ? (
          <p className="text-muted-foreground text-sm">
            {t("Project names are temporarily unavailable. Project IDs are shown instead.")}
          </p>
        ) : null}

        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold">{t("Active credentials")}</h3>
              <p className="text-muted-foreground text-xs">
                {t("Revoke a credential before deactivating the employee or narrowing access.")}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              disabled={grants.isFetching}
              onClick={() => grants.refetch()}
            >
              <RefreshCw className={grants.isFetching ? "size-4 animate-spin" : "size-4"} />
              {t("Refresh")}
            </Button>
          </div>

          {grants.isPending ? (
            <AppLoader label={t("Loading…")} className="py-6" />
          ) : grants.error ? (
            <AppErrorState
              message={errorMessage(grants.error)}
              onRetry={() => grants.refetch()}
            />
          ) : (grants.data ?? []).length === 0 ? (
            <p className="text-muted-foreground text-sm">{t("No active Collect credentials.")}</p>
          ) : (
            <div className="grid gap-3 lg:grid-cols-2">
              {(grants.data ?? []).map((credential) => (
                <article
                  key={`${credential.project_id}-${credential.remote_id}`}
                  className="bg-card space-y-3 rounded-xl border p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h4 className="font-semibold break-words">
                        {projectName(credential.project_id)}
                      </h4>
                      <p className="text-muted-foreground text-xs">
                        {t("Project ID")} {credential.project_id} · {t("Credential")}{" "}
                        <code>{credential.remote_id}</code>
                      </p>
                    </div>
                    <Badge variant="secondary">
                      {t("{{count}} forms", { count: credential.checklists.length })}
                    </Badge>
                  </div>
                  <div className="space-y-2">
                    {credential.checklists.map((item) => (
                      <div
                        key={item.grant_id}
                        className="flex items-center justify-between gap-3 rounded-lg border p-2 text-sm"
                      >
                        <span className="min-w-0 break-words">{item.checklist_name}</span>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={revoke.isPending}
                          onClick={() => revoke.mutate(item.grant_id)}
                        >
                          {t("Remove")}
                        </Button>
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="space-y-3">
          <div>
            <h3 className="text-sm font-semibold">{t("Add checklists")}</h3>
            <p className="text-muted-foreground text-xs">
              {t(
                "Checklists from the same project share one credential. Different projects create separate credentials.",
              )}
            </p>
          </div>

          {grouped.length === 0 ? (
            <p className="text-muted-foreground text-sm">{t("No deployed checklists.")}</p>
          ) : (
            <div className="space-y-4">
              {grouped.map(([projectId, items]) => (
                <div key={projectId} className="rounded-xl border p-4">
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <p className="font-medium">{projectName(projectId)}</p>
                    <Badge variant="outline">
                      {t("Project ID")} {projectId}
                    </Badge>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {items.map((checklist) => (
                      <label
                        key={checklist.id}
                        className="flex items-start gap-3 rounded-lg border p-3 text-sm"
                      >
                        <input
                          type="checkbox"
                          className="mt-1"
                          checked={selected.includes(checklist.id)}
                          onChange={() => toggle(checklist.id)}
                        />
                        <span>
                          <span className="block font-medium">{checklist.name}</span>
                          <code className="text-muted-foreground text-xs">{checklist.code}</code>
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          <Button
            disabled={selected.length === 0 || provision.isPending || !employee.is_active}
            onClick={() => provision.mutate()}
          >
            <KeyRound />
            {provision.isPending ? t("Creating…") : t("Create or update Collect access")}
          </Button>
          {!employee.is_active ? (
            <p className="text-muted-foreground text-xs">
              {t("Activate the employee before creating collection access.")}
            </p>
          ) : null}
        </section>

        {added.length > 0 ? (
          <p role="status" className="text-sm">
            {t("Added to the existing credential:")}{" "}
            {added.map((item) => item.checklist_name).join(", ")}.
          </p>
        ) : null}
        {unchanged.length > 0 ? (
          <p className="text-muted-foreground text-sm">
            {t("Already granted:")} {unchanged.map((item) => item.checklist_name).join(", ")}.
          </p>
        ) : null}

        {newCredentials.length > 0 ? (
          <section className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold">{t("New credential")}</h3>
              <p className="text-muted-foreground text-xs">
                {t(
                  "Scan each QR code in ODK Collect, or copy the server URL. Mandi does not store the token.",
                )}
              </p>
            </div>
            <div className="grid gap-3 lg:grid-cols-2">
              {newCredentials.map((credential) => (
                <article
                  key={`${credential.project_id}-${credential.remote_id}`}
                  className="space-y-3 rounded-xl border p-4"
                >
                  <div className="flex items-center justify-between gap-2">
                    <h4 className="font-semibold">{projectName(credential.project_id)}</h4>
                    <Badge variant="secondary">
                      {t("Project ID")} {credential.project_id}
                    </Badge>
                  </div>
                  <p className="text-muted-foreground text-sm">
                    {credential.checklists.map((item) => item.checklist_name).join(", ")}
                  </p>
                  {credential.qr ? (
                    <img
                      src={credential.qr}
                      alt={t("ODK Collect settings QR code")}
                      className="mx-auto max-w-56 rounded border bg-white p-2"
                    />
                  ) : (
                    <QrCode className="text-muted-foreground mx-auto size-12" />
                  )}
                  <textarea
                    aria-label={t("ODK Collect server URL")}
                    readOnly
                    className="w-full rounded border p-2 font-mono text-xs break-all"
                    value={credential.server_url}
                  />
                </article>
              ))}
            </div>
            <Button variant="outline" onClick={() => setNewCredentials([])}>
              {t("Hide credentials")}
            </Button>
          </section>
        ) : null}

        {error ? (
          <p role="alert" className="error-box">
            {errorMessage(error)}
          </p>
        ) : null}
      </div>
    </PageSection>
  );
}
