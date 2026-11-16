import { FieldSupport } from "@/components/ui/field-support";
import { CancelButton, SaveButton } from "@/components/public/ActionButton";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { DialogClose } from "@/components/ui/dialog";
import CustomForm from "@/components/ui/custom/CustomForm";
import FormInput from "@/components/ui/custom/CustomInput";
import FormSelect from "@/components/ui/custom/CustomSelect";
import FormTextarea from "@/components/ui/custom/CustomTextarea";
import { api, errorMessage } from "@/lib/api";
import type { Establishment } from "@/lib/api";
import { choiceLabel, establishmentKinds } from "@/features/shared/labels";

export default function EstablishmentForm({
  existing,
  onClose,
}: {
  existing?: Establishment;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const navigate = useNavigate();
  const form = useForm({
    defaultValues: {
      name: existing?.name || "",
      kind: existing?.kind || "pharmacy",
      province: existing?.province || "",
      district: existing?.district || "",
      subtype: existing?.subtype || "",
      phone: existing?.phone || "",
      address: existing?.address || "",
    },
  });
  const mutation = useMutation({
    mutationFn: async (values: typeof form.formState.defaultValues) =>
      (existing
        ? await api.patch(`/establishments/${existing.id}/`, values)
        : await api.post("/establishments/", values)
      ).data,
    onSuccess: (data) => {
      client.invalidateQueries();
      onClose();
      navigate(`/establishments/${data.id}`);
    },
  });

  return (
    <CustomForm
      busy={mutation.isPending}
      form={form}
      onSubmit={(values) => mutation.mutate(values)}
      className="space-y-4"
    >
      <div className="form-grid">
        <FormInput
          form={form}
          name="name"
          label={t("Name")}
          maxLength={250}
          rules={{ required: t("Required") }}
        />
        <FormSelect
          form={form}
          name="kind"
          label={t("Type")}
          items={establishmentKinds.map((value) => ({
            value,
            label: t(choiceLabel(value)),
          }))}
        />
        <FormInput
          form={form}
          name="province"
          label={t("Province")}
          maxLength={100}
          rules={{ required: t("Required") }}
        />
        <FormInput form={form} name="district" label={t("District")} maxLength={100} />
        <FormInput form={form} name="subtype" label={t("Subtype")} maxLength={100} />
        <FormInput form={form} name="phone" label={t("Phone")} maxLength={100} />
      </div>
      <FormTextarea form={form} name="address" label={t("Address")} />
      <FieldSupport error={mutation.error ? errorMessage(mutation.error) : undefined} />
      <div className="form-actions">
        <DialogClose asChild>
          <CancelButton type="button" variant="secondary" disabled={mutation.isPending} />
        </DialogClose>
        <SaveButton disabled={mutation.isPending} loading={mutation.isPending} />
      </div>
    </CustomForm>
  );
}
