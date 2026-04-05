import { useCallback, useEffect, useMemo, useState } from "react";

export type DashboardTheme = "light" | "dark";

const THEME_STORAGE_KEY = "rpl-dashboard-theme";

function readStoredTheme(): DashboardTheme {
  if (typeof window === "undefined") {
    return "light";
  }
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === "dark") {
    return "dark";
  }
  if (stored === "light") {
    return "light";
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)")?.matches ? "dark" : "light";
}

function persistTheme(theme: DashboardTheme) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }
}

export function applyTheme(theme: DashboardTheme) {
  if (typeof document === "undefined") {
    return;
  }
  document.documentElement.dataset.theme = theme;
  persistTheme(theme);
}

export function useDashboardTheme() {
  const [theme, setTheme] = useState<DashboardTheme>(() => readStoredTheme());

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => (current === "light" ? "dark" : "light"));
  }, []);

  return useMemo(
    () => ({
      theme,
      toggleTheme,
      setTheme,
    }),
    [theme, toggleTheme]
  );
}
