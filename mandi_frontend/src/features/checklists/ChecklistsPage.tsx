import { CreateButton, EditButton, CancelButton } from "@/components/public/ActionButton";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, ExternalLink, FileSpreadsheet, FolderKanban, Rocket } from "lucide-react";
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
import OdkProjectsDialog from "@/features/checklists/OdkProjectsDialog";
import { useApiQuery } from "@/features/shared/api";
import type { Checklist, OdkProject } from "@/lib/api";
import { api, errorMessage } from "@/lib/api";

function structureConflict(error: unknown) {
  return (
    (error as { response?: { status?: number } } | null)?.response?.status === 409
  );
}

export default function ChecklistsPage() {
  const { t } = useTranslation();
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [deploying, setDeploying] = useState<Checklist | null>(null);
  const [editing, setEditing] = useState<Checklist | null>(null);
  const [projectsOpen, setProjectsOpen] = useState(false);
  const [deployProject, setDeployProject] = useState<number | "">("");
  const checklists = useApiQuery<Checklist[]>(["checklists"], "/checklists/");
  const projects = useApiQuery<OdkProject[]>(
    ["odk-projects"],
    "/odk/projects/",
    {},
    { enabled: Boolean(deploying) },
  );
  const deploy = useMutation({
    mutationFn: ({ checklist, force }: { checklist: Checklist; force?: boolean }) =>
      api.post(`/checklists/${checklist.id}/deploy/`, {
        ...(deployProject ? { project_id: deployProject } : {}),
        ...(force ? { force: true } : {}),
      }),
    onSuccess: () => setDeploying(null),
    onSettled: () => {
      client.invalidateQueries({ queryKey: ["checklists"] });
      client.invalidateQueries({ queryKey: ["form-checklists"] });
    },
  });
  const downloadXls = useMutation({
    mutationFn: async (checklist: Checklist) => {
      const response = await api.get(`/checklists/${checklist.id}/download/`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = checklist.xlsform?.split("/").pop() || "checklist.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    },
  });
  const downloadCsv = useMutation({
    mutationFn: async () => {
      const response = await api.get("/integrations/establishments.csv", {
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
  const deployingId = deploy.isPending && deploy.variables ? deploy.variables.checklist.id : null;

  return (
    <div className="space-y-6">
      <PageSection
        headingLevel={1}
        title={t("Checklists")}
        description={t("Upload and manage the XLSForms used to collect submissions.")}
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
            <Can permission="inspections.deploy_checklist">
              <Button variant="outline" onClick={() => setProjectsOpen(true)}>
                <FolderKanban />
                {t("ODK projects")}
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
        {deploy.error || downloadCsv.error || downloadXls.error ? (
          <div role="alert" className="error-box">
            {errorMessage(deploy.error ?? downloadCsv.error ?? downloadXls.error)}
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
          <AppTable className="min-w-[780px]">
            <TableHeader>
              <TableRow>
                <TableHead>{t("Name")}</TableHead>
                <TableHead>{t("Checklist code")}</TableHead>
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
                  <TableCell>
                    {checklist.xlsform ? (
                      <a
                        className="text-link"
                        href="#"
                        onClick={(event) => {
                          event.preventDefault();
                          downloadXls.mutate(checklist);
                        }}
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
                      <DeploymentBadge status={checklist.collection.status} />
                      {checklist.collection.deployed_at ? (
                        <small className="muted block">
                          <SystemDateTime value={checklist.collection.deployed_at} includeTime />
                        </small>
                      ) : null}
                      {checklist.collection.error ? (
                        <small className="text-destructive block max-w-72 whitespace-normal">
                          {checklist.collection.error}
                        </small>
                      ) : null}
                      {checklist.collection.url ? (
                        <a
                          className="text-link"
                          href={checklist.collection.url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <ExternalLink className="size-4" />
                          {t("Open collection service")}
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
                            checklist.collection.status === "deploying"
                          }
                          onClick={() => {
                            deploy.reset();
                            setDeployProject(checklist.collection.project_id ?? "");
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
          "This will publish this checklist version to collection service. Review the name and version before continuing.",
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
                if (deploying) deploy.mutate({ checklist: deploying });
              }}
            >
              {deploy.isPending ? t("Deploying…") : t("Deploy")}
            </Button>
          </>
        }
      >
        <p className="font-medium">
          {deploying?.name}
        </p>
        <label className="mt-4 block space-y-1 text-sm">
          <span className="font-medium">{t("ODK project")}</span>
          <select
            className="border-input bg-background h-9 w-full rounded-md border px-3 text-sm"
            value={deployProject}
            onChange={(event) =>
              setDeployProject(event.target.value ? Number(event.target.value) : "")
            }
            disabled={deploy.isPending}
          >
            <option value="">{t("Default project")}</option>
            {(projects.data ?? [])
              .filter((project) => !project.archived)
              .map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
          </select>
        </label>
        {projects.error ? (
          <p className="muted text-sm">{errorMessage(projects.error)}</p>
        ) : null}
        {deploy.error && (
          <div role="alert" className="error-box space-y-3">
            <p>{errorMessage(deploy.error)}</p>
            {structureConflict(deploy.error) ? (
              <>
                <p className="text-sm">
                  {t(
                    "Publishing anyway can make earlier submissions unreadable. Continue only if you accept that risk.",
                  )}
                </p>
                <Button
                  variant="destructive"
                  disabled={deploy.isPending}
                  onClick={() => {
                    if (deploying) deploy.mutate({ checklist: deploying, force: true });
                  }}
                >
                  {deploy.isPending ? t("Publishing…") : t("Publish anyway")}
                </Button>
              </>
            ) : null}
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

      <OdkProjectsDialog open={projectsOpen} onOpenChange={setProjectsOpen} />
    </div>
  );
}
