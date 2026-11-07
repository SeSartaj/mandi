import React, { ReactNode } from "react";
import { FormField, FormLabel } from "@/components/ui/form";
import { Switch } from "@/components/ui/switch";
import type { UseFormReturn, Path, FieldValues } from "react-hook-form";
import { cn } from "@/lib/utils";
import { changeFieldValue, type ClearFieldItem } from "@/utils/form-utils";
import { FormInputLayout, SimpleInputLayout } from "./InputLayout";

// ===== Base Component (UI Logic) =====
interface BaseSwitchProps {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;

  label?: ReactNode;
  description?: ReactNode;
  disabled?: boolean;
  hasError?: boolean;

  containerClassName?: string;
  labelClassName?: string;
}

function BaseSwitch({
  checked,
  onCheckedChange,
  label,
  description,
  disabled,
  hasError,
  containerClassName,
  labelClassName,
  ...props
}: BaseSwitchProps & React.ComponentPropsWithoutRef<typeof Switch>) {
  return (
    <div
      className={cn(
        "flex flex-row items-center justify-between rounded-md border p-4",
        hasError && "border-destructive",
        containerClassName,
      )}
    >
      <div className="space-y-0.5">
        {label && (
          <label
            className={cn(
              "text-sm leading-none font-medium peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
              hasError && "text-destructive",
              labelClassName,
            )}
          >
            {label}
          </label>
        )}
        {description && <p className="text-muted-foreground text-sm">{description}</p>}
      </div>

      <Switch checked={checked} onCheckedChange={onCheckedChange} disabled={disabled} {...props} />
    </div>
  );
}

// ===== Form Switch (React Hook Form Wrapper) =====
interface FormSwitchProps<T extends FieldValues> {
  form: UseFormReturn<T>;
  name: Path<T>;
  label: string;
  description?: string;

  containerClassName?: string;
  labelClassName?: string;

  disabled?: boolean;

  clearFieldsOnChange?: ClearFieldItem<T>[];
  defaultClearValue?: unknown;

  onCheckedChange?: (checked: boolean) => void;
}

function FormSwitch<T extends FieldValues>({
  form,
  name,
  label,
  description,
  containerClassName,
  labelClassName,
  disabled,
  clearFieldsOnChange = [],
  defaultClearValue = false,
  onCheckedChange,
}: FormSwitchProps<T>) {
  return (
    <FormField
      control={form.control}
      name={name}
      render={({ field, fieldState }) => {
        const handleCheckedChange = (checked: boolean) => {
          field.onChange(checked);

          if (clearFieldsOnChange.length) {
            changeFieldValue(form, clearFieldsOnChange, defaultClearValue, {
              shouldDirty: true,
            });
          }

          onCheckedChange?.(checked);
        };

        return (
          <FormInputLayout>
            <BaseSwitch
              checked={field.value}
              onCheckedChange={handleCheckedChange}
              label={<FormLabel className={labelClassName}>{label}</FormLabel>}
              description={description}
              disabled={disabled}
              hasError={!!fieldState.error}
              containerClassName={containerClassName}
            />
          </FormInputLayout>
        );
      }}
    />
  );
}

export default FormSwitch;

// ===== Simple Switch (Standalone) =====
interface SimpleSwitchProps extends BaseSwitchProps {
  error?: string;
}

export function SimpleSwitch({
  error,
  containerClassName,
  labelClassName,
  ...props
}: SimpleSwitchProps) {
  return (
    <SimpleInputLayout error={error}>
      <BaseSwitch
        {...props}
        hasError={!!error}
        containerClassName={containerClassName}
        labelClassName={labelClassName}
      />
    </SimpleInputLayout>
  );
}
