import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

/** Small query helper shared by the copied CMS-style list pages. */
export function useApiQuery<T>(
  key: readonly unknown[],
  url: string,
  params: Record<string, unknown> = {},
) {
  return useQuery({
    queryKey: [...key, params],
    queryFn: async () => (await api.get<T>(url, { params })).data,
  });
}
