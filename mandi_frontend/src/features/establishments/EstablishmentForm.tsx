import { useEstablishmentKinds } from "@/features/establishments/registry";
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
import { choiceLabel } from "@/features/shared/labels";

export default function EstablishmentForm({
  existing,
  onClose,
}: {
  existing?: Establishment;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const establishmentKinds = useEstablishmentKinds();
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
      latitude: existing?.latitude?.toString() ?? "",
      longitude: existing?.longitude?.toString() ?? "",
      license_number: existing?.license_number || "",
      status: existing?.status || "",
      attributes: JSON.stringify(existing?.attributes ?? {}, null, 2),
    },
  });
  const mutation = useMutation({
    mutationFn: async (values: typeof form.formState.defaultValues) => {
      const attributes: unknown = JSON.parse(values?.attributes || "{}");
      if (!attributes || Array.isArray(attributes) || typeof attributes !== "object")
        throw new Error("Attributes must be a JSON object.");
      const latitude = values?.latitude?.trim() ? Number(values.latitude) : null;
      const longitude = values?.longitude?.trim() ? Number(values.longitude) : null;
      if ((latitude === null) !== (longitude === null))
        throw new Error(t("Provide both latitude and longitude."));
      if (
        (latitude !== null && (!Number.isFinite(latitude) || Math.abs(latitude) > 90)) ||
        (longitude !== null && (!Number.isFinite(longitude) || Math.abs(longitude) > 180))
      )
        throw new Error(t("Invalid coordinates."));
      const payload = { ...values, attributes, latitude, longitude };
      return (
        existing
          ? await api.patch(`/establishments/${existing.id}/`, payload)
          : await api.post("/establishments/", payload)
      ).data;
    },
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
      <div className="form-grid">
        <FormInput form={form} name="latitude" label={t("Latitude")} />
        <FormInput form={form} name="longitude" label={t("Longitude")} />
      </div>
      <FormInput form={form} name="license_number" label={t("License number")} maxLength={200} />
      <FormInput form={form} name="status" label={t("Status")} maxLength={100} />
      <FormTextarea
        form={form}
        name="attributes"
        label={t("Type-specific attributes (JSON object)")}
      />
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
