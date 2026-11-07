import { useTranslation } from "react-i18next";
import { useLocaleStore } from "@/store/locale";

/**
 * Mimics next-intl's `useTranslations(namespace)`.
 * Returns a callable `t` function scoped to the given namespace.
 */
export function useTranslations(namespace: string) {
  const { t: baseT } = useTranslation();
  // Subscribe to locale changes so translations re-render on switch
  useLocaleStore((s) => s.locale);

  const t = (key: string, options?: Record<string, unknown>) => {
    const fullKey = `${namespace}.${key}`;
    const value = baseT(fullKey, options as Record<string, string>);
    // If i18next returns the key itself (missing), fall back to the raw key
    return value === fullKey ? key : value;
  };

  return t;
}

/**
 * Mimics next-intl's `useLocale()`.
 */
export function useLocale(): string {
  return useLocaleStore((s) => s.locale);
}
