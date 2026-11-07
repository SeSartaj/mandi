export function positiveInteger(value: unknown, fallback: number): number {
  const number = Number(value);
  return Number.isSafeInteger(number) && number > 0 ? number : fallback;
}

export function paginationState(
  pageValue: unknown,
  sizeValue: unknown,
  totalItems: number,
  sizes: number[],
  totalPagesValue?: number,
) {
  const options = [...new Set(sizes.filter((size) => positiveInteger(size, 0) > 0))];
  if (!options.length) options.push(10);
  const requestedSize = positiveInteger(sizeValue, options[0]);
  const pageSize = options.includes(requestedSize) ? requestedSize : options[0];
  const totalPages = positiveInteger(
    totalPagesValue,
    Math.max(1, Math.ceil(Math.max(0, totalItems) / pageSize)),
  );
  const page = Math.min(positiveInteger(pageValue, 1), totalPages);
  const pages = [...new Set([1, totalPages, page - 1, page, page + 1])]
    .filter((value) => value >= 1 && value <= totalPages)
    .sort((a, b) => a - b);
  return { page, pageSize, totalPages, options, pages };
}
