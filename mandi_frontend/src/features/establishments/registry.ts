import { useApiQuery } from "@/features/shared/api";

export type RegistryCatalog = {
  types: { code: string; name: string }[];
  systems: { code: string; name: string; adapter: string; searchable?: boolean }[];
};
export function useRegistryCatalog() {
  return useApiQuery<RegistryCatalog>(["registry"], "/registry/");
}
export function useEstablishmentKinds() {
  const catalog = useRegistryCatalog();
  return catalog.data?.types.map((item) => item.code) ?? [];
}
