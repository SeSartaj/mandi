import { useSyncExternalStore } from "react";
import { getSystemCalendar } from "@/lib/calenders";
const subscribe = (listener: () => void) => {
  window.addEventListener("calendar-format-change", listener);
  window.addEventListener("storage", listener);
  return () => {
    window.removeEventListener("calendar-format-change", listener);
    window.removeEventListener("storage", listener);
  };
};
export function useSystemCalendar() {
  return useSyncExternalStore(subscribe, getSystemCalendar, () => "miladi" as const);
}
