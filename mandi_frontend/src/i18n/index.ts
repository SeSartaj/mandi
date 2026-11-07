import i18next from "i18next";
import { initReactI18next } from "react-i18next";
import en from "@/messages/en.json";
import fa from "@/messages/fa.json";
import ps from "@/messages/ps.json";
import cmsEn from "@/messages/cms-en.json";
import cmsFa from "@/messages/cms-fa.json";
import cmsPs from "@/messages/cms-ps.json";
const routes = {
  en: {
    home: "Home",
    establishments: "Establishments",
    inspections: "Inspections",
    checklists: "Checklists",
    reports: "Coverage",
    establishment_details: "Establishment details",
    inspection_details: "Inspection details",
  },
  fa: {
    home: "خانه",
    establishments: "تأسیسات",
    inspections: "بازرسی‌ها",
    checklists: "چک لیست‌ها",
    reports: "پوشش",
    establishment_details: "معلومات تأسیس",
    inspection_details: "معلومات بازرسی",
  },
  ps: {
    home: "کور",
    establishments: "تأسیسات",
    inspections: "پلټنې",
    checklists: "چک لېستونه",
    reports: "پوښښ",
    establishment_details: "د تأسیس معلومات",
    inspection_details: "د پلټنې معلومات",
  },
};
const breadcrumb = (locale: keyof typeof routes) =>
  Object.fromEntries(Object.entries(routes[locale]).map(([k, v]) => ["Breadcrumb." + k, v]));
i18next.use(initReactI18next).init({
  lng: localStorage.getItem("mandi-locale") || "en",
  fallbackLng: "en",
  supportedLngs: ["en", "fa", "ps"],
  resources: {
    en: { translation: { ...cmsEn, ...en, ...breadcrumb("en") } },
    fa: { translation: { ...cmsFa, ...fa, ...breadcrumb("fa") } },
    ps: { translation: { ...cmsPs, ...ps, ...breadcrumb("ps") } },
  },
  keySeparator: false,
  interpolation: { escapeValue: false },
});
export default i18next;
