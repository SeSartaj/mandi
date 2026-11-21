import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { AppDialog } from "@/components/public/AppDialog";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiQuery } from "@/features/shared/api";
import { api, errorMessage, type OdkProject } from "@/lib/api";

export default function OdkProjectsDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const [name, setName] = useState("");
  const [editId, setEditId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const projects = useApiQuery<OdkProject[]>(
    ["odk-projects"],
    "/odk/projects/",
    {},
    { enabled: open },
  );
  const invalidate = () =>
    client.invalidateQueries({ queryKey: ["odk-projects"] });
  const create = useMutation({
    mutationFn: (value: string) => api.post("/odk/projects/", { name: value }),
    onSuccess: () => {
      setName("");
      invalidate();
    },
  });
  const update = useMutation({
    mutationFn: ({
      id,
      ...body
    }: {
      id: number;
      name?: string;
      archived?: boolean;
    }) => api.patch(`/odk/projects/${id}/`, body),
    onSettled: () => {
      setEditId(null);
      invalidate();
    },
  });
  const error = create.error || update.error;

  return (
    <AppDialog
      open={open}
      onOpenChange={onOpenChange}
      title={t("ODK projects")}
      size="lg"
      contentClassName="max-h-[90vh] overflow-y-auto"
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-end gap-2">
          <div className="flex-1">
            <label className="mb-1 block text-sm font-medium" htmlFor="odk-project-name">
              {t("New project name")}
            </label>
            <Input
              id="odk-project-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder={t("New project name")}
            />
          </div>
          <Button
            disabled={!name.trim() || create.isPending}
            onClick={() => create.mutate(name.trim())}
          >
            {create.isPending ? t("Creating…") : t("Create")}
          </Button>
        </div>
        {error ? (
          <div role="alert" className="error-box">
            {errorMessage(error)}
          </div>
        ) : null}
        {projects.isPending ? (
          <AppLoader label={t("Loading…")} className="py-6" />
        ) : projects.error ? (
          <AppErrorState
            message={errorMessage(projects.error)}
            onRetry={() => projects.refetch()}
          />
        ) : (projects.data ?? []).length === 0 ? (
          <p className="muted">{t("No ODK projects yet.")}</p>
        ) : (
          <div className="space-y-2">
            {(projects.data ?? []).map((project) => (
              <div
                key={project.id}
                className="flex flex-wrap items-center justify-between gap-3 border-b py-2"
              >
                {editId === project.id ? (
                  <div className="flex flex-1 flex-wrap items-center gap-2">
                    <Input
                      value={editName}
                      onChange={(event) => setEditName(event.target.value)}
                      aria-label={t("Project name")}
                    />
                    <Button
                      disabled={!editName.trim() || update.isPending}
                      onClick={() =>
                        update.mutate({ id: project.id, name: editName.trim() })
                      }
                    >
                      {t("Save")}
                    </Button>
                    <Button variant="secondary" onClick={() => setEditId(null)}>
                      {t("Cancel")}
                    </Button>
                  </div>
                ) : (
                  <>
                    <div>
                      <span className="font-medium">{project.name}</span>
                      {project.archived ? (
                        <Badge variant="secondary" className="ml-2">
                          {t("Archived")}
                        </Badge>
                      ) : null}
                      <small className="muted block">ID {project.id}</small>
                    </div>
                    <div className="inline-actions">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setEditId(project.id);
                          setEditName(project.name);
                        }}
                      >
                        {t("Rename")}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={update.isPending}
                        onClick={() =>
                          update.mutate({
                            id: project.id,
                            archived: !project.archived,
                          })
                        }
                      >
                        {project.archived ? t("Restore") : t("Archive")}
                      </Button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </AppDialog>
  );
}
