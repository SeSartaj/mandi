export const inspectionFilterKeys = [
  "date_from",
  "date_to",
  "kind",
  "approved",
  "establishment_kind",
  "province",
  "inspector_id",
  "checklist_id",
] as const;

/** Persist only supported filters; keep links and browser history reproducible. */
export function readInspectionFilters(params: URLSearchParams): Record<string, string> {
  return Object.fromEntries(
    inspectionFilterKeys.flatMap((key) => {
      const value = params.get(key);
      return value && value !== "__all__" ? [[key, value]] : [];
    }),
  );
}

export function writeInspectionFilters(params: URLSearchParams, values: Record<string, string>) {
  const next = new URLSearchParams(params);
  for (const key of inspectionFilterKeys) {
    const value = values[key];
    if (value && value !== "__all__") next.set(key, value);
    else next.delete(key);
  }
  next.set("page", "1");
  return next;
}

export function validDateRange(from?: string, to?: string) {
  return !from || !to || from <= to;
}
