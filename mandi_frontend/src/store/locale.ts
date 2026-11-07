import { create } from "zustand";
import i18next from "i18next";
import { isRTL } from "@/config/languages";
export const useLocaleStore = create<{ locale: string; setLocale: (locale: string) => void }>(
  (set) => ({
    locale: localStorage.getItem("mandi-locale") || "en",
    setLocale: (locale) => {
      if (!["en", "fa", "ps"].includes(locale)) return;
      localStorage.setItem("mandi-locale", locale);
      i18next.changeLanguage(locale);
      set({ locale });
    },
  }),
);
export const getCurrentLocale = () => useLocaleStore.getState().locale;
export const isCurrentRTL = () => isRTL(getCurrentLocale());
