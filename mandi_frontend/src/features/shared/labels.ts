export const establishmentKinds = [
  "pharmacy",
  "wholesaler",
  "importer",
  "factory",
  "hospital",
  "clinic",
] as const;

const labels: Record<string, string> = {
  pharmacy: "Pharmacy",
  wholesaler: "Wholesaler",
  importer: "Importer",
  factory: "Factory",
  hospital: "Hospital",
  clinic: "Clinic",
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
