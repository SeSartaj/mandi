import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileSpreadsheet, Plus, Rocket } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Can } from "@/components/Can";
import { PageSection } from "@/components/PageSection";
import { AppDialog } from "@/components/public/AppDialog";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import AppTable from "@/components/public/AppTable";
import { SystemDateTime } from "@/components/public/SystemDateTime";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import ChecklistForm from "@/features/checklists/ChecklistForm";
import { useApiQuery } from "@/features/shared/api";
import { choiceLabel } from "@/features/shared/labels";
import type { Checklist } from "@/lib/api";
import { api, errorMessage, fileUrl } from "@/lib/api";

function DeploymentBadge({ status }: { status: Checklist["kobo_deployment_status"] }) {
  const { t } = useTranslation();
  const variants: Record<
    Checklist["kobo_deployment_status"],
    "default" | "secondary" | "destructive" | "outline"
  > = {
    not_deployed: "secondary",
    deploying: "outline",
    deployed: "default",
    failed: "destructive",
  };
  const labels: Record<Checklist["kobo_deployment_status"], string> = {
    not_deployed: "Not deployed",
    deploying: "Deploying…",
    deployed: "Deployed",
    failed: "Deployment failed",
  };
  return <Badge variant={variants[status]}>{t(labels[status])}</Badge>;
}

export default function ChecklistsPage() {
  const { t } = useTranslation();
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Checklist | null>(null);
  const checklists = useApiQuery<Checklist[]>(["checklists"], "/checklists/");
  const deploy = useMutation({
    mutationFn: (checklist: Checklist) => api.post(`/checklists/${checklist.id}/deploy/`),
    onSettled: () => {
      client.invalidateQueries({ queryKey: ["checklists"] });
      client.invalidateQueries({ queryKey: ["form-checklists"] });
    },
  });

  const close = () => {
    setOpen(false);
    setEditing(null);
  };

  const rows = checklists.data ?? [];
  const deployingId = deploy.isPending && deploy.variables ? deploy.variables.id : null;

  return (
    <div className="space-y-6">
      <PageSection
        title={t("Checklists")}
        description={t("Upload and manage the XLSForms used for inspections.")}
        actions={
          <Can permission="inspections.add_checklist">
            <Button
              onClick={() => {
                setEditing(null);
                setOpen(true);
              }}
            >
              <Plus />
              {t("Add checklist")}
            </Button>
          </Can>
        }
      >
        {deploy.error ? (
          <div role="alert" className="error-box">
            {errorMessage(deploy.error)}
          </div>
        ) : null}

        {checklists.isPending ? (
          <AppLoader label={t("Loading…")} className="py-10" />
        ) : checklists.error ? (
          <AppErrorState
            message={errorMessage(checklists.error)}
            onRetry={() => checklists.refetch()}
          />
        ) : (
          <AppTable className="min-w-[980px]">
            <TableHeader>
              <TableRow>
                <TableHead>{t("Name")}</TableHead>
                <TableHead>{t("Checklist code")}</TableHead>
                <TableHead>{t("Version")}</TableHead>
                <TableHead>{t("Type")}</TableHead>
                <TableHead>{t("XLSForm")}</TableHead>
                <TableHead>{t("Deployment")}</TableHead>
                <TableHead>{t("Action")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((checklist) => (
                <TableRow key={checklist.id}>
                  <TableCell>{checklist.name}</TableCell>
                  <TableCell>{checklist.code}</TableCell>
                  <TableCell>{checklist.version}</TableCell>
                  <TableCell>{t(choiceLabel(checklist.establishment_kind))}</TableCell>
                  <TableCell>
                    {checklist.xlsform ? (
                      <a
                        className="text-link"
                        href={fileUrl(checklist.xlsform)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <FileSpreadsheet className="size-4" />
                        {t("Download")}
                      </a>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <DeploymentBadge status={checklist.kobo_deployment_status} />
                      {checklist.kobo_deployed_at ? (
                        <small className="muted block">
                          <SystemDateTime value={checklist.kobo_deployed_at} includeTime />
                        </small>
                      ) : null}
                      {checklist.kobo_deployment_error ? (
                        <small className="text-destructive block max-w-72 whitespace-normal">
                          {checklist.kobo_deployment_error}
                        </small>
                      ) : null}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="inline-actions">
                      <Can permission="inspections.change_checklist">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setEditing(checklist);
                            setOpen(true);
                          }}
                        >
                          {t("Edit")}
                        </Button>
                      </Can>
                      <Can permission="inspections.deploy_checklist">
                        <Button
                          size="sm"
                          disabled={!checklist.xlsform || deploy.isPending}
                          onClick={() => deploy.mutate(checklist)}
                        >
                          <Rocket />
                          {deployingId === checklist.id ? t("Deploying…") : t("Deploy")}
                        </Button>
                      </Can>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-muted-foreground py-8 text-center">
                    {t("No checklists yet.")}
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </AppTable>
        )}
      </PageSection>

      <AppDialog
        open={open}
        onOpenChange={(value) => {
          if (!value) close();
        }}
        title={editing ? t("Edit checklist") : t("Add checklist")}
        size="lg"
        contentClassName="max-h-[90vh] overflow-y-auto"
      >
        <ChecklistForm existing={editing ?? undefined} onClose={close} />
      </AppDialog>
    </div>
  );
}
