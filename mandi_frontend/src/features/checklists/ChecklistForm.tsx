import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileSpreadsheet } from "lucide-react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

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
      establishment_kind: existing?.establishment_kind ?? "pharmacy",
      xlsform: null,
    },
  });
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
    <CustomForm form={form} onSubmit={(values) => mutation.mutate(values)} className="space-y-4">
      <div className="form-grid">
        <FormInput form={form} name="name" label={t("Name")} rules={{ required: t("Required") }} />
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
          items={establishmentKinds.map((value) => ({
            value,
            label: t(choiceLabel(value)),
          }))}
        />
      </div>

      {existing?.xlsform ? (
        <a className="text-link" href={fileUrl(existing.xlsform)} target="_blank" rel="noreferrer">
          <FileSpreadsheet className="size-4" />
          {t("Current XLSForm")}
        </a>
      ) : null}

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

      {mutation.error ? (
        <div role="alert" className="error-box">
          {errorMessage(mutation.error)}
        </div>
      ) : null}
      <div className="form-actions">
        <Button type="button" variant="outline" onClick={onClose}>
          {t("Cancel")}
        </Button>
        <Button disabled={mutation.isPending}>{t("Save")}</Button>
      </div>
    </CustomForm>
  );
}
