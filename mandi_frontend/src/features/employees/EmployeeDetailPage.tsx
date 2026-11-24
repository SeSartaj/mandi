import { useMemo, useState, type ReactNode } from "react";
import { ArrowLeft, CalendarDays, KeyRound, ShieldCheck, UserRound } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { Can } from "@/components/Can";
import { PageSection } from "@/components/PageSection";
import { EditButton } from "@/components/public/ActionButton";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import AppTitle from "@/components/public/AppTitle";
import { SystemDateTime } from "@/components/public/SystemDateTime";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { CollectAccessSection } from "@/features/employees/CollectAccessSection";
import { EmployeeEditDialog } from "@/features/employees/EmployeeEditDialog";
import { projectNameMap } from "@/features/employees/projects";
import { useApiQuery } from "@/features/shared/api";
import type {
  Checklist,
  CollectionProjectDirectory,
  EmployeeDetail,
} from "@/lib/api";
import { errorMessage } from "@/lib/api";

function Stat({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: ReactNode;
  icon: typeof UserRound;
}) {
  return (
    <Card className="stat-card">
      <div>
        <span>{label}</span>
        <Icon size={20} />
      </div>
      <strong>{value}</strong>
    </Card>
  );
}

export default function EmployeeDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const [editing, setEditing] = useState(false);
  const employee = useApiQuery<EmployeeDetail>(["employee", String(id)], `/employees/${id}/`);
  const checklists = useApiQuery<Checklist[]>(["checklists"], "/checklists/");
  const projectDirectory = useApiQuery<CollectionProjectDirectory>(
    ["collection-projects"],
    "/collection/projects/",
  );
  const projectNames = useMemo(
    () => projectNameMap(projectDirectory.data),
    [projectDirectory.data],
  );

  if (employee.isPending) return <AppLoader label={t("Loading…")} className="py-16" />;
  if (employee.error) {
    return (
      <AppErrorState
        message={errorMessage(employee.error)}
        onRetry={() => employee.refetch()}
      />
    );
  }

  const data = employee.data!;
  const displayName = data.display_name || data.username;
  const checklistScope = data.restrict_checklist_access
    ? t("{{count}} checklists", { count: data.allowed_checklists_info.length })
    : t("All checklists");

  return (
    <div className="space-y-6">
      <Link className="back-link" to="/employees">
        <ArrowLeft size={16} />
        {t("Employees")}
      </Link>

      <AppTitle
        title={displayName}
        description={
          <span className="inline-flex flex-wrap items-center gap-2">
            <span>@{data.username}</span>
            {data.position ? <span>· {data.position}</span> : null}
            <Badge variant={data.is_active ? "default" : "secondary"}>
              {t(data.is_active ? "Active" : "Inactive")}
            </Badge>
          </span>
        }
        others={
          <Can permission="accounts.change_user">
            <EditButton
              variant="secondary"
              label={t("Edit employee")}
              onClick={() => setEditing(true)}
            />
          </Can>
        }
      />

      <div className="stats-grid">
        <Stat
          label={t("Status")}
          value={t(data.is_active ? "Active" : "Inactive")}
          icon={UserRound}
        />
        <Stat
          label={t("Permission groups")}
          value={String(data.groups_info.length)}
          icon={ShieldCheck}
        />
        <Stat
          label={t("Checklist access")}
          value={checklistScope}
          icon={KeyRound}
        />
        <Stat
          label={t("Joined")}
          value={<SystemDateTime value={data.date_joined} />}
          icon={CalendarDays}
        />
      </div>

      <PageSection
        title={t("Employee overview")}
        description={t("Account details and access summary.")}
      >
        <dl className="info-grid">
          {(
            [
              ["Full name", displayName],
              ["Username", data.username],
              ["Position", data.position || "—"],
              ["Status", t(data.is_active ? "Active" : "Inactive")],
              ["Staff access", data.is_staff ? t("Yes") : t("No")],
              ["Superuser", data.is_superuser ? t("Yes") : t("No")],
            ] as [string, string][]
          ).map(([label, value]) => (
            <div key={label}>
              <dt>{t(label)}</dt>
              <dd>{value}</dd>
            </div>
          ))}
          <div>
            <dt>{t("Joined")}</dt>
            <dd>
              <SystemDateTime value={data.date_joined} includeTime />
            </dd>
          </div>
          <div>
            <dt>{t("Last login")}</dt>
            <dd>
              <SystemDateTime value={data.last_login} includeTime />
            </dd>
          </div>
        </dl>
      </PageSection>

      <div className="grid gap-6 lg:grid-cols-2">
        <PageSection
          title={t("Permission groups")}
          description={t("Role groups assigned to this employee.")}
        >
          {data.groups_info.length === 0 ? (
            <p className="text-muted-foreground text-sm">{t("No permission groups assigned.")}</p>
          ) : (
            <div className="space-y-3">
              {data.groups_info.map((group) => (
                <article key={group.id} className="rounded-xl border p-4">
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-medium">{t(group.name)}</h3>
                    <Badge variant="secondary">
                      {t("{{count}} permissions", { count: group.permissions.length })}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {group.permissions.map((permission) => (
                      <code
                        key={permission}
                        className="bg-muted rounded px-1.5 py-0.5 text-[11px] break-all"
                      >
                        {permission}
                      </code>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          )}
        </PageSection>

        <PageSection
          title={t("Checklist access")}
          description={t("Checklists this employee can open and work with.")}
        >
          {!data.restrict_checklist_access ? (
            <div className="rounded-xl border p-4">
              <p className="font-medium">{t("All checklists")}</p>
              <p className="text-muted-foreground text-sm">
                {t("The employee's role still determines which actions are allowed.")}
              </p>
            </div>
          ) : data.allowed_checklists_info.length === 0 ? (
            <p className="text-muted-foreground text-sm">{t("No checklists allowed.")}</p>
          ) : (
            <div className="space-y-2">
              {data.allowed_checklists_info.map((checklist) => (
                <div
                  key={checklist.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3 text-sm"
                >
                  <span className="font-medium">{checklist.name}</span>
                  <code className="text-muted-foreground text-xs">{checklist.code}</code>
                </div>
              ))}
            </div>
          )}
        </PageSection>
      </div>

      <Can permission="accounts.change_user">
        <CollectAccessSection
          employee={data}
          checklists={checklists.data ?? []}
          projectNames={projectNames}
          projectDirectory={projectDirectory.data}
        />
      </Can>

      {editing ? (
        <EmployeeEditDialog
          key={data.id}
          employee={data}
          checklists={checklists.data ?? []}
          projectNames={projectNames}
          onClose={() => setEditing(false)}
        />
      ) : null}
    </div>
  );
}
