export function validDateRange(from?: string, to?: string) {
  return !from || !to || from <= to;
}
