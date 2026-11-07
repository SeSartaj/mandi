// AFDA CMS calendar selector; canonical choices drive the copied date controls.
import { CalendarDays } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CustomTooltip } from "./CustomTooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTranslation } from "react-i18next";
import { useSystemCalendar } from "@/hooks/use-system-calendar";
export default function CalendarFormatSelector() {
  const { t } = useTranslation();
  const format = useSystemCalendar();
  return (
    <DropdownMenu>
      <CustomTooltip title={t("Calendar format")}>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="icon" aria-label={t("Calendar format")}>
            <CalendarDays className="size-4" />
          </Button>
        </DropdownMenuTrigger>
      </CustomTooltip>
      <DropdownMenuContent align="end">
        {[
          ["miladi", "Gregorian"],
          ["qamari", "Hijri Qamari"],
          ["shamsi", "Hijri Shamsi"],
        ].map(([value, label]) => (
          <DropdownMenuItem
            key={value}
            onClick={() => {
              localStorage.setItem("calendar-format", value);
              window.dispatchEvent(new CustomEvent("calendar-format-change", { detail: value }));
            }}
            className={format === value ? "bg-accent" : ""}
          >
            {t(label)}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
