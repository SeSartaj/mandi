import type { FieldValues, Path, UseFormReturn } from "react-hook-form";

/**
 * A field to clear when another field changes.
 * - `name`: the field path to reset.
 * - `value`: optional explicit value to set; falls back to `defaultClearValue`.
 */
export type ClearFieldItem<T extends FieldValues> = {
  name: Path<T>;
  value?: unknown;
};

export type ClearFieldTarget<T extends FieldValues> = Path<T> | ClearFieldItem<T>;

export interface ChangeFieldValueOptions {
  shouldDirty?: boolean;
  shouldValidate?: boolean;
  shouldTouch?: boolean;
}

/**
 * Reset one or more form fields to a default value.
 *
 * Accepts either plain field paths (`Path<T>`) or `ClearFieldItem<T>` objects
 * (which may carry an explicit `value`). When an item has no explicit value,
 * `defaultClearValue` is used.
 */
export function changeFieldValue<T extends FieldValues>(
  form: UseFormReturn<T>,
  clearFieldsOnChange: ClearFieldTarget<T>[],
  defaultClearValue: unknown = "",
  options: ChangeFieldValueOptions = {},
): void {
  const { shouldDirty = true, shouldValidate = false, shouldTouch = false } = options;

  clearFieldsOnChange.forEach((target) => {
    const name = typeof target === "string" ? target : target.name;
    const value =
      typeof target === "object" && "value" in target ? target.value : defaultClearValue;

    form.setValue(name, value as T[Path<T>], {
      shouldDirty,
      shouldValidate,
      shouldTouch,
    });
  });
}
