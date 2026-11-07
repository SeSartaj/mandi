import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type MouseEvent,
  type KeyboardEventHandler,
} from "react";
import DatePickerModule, { DateObject, type DatePickerRef } from "react-multi-date-picker";
import { CalendarIcon, ChevronLeft, ChevronRight, X } from "lucide-react";
import {
  useWatch,
  type FieldValues,
  type Path,
  type RegisterOptions,
  type UseFormReturn,
} from "react-hook-form";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { FormField } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { changeFieldValue, type ClearFieldItem } from "@/utils/form-utils";
import { CALENDARS, CalendarConfig, CalendarType } from "@/lib/calenders";
import { FormInputLayout, SimpleInputLayout } from "./InputLayout";
import { useTranslations } from "@/i18n/useTranslations";
import styles from "./CustomDatePickerType.module.css";

const DatePicker =
  (
    DatePickerModule as unknown as {
      default?: typeof import("react-multi-date-picker").default;
    }
  ).default ?? DatePickerModule;

// ===== Hook: Date Logic (Conversions) =====
const useDateLogic = (
  value: string | undefined | null,
  outputFormat: string,
  calendarType: CalendarType,
  saveInCalendar: CalendarType,
) => {
  const currentCalendarConfig = CALENDARS[calendarType];
  const saveCalendarConfig = CALENDARS[saveInCalendar];

  const { onlyYearPicker, onlyMonthPicker } = useMemo(() => {
    const hasDay = /D/i.test(outputFormat);
    const hasMonth = /M/i.test(outputFormat);
    const hasYear = /Y/i.test(outputFormat);

    return {
      onlyMonthPicker: hasMonth && !hasDay,
      onlyYearPicker: hasYear && !hasMonth && !hasDay,
    };
  }, [outputFormat]);

  const displayDateObject = useMemo(() => {
    if (!value) return null;
    try {
      const date = new DateObject({
        date: value,
        format: outputFormat,
        calendar: saveCalendarConfig.calendar,
        locale: saveCalendarConfig.locale,
      });

      if (onlyYearPicker) {
        date.setMonth(6).setDay(15);
      } else if (onlyMonthPicker) {
        date.setDay(15);
      }

      date.convert(currentCalendarConfig.calendar, currentCalendarConfig.locale);
      return date;
    } catch (error) {
      console.error(error);
      return null;
    }
  }, [
    value,
    outputFormat,
    saveCalendarConfig,
    currentCalendarConfig,
    onlyYearPicker,
    onlyMonthPicker,
  ]);

  let inputValue = "";
  if (displayDateObject) {
    if (onlyYearPicker) inputValue = displayDateObject.format("YYYY");
    else if (onlyMonthPicker) inputValue = displayDateObject.format("MMMM YYYY");
    else inputValue = displayDateObject.format(outputFormat);
  }

  return {
    currentCalendarConfig,
    saveCalendarConfig,
    onlyYearPicker,
    onlyMonthPicker,
    displayDateObject,
    inputValue,
  };
};

// ===== Base Component (UI Logic) =====
interface BaseDatePickerProps {
  ariaLabel?: string;
  calendarType: CalendarType;
  setCalendarType: (type: CalendarType) => void;

  displayDateObject: DateObject | null;
  inputValue: string;
  onDateChange: (date: DateObject | null) => void;

  currentCalendarConfig: CalendarConfig;
  outputFormat: string;

  placeholder?: string;
  disabled?: boolean;
  hasError?: boolean;
  showCalendarSwitcher?: boolean;

  minDate?: string | Date | DateObject;
  maxDate?: string | Date | DateObject;
  currentDate?: DateObject;
  onlyYearPicker?: boolean;
  onlyMonthPicker?: boolean;

  containerClassName?: string;
  calendarFooter?: ReactNode;
}

function CalendarFooterPlugin({
  position,
  calendarFooter,
}: {
  position: string;
  calendarFooter: ReactNode;
}) {
  void position;
  return <div className="border-t p-2">{calendarFooter}</div>;
}

function BaseDatePicker({
  ariaLabel,
  calendarType,
  setCalendarType,
  displayDateObject,
  inputValue,
  onDateChange,
  currentCalendarConfig,
  outputFormat,
  placeholder,
  disabled,
  hasError,
  showCalendarSwitcher,
  minDate,
  maxDate,
  currentDate,
  onlyYearPicker,
  onlyMonthPicker,
  containerClassName,
  calendarFooter,
}: BaseDatePickerProps) {
  const calendarOptions = Object.values(CALENDARS);
  const t = useTranslations("Date");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const datePickerRef = useRef<DatePickerRef>(null);
  const datePickerId = useId();
  useEffect(() => {
    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target;

      if (!(target instanceof Node)) return;
      if (containerRef.current?.contains(target)) return;
      if (
        target instanceof Element &&
        target.closest(`[data-date-picker-calendar-switcher="${datePickerId}"]`)
      ) {
        return;
      }

      datePickerRef.current?.closeCalendar();
      setOpen(false);
    };

    document.addEventListener("pointerdown", handlePointerDown, true);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown, true);
    };
  }, [datePickerId]);

  return (
    <div
      ref={containerRef}
      className={cn("dir-rtl relative flex w-full items-stretch", containerClassName)}
    >
      {showCalendarSwitcher && (
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button
              type="button"
              tabIndex={-1}
              variant="outline"
              className={cn(
                "border-input bg-muted/50 hover:bg-muted z-10 h-9 shrink-0 rounded-e-none border-e-0 px-3",
                "text-muted-foreground min-w-9 font-normal focus:z-20",
                hasError && "border-destructive",
                disabled && "pointer-events-none opacity-50",
              )}
              title={t("switch_calendar")}
              disabled={disabled}
            >
              <CalendarIcon
                className={cn(
                  "pointer-events-none top-3 h-4 w-4 opacity-50",
                  disabled && "opacity-20",
                  hasError && "text-destructive opacity-100",
                )}
                tabIndex={-1}
                aria-hidden="true"
              />
            </Button>
          </PopoverTrigger>

          <PopoverContent
            data-date-picker-calendar-switcher={datePickerId}
            className="z-2000 w-40 p-1"
            align="start"
          >
            {calendarOptions.map((item) => (
              <div
                key={item.key}
                onClick={() => {
                  setCalendarType(item.key as CalendarType);
                  setOpen(false);
                }}
                className={cn(
                  "hover:bg-accent flex cursor-pointer items-center gap-2 rounded-sm px-2 py-2 text-sm transition-colors",
                  item.key === calendarType && "bg-muted font-medium",
                )}
              >
                <span>{t(item.label)}</span>
              </div>
            ))}
          </PopoverContent>
        </Popover>
      )}

      <div className="relative w-full min-w-0 flex-1">
        <DatePicker
          ref={datePickerRef}
          key={`${calendarType}-${outputFormat}`}
          value={displayDateObject}
          onChange={onDateChange}
          calendar={currentCalendarConfig.calendar}
          locale={currentCalendarConfig.locale}
          format={outputFormat}
          calendarPosition="bottom-right"
          disabled={disabled}
          minDate={minDate}
          maxDate={maxDate}
          currentDate={currentDate}
          // Opening an empty picker should position the calendar, not select today.
          onOpenPickNewDate={false}
          onlyYearPicker={onlyYearPicker}
          onlyMonthPicker={onlyMonthPicker}
          renderButton={(
            direction: string,
            handleClick: (event: MouseEvent<HTMLButtonElement>) => void,
            isDisabled: boolean,
            onKeyDown: KeyboardEventHandler<HTMLButtonElement>,
          ) => (
            <button
              type="button"
              className={styles.navigationButton}
              onClick={handleClick}
              onKeyDown={onKeyDown}
              disabled={isDisabled}
              aria-label={t(direction === "left" ? "previous_period" : "next_period")}
            >
              {/* The library swaps previous/next positions for RTL calendars. */}
              {direction === (calendarType === "miladi" ? "left" : "right") ? (
                <ChevronLeft size={18} />
              ) : (
                <ChevronRight size={18} />
              )}
            </button>
          )}
          plugins={
            calendarFooter
              ? [
                  <CalendarFooterPlugin
                    key="footer"
                    position="bottom"
                    calendarFooter={calendarFooter}
                  />,
                ]
              : []
          }
          containerStyle={{ width: "100%", display: "block" }}
          className={cn("z-2000", styles.calendar)}
          render={(_, openCalendar) => (
            <div className="relative w-full">
              <Input
                aria-label={ariaLabel}
                value={inputValue}
                onClick={!disabled ? openCalendar : undefined}
                placeholder={
                  placeholder ||
                  (onlyYearPicker
                    ? `${t("year")} (${t(currentCalendarConfig.label)})`
                    : onlyMonthPicker
                      ? `${t("year_and_month")} (${t(currentCalendarConfig.label)})`
                      : `${t("date")} (${t(currentCalendarConfig.label)})`)
                }
                className={cn(
                  "bg-input-bg text-foreground h-9 w-full text-start transition-colors",
                  showCalendarSwitcher &&
                    "relative z-0 rounded-s-none focus:z-10 focus-visible:ring-0 focus-visible:ring-offset-0",
                  !disabled && "hover:bg-accent/5 cursor-pointer",
                  disabled && "cursor-not-allowed opacity-50",
                  !inputValue && "text-muted-foreground",
                  hasError &&
                    "border-destructive focus-visible:ring-destructive placeholder:text-destructive/50",
                )}
                readOnly
                disabled={disabled}
              />
              {inputValue && !disabled && (
                <button
                  type="button"
                  tabIndex={-1}
                  aria-label={t("clear_date")}
                  title={t("clear_date")}
                  className="text-muted-foreground hover:text-foreground absolute inset-y-0 end-2 flex items-center"
                  onClick={(event) => {
                    event.stopPropagation();
                    onDateChange(null);
                  }}
                >
                  <X className="size-4" />
                </button>
              )}
            </div>
          )}
        />
      </div>
    </div>
  );
}

// ===== Form DatePicker (React Hook Form Wrapper) =====
interface FormDatePickerProps<T extends FieldValues> {
  form: UseFormReturn<T>;
  name: Path<T>;
  label: string;

  placeholder?: string;
  disabled?: boolean;

  initialCalendar?: CalendarType;
  saveInCalendar?: CalendarType;
  outputFormat?: string;

  minDate?: string | Date | DateObject;
  maxDate?: string | Date | DateObject;
  showCalendarSwitcher?: boolean;

  containerClassName?: string;
  labelClassName?: string;

  clearFieldsOnChange?: ClearFieldItem<T>[];
  defaultClearValue?: unknown;

  onValueChange?: (value: string) => void;
  rules?: RegisterOptions<T, Path<T>>;
  reserveErrorSpace?: boolean;
  calendarFooter?: ReactNode;
}

function FormDatePicker<T extends FieldValues>({
  form,
  name,
  label,

  placeholder,
  disabled = false,

  initialCalendar = "shamsi",
  saveInCalendar = "miladi",
  outputFormat = "YYYY-MM-DD",

  minDate,
  maxDate,
  showCalendarSwitcher = true,

  containerClassName,
  labelClassName,

  clearFieldsOnChange = [],
  defaultClearValue = "",
  onValueChange,
  rules,
  reserveErrorSpace = false,
  calendarFooter,
}: FormDatePickerProps<T>) {
  const [calendarType, setCalendarType] = useState<CalendarType>(initialCalendar);
  useEffect(() => setCalendarType(initialCalendar), [initialCalendar]);

  const watchedValue = useWatch({ control: form.control, name });

  // Now we can call the hook safely
  const logic = useDateLogic(watchedValue, outputFormat, calendarType, saveInCalendar);

  return (
    <FormField
      control={form.control}
      name={name}
      rules={rules}
      render={({ field, fieldState }) => {
        const handleDateChange = (date: DateObject | null) => {
          let newValue = "";

          if (date) {
            date.convert(logic.saveCalendarConfig.calendar, logic.saveCalendarConfig.locale);
            newValue = date.format(outputFormat);
          }

          // 1) Update RHF
          field.onChange(newValue);

          // 2) Clear dependent fields
          if (clearFieldsOnChange.length) {
            changeFieldValue(form, clearFieldsOnChange, defaultClearValue, {
              shouldDirty: true,
            });
          }

          // 3) Consumer callback
          onValueChange?.(newValue);
        };

        return (
          <FormInputLayout
            labelClassName={labelClassName}
            containerClassName={containerClassName}
            label={label}
            reserveErrorSpace={reserveErrorSpace}
          >
            <BaseDatePicker
              ariaLabel={label}
              calendarType={calendarType}
              setCalendarType={setCalendarType}
              displayDateObject={logic.displayDateObject}
              inputValue={logic.inputValue}
              onDateChange={handleDateChange}
              currentCalendarConfig={logic.currentCalendarConfig}
              outputFormat={outputFormat}
              placeholder={placeholder}
              disabled={disabled}
              showCalendarSwitcher={showCalendarSwitcher}
              minDate={minDate}
              maxDate={maxDate}
              onlyYearPicker={logic.onlyYearPicker}
              onlyMonthPicker={logic.onlyMonthPicker}
              hasError={!!fieldState.error}
              calendarFooter={calendarFooter}
            />
          </FormInputLayout>
        );
      }}
    />
  );
}

export default FormDatePicker;

// ===== Simple DatePicker (Standalone) =====
interface SimpleDatePickerProps {
  value?: string;
  /** Initial calendar position in the storage calendar; does not select a date. */
  initialViewDate?: string;
  onChange?: (value: string) => void;
  label?: string;

  placeholder?: string;
  disabled?: boolean;
  error?: string;

  initialCalendar?: CalendarType;
  saveInCalendar?: CalendarType;
  outputFormat?: string;

  minDate?: string | Date | DateObject;
  maxDate?: string | Date | DateObject;
  showCalendarSwitcher?: boolean;

  containerClassName?: string;
  labelClassName?: string;
}

export function SimpleDatePicker({
  value,
  initialViewDate,
  onChange,
  label,

  placeholder,
  disabled,
  error,

  initialCalendar = "shamsi",
  saveInCalendar = "miladi",
  outputFormat = "YYYY-MM-DD",

  minDate,
  maxDate,
  showCalendarSwitcher = true,

  containerClassName,
  labelClassName,
}: SimpleDatePickerProps) {
  const [calendarType, setCalendarType] = useState<CalendarType>(initialCalendar);
  useEffect(() => setCalendarType(initialCalendar), [initialCalendar]);

  const logic = useDateLogic(value, outputFormat, calendarType, saveInCalendar);
  const viewLogic = useDateLogic(
    value || initialViewDate,
    outputFormat,
    calendarType,
    saveInCalendar,
  );

  const handleDateChange = (date: DateObject | null) => {
    if (!date) {
      onChange?.("");
      return;
    }
    date.convert(logic.saveCalendarConfig.calendar, logic.saveCalendarConfig.locale);
    onChange?.(date.format(outputFormat));
  };

  return (
    <SimpleInputLayout
      containerClassName={containerClassName}
      labelClassName={labelClassName}
      label={label}
      error={error}
    >
      <BaseDatePicker
        ariaLabel={label}
        calendarType={calendarType}
        setCalendarType={setCalendarType}
        displayDateObject={logic.displayDateObject}
        inputValue={logic.inputValue}
        onDateChange={handleDateChange}
        currentCalendarConfig={logic.currentCalendarConfig}
        outputFormat={outputFormat}
        placeholder={placeholder}
        disabled={disabled}
        showCalendarSwitcher={showCalendarSwitcher}
        minDate={minDate}
        maxDate={maxDate}
        currentDate={initialViewDate ? (viewLogic.displayDateObject ?? undefined) : undefined}
        onlyYearPicker={logic.onlyYearPicker}
        onlyMonthPicker={logic.onlyMonthPicker}
        hasError={!!error}
      />
    </SimpleInputLayout>
  );
}
