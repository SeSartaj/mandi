import { TfiWorld } from "react-icons/tfi";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { languageOptions } from "@/config/languages";
import { cn } from "@/lib/utils";
import { CustomTooltip } from "@/components/ui/custom/CustomTooltip";
import { setCookieItem } from "@/utils/cookie";
import { useLocale, useTranslations } from "@/i18n/useTranslations";
import { useLocaleStore } from "@/store/locale";

export default function LanguageSwitcher() {
  const t = useTranslations("Language");
  const language = languageOptions(t);
  const currentLocale = useLocale();
  const setLocale = useLocaleStore((s) => s.setLocale);

  const changeLanguage = (newLocale: string) => {
    setCookieItem("NEXT_LOCALE", newLocale, {
      hours: 24 * 30,
    });

    setLocale(newLocale);
  };

  return (
    <DropdownMenu>
      <CustomTooltip title={t("title")}>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size={"icon"} aria-label={t("title")}>
            <TfiWorld className="text-foreground" />
          </Button>
        </DropdownMenuTrigger>
      </CustomTooltip>
      <DropdownMenuContent
        align="start"
        className="z-[100] min-w-36 border-slate-200 bg-white p-1 text-slate-900 shadow-xl dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
      >
        {language?.map((item, index) => (
          <DropdownMenuItem
            className={cn(
              "cursor-pointer focus:bg-slate-100 focus:text-slate-900 dark:focus:bg-slate-800 dark:focus:text-slate-100",
              item?.value == currentLocale && "bg-slate-100 dark:bg-slate-800",
            )}
            onClick={() => changeLanguage(item?.value)}
            disabled={item?.value == currentLocale}
            key={index}
          >
            {item?.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
