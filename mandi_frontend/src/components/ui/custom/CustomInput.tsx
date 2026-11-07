import React, { useEffect, useRef, useState } from "react";
import { FormField } from "@/components/ui/form";
import { InputGroup, InputGroupAddon, InputGroupInput } from "@/components/ui/input-group";
import { Button } from "@/components/ui/button";
import { FieldValues, Path, RegisterOptions, UseFormReturn } from "react-hook-form";
import { cn, toEnglishDigits } from "@/lib/utils";
import { changeFieldValue, type ClearFieldItem } from "@/utils/form-utils";
import { EyeIcon, EyeOffIcon } from "lucide-react";
import { FormInputLayout, SimpleInputLayout } from "./InputLayout";

// ===== Utility: Smart Pattern Formatter =====
const formatByPattern = (
  value: string,
  pattern: string,
  allowTrailingSeparator: boolean = false,
): string => {
  if (!value) return "";

  const rawValue = toEnglishDigits(value).replace(/[^a-zA-Z0-9]/g, "");
  let formatted = "";
  let rawIndex = 0;

  for (let i = 0; i < pattern.length; i++) {
    const patternChar = pattern[i];

    if (patternChar === "#") {
      if (rawIndex >= rawValue.length) break;
      formatted += rawValue[rawIndex];
      rawIndex++;
    } else {
      if (rawIndex < rawValue.length) {
        formatted += patternChar;
      } else if (allowTrailingSeparator) {
        formatted += patternChar;
      } else {
        break;
      }
    }
  }

  return formatted;
};

const sanitizeInputValue = (value: string, onlyDigits: boolean, length?: number) => {
  const normalized = onlyDigits ? toEnglishDigits(value).replace(/\D/g, "") : value;
  return length ? normalized.slice(0, length) : normalized;
};

// ===== Base Component =====
interface BaseInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "form"> {
  leftAddon?: React.ReactNode;
  rightAddon?: React.ReactNode;
  inputClassName?: string;
  addonClassName?: string;
  hasError?: boolean;
}

const BaseInput = React.forwardRef<HTMLInputElement, BaseInputProps>(
  (
    {
      type = "text",
      placeholder,
      disabled,
      dir = "auto",
      leftAddon,
      rightAddon,
      className,
      inputClassName,
      addonClassName,
      hasError,
      ...props
    },
    ref,
  ) => {
    const [showPassword, setShowPassword] = useState(false);

    const inputType = type === "password" ? (showPassword ? "text" : "password") : type;

    const hasRightSide = Boolean(rightAddon) || type === "password";

    return (
      <InputGroup
        dir={dir === "auto" ? undefined : dir}
        className={cn(
          "bg-input-bg overflow-hidden rounded-md border shadow-xs transition-[color,box-shadow] outline-none",
          !hasError &&
            "border-input focus-within:border-ring focus-within:ring-ring/50 focus-within:ring-[3px]",
          hasError &&
            "border-destructive focus-within:border-destructive focus-within:ring-destructive/20 dark:focus-within:ring-destructive/40 focus-within:ring-[3px]",
          className,
        )}
      >
        {leftAddon && (
          <InputGroupAddon
            align="inline-start"
            className={cn("bg-muted text-muted-foreground h-full border-r px-3", addonClassName)}
          >
            {leftAddon}
          </InputGroupAddon>
        )}

        <InputGroupInput
          {...props}
          ref={ref}
          disabled={disabled}
          placeholder={placeholder}
          type={inputType}
          dir={dir === "auto" ? undefined : dir}
          className={cn(
            "hide-password-toggle border-0 px-2 outline-none focus-visible:ring-0 focus-visible:ring-transparent focus-visible:outline-none",
            inputClassName,
          )}
        />

        {hasRightSide && (
          <InputGroupAddon align="inline-end" className={cn("h-full px-0", addonClassName)}>
            <div className="flex items-center gap-1">
              {rightAddon}
              {type === "password" && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  tabIndex={-1}
                  className="hover:bg-transparent"
                  onClick={() => setShowPassword((p) => !p)}
                  disabled={disabled}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeIcon className="h-4 w-4" aria-hidden="true" />
                  ) : (
                    <EyeOffIcon className="h-4 w-4" aria-hidden="true" />
                  )}
                </Button>
              )}
            </div>
          </InputGroupAddon>
        )}

        <style>{`
          .hide-password-toggle::-ms-reveal,
          .hide-password-toggle::-ms-clear {
            visibility: hidden;
            pointer-events: none;
            display: none;
          }
        `}</style>
      </InputGroup>
    );
  },
);

BaseInput.displayName = "BaseInput";

// ===== Form Input =====
interface FormInputProps<T extends FieldValues> extends Omit<
  BaseInputProps,
  "name" | "value" | "onChange" | "hasError" | "leftAddon"
> {
  form: UseFormReturn<T>;
  name: Path<T>;
  label: string;
  containerClassName?: string;
  labelClassName?: string;
  clearFieldsOnChange?: ClearFieldItem<T>[];
  defaultClearValue?: unknown;
  onValueChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  rules?: RegisterOptions<T, Path<T>>;
  reserveErrorSpace?: boolean;
  /** Convert pasted/typed non-Latin digits to Latin digits and remove non-digits. */
  onlyDigits?: boolean;
  /** Maximum number of characters accepted by the input. */
  length?: number;
  mask?: string;
  prefixValue?: string;
  leftAddon?: React.ReactNode;
}

function FormInput<T extends FieldValues>({
  form,
  name,
  label,
  containerClassName,
  labelClassName,
  clearFieldsOnChange = [],
  defaultClearValue = "",
  onValueChange,
  rules,
  reserveErrorSpace = false,
  onlyDigits = false,
  length,
  mask,
  prefixValue,
  leftAddon,
  ...inputProps
}: FormInputProps<T>) {
  return (
    <FormField
      control={form.control}
      name={name}
      rules={rules}
      render={({ field, fieldState }) => {
        let displayValue = field.value ?? "";
        if (
          prefixValue &&
          typeof displayValue === "string" &&
          displayValue.startsWith(prefixValue)
        ) {
          displayValue = displayValue.substring(prefixValue.length);
        }

        const handleChange: React.ChangeEventHandler<HTMLInputElement> = (e) => {
          let inputValue = sanitizeInputValue(e.target.value, onlyDigits, length);

          if (mask) {
            // Type Casting to InputEvent correctly
            const nativeEvent = e.nativeEvent as InputEvent;
            const isDeleting =
              nativeEvent.inputType === "deleteContentBackward" ||
              nativeEvent.inputType === "deleteContentForward";

            inputValue = formatByPattern(inputValue, mask, !isDeleting);
          }

          let storageValue = inputValue;
          if (prefixValue) {
            storageValue = prefixValue + inputValue;
          }

          e.target.value = inputValue;
          field.onChange(storageValue);

          if (clearFieldsOnChange.length) {
            changeFieldValue(form, clearFieldsOnChange, defaultClearValue, {
              shouldDirty: true,
            });
          }

          onValueChange?.(e);
        };

        const finalLeftAddon = prefixValue ? (
          <span className="dir-ltr text-sm font-bold text-gray-500 select-none">{prefixValue}</span>
        ) : (
          leftAddon
        );

        return (
          <FormInputLayout
            labelClassName={labelClassName}
            containerClassName={containerClassName}
            label={label}
            required={inputProps.required}
            reserveErrorSpace={reserveErrorSpace}
          >
            <BaseInput
              {...inputProps}
              {...field}
              value={displayValue}
              onChange={handleChange}
              hasError={!!fieldState.error}
              leftAddon={finalLeftAddon}
              dir={prefixValue || mask ? "ltr" : inputProps.dir}
              maxLength={mask ? mask.length : (length ?? inputProps.maxLength)}
            />
          </FormInputLayout>
        );
      }}
    />
  );
}

export default FormInput;

// ===== Simple Input =====
interface SimpleInputProps extends Omit<BaseInputProps, "leftAddon"> {
  label?: string;
  error?: string;
  containerClassName?: string;
  labelClassName?: string;
  mask?: string;
  prefixValue?: string;
  leftAddon?: React.ReactNode;
  reserveErrorSpace?: boolean;
  /** Convert pasted/typed non-Latin digits to Latin digits and remove non-digits. */
  onlyDigits?: boolean;
  /** Maximum number of characters accepted by the input. */
  length?: number;

  /** debounce time in ms (e.g. 400). If set, onChange will be debounced. */
  debounce?: number;
}

export function SimpleInput({
  label,
  error,
  containerClassName,
  labelClassName,
  mask,
  prefixValue,
  value,
  onChange,
  leftAddon,
  reserveErrorSpace = false,
  onlyDigits = false,
  length,
  required = false,
  debounce,
  ...inputProps
}: SimpleInputProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const timerRef = useRef<number | null>(null);
  const lastEmittedValueRef = useRef<string>("");

  let displayValue = value;

  // remove prefix from displayed value
  if (prefixValue && typeof displayValue === "string" && displayValue.startsWith(prefixValue)) {
    displayValue = displayValue.substring(prefixValue.length);
  }

  const isDebounced = typeof debounce === "number" && debounce > 0;

  // When debounced, sync DOM input value with external value changes (URL/back/forward/reset)
  useEffect(() => {
    if (!isDebounced) return;
    const el = inputRef.current;
    if (!el) return;

    const next = (displayValue ?? "") as string;
    if (el.value !== next) el.value = next;
  }, [isDebounced, displayValue]);

  // cleanup timer
  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, []);

  const emitChange = (finalValue: string, name?: string) => {
    if (!onChange) return;

    lastEmittedValueRef.current = finalValue;

    const syntheticEvent = {
      target: {
        value: finalValue,
        name: name ?? inputProps.name,
      },
    } as React.ChangeEvent<HTMLInputElement>;

    onChange(syntheticEvent);
  };

  const handleChange: React.ChangeEventHandler<HTMLInputElement> = (e) => {
    let inputValue = sanitizeInputValue(e.target.value, onlyDigits, length);

    if (mask) {
      const nativeEvent = e.nativeEvent as InputEvent;
      const isDeleting =
        nativeEvent.inputType === "deleteContentBackward" ||
        nativeEvent.inputType === "deleteContentForward";

      inputValue = formatByPattern(inputValue, mask, !isDeleting);
    }

    // update the displayed value (DOM)
    e.target.value = inputValue;

    const finalValue = prefixValue ? prefixValue + inputValue : inputValue;

    if (!isDebounced) {
      emitChange(finalValue, e.target.name);
      return;
    }

    // debounced emit
    if (timerRef.current) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => {
      emitChange(finalValue, e.target.name);
    }, debounce);
  };

  // optional: flush debounced value on blur (so it doesn't stay pending)
  const handleBlur: React.FocusEventHandler<HTMLInputElement> = (e) => {
    inputProps.onBlur?.(e);

    if (!isDebounced) return;

    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    const inputValue = e.target.value ?? "";
    const finalValue = prefixValue ? prefixValue + inputValue : inputValue;

    // avoid duplicate emit
    if (finalValue !== lastEmittedValueRef.current) {
      emitChange(finalValue, e.target.name);
    }
  };

  const finalLeftAddon = prefixValue ? (
    <span className="dir-ltr text-sm font-bold text-gray-500 select-none">{prefixValue}</span>
  ) : (
    leftAddon
  );

  return (
    <SimpleInputLayout
      id={inputProps.id}
      containerClassName={containerClassName}
      labelClassName={labelClassName}
      label={label}
      error={error}
      required={required}
      reserveErrorSpace={reserveErrorSpace}
    >
      <BaseInput
        {...inputProps}
        ref={inputRef}
        // اگر debounce فعال بود => uncontrolled تا تایپ لگ نداشته باشد
        {...(isDebounced
          ? { defaultValue: (displayValue ?? "") as string }
          : { value: displayValue })}
        onChange={handleChange}
        onBlur={handleBlur}
        hasError={!!error}
        required={required}
        leftAddon={finalLeftAddon}
        dir={prefixValue || mask ? "ltr" : inputProps.dir}
        maxLength={mask ? mask.length : (length ?? inputProps.maxLength)}
      />
    </SimpleInputLayout>
  );
}
