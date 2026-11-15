import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useWatch } from "react-hook-form";
import { FileSpreadsheet } from "lucide-react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { DialogClose } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import CustomFileInput from "@/components/ui/custom/CustomFileInput";
import CustomForm from "@/components/ui/custom/CustomForm";
import FormInput from "@/components/ui/custom/CustomInput";
import FormSelect from "@/components/ui/custom/CustomSelect";
import { choiceLabel, establishmentKinds } from "@/features/shared/labels";
import type { Checklist } from "@/lib/api";
import { api, errorMessage, fileUrl } from "@/lib/api";

type ChecklistValues = {
  code: string;
  name: string;
  version: string;
  establishment_kind: string;
  xlsform: File | null;
};

export default function ChecklistForm({
  existing,
  onClose,
}: {
  existing?: Checklist;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const form = useForm<ChecklistValues>({
    defaultValues: {
      code: existing?.code ?? "",
      name: existing?.name ?? "",
      version: existing?.version ?? "",
      establishment_kind: existing?.establishment_kind ?? "",
      xlsform: null,
    },
  });
  const file = useWatch({ control: form.control, name: "xlsform" });
  const [reading, setReading] = useState(false);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  useEffect(() => {
    if (!file) {
      setReading(false);
      setMetadataError(null);
      return;
    }
    const controller = new AbortController();
    const body = new FormData();
    body.append("xlsform", file);
    setReading(true);
    setMetadataError(null);
    api
      .post<Partial<Record<"name" | "code" | "version" | "establishment_kind", string>>>(
        "/checklists/metadata/",
        body,
        { signal: controller.signal },
      )
      .then(({ data }) => {
        if (controller.signal.aborted) return;
        for (const field of ["name", "code", "version", "establishment_kind"] as const) {
          // Never overwrite existing records or values the user has edited.
          if (!form.getFieldState(field).isDirty && !existing) {
            form.setValue(field, data[field] ?? "", { shouldValidate: true });
          }
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted) setMetadataError(errorMessage(error));
      })
      .finally(() => {
        if (!controller.signal.aborted) setReading(false);
      });
    return () => controller.abort();
  }, [file, form, existing]);
  const mutation = useMutation({
    mutationFn: async (values: ChecklistValues) => {
      const body = new FormData();
      body.append("code", values.code);
      body.append("name", values.name);
      body.append("version", values.version);
      body.append("establishment_kind", values.establishment_kind);
      if (values.xlsform) body.append("xlsform", values.xlsform);
      return (
        existing
          ? await api.patch(`/checklists/${existing.id}/`, body)
          : await api.post("/checklists/", body)
      ).data;
    },
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["checklists"] });
      client.invalidateQueries({ queryKey: ["form-checklists"] });
      onClose();
    },
  });

  return (
    <CustomForm
      busy={mutation.isPending}
      form={form}
      onSubmit={(values) => mutation.mutate(values)}
      className="space-y-4"
    >
      <CustomFileInput
        form={form}
        name="xlsform"
        label={t("XLSForm")}
        accept={{
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
          "application/vnd.ms-excel": [".xls"],
        }}
        rules={existing ? undefined : { required: t("Select an XLSForm file.") }}
        description={t("Upload the .xls or .xlsx form used for this checklist.")}
        required={!existing}
      />
      <p className="text-muted-foreground text-sm">
        {t(
          "Checklist details are read from the XLSForm settings. Review them and fill in any missing values.",
        )}
      </p>
      {reading && <p role="status">{t("Reading XLSForm settings...")}</p>}
      {metadataError && (
        <div role="alert" className="error-box">
          {metadataError}
        </div>
      )}
      <fieldset disabled={reading || mutation.isPending}>
        <div className="form-grid">
          <FormInput
            form={form}
            name="name"
            label={t("Name")}
            rules={{ required: t("Required") }}
          />
          <FormInput
            form={form}
            name="code"
            label={t("Checklist code")}
            rules={{ required: t("Required") }}
          />
          <FormInput
            form={form}
            name="version"
            label={t("Version")}
            rules={{ required: t("Required") }}
          />
          <FormSelect
            form={form}
            name="establishment_kind"
            label={t("Type")}
            rules={{ required: t("Required") }}
            items={establishmentKinds.map((value) => ({
              value,
              label: t(choiceLabel(value)),
            }))}
          />
        </div>
      </fieldset>

      {existing?.xlsform ? (
        <a className="text-link" href={fileUrl(existing.xlsform)} target="_blank" rel="noreferrer">
          <FileSpreadsheet className="size-4" />
          {t("Current XLSForm")}
        </a>
      ) : null}

      {mutation.error ? (
        <div role="alert" className="error-box">
          {errorMessage(mutation.error)}
        </div>
      ) : null}
      <div className="form-actions">
        <DialogClose asChild>
          <Button type="button" variant="outline" disabled={mutation.isPending}>
            {t("Cancel")}
          </Button>
        </DialogClose>
        <Button disabled={mutation.isPending || reading}>
          {mutation.isPending ? t("Saving…") : t("Save")}
        </Button>
      </div>
    </CustomForm>
  );
}
