import React from "react";
import { FormControl, FormItem, FormLabel, FormMessage } from "@/components/ui/form"; // مسیر کامپوننت‌های shadcn خود را چک کنید
import { FieldSupport } from "@/components/ui/field-support";
import { cn } from "@/lib/utils";

// ==========================================
// 1. Form Wrapper (برای React Hook Form)
// ==========================================
interface FormInputLayoutProps {
  label?: React.ReactNode;
  required?: boolean;
  /** @deprecated Message space is always reserved. */
  reserveErrorSpace?: boolean;
  description?: React.ReactNode;
  labelClassName?: string;
  containerClassName?: string;
  children: React.ReactNode;
}

export const FormInputLayout = ({
  label,
  required = false,
  description,
  labelClassName,
  containerClassName,
  children,
}: FormInputLayoutProps) => {
  return (
    <FormItem className={cn("flex flex-col gap-1.5", containerClassName)}>
      {label && (
        <FormLabel className={labelClassName}>
          {label}
          {required && <span className="text-destructive"> *</span>}
        </FormLabel>
      )}
      <FormControl>{children}</FormControl>
      <FormMessage>{description}</FormMessage>
    </FormItem>
  );
};

// ==========================================
// 2. Simple Wrapper (برای حالت ساده)
// ==========================================
interface SimpleInputLayoutProps {
  id?: string;
  label?: string;
  error?: string;
  required?: boolean;
  /** @deprecated Message space is always reserved. */
  reserveErrorSpace?: boolean;
  description?: React.ReactNode;
  labelClassName?: string;
  containerClassName?: string;
  children: React.ReactNode;
}

export const SimpleInputLayout = ({
  id,
  label,
  error,
  required = false,
  description,
  labelClassName,
  containerClassName,
  children,
}: SimpleInputLayoutProps) => {
  return (
    <div className={cn("flex flex-col gap-1.5", containerClassName)}>
      {label && (
        <label
          htmlFor={id}
          className={cn(
            "text-sm leading-none font-medium peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
            labelClassName,
            error && "text-destructive",
          )}
        >
          {label}
          {required && <span className="text-destructive"> *</span>}
        </label>
      )}

      {children}

      <FieldSupport id={id ? `${id}-error` : undefined} error={error} description={description} />
    </div>
  );
};
