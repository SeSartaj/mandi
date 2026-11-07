import { useCallback, useState } from "react";

export const TABLE_PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const;
const STORAGE_KEY = "table-page-size";
const DEFAULT_PAGE_SIZE = 20;

function readPageSize(): number {
  if (typeof window === "undefined") return DEFAULT_PAGE_SIZE;
  try {
    const value = Number(window.localStorage.getItem(STORAGE_KEY));
    return TABLE_PAGE_SIZE_OPTIONS.includes(value as (typeof TABLE_PAGE_SIZE_OPTIONS)[number])
      ? value
      : DEFAULT_PAGE_SIZE;
  } catch {
    return DEFAULT_PAGE_SIZE;
  }
}

export function useTablePageSize() {
  const [pageSize, setPageSizeState] = useState(readPageSize);
  const setPageSize = useCallback((value: number) => {
    if (!TABLE_PAGE_SIZE_OPTIONS.includes(value as (typeof TABLE_PAGE_SIZE_OPTIONS)[number]))
      return;
    setPageSizeState(value);
    try {
      window.localStorage.setItem(STORAGE_KEY, String(value));
    } catch {
      // Keep the in-memory preference if storage is unavailable.
    }
  }, []);

  return [pageSize, setPageSize] as const;
}
