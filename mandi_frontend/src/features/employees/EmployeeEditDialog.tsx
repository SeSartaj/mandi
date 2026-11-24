import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { AppDialog } from "@/components/public/AppDialog";
import { AppErrorState } from "@/components/public/AppErrorState";
import { CancelButton, SaveButton } from "@/components/public/ActionButton";
import { FieldSupport } from "@/components/ui/field-support";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { api, errorMessage } from "@/lib/api";
import type { Checklist, EmployeeDetail } from "@/lib/api";

type PermissionGroup = { id: number; name: string };

type Props = {
  employee: EmployeeDetail;
  checklists: Checklist[];
  projectNames: Map<number, string>;
  onClose: () => void;
};

function groupChecklists(
  checklists: Checklist[],
  projectNames: Map<number, string>,
  projectFallback: string,
  undeployedLabel: string,
) {
  const groups = new Map<string, { key: string; name: string; items: Checklist[] }>();
  for (const checklist of checklists) {
    const projectId = checklist.collection.project_id;
    const key = projectId === null ? "undeployed" : String(projectId);
    const name =
      projectId === null
        ? undeployedLabel
        : (projectNames.get(projectId) ?? `${projectFallback} ${projectId}`);
    const group = groups.get(key) ?? { key, name, items: [] };
    group.items.push(checklist);
    groups.set(key, group);
  }
  return [...groups.values()].sort((left, right) => left.name.localeCompare(right.name));
}

export function EmployeeEditDialog({ employee, checklists, projectNames, onClose }: Props) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const [name, setName] = useState(employee.display_name);
  const [position, setPosition] = useState(employee.position);
  const [password, setPassword] = useState("");
  const [active, setActive] = useState(employee.is_active);
  const [groups, setGroups] = useState(employee.groups);
  const [restricted, setRestricted] = useState(employee.restrict_checklist_access);
  const [allowed, setAllowed] = useState(employee.allowed_checklists);

  const permissionGroups = useQuery({
    queryKey: ["permission-groups"],
    queryFn: async () =>
      (await api.get<PermissionGroup[]>("/permission-groups/")).data,
  });

  const checklistGroups = useMemo(
    () => groupChecklists(checklists, projectNames, t("ODK project"), t("Not deployed")),
    [checklists, projectNames, t],
  );

  const save = useMutation({
    mutationFn: async () => {
      const values: Record<string, unknown> = { display_name: name, position };
      if (password) values.password = password;
      if (active !== employee.is_active) values.is_active = active;
      if (JSON.stringify(groups) !== JSON.stringify(employee.groups)) values.group_ids = groups;
      if (restricted !== employee.restrict_checklist_access)
        values.restrict_checklist_access = restricted;
      if (JSON.stringify(allowed) !== JSON.stringify(employee.allowed_checklists))
        values.checklist_ids = allowed;
      return api.patch<EmployeeDetail>(`/employees/${employee.id}/`, values);
    },
    onSuccess: (response) => {
      client.setQueryData(["employee", String(employee.id)], response.data);
      client.invalidateQueries({ queryKey: ["employees"] });
      onClose();
    },
  });

  const toggle = (list: number[], id: number) =>
    list.includes(id) ? list.filter((item) => item !== id) : [...list, id];

  return (
    <AppDialog
      open
      onOpenChange={(value) => {
        if (!value) onClose();
      }}
      title={t("Edit employee")}
      description={t("Update profile, permissions, and checklist access.")}
      size="lg"
      contentClassName="max-h-[90vh] overflow-y-auto"
    >
      <div className="space-y-6 py-2">
        <section className="space-y-3">
          <h3 className="text-sm font-semibold">{t("Profile")}</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="font-medium">{t("Full name")}</span>
              <Input value={name} onChange={(event) => setName(event.target.value)} />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium">{t("Position")}</span>
              <Input value={position} onChange={(event) => setPosition(event.target.value)} />
            </label>
            <label className="space-y-1 text-sm sm:col-span-2">
              <span className="font-medium">{t("New password")}</span>
              <Input
                type="password"
                autoComplete="new-password"
                placeholder={t("Leave blank to keep the current password")}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
          </div>
          <div className="flex items-center justify-between gap-4 rounded-lg border p-3">
            <div>
              <p className="text-sm font-medium">{t("Active account")}</p>
              <p className="text-muted-foreground text-xs">
                {t("Inactive employees cannot sign in or use collection access.")}
              </p>
            </div>
            <Switch checked={active} onCheckedChange={setActive} aria-label={t("Active account")} />
          </div>
        </section>

        <section className="space-y-3">
          <div>
            <h3 className="text-sm font-semibold">{t("Permission groups")}</h3>
            <p className="text-muted-foreground text-xs">
              {t("Groups grant the backend permissions used by every screen and API action.")}
            </p>
          </div>
          {permissionGroups.isPending ? (
            <p className="text-muted-foreground text-sm">{t("Loading…")}</p>
          ) : permissionGroups.error ? (
            <AppErrorState
              message={errorMessage(permissionGroups.error)}
              onRetry={() => permissionGroups.refetch()}
            />
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              {(permissionGroups.data ?? []).map((group) => (
                <label
                  key={group.id}
                  className="flex items-start gap-3 rounded-lg border p-3 text-sm"
                >
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={groups.includes(group.id)}
                    onChange={() => setGroups(toggle(groups, group.id))}
                  />
                  <span>
                    <span className="block font-medium">{t(group.name)}</span>
                    <span className="text-muted-foreground text-xs">
                      {t("Role group")}
                    </span>
                  </span>
                </label>
              ))}
            </div>
          )}
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between gap-4 rounded-lg border p-3">
            <div>
              <p className="text-sm font-medium">{t("Restrict checklist access")}</p>
              <p className="text-muted-foreground text-xs">
                {t("When enabled, only the selected checklists and their submissions are visible.")}
              </p>
            </div>
            <Switch
              checked={restricted}
              onCheckedChange={setRestricted}
              aria-label={t("Restrict checklist access")}
            />
          </div>
          {restricted ? (
            checklistGroups.length === 0 ? (
              <p className="text-muted-foreground text-sm">{t("No deployed checklists.")}</p>
            ) : (
              <div className="space-y-4">
                {checklistGroups.map((group) => (
                  <div key={group.key} className="space-y-2">
                    <p className="text-muted-foreground text-xs font-medium uppercase tracking-wide">
                      {group.name}
                    </p>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {group.items.map((checklist) => (
                        <label
                          key={checklist.id}
                          className="flex items-start gap-3 rounded-lg border p-3 text-sm"
                        >
                          <input
                            type="checkbox"
                            className="mt-1"
                            checked={allowed.includes(checklist.id)}
                            onChange={() => setAllowed(toggle(allowed, checklist.id))}
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
            )
          ) : (
            <p className="text-muted-foreground text-sm">
              {t("This employee can access all checklists allowed by their role.")}
            </p>
          )}
        </section>

        <FieldSupport error={save.error ? errorMessage(save.error) : undefined} />
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Badge variant="secondary">{t("Changes apply immediately")}</Badge>
          <CancelButton type="button" variant="secondary" onClick={onClose} disabled={save.isPending} />
          <SaveButton
            type="button"
            loading={save.isPending}
            loadingLabel={t("Saving…")}
            onClick={() => save.mutate()}
          />
        </div>
      </div>
    </AppDialog>
  );
}
