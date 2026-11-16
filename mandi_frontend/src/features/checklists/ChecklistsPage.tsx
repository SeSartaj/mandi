import { CreateButton, EditButton, CancelButton } from "@/components/public/ActionButton";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, ExternalLink, FileSpreadsheet, Rocket } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { Can } from "@/components/Can";
import { PageSection } from "@/components/PageSection";
import { AppDialog } from "@/components/public/AppDialog";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import AppTable from "@/components/public/AppTable";
import { SystemDateTime } from "@/components/public/SystemDateTime";
import { DeploymentBadge } from "./DeploymentBadge";
import { Button } from "@/components/ui/button";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import ChecklistForm from "@/features/checklists/ChecklistForm";
import { useApiQuery } from "@/features/shared/api";
import { choiceLabel } from "@/features/shared/labels";
import type { Checklist } from "@/lib/api";
import { api, errorMessage, fileUrl } from "@/lib/api";

export default function ChecklistsPage() {
  const { t } = useTranslation();
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [deploying, setDeploying] = useState<Checklist | null>(null);
  const [editing, setEditing] = useState<Checklist | null>(null);
  const checklists = useApiQuery<Checklist[]>(["checklists"], "/checklists/");
  const deploy = useMutation({
    mutationFn: (checklist: Checklist) => api.post(`/checklists/${checklist.id}/deploy/`),
    onSuccess: () => setDeploying(null),
    onSettled: () => {
      client.invalidateQueries({ queryKey: ["checklists"] });
      client.invalidateQueries({ queryKey: ["form-checklists"] });
    },
  });
  const downloadCsv = useMutation({
    mutationFn: async () => {
      const response = await api.get("/integrations/kobo/establishments.csv", {
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "establishments.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
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
        headingLevel={1}
        title={t("Checklists")}
        description={t("Upload and manage the XLSForms used for inspections.")}
        actions={
          <div className="inline-actions">
            <Can permission="establishments.view_establishment">
              <Button
                variant="outline"
                disabled={downloadCsv.isPending}
                onClick={() => downloadCsv.mutate()}
              >
                <Download />
                {t("Download establishments CSV")}
              </Button>
            </Can>
            <Can permission="inspections.add_checklist">
              <CreateButton
                onClick={() => {
                  setEditing(null);
                  setOpen(true);
                }}
                label={t("Add checklist")}
              />
            </Can>
          </div>
        }
      >
        {deploy.error || downloadCsv.error ? (
          <div role="alert" className="error-box">
            {errorMessage(deploy.error ?? downloadCsv.error)}
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
                  <TableCell>
                    <Link className="entity-link" to={`/checklists/${checklist.id}`}>
                      {checklist.name}
                    </Link>
                  </TableCell>
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
                      {checklist.kobo_project_url ? (
                        <a
                          className="text-link"
                          href={checklist.kobo_project_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <ExternalLink className="size-4" />
                          {t("Open in KoBo")}
                        </a>
                      ) : null}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="inline-actions">
                      <Can permission="inspections.change_checklist">
                        <EditButton
                          size="sm"
                          variant="secondary"
                          onClick={() => {
                            setEditing(checklist);
                            setOpen(true);
                          }}
                        />
                      </Can>
                      <Can permission="inspections.deploy_checklist">
                        <Button
                          size="sm"
                          disabled={
                            !checklist.xlsform ||
                            deploy.isPending ||
                            checklist.kobo_deployment_status === "deploying"
                          }
                          onClick={() => {
                            deploy.reset();
                            setDeploying(checklist);
                          }}
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
        open={Boolean(deploying)}
        onOpenChange={(value) => {
          if (!value && !deploy.isPending) setDeploying(null);
        }}
        title={t("Deploy checklist?")}
        description={t(
          "This will publish this checklist version to KoBo. Review the name and version before continuing.",
        )}
        showCloseButton={!deploy.isPending}
        contentProps={{
          onEscapeKeyDown: (event) => {
            if (deploy.isPending) event.preventDefault();
          },
        }}
        footer={
          <>
            <CancelButton
              variant="secondary"
              disabled={deploy.isPending}
              onClick={() => setDeploying(null)}
            />
            <Button
              disabled={deploy.isPending}
              onClick={() => {
                if (deploying) deploy.mutate(deploying);
              }}
            >
              {deploy.isPending ? t("Deploying…") : t("Deploy")}
            </Button>
          </>
        }
      >
        <p className="font-medium">
          {deploying?.name} · {deploying?.version}
        </p>
        {deploy.error && (
          <div role="alert" className="error-box">
            {errorMessage(deploy.error)}
          </div>
        )}
      </AppDialog>

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
