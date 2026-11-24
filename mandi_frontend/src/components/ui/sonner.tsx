import { CheckCircle2 } from "lucide-react";
import { Toaster as Sonner, type ToasterProps } from "sonner";

import { isRTL } from "@/config/languages";
import { useLocale } from "@/i18n/useTranslations";
import { useThemeStore } from "@/store/theme";

export function Toaster({ toastOptions, ...props }: ToasterProps) {
  const theme = useThemeStore((state) => state.theme);
  const rtl = isRTL(useLocale());

  return (
    <Sonner
      theme={theme}
      position="top-center"
      dir={rtl ? "rtl" : "ltr"}
      richColors
      icons={{
        success: <CheckCircle2 className="size-4 text-emerald-600 dark:text-emerald-400" />,
      }}
      toastOptions={{
        ...toastOptions,
        style: {
          padding: "1.25rem 1.5rem",
          ...toastOptions?.style,
          fontFamily: '"Vazirmatn", sans-serif',
          fontSize: "1rem",
          fontWeight: 700,
        },
        classNames: {
          ...toastOptions?.classNames,
          toast: "rounded-xl shadow-lg",
          // Descriptions often come from the API and may be English inside an RTL
          // layout; `plaintext` lets the bidi algorithm pick the direction per line.
          description: "[unicode-bidi:plaintext]",
          success:
            "border-emerald-500/50 bg-emerald-50 text-emerald-950 dark:border-emerald-400/50 dark:bg-emerald-950 dark:text-emerald-50",
        },
      }}
      {...props}
    />
  );
}
