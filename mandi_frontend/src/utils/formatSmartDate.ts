import DateObjectImport from "react-date-object";
type DateObject = DateObjectImport;
const DateObject =
  (DateObjectImport as unknown as { default?: typeof DateObjectImport }).default ??
  DateObjectImport;

import gregorian from "react-date-object/calendars/gregorian";
import gregorian_en from "react-date-object/locales/gregorian_en";
import persian from "react-date-object/calendars/persian";
// import persian_fa from "react-date-object/locales/persian_fa";
import arabic from "react-date-object/calendars/arabic";
import arabic_ar from "react-date-object/locales/arabic_ar";
import { dariLocale } from "@/lib/calenders";
export type SmartDateMode = "year" | "year-month" | "full";
export type CalendarType = "shamsi" | "hijri" | "gregorian";
export type SmartDateValue = string | number | Date | DateObject | null | undefined;

export interface FormatSmartDateParams {
  date?: SmartDateValue;
  mode?: SmartDateMode;
  calendarType?: CalendarType;
}

type CalendarValue = typeof gregorian | typeof persian | typeof arabic;
type LocaleValue = typeof gregorian_en | typeof dariLocale | typeof arabic_ar;

interface CalendarConfig {
  calendar: CalendarValue;
  locale: LocaleValue;
}

const CALENDARS: Record<CalendarType, CalendarConfig> = {
  shamsi: { calendar: persian, locale: dariLocale },
  hijri: { calendar: arabic, locale: arabic_ar },
  gregorian: { calendar: gregorian, locale: gregorian_en },
};

const FORMATS: Record<SmartDateMode, string> = {
  year: "YYYY",
  "year-month": "YYYY/MM",
  full: "YYYY/MM/DD",
};

export function formatSmartDate({
  date,
  mode = "full",
  calendarType,
}: FormatSmartDateParams): string {
  if (date === null || date === undefined || date === "") {
    return "";
  }

  try {
    const dateStr = String(date);
    const selectedCalendar =
      calendarType ??
      ((typeof window !== "undefined"
        ? localStorage.getItem("calendar-format")
        : null) as CalendarType | null);
    const target = CALENDARS[selectedCalendar || "gregorian"] || CALENDARS.gregorian;

    const safeDate: string | number | Date | DateObject = /^\d{4}$/.test(dateStr)
      ? `${dateStr}/01/01`
      : date;

    const dateObj = new DateObject({
      date: safeDate,
      calendar: gregorian,
      locale: gregorian_en,
    });

    dateObj.convert(target.calendar, target.locale);

    return dateObj.format(FORMATS[mode] || FORMATS.full);
  } catch (error) {
    console.error("Error formatting date:", error);
    return String(date);
  }
}

export function formatLocalizedTime(value: string, locale: string) {
  const date = new Date(value);

  if (locale === "fa" || locale === "ps") {
    const hour = date.getHours();
    const period = ["fa", "ps"].includes(locale)
      ? hour >= 12
        ? "ب.ظ"
        : "ق.ظ"
      : hour >= 12
        ? "و.غ"
        : "م.غ";
    const hour12 = hour % 12 || 12;
    const toArabicDigits = (number: number) =>
      String(number)
        .padStart(2, "0")
        .replace(/\d/g, (digit) => "٠١٢٣٤٥٦٧٨٩"[Number(digit)]);

    return `${toArabicDigits(hour12)}:${toArabicDigits(date.getMinutes())} ${period}`;
  }

  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export const formatTime = (d: string) => {
  const date = new Date(d);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
};
