"use client";

import { Moon, Sun } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useLocale, useTranslations } from "@/i18n/useTranslations";
import { isLTR } from "@/config/languages";
import { CustomTooltip } from "./CustomTooltip";
import { useThemeStore } from "@/store/theme";

export function ThemeToggle() {
  const setTheme = useThemeStore((s) => s.setTheme);
  const t = useTranslations("Theme");
  const locale = useLocale();

  return (
    <DropdownMenu>
      <CustomTooltip title={t("title")}>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="icon">
            <Sun className="text-foreground h-[1.2rem] w-[1.2rem] scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
            <Moon className="text-foreground absolute h-[1.2rem] w-[1.2rem] scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0" />
            <span className="sr-only">{t("title")}</span>
          </Button>
        </DropdownMenuTrigger>
      </CustomTooltip>
      <DropdownMenuContent align="center">
        <DropdownMenuItem
          dir={isLTR(locale) ? "ltr" : "rtl"}
          className="text-start"
          onClick={() => setTheme("light")}
        >
          {t("light")}
        </DropdownMenuItem>
        <DropdownMenuItem dir={isLTR(locale) ? "ltr" : "rtl"} onClick={() => setTheme("dark")}>
          {t("dark")}
        </DropdownMenuItem>
        <DropdownMenuItem dir={isLTR(locale) ? "ltr" : "rtl"} onClick={() => setTheme("system")}>
          {t("system")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
