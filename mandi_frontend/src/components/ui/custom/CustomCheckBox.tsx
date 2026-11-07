import type { ReactNode } from "react";
import { FormField, FormLabel } from "@/components/ui/form";
import type { UseFormReturn, Path, FieldValues } from "react-hook-form";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import { changeFieldValue, type ClearFieldItem } from "@/utils/form-utils";
import { FormInputLayout, SimpleInputLayout } from "./InputLayout";

// ===== Base Component (UI Logic) =====
interface BaseCheckBoxProps {
  checked?: boolean | "indeterminate";
  onCheckedChange?: (checked: boolean) => void;

  label?: ReactNode;
  description?: ReactNode;
  disabled?: boolean;
  hasError?: boolean;

  containerClassName?: string;
  labelClassName?: string;
}

function BaseCheckBox({
  checked,
  onCheckedChange,
  label,
  description,
  disabled,
  hasError,
  containerClassName,
  labelClassName,
}: BaseCheckBoxProps) {
  return (
    <div
      className={cn(
        "flex flex-row items-start gap-3 space-y-0 rounded-md border p-4",
        hasError && "border-destructive",
        containerClassName,
      )}
    >
      <Checkbox
        id={label as string}
        checked={checked}
        onCheckedChange={onCheckedChange}
        disabled={disabled}
      />
      <div className="space-y-1 leading-none">
        {label && (
          <label
            htmlFor={label as string}
            className={cn(
              "text-sm leading-none font-medium peer-disabled:cursor-not-allowed peer-disabled:opacity-70 hover:cursor-pointer",
              hasError && "text-destructive",
              labelClassName,
            )}
            onClick={(e) => {
              console.log(e);
              // Optional: Allow clicking label to toggle checkbox if not handled natively by ID
              // But usually Shadcn FormLabel handles this or the wrapper structure.
              // Keeping it simple as a div wrapper here.
            }}
          >
            {label}
          </label>
        )}
        {description && <p className="text-muted-foreground text-sm">{description}</p>}
      </div>
    </div>
  );
}

// ===== Form CheckBox (React Hook Form Wrapper) =====
interface FormCheckBoxProps<T extends FieldValues> {
  form: UseFormReturn<T>;
  name: Path<T>;
  label: string;
  description?: string; // Optional description text

  containerClassName?: string;
  labelClassName?: string;

  disabled?: boolean;

  clearFieldsOnChange?: ClearFieldItem<T>[];
  defaultClearValue?: unknown;

  onCheckedChange?: (checked: boolean) => void;
}

function FormCheckBox<T extends FieldValues>({
  form,
  name,
  label,
  description,
  containerClassName,
  labelClassName,
  disabled,
  clearFieldsOnChange = [],
  defaultClearValue = false, // Checkboxes usually clear to false/unchecked
  onCheckedChange,
}: FormCheckBoxProps<T>) {
  return (
    <FormField
      control={form.control}
      name={name}
      render={({ field, fieldState }) => {
        const handleCheckedChange = (checked: boolean) => {
          // 1) Update RHF
          field.onChange(checked);

          // 2) Clear dependent fields
          if (clearFieldsOnChange.length) {
            changeFieldValue(form, clearFieldsOnChange, defaultClearValue, {
              shouldDirty: true,
            });
          }

          // 3) Consumer callback
          onCheckedChange?.(checked);
        };

        return (
          <FormInputLayout>
            <BaseCheckBox
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

export default FormCheckBox;

// ===== Simple CheckBox (Standalone) =====
interface SimpleCheckBoxProps extends BaseCheckBoxProps {
  error?: string;
}

export function SimpleCheckBox({
  error,
  containerClassName,
  labelClassName,
  ...props
}: SimpleCheckBoxProps) {
  return (
    <SimpleInputLayout error={error}>
      <BaseCheckBox
        {...props}
        hasError={!!error}
        containerClassName={containerClassName}
        labelClassName={labelClassName}
      />
    </SimpleInputLayout>
  );
}
