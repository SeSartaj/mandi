import React, { useMemo } from "react";
import type { FieldValues, Path, PathValue, UseFormReturn } from "react-hook-form";

import DatePicker, { DateObject } from "react-multi-date-picker";
import type { Calendar, Locale } from "react-date-object";

// Calendars
import persian from "react-date-object/calendars/persian";
import gregorian from "react-date-object/calendars/gregorian";
import arabic from "react-date-object/calendars/arabic"; // Hijri/Islamic

// Locales
import persian_fa from "react-date-object/locales/persian_fa";
import gregorian_en from "react-date-object/locales/gregorian_en";
import arabic_ar from "react-date-object/locales/arabic_ar";

import { FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";

import { InputGroup, InputGroupAddon, InputGroupInput } from "@/components/ui/input-group";

import { cn, toEnglishDigits } from "@/lib/utils";
import { changeFieldValue, type ClearFieldItem } from "@/utils/form-utils";

type PickerValueType = "full_year" | "full_date";
type CalendarType = "gregorian" | "jalali" | "hijri";

export type DateFormat = "YYYY" | "YYYY-MM-DD" | "YYYY/MM/DD" | "YYYY.MM.DD" | (string & {});

type FormatConfig = {
  full_year?: DateFormat; // default "YYYY"
  full_date?: DateFormat; // default "YYYY-MM-DD"
};

type CalendarLocaleConfig = {
  calendar: Calendar;
  locale: Locale;
};

function getCalendarAndLocale(
  calendarType: CalendarType,
  dariLocale: Locale,
): CalendarLocaleConfig {
  switch (calendarType) {
    case "gregorian":
      return {
        calendar: gregorian as Calendar,
        locale: gregorian_en as Locale,
      };
    case "hijri":
      return {
        calendar: arabic as Calendar,
        locale: arabic_ar as Locale,
      };
    case "jalali":
    default:
      return {
        calendar: persian as Calendar,
        locale: dariLocale,
      };
  }
}

/**
 * Some versions of `react-date-object` type definitions only allow 0-1 constructor
 * argument, while runtime supports config objects:
 * new DateObject({ date, format, calendar, locale })
 *
 * We keep it safe by using `unknown` cast (no `any`).
 */
type DateObjectCtorArg = ConstructorParameters<typeof DateObject>[0];
type DateObjectInit = {
  date: string;
  format?: string;
  calendar?: Calendar;
  locale?: Locale;
};
function createDateObject(init: DateObjectInit): DateObject {
  return new DateObject(init as unknown as DateObjectCtorArg);
}

export type FormDatePickerProps<T extends FieldValues> = {
  form: UseFormReturn<T>;
  name: Path<T>;
  label: string;

  /** Only year picker or full date picker */
  type?: PickerValueType;

  /** UI calendar (what user sees and selects) */
  calendarType?: CalendarType;

  /** Storage calendar (how value is saved). Default: "gregorian" */
  storageCalendarType?: CalendarType;

  /** Storage format (string saved in the form) */
  storageFormat?: FormatConfig;

  /** Display format (what is shown in the input) */
  displayFormat?: FormatConfig;

  maxDate?: Date | DateObject | string | number;
  disabled?: boolean;
  placeholder?: string;

  /** Value assigned to THIS field when user clears the date (default: "") */
  emptyValue?: PathValue<T, Path<T>>;

  /** Clear dependent fields ONLY when user changes this picker */
  clearFieldsOnChange?: ClearFieldItem<T>[];
  defaultClearValue?: unknown;

  /** Optional addons like FormInput */
  leftAddon?: React.ReactNode;
  rightAddon?: React.ReactNode;
  addonClassName?: string;

  /**
   * When type="full_year", DateObject needs a complete date internally.
   * We create an anchor date: YEAR-(anchorMonth)-(anchorDay)
   */
  yearAnchorMonth?: number; // 1..12 (default 1)
  yearAnchorDay?: number; // 1..31 (default 1)

  /** Class names */
  containerClassName?: string;
  labelClassName?: string;
  inputClassName?: string;
};

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function FormDatePicker<T extends FieldValues>({
  form,
  name,
  label,

  type = "full_year",

  calendarType = "jalali",
  storageCalendarType = "gregorian",

  storageFormat,
  displayFormat,

  maxDate,
  placeholder = "",
  disabled = false,

  emptyValue,

  clearFieldsOnChange = [],
  defaultClearValue = "",

  leftAddon,
  rightAddon,
  addonClassName,

  yearAnchorMonth = 1,
  yearAnchorDay = 1,

  containerClassName,
  labelClassName,
  inputClassName,
}: FormDatePickerProps<T>) {
  // Dari month names for Jalali UI
  const dariLocale = useMemo(() => {
    const base = persian_fa as unknown as Locale;

    return {
      ...(base as object),
      months: [
        ["حمل", "حمل"],
        ["ثور", "ثور"],
        ["جوزا", "جوزا"],
        ["سرطان", "سرطان"],
        ["اسد", "اسد"],
        ["سنبله", "سنبله"],
        ["میزان", "میزان"],
        ["عقرب", "عقرب"],
        ["قوس", "قوس"],
        ["جدی", "جدی"],
        ["دلو", "دلو"],
        ["حوت", "حوت"],
      ],
    } as unknown as Locale;
  }, []);

  const ui = useMemo(
    () => getCalendarAndLocale(calendarType, dariLocale),
    [calendarType, dariLocale],
  );

  const store = useMemo(
    () => getCalendarAndLocale(storageCalendarType, dariLocale),
    [storageCalendarType, dariLocale],
  );

  const resolvedStorageFormat =
    type === "full_year"
      ? (storageFormat?.full_year ?? "YYYY")
      : (storageFormat?.full_date ?? "YYYY-MM-DD");

  const resolvedDisplayFormat =
    type === "full_year"
      ? (displayFormat?.full_year ?? "YYYY")
      : (displayFormat?.full_date ?? "YYYY-MM-DD");

  const baseAddonClasses = "px-3"; // ✅ prevents sticking to borders
  type RmdpProps = React.ComponentProps<typeof DatePicker>;

  return (
    <FormField
      control={form.control}
      name={name}
      render={({ field, fieldState }) => {
        // Convert stored value (storage calendar + storage format) -> UI DateObject
        let pickerValue: DateObject | undefined = undefined;

        if (field.value !== null && field.value !== undefined && field.value !== "") {
          const raw = toEnglishDigits(String(field.value));

          /**
           * ✅ IMPORTANT FIX:
           * When we store only a year (e.g. "2024"), some versions do not render it
           * unless DateObject has a complete date.
           *
           * We create an anchor date: "YYYY-01-01" (or custom month/day)
           * and parse it with "YYYY-MM-DD". Then display format remains "YYYY".
           */
          const parseDate =
            type === "full_year" ? `${raw}-${pad2(yearAnchorMonth)}-${pad2(yearAnchorDay)}` : raw;

          const parseFormat = type === "full_year" ? "YYYY-MM-DD" : resolvedStorageFormat;

          const base = createDateObject({
            date: parseDate,
            format: parseFormat,
            calendar: store.calendar,
            locale: store.locale,
          });

          pickerValue = base.convert(ui.calendar).setLocale(ui.locale);
        }

        const handleUserChange = (date: DateObject | null) => {
          // User cleared
          if (!date) {
            const nextEmpty = (emptyValue ?? ("" as unknown)) as PathValue<T, Path<T>>;

            form.setValue(name, nextEmpty, { shouldDirty: true });

            if (clearFieldsOnChange.length) {
              changeFieldValue(form, clearFieldsOnChange, defaultClearValue, {
                shouldDirty: true,
              });
            }
            return;
          }

          // UI date -> storage calendar -> storage format -> save string
          const stored = date.convert(store.calendar).setLocale(store.locale);

          const formatted = stored.format(resolvedStorageFormat);
          const nextValue = toEnglishDigits(formatted) as PathValue<T, Path<T>>;

          form.setValue(name, nextValue, { shouldDirty: true });

          if (clearFieldsOnChange.length) {
            changeFieldValue(form, clearFieldsOnChange, defaultClearValue, {
              shouldDirty: true,
            });
          }
        };

        return (
          <FormItem className={cn("flex flex-1 flex-col gap-2", containerClassName)}>
            <FormLabel className={labelClassName}>{label}</FormLabel>

            <FormControl>
              <DatePicker
                // ✅ force single-date mode (prevents TS/value union issues)
                multiple={false}
                range={false}
                value={pickerValue}
                disabled={disabled}
                onChange={handleUserChange as unknown as RmdpProps["onChange"]}
                format={resolvedDisplayFormat as unknown as RmdpProps["format"]}
                onlyYearPicker={type === "full_year"}
                maxDate={maxDate as unknown as RmdpProps["maxDate"]}
                locale={ui.locale as unknown as RmdpProps["locale"]}
                calendar={ui.calendar as unknown as RmdpProps["calendar"]}
                render={(value: string, openCalendar: () => void) => (
                  <InputGroup className="h-9 overflow-hidden">
                    {leftAddon && (
                      <InputGroupAddon
                        align="inline-start"
                        className={cn(baseAddonClasses, addonClassName)}
                      >
                        <div className="flex items-center">{leftAddon}</div>
                      </InputGroupAddon>
                    )}

                    <InputGroupInput
                      readOnly
                      disabled={disabled}
                      value={value || ""}
                      placeholder={placeholder}
                      onClick={() => !disabled && openCalendar()}
                      className={cn(
                        "h-full",
                        inputClassName,
                        fieldState.error && "border-red-500 focus-visible:ring-red-500",
                      )}
                    />

                    {rightAddon && (
                      <InputGroupAddon
                        align="inline-end"
                        className={cn(baseAddonClasses, addonClassName)}
                      >
                        <div className="flex items-center">{rightAddon}</div>
                      </InputGroupAddon>
                    )}
                  </InputGroup>
                )}
              />
            </FormControl>

            <FormMessage />
          </FormItem>
        );
      }}
    />
  );
}

export default FormDatePicker;
