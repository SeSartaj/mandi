import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";

import AppFilterPanel, { type ActiveFilter } from "@/components/public/AppFilterPanel";
import { Button } from "@/components/ui/button";
import CustomForm from "@/components/ui/custom/CustomForm";
import FormDatePicker from "@/components/ui/custom/CustomDatePickerType";
import FormInput from "@/components/ui/custom/CustomInput";
import FormSelect from "@/components/ui/custom/CustomSelect";
import { CustomSearchSelector } from "@/components/ui/custom/CustomSearchSelector";
import { choiceLabel, establishmentKinds, inspectionKinds } from "@/features/shared/labels";
import { useSystemCalendar } from "@/hooks/use-system-calendar";
import { api } from "@/lib/api";
import type { Employee, Page } from "@/lib/api";

export type InspectionFilterValues = Record<string, string>;

const emptyFilters: InspectionFilterValues = {
  date_from: "",
  date_to: "",
  kind: "__all__",
  approved: "__all__",
  establishment_kind: "__all__",
  province: "",
  inspector_id: "",
  checklist_id: "",
};

const fieldLabels: Record<string, string> = {
  date_from: "Start date",
  date_to: "End date",
  kind: "Type",
  approved: "Approval",
  establishment_kind: "Establishments",
  province: "Province",
  inspector_id: "Inspector",
  checklist_id: "Checklist",
};

export function InspectionFilters({
  onApply,
  initial = {},
}: {
  onApply: (values: InspectionFilterValues) => void;
  initial?: InspectionFilterValues;
}) {
  const { t } = useTranslation();
  const calendar = useSystemCalendar();
  const [active, setActive] = useState<InspectionFilterValues>(initial);
  const form = useForm<InspectionFilterValues>({
    defaultValues: { ...emptyFilters, ...initial },
  });
  const employees = useQuery({
    queryKey: ["form-employees"],
    queryFn: async () =>
      (await api.get<Page<Employee>>("/employees/", { params: { page_size: 100 } })).data,
  });
  const checklists = useQuery({
    queryKey: ["form-checklists"],
    queryFn: async () =>
      (await api.get<{ id: number; name: string; version: string }[]>("/checklists/")).data,
  });

  const withAll = (placeholder: string, items: { value: string; label: string }[]) => [
    { value: "__all__", label: t(placeholder) },
    ...items,
  ];

  const displayValue = (key: string, value: string) => {
    if (key === "kind" || key === "establishment_kind") return t(choiceLabel(value));
    if (key === "approved") return t(value === "true" ? "Approved" : "Unapproved");
    return value;
  };

  const activeFilters: ActiveFilter[] = Object.entries(active)
    .filter(([, value]) => value && value !== "__all__")
    .map(([key, value]) => ({
      key,
      label: t(fieldLabels[key] ?? key),
      value: displayValue(key, value),
    }));

  const submit = (values: InspectionFilterValues) => {
    const cleaned = Object.fromEntries(
      Object.entries(values)
        .map(([key, value]) => [key, value === "__all__" ? "" : value])
        .filter(([, value]) => value !== ""),
    );
    setActive(cleaned);
    onApply(cleaned);
  };

  const reset = () => {
    form.reset(emptyFilters);
    setActive({});
    onApply({});
  };

  return (
    <AppFilterPanel
      activeFilters={activeFilters}
      onRemoveFilter={(key) => {
        const next = { ...active };
        delete next[key];
        form.setValue(key, emptyFilters[key] ?? "");
        setActive(next);
        onApply(next);
      }}
      onClearAll={reset}
    >
      <CustomForm form={form} onSubmit={submit} className="flex w-full flex-wrap items-end gap-3">
        <FormDatePicker
          form={form}
          name="date_from"
          label={t("Start date")}
          initialCalendar={calendar}
          saveInCalendar="miladi"
          outputFormat="YYYY-MM-DD"
        />
        <FormDatePicker
          form={form}
          name="date_to"
          label={t("End date")}
          initialCalendar={calendar}
          saveInCalendar="miladi"
          outputFormat="YYYY-MM-DD"
        />
        <FormSelect
          form={form}
          name="kind"
          label={t("Type")}
          items={withAll(
            "All inspection types",
            inspectionKinds.map((value) => ({ value, label: t(choiceLabel(value)) })),
          )}
        />
        <FormSelect
          form={form}
          name="approved"
          label={t("Approval")}
          items={withAll("All statuses", [
            { value: "true", label: t("Approved") },
            { value: "false", label: t("Unapproved") },
          ])}
        />
        <FormSelect
          form={form}
          name="establishment_kind"
          label={t("Establishments")}
          items={withAll(
            "All types",
            establishmentKinds.map((value) => ({ value, label: t(choiceLabel(value)) })),
          )}
        />
        <FormInput form={form} name="province" label={t("Province")} />
        <CustomSearchSelector
          form={form}
          name="inspector_id"
          label={t("Inspector")}
          placeholder={t("All inspectors")}
          items={(employees.data?.results || []).map((employee) => ({
            value: String(employee.id),
            label: employee.display_name || employee.username,
          }))}
        />
        <CustomSearchSelector
          form={form}
          name="checklist_id"
          label={t("Checklist")}
          placeholder={t("All checklists")}
          items={(checklists.data || []).map((checklist) => ({
            value: String(checklist.id),
            label: `${checklist.name} · ${checklist.version}`,
          }))}
        />
        <Button>{t("Apply filters")}</Button>
        <Button type="button" variant="outline" onClick={reset}>
          {t("Reset")}
        </Button>
      </CustomForm>
    </AppFilterPanel>
  );
}
