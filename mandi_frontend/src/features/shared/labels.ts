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

const pharmacyTypeLabels: Record<string, string> = {
  "1": "دواخانه شبانه‌روزی",
  "2": "دواخانه فارمسست",
  "3": "ادویه فروشی معاون فارمسست",
  "4": "دواخانه دولتی",
  "5": "دواخانه شفاخانه",
  "6": "ادویه فروشی فروشگاهی",
  "7": "دواخانه سنتی",
};

export function pharmacyTypeLabel(value?: string | number | null) {
  return pharmacyTypeLabels[String(value ?? "").trim()] ?? "";
}

/**
 * Hide Latin-script fragments from registry addresses while keeping local text
 * and house numbers. Registries often send the same address in Dari, Pashto and
 * English separated by bullets; the map should only show the local version.
 */
export function localizeAddress(address?: string | null) {
  const value = (address ?? "").trim();
  if (!value) return "";
  const segments = value
    .split(/\s*[·•|]\s*/)
    .filter((part) => part && !/[A-Za-z]/.test(part));
  if (segments.length) return segments.join(" · ");
  const tokens = value
    .split(/\s+/)
    .filter((token) => token && !/[A-Za-z]/.test(token));
  const cleaned = tokens
    .join(" ")
    .replace(/\s*·(\s*·)+\s*/g, " · ")
    .replace(/^[\s·]+|[\s·]+$/g, "")
    .trim();
  return cleaned || value;
}
