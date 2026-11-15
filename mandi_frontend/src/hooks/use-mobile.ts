import { useSyncExternalStore } from "react";

const mobileQuery = "(max-width: 767px)";
const subscribe = (notify: () => void) => {
  const media = window.matchMedia(mobileQuery);
  media.addEventListener("change", notify);
  return () => media.removeEventListener("change", notify);
};
const getSnapshot = () => window.matchMedia(mobileQuery).matches;

export function useIsMobile() {
  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}
