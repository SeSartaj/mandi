export const establishmentKinds = ["pharmacy", "wholesaler", "importer", "factory"] as const;

export const inspectionKinds = ["comprehensive", "brief", "follow_up", "special"] as const;

const labels: Record<string, string> = {
  pharmacy: "Pharmacy",
  wholesaler: "Wholesaler",
  importer: "Importer",
  factory: "Factory",
  comprehensive: "Comprehensive",
  brief: "Brief",
  follow_up: "Follow-up",
  special: "Special",
};

/** Translation key for a backend choice value. */
export function choiceLabel(value: string) {
  return labels[value] ?? value;
}

export function pageCount(total: number, pageSize: number) {
  return Math.max(1, Math.ceil(total / Math.max(1, pageSize)));
}
