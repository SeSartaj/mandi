import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemeMode = "light" | "dark" | "system";

interface ThemeState {
  theme: ThemeMode;
  resolvedTheme: "light" | "dark";
  setTheme: (theme: ThemeMode) => void;
  applyTheme: () => void;
}

function resolveSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyThemeClass(theme: "light" | "dark") {
  const root = document.documentElement;
  if (theme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
  root.style.colorScheme = theme;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "system",
      resolvedTheme: "light",
      setTheme: (theme) => {
        const resolved = theme === "system" ? resolveSystemTheme() : theme;
        set({ theme, resolvedTheme: resolved });
        applyThemeClass(resolved);
      },
      applyTheme: () => {
        const { theme } = get();
        const resolved = theme === "system" ? resolveSystemTheme() : theme;
        set({ resolvedTheme: resolved });
        applyThemeClass(resolved);
      },
    }),
    { name: "theme" },
  ),
);

export function getResolvedTheme(): "light" | "dark" {
  return useThemeStore.getState().resolvedTheme;
}
