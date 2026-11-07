import type { TranslationMethods } from "@/types/translation";

// Languages that use Right-to-Left direction
export const RTL_LANGUAGES = ["ps", "fa"];

// Left-to-Right languages
export const LTR_LANGUAGES = ["en"];

// All supported languages
export const ALL_LANGUAGES = [...RTL_LANGUAGES, ...LTR_LANGUAGES];

// Default language
export const DEFAULT_LANGUAGE = "ps";

// Language Selector Options

export const languageOptions = (t: TranslationMethods) =>
  ALL_LANGUAGES.map((lang) => ({
    value: lang,
    label: t(`${lang}`),
  }));

// Helper function to check direction
export function isRTL(locale: string): boolean {
  return RTL_LANGUAGES.includes(locale.split("-")[0].toLowerCase());
}

export function isLTR(locale: string): boolean {
  return LTR_LANGUAGES.includes(locale.split("-")[0].toLowerCase());
}
