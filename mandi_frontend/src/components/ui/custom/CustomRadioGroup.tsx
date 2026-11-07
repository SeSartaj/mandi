"use client";

import * as React from "react";
import { CircleIcon } from "lucide-react";
import { RadioGroup as RadioGroupPrimitive } from "radix-ui";
import type { FieldValues, Path, UseFormReturn } from "react-hook-form";

import { FormField, FormLabel } from "@/components/ui/form";
import { cn } from "@/lib/utils";
import { changeFieldValue, type ClearFieldItem } from "@/utils/form-utils";
import { FormInputLayout, SimpleInputLayout } from "./InputLayout";

/* =========================
   Types
========================= */
export type RadioOption = {
  value: string;
  label: React.ReactNode;
  description?: React.ReactNode;
  disabled?: boolean;
};

/* =========================
   Base: one "radio card" (دانه‌ای)
========================= */
type RadioCardItemProps = {
  value: string;
  label?: React.ReactNode;
  description?: React.ReactNode;
  hasError?: boolean;
  containerClassName?: string;
  labelClassName?: string;
} & React.ComponentPropsWithoutRef<typeof RadioGroupPrimitive.Item>;

export function RadioCardItem({
  value,
  label,
  description,
  hasError,
  containerClassName,
  labelClassName,
  className,
  disabled,
  ...props
}: RadioCardItemProps) {
  return (
    <RadioGroupPrimitive.Item
      value={value}
      disabled={disabled}
      data-slot="radio-group-item"
      className={cn(
        "flex flex-row items-start justify-between gap-3 rounded-md border p-4",
        "transition-colors outline-none select-none",
        "border-input text-sm",
        "peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
        "focus-visible:ring-ring/30 focus-visible:ring-4",
        "data-[state=checked]:border-ring data-[state=checked]:ring-ring/50 data-[state=checked]:ring-1",
        hasError && "border-destructive data-[state=checked]:border-destructive",
        disabled && "cursor-not-allowed opacity-70",
        className,
      )}
      {...props}
    >
      <div className="flex-1 space-y-0.5">
        {label && (
          <div
            className={cn(
              "leading-none font-medium",
              hasError && "text-destructive",
              labelClassName,
            )}
          >
            {label}
          </div>
        )}
        {description && <p className="text-muted-foreground text-sm">{description}</p>}
      </div>

      {/* Radio indicator (دایره رادیویی) */}
      <div className="mt-0.5">
        <span className="border-input bg-input-bg relative inline-flex h-4 w-4 items-center justify-center rounded-full border">
          <RadioGroupPrimitive.Indicator asChild>
            {/* یک indicator داخل دایره */}
            <span className="flex items-center justify-center">
              <CircleIcon className="fill-primary size-2" aria-hidden />
            </span>
          </RadioGroupPrimitive.Indicator>
        </span>
      </div>

      {/* استایل placeholder برای حالت unchecked: Indicator ندارد، فقط دایره Outline می‌ماند */}
    </RadioGroupPrimitive.Item>
  );
}

/* =========================
   Base: group wrapper (گروپی)
========================= */
type RadioCardGroupProps = {
  value: string;
  onValueChange: (value: string) => void;
  options: RadioOption[];
  disabled?: boolean;
  hasError?: boolean;
  className?: string;
  itemClassName?: string;
};

function RadioCardGroup({
  value,
  onValueChange,
  options,
  disabled,
  hasError,
  className,
  itemClassName,
}: RadioCardGroupProps) {
  return (
    <RadioGroupPrimitive.Root
      data-slot="radio-group"
      className={cn("grid gap-3", className)}
      value={value}
      onValueChange={onValueChange}
      disabled={disabled}
    >
      {options.map((opt) => (
        <RadioCardItem
          key={opt.value}
          value={opt.value}
          label={opt.label}
          description={opt.description}
          disabled={disabled || opt.disabled}
          hasError={hasError}
          className={itemClassName}
        />
      ))}
    </RadioGroupPrimitive.Root>
  );
}

/* =========================
   Form: گروپی داخل RHF
========================= */
type FormRadioGroupProps<T extends FieldValues> = {
  form: UseFormReturn<T>;
  name: Path<T>;
  label: string;
  description?: string;

  options: RadioOption[];
  disabled?: boolean;

  // مثل switch:
  clearFieldsOnChange?: ClearFieldItem<T>[];
  defaultClearValue?: unknown;

  onValueChange?: (value: string) => void;

  className?: string;
  itemClassName?: string;

  labelClassName?: string;
};

export function FormRadioGroup<T extends FieldValues>({
  form,
  name,
  label,
  description,
  options,
  disabled,
  clearFieldsOnChange = [],
  defaultClearValue = undefined,
  onValueChange,
  className,
  itemClassName,
  labelClassName,
}: FormRadioGroupProps<T>) {
  return (
    <FormField
      control={form.control}
      name={name}
      render={({ field, fieldState }) => {
        const currentValue = field.value == null ? "" : String(field.value);

        const handleChange = (next: string) => {
          field.onChange(next);

          if (clearFieldsOnChange.length) {
            changeFieldValue(form, clearFieldsOnChange, defaultClearValue, {
              shouldDirty: true,
            });
          }

          onValueChange?.(next);
        };

        return (
          <FormInputLayout>
            <div className="space-y-2">
              <FormLabel className={labelClassName}>{label}</FormLabel>
              {description && <p className="text-muted-foreground text-sm">{description}</p>}

              <RadioCardGroup
                value={currentValue}
                onValueChange={handleChange}
                options={options}
                disabled={disabled}
                hasError={!!fieldState.error}
                className={className}
                itemClassName={itemClassName}
              />
            </div>
          </FormInputLayout>
        );
      }}
    />
  );
}

/* =========================
   Simple: گروپی مستقل
========================= */
type SimpleRadioGroupProps = {
  label: string;
  description?: string;
  options: RadioOption[];

  disabled?: boolean;

  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;

  error?: string;
  className?: string;
  itemClassName?: string;

  labelClassName?: string;
};

export function SimpleRadioGroup({
  label,
  description,
  options,
  disabled,
  value,
  defaultValue,
  onValueChange,
  error,
  className,
  itemClassName,
  labelClassName,
}: SimpleRadioGroupProps) {
  return (
    <SimpleInputLayout error={error}>
      <div className="space-y-2">
        <FormLabel className={labelClassName}>{label}</FormLabel>
        {description && <p className="text-muted-foreground text-sm">{description}</p>}

        <RadioGroupPrimitive.Root
          data-slot="radio-group"
          className={cn("grid gap-3", className)}
          disabled={disabled}
          value={value}
          defaultValue={defaultValue}
          onValueChange={onValueChange}
        >
          {options.map((opt) => (
            <RadioCardItem
              key={opt.value}
              value={opt.value}
              label={opt.label}
              description={opt.description}
              disabled={disabled || opt.disabled}
              hasError={!!error}
              className={itemClassName}
            />
          ))}
        </RadioGroupPrimitive.Root>
      </div>
    </SimpleInputLayout>
  );
}
