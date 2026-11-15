import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

/** Small query helper shared by the copied CMS-style list pages. */
export function useApiQuery<T>(
  key: readonly unknown[],
  url: string,
  params: Record<string, unknown> = {},
  options: { enabled?: boolean } = {},
) {
  return useQuery({
    enabled: options.enabled,
    queryKey: [...key, params],
    queryFn: async ({ signal }) => (await api.get<T>(url, { params, signal })).data,
  });
}
