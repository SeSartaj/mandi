import { useTranslation } from "react-i18next";
import { useApiQuery } from "@/features/shared/api";

export type RegistryCatalog = {
  types: { code: string; name: string }[];
  systems: { code: string; name: string; adapter: string; searchable?: boolean }[];
  provinces: { id: number; name: string; name_local: string }[];
  districts: { id: number; name: string; name_local: string; province_id: number }[];
};
export function useRegistryCatalog() {
  return useApiQuery<RegistryCatalog>(["registry"], "/registry/");
}
export function useEstablishmentKinds() {
  const catalog = useRegistryCatalog();
  return catalog.data?.types.map((item) => item.code) ?? [];
}
export function useLocations() {
  const catalog = useRegistryCatalog();
  return {
    provinces: catalog.data?.provinces ?? [],
    districts: catalog.data?.districts ?? [],
  };
}

/** Pick the local-script name for Pashto/Dari, English for English. */
export function useLocationName() {
  const { i18n } = useTranslation();
  return (name?: string | null, nameLocal?: string | null) =>
    i18n.language === "en" ? name || "" : nameLocal || name || "";
}
