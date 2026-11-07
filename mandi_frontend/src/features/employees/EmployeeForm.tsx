import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { Can } from "@/components/Can";
import { Button } from "@/components/ui/button";
import CustomForm from "@/components/ui/custom/CustomForm";
import FormInput from "@/components/ui/custom/CustomInput";
import { CustomSearchSelector } from "@/components/ui/custom/CustomSearchSelector";
import { api, errorMessage } from "@/lib/api";

type EmployeeValues = {
  username: string;
  display_name: string;
  position: string;
  password: string;
  group_ids: string[];
};

export default function EmployeeForm({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const form = useForm<EmployeeValues>({
    defaultValues: {
      username: "",
      display_name: "",
      position: "",
      password: "",
      group_ids: [],
    },
  });
  const groups = useQuery({
    queryKey: ["permission-groups"],
    queryFn: async () =>
      (await api.get<{ id: number; name: string }[]>("/permission-groups/")).data,
    retry: false,
  });
  const mutation = useMutation({
    mutationFn: (values: EmployeeValues) =>
      api.post("/employees/", { ...values, group_ids: values.group_ids.map(Number) }),
    onSuccess: () => {
      client.invalidateQueries();
      onClose();
    },
  });

  return (
    <CustomForm form={form} onSubmit={(values) => mutation.mutate(values)} className="space-y-4">
      <FormInput
        form={form}
        name="display_name"
        label={t("Full name")}
        rules={{ required: t("Required") }}
      />
      <FormInput
        form={form}
        name="username"
        label={t("Username")}
        rules={{ required: t("Required") }}
      />
      <FormInput form={form} name="position" label={t("Position")} />
      <FormInput
        form={form}
        name="password"
        label={t("Password")}
        type="password"
        autoComplete="new-password"
        rules={{ required: t("Required") }}
      />
      <Can permissions={["auth.view_group", "accounts.change_user"]} operator="and">
        <CustomSearchSelector
          form={form}
          name="group_ids"
          label={t("Permission groups")}
          items={(groups.data || []).map((group) => ({
            value: String(group.id),
            label: t(group.name),
          }))}
          multichoice
        />
      </Can>
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
