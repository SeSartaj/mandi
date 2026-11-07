import {
  cloneElement,
  Fragment,
  isValidElement,
  useId,
  type ComponentProps,
  type ReactNode,
} from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export type LabelDisplay = "stacked" | "row";

type FormFieldProps = {
  id?: string;
  label?: ReactNode;
  hideLabel?: boolean;
  labelDisplay?: LabelDisplay;
  required?: boolean;
  description?: ReactNode;
  error?: ReactNode;
  reserveErrorSpace?: boolean;
  className?: string;
  children: ReactNode;
};

/** Shared accessible field layout for the quick-entry forms. */
export function FormField({
  id,
  label,
  hideLabel = false,
  labelDisplay = "stacked",
  required = false,
  description,
  error,
  reserveErrorSpace = false,
  className,
  children,
}: FormFieldProps) {
  const generatedId = useId();
  const child =
    isValidElement<ComponentProps<typeof Input>>(children) && children.type !== Fragment
      ? children
      : null;
  const fieldId = id ?? child?.props.id ?? generatedId;
  const describedBy =
    [
      ...new Set(
        [
          child?.props["aria-describedby"],
          description ? `${fieldId}-description` : undefined,
          error ? `${fieldId}-error` : undefined,
        ]
          .filter(Boolean)
          .flatMap((value) => value!.split(/\s+/)),
      ),
    ].join(" ") || undefined;
  const control = child
    ? cloneElement(child, {
        id: fieldId,
        "aria-describedby": describedBy,
        "aria-invalid": error ? true : child.props["aria-invalid"],
        "aria-required": required || child.props["aria-required"],
      })
    : children;
  const hasLabel = !hideLabel && Boolean(label);
  const labelElement = hasLabel ? (
    <Label htmlFor={fieldId} className={labelDisplay === "row" ? "shrink-0" : undefined}>
      {label}
      {required && (
        <span className="text-destructive" aria-hidden="true">
          *
        </span>
      )}
      {labelDisplay === "row" && <span aria-hidden="true">:</span>}
    </Label>
  ) : null;

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      {labelDisplay === "row" ? (
        <div className="flex items-center gap-2">
          {labelElement}
          {control}
        </div>
      ) : (
        <>
          {labelElement}
          {control}
        </>
      )}
      {description && (
        <p id={`${fieldId}-description`} className="text-muted-foreground text-sm">
          {description}
        </p>
      )}
      {(error || reserveErrorSpace) && (
        <p
          id={`${fieldId}-error`}
          role={error ? "alert" : undefined}
          className="text-destructive text-xxs min-h-3 leading-3"
        >
          {error || "\u00a0"}
        </p>
      )}
    </div>
  );
}

type TextFieldProps = Omit<ComponentProps<typeof Input>, "id" | "value" | "onChange"> & {
  id: string;
  label: ReactNode;
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  fieldClassName?: string;
  labelDisplay?: LabelDisplay;
  description?: ReactNode;
  error?: ReactNode;
  reserveErrorSpace?: boolean;
};

/** Input plus the shared field label, spacing, and validation affordances. */
export function TextField({
  id,
  label,
  value,
  defaultValue,
  onChange,
  fieldClassName,
  labelDisplay,
  description,
  error,
  reserveErrorSpace = false,
  ...inputProps
}: TextFieldProps) {
  return (
    <FormField
      id={id}
      label={label}
      labelDisplay={labelDisplay}
      required={inputProps.required}
      description={description}
      error={error}
      reserveErrorSpace={reserveErrorSpace}
      className={fieldClassName}
    >
      <Input
        {...inputProps}
        id={id}
        aria-invalid={error ? true : inputProps["aria-invalid"]}
        aria-describedby={
          [
            inputProps["aria-describedby"],
            description ? `${id}-description` : undefined,
            error ? `${id}-error` : undefined,
          ]
            .filter(Boolean)
            .join(" ") || undefined
        }
        name={inputProps.name ?? id}
        value={value}
        defaultValue={defaultValue}
        onChange={onChange ? (event) => onChange(event.target.value) : undefined}
      />
    </FormField>
  );
}
