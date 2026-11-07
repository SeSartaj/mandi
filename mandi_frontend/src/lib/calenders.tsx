import React from "react";
import type { Calendar, Locale } from "react-date-object";

import persian from "react-date-object/calendars/persian";
import arabic from "react-date-object/calendars/arabic";
import gregorian from "react-date-object/calendars/gregorian";

import persian_fa from "react-date-object/locales/persian_fa";
import arabic_ar from "react-date-object/locales/arabic_ar";
import gregorian_en from "react-date-object/locales/gregorian_en";

import { FaCalendarAlt, FaMoon, FaGlobeAmericas } from "react-icons/fa";

export interface CalendarConfig {
  key: string;
  label: string;
  icon: React.ReactNode;
  calendar: Calendar;
  locale: Locale;
  defaultFormat: string;
}

export const dariLocale: Locale = {
  ...persian_fa,
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
};

export type CalendarType = "shamsi" | "qamari" | "miladi";

export function getSystemCalendar(): CalendarType {
  const value = typeof window !== "undefined" ? localStorage.getItem("calendar-format") : null;
  if (value === "shamsi") return "shamsi";
  if (value === "qamari" || value === "hijri") return "qamari";
  return "miladi";
}

export const CALENDARS: Record<CalendarType, CalendarConfig> = {
  shamsi: {
    key: "shamsi",
    label: "shamsi",
    icon: <FaCalendarAlt />,
    calendar: persian,
    locale: dariLocale,
    defaultFormat: "jYYYY/jMM/jDD",
  },

  qamari: {
    key: "qamari",
    label: "hijri",
    icon: <FaMoon />,
    calendar: arabic,
    locale: arabic_ar,
    defaultFormat: "iYYYY/iMM/iDD",
  },

  miladi: {
    key: "miladi",
    label: "gregorian",
    icon: <FaGlobeAmericas />,
    calendar: gregorian,
    locale: gregorian_en,
    defaultFormat: "YYYY-MM-DD",
  },
};
