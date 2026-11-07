import React, { ReactNode } from "react";
import { FormField } from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { UseFormReturn, Path, FieldValues, RegisterOptions } from "react-hook-form";
import { changeFieldValue, type ClearFieldItem } from "@/utils/form-utils";
import { cn } from "@/lib/utils";
import { FormInputLayout, SimpleInputLayout } from "./InputLayout";
import { useTranslations } from "@/i18n/useTranslations";

// ===== Shared Types =====
export interface SelectOption {
  value: string;
  label: ReactNode;
}

// ===== Base Component (UI Logic) =====
interface BaseSelectProps {
  ariaLabel?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  items: SelectOption[];

  placeholder?: string;
  disabled?: boolean;
  hasError?: boolean;

  triggerClassName?: string;
  contentClassName?: string;
  itemClassName?: string;

  leftAddon?: React.ReactNode;
  rightAddon?: React.ReactNode;
  addonClassName?: string;
}

function BaseSelect({
  ariaLabel,
  value,
  onValueChange,
  items = [],

  placeholder,
  disabled = false,
  hasError = false,

  triggerClassName,
  contentClassName,
  itemClassName,

  leftAddon,
  rightAddon,
  addonClassName,
}: BaseSelectProps) {
  const t = useTranslations("Form");
  return (
    <Select value={value} onValueChange={onValueChange} disabled={disabled}>
      <SelectTrigger
        aria-label={ariaLabel}
        className={cn(
          "w-full",
          hasError && "border-destructive text-destructive placeholder:text-destructive/50",
          triggerClassName,
        )}
      >
        <div className="flex min-w-0 flex-1 items-center gap-2">
          {leftAddon && (
            <span className={cn("text-muted-foreground shrink-0", addonClassName)}>
              {leftAddon}
            </span>
          )}

          <span className="min-w-0 flex-1 truncate text-start">
            <SelectValue placeholder={placeholder || t("select")} />
          </span>

          {rightAddon && (
            <span className={cn("text-muted-foreground shrink-0", addonClassName)}>
              {rightAddon}
            </span>
          )}
        </div>
      </SelectTrigger>

      <SelectContent className={contentClassName}>
        {items.map((item) => (
          <SelectItem key={item.value} value={item.value} className={itemClassName}>
            {item.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

// ===== Form Select (React Hook Form Wrapper) =====
interface FormSelectProps<T extends FieldValues> {
  form: UseFormReturn<T>;
  name: Path<T>;
  label: string;
  items: SelectOption[];

  placeholder?: string;
  disabled?: boolean;

  triggerClassName?: string;
  contentClassName?: string;
  itemClassName?: string;

  labelClassName?: string;
  containerClassName?: string;

  clearFieldsOnChange?: ClearFieldItem<T>[];
  defaultClearValue?: unknown;

  leftAddon?: React.ReactNode;
  rightAddon?: React.ReactNode;
  addonClassName?: string;

  onValueChange?: (value: string) => void;
  rules?: RegisterOptions<T, Path<T>>;
  reserveErrorSpace?: boolean;
}

function FormSelect<T extends FieldValues>({
  form,
  name,
  label,
  items,
  placeholder,
  disabled,

  triggerClassName,
  contentClassName,
  itemClassName,

  labelClassName,
  containerClassName,

  clearFieldsOnChange = [],
  defaultClearValue = "",

  leftAddon,
  rightAddon,
  addonClassName,

  onValueChange,
  rules,
  reserveErrorSpace = false,
}: FormSelectProps<T>) {
  return (
    <FormField
      control={form.control}
      name={name}
      rules={rules}
      render={({ field, fieldState }) => {
        const handleValueChange = (value: string) => {
          field.onChange(value);

          if (clearFieldsOnChange.length) {
            changeFieldValue(form, clearFieldsOnChange, defaultClearValue, {
              shouldDirty: true,
            });
          }

          onValueChange?.(value);
        };

        return (
          <FormInputLayout
            labelClassName={labelClassName}
            containerClassName={containerClassName}
            label={label}
            reserveErrorSpace={reserveErrorSpace}
          >
            <BaseSelect
              ariaLabel={label}
              value={field.value}
              onValueChange={handleValueChange}
              items={items}
              placeholder={placeholder}
              disabled={disabled}
              hasError={!!fieldState.error}
              triggerClassName={triggerClassName}
              contentClassName={contentClassName}
              itemClassName={itemClassName}
              leftAddon={leftAddon}
              rightAddon={rightAddon}
              addonClassName={addonClassName}
            />
          </FormInputLayout>
        );
      }}
    />
  );
}

export default FormSelect;

// ===== Simple Select (Standalone) =====
interface SimpleSelectProps {
  value?: string;
  onValueChange?: (value: string) => void;
  items: SelectOption[];

  label?: string;
  placeholder?: string;
  disabled?: boolean;
  error?: string;

  triggerClassName?: string;
  contentClassName?: string;
  itemClassName?: string;

  labelClassName?: string;
  containerClassName?: string;

  leftAddon?: React.ReactNode;
  rightAddon?: React.ReactNode;
  addonClassName?: string;
}

export function SimpleSelect({
  value,
  onValueChange,
  items,

  label,
  placeholder,
  disabled,
  error,

  triggerClassName,
  contentClassName,
  itemClassName,

  labelClassName,
  containerClassName,

  leftAddon,
  rightAddon,
  addonClassName,
}: SimpleSelectProps) {
  return (
    <SimpleInputLayout
      containerClassName={containerClassName}
      labelClassName={labelClassName}
      label={label}
      error={error}
    >
      <BaseSelect
        ariaLabel={label}
        value={value}
        onValueChange={onValueChange}
        items={items}
        placeholder={placeholder}
        disabled={disabled}
        hasError={!!error}
        triggerClassName={triggerClassName}
        contentClassName={contentClassName}
        itemClassName={itemClassName}
        leftAddon={leftAddon}
        rightAddon={rightAddon}
        addonClassName={addonClassName}
      />
    </SimpleInputLayout>
  );
}
