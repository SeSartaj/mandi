export function setCookieItem(name: string, value: string, options?: { hours?: number }) {
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${Math.round((options?.hours ?? 24 * 30) * 3600)}`;
}
