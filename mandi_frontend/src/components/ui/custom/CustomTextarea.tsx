import React from "react";
import { FormField } from "@/components/ui/form";
import { Textarea } from "@/components/ui/textarea";
import { FieldValues, Path, UseFormReturn } from "react-hook-form";
import { cn } from "@/lib/utils";
import { changeFieldValue, type ClearFieldItem } from "@/utils/form-utils";
import { FormInputLayout, SimpleInputLayout } from "./InputLayout";

// ===== Base Component (UI Logic) =====
interface BaseTextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  hasError?: boolean;
}

function BaseTextarea({ className, hasError, dir = "auto", ...props }: BaseTextareaProps) {
  return (
    <Textarea
      className={cn(
        "min-h-20 resize-y", // Default styles
        hasError &&
          "border-destructive placeholder:text-destructive/50 focus-visible:ring-destructive",
        className,
      )}
      dir={dir === "auto" ? undefined : dir}
      {...props}
    />
  );
}

// ===== Form Textarea (React Hook Form Wrapper) =====
interface FormTextareaProps<T extends FieldValues> extends Omit<
  BaseTextareaProps,
  "name" | "value" | "onChange" | "form"
> {
  form: UseFormReturn<T>;
  name: Path<T>;
  label: string;

  containerClassName?: string;
  labelClassName?: string;

  clearFieldsOnChange?: ClearFieldItem<T>[];
  defaultClearValue?: unknown;

  onValueChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
}

function FormTextarea<T extends FieldValues>({
  form,
  name,
  label,
  containerClassName,
  labelClassName,
  clearFieldsOnChange = [],
  defaultClearValue = "",
  onValueChange,
  ...textareaProps
}: FormTextareaProps<T>) {
  return (
    <FormField
      control={form.control}
      name={name}
      render={({ field, fieldState }) => {
        const handleChange: React.ChangeEventHandler<HTMLTextAreaElement> = (e) => {
          // 1) Update RHF state
          field.onChange(e);

          // 2) Clear dependent fields
          if (clearFieldsOnChange.length) {
            changeFieldValue(form, clearFieldsOnChange, defaultClearValue, {
              shouldDirty: true,
            });
          }

          // 3) Consumer callback
          onValueChange?.(e);
        };

        return (
          <FormInputLayout
            labelClassName={labelClassName}
            containerClassName={containerClassName}
            label={label}
          >
            <BaseTextarea
              {...textareaProps}
              {...field}
              onChange={handleChange}
              hasError={!!fieldState.error}
            />
          </FormInputLayout>
        );
      }}
    />
  );
}

export default FormTextarea;

// ===== Simple Textarea (Standalone) =====
interface SimpleTextareaProps extends BaseTextareaProps {
  label?: string;
  error?: string;
  containerClassName?: string;
  labelClassName?: string;
}

export function SimpleTextarea({
  label,
  error,
  containerClassName,
  labelClassName,
  ...textareaProps
}: SimpleTextareaProps) {
  return (
    <SimpleInputLayout
      containerClassName={containerClassName}
      labelClassName={labelClassName}
      label={label}
      error={error}
    >
      <BaseTextarea hasError={!!error} {...textareaProps} />
    </SimpleInputLayout>
  );
}
