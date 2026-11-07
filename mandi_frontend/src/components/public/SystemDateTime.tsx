// Adapted from the AFDA CMS SystemDateTime: all stored values are Gregorian.
import { useLocale } from "@/i18n/useTranslations";
import { useSystemCalendar } from "@/hooks/use-system-calendar";
import { formatSmartDate } from "@/utils/formatSmartDate";
export function SystemDateTime({
  value,
  includeTime = false,
}: {
  value?: string | null;
  includeTime?: boolean;
}) {
  const calendar = useSystemCalendar();
  const locale = useLocale();
  if (!value) return <span>—</span>;
  const dateOnly = includeTime
    ? new Intl.DateTimeFormat("en-CA", {
        timeZone: "Asia/Kabul",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }).format(new Date(value))
    : value.slice(0, 10);
  const date = formatSmartDate({
    date: dateOnly,
    calendarType: calendar === "miladi" ? "gregorian" : calendar === "qamari" ? "hijri" : "shamsi",
  });
  const time = includeTime
    ? new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "fa-AF", {
        timeZone: "Asia/Kabul",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(value))
    : "";
  return (
    <span dir="ltr">
      {date}
      {time ? " " + time : ""}
    </span>
  );
}
