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
import { api, errorMessage, type EstablishmentType } from "@/lib/api";

export default function EstablishmentTypesDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [editCode, setEditCode] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const types = useApiQuery<EstablishmentType[]>(
    ["establishment-types"],
    "/establishment-types/",
    {},
    { enabled: open },
  );
  const invalidate = () => {
    client.invalidateQueries({ queryKey: ["establishment-types"] });
    client.invalidateQueries({ queryKey: ["registry"] });
  };
  const create = useMutation({
    mutationFn: () =>
      api.post("/establishment-types/", { code: code.trim(), name: name.trim() }),
    onSuccess: () => {
      setCode("");
      setName("");
      invalidate();
    },
  });
  const update = useMutation({
    mutationFn: ({
      value,
      ...body
    }: {
      value: string;
      name?: string;
      is_active?: boolean;
    }) => api.patch(`/establishment-types/${value}/`, body),
    onSettled: () => {
      setEditCode(null);
      invalidate();
    },
  });
  const error = create.error || update.error;

  return (
    <AppDialog
      open={open}
      onOpenChange={onOpenChange}
      title={t("Establishment types")}
      size="lg"
      contentClassName="max-h-[90vh] overflow-y-auto"
    >
      <div className="space-y-4">
        <div className="form-grid">
          <div>
            <label className="mb-1 block text-sm font-medium" htmlFor="type-code">
              {t("Code")}
            </label>
            <Input
              id="type-code"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              placeholder="pharmacy"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium" htmlFor="type-name">
              {t("Name")}
            </label>
            <Input
              id="type-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder={t("Pharmacy")}
            />
          </div>
        </div>
        <Button
          disabled={!code.trim() || !name.trim() || create.isPending}
          onClick={() => create.mutate()}
        >
          {create.isPending ? t("Creating…") : t("Add type")}
        </Button>
        {error ? (
          <div role="alert" className="error-box">
            {errorMessage(error)}
          </div>
        ) : null}
        {types.isPending ? (
          <AppLoader label={t("Loading…")} className="py-6" />
        ) : types.error ? (
          <AppErrorState
            message={errorMessage(types.error)}
            onRetry={() => types.refetch()}
          />
        ) : (types.data ?? []).length === 0 ? (
          <p className="muted">{t("No establishment types yet.")}</p>
        ) : (
          <div className="space-y-2">
            {(types.data ?? []).map((type) => (
              <div
                key={type.code}
                className="flex flex-wrap items-center justify-between gap-3 border-b py-2"
              >
                {editCode === type.code ? (
                  <div className="flex flex-1 flex-wrap items-center gap-2">
                    <Input
                      value={editName}
                      onChange={(event) => setEditName(event.target.value)}
                      aria-label={t("Name")}
                    />
                    <Button
                      disabled={!editName.trim() || update.isPending}
                      onClick={() =>
                        update.mutate({ value: type.code, name: editName.trim() })
                      }
                    >
                      {t("Save")}
                    </Button>
                    <Button variant="secondary" onClick={() => setEditCode(null)}>
                      {t("Cancel")}
                    </Button>
                  </div>
                ) : (
                  <>
                    <div>
                      <span className="font-medium">{type.name}</span>
                      {!type.is_active ? (
                        <Badge variant="secondary" className="ml-2">
                          {t("Inactive")}
                        </Badge>
                      ) : null}
                      <small className="muted block">{type.code}</small>
                    </div>
                    <div className="inline-actions">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setEditCode(type.code);
                          setEditName(type.name);
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
                            value: type.code,
                            is_active: !type.is_active,
                          })
                        }
                      >
                        {type.is_active ? t("Deactivate") : t("Activate")}
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
