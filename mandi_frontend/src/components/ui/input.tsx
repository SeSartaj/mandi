import * as React from "react";

import { cn, toEnglishDigits } from "@/lib/utils";

function normalizeNumericValue(value: string) {
  return toEnglishDigits(value)
    .replace(/\u066b/g, ".")
    .replace(/\u066c/g, "");
}

type InputProps = React.ComponentProps<"input"> & {
  normalizeDigits?: boolean;
};

function Input({
  className,
  type,
  inputMode,
  normalizeDigits = false,
  dir,
  value,
  defaultValue,
  onChange,
  ...props
}: InputProps) {
  const isNumberInput = type === "number";
  const shouldNormalizeDigits = isNumberInput || normalizeDigits;
  const normalizedValue =
    isNumberInput && value !== undefined ? normalizeNumericValue(String(value)) : value;
  const normalizedDefaultValue =
    isNumberInput && defaultValue !== undefined
      ? normalizeNumericValue(String(defaultValue))
      : defaultValue;

  const handleChange: React.ChangeEventHandler<HTMLInputElement> = (event) => {
    if (shouldNormalizeDigits) {
      event.target.value = normalizeNumericValue(event.target.value);
    }
    onChange?.(event);
  };

  return (
    <input
      type={type}
      inputMode={isNumberInput ? (inputMode ?? "decimal") : inputMode}
      dir={isNumberInput ? (dir ?? "ltr") : dir}
      value={normalizedValue}
      defaultValue={normalizedDefaultValue}
      onChange={handleChange}
      data-slot="input"
      className={cn(
        "file:text-foreground placeholder:text-muted-foreground selection:bg-primary selection:text-primary-foreground border-input bg-input-bg h-9 w-full min-w-0 rounded-md border px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
        isNumberInput && "text-left tabular-nums",
        "focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]",
        "aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive",
        className,
      )}
      {...props}
    />
  );
}

export { Input };
