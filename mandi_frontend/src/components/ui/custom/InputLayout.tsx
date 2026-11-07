import React from "react";
import { FormControl, FormItem, FormLabel, FormMessage } from "@/components/ui/form"; // مسیر کامپوننت‌های shadcn خود را چک کنید
import { cn } from "@/lib/utils";

// ==========================================
// 1. Form Wrapper (برای React Hook Form)
// ==========================================
interface FormInputLayoutProps {
  label?: React.ReactNode;
  required?: boolean;
  reserveErrorSpace?: boolean;
  labelClassName?: string;
  containerClassName?: string;
  children: React.ReactNode;
}

export const FormInputLayout = ({
  label,
  required = false,
  reserveErrorSpace = false,
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
      <div className={reserveErrorSpace ? "min-h-3" : undefined}>
        <FormMessage className="text-destructive text-xs leading-3" />
      </div>
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
  reserveErrorSpace?: boolean;
  labelClassName?: string;
  containerClassName?: string;
  children: React.ReactNode;
}

export const SimpleInputLayout = ({
  id,
  label,
  error,
  required = false,
  reserveErrorSpace = false,
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

      {(error || reserveErrorSpace) && (
        <p
          id={id ? `${id}-error` : undefined}
          role={error ? "alert" : undefined}
          className="text-destructive min-h-3 text-xs leading-3 font-medium"
        >
          {error || "\u00a0"}
        </p>
      )}
    </div>
  );
};
