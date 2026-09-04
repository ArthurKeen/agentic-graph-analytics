"use client";

import { useEffect, useState } from "react";

export const THEME_STORAGE_KEY = "aga-theme";

type Theme = "light" | "dark";

/**
 * Light/dark switch pinned to the top-right of the viewport.
 *
 * Light is the default: the ArangoDB application palette is a light-first
 * design system, so the app renders light until the user opts into dark and
 * that choice is remembered on the device.
 *
 * `theme` starts as `null` so the server render and the first client render
 * agree (both show the light-mode affordance); the stored preference is read
 * in an effect. A tiny inline script in `layout.tsx` applies the stored value
 * before first paint so a dark-mode user never sees a white flash.
 */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme | null>(null);

  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    } catch {
      // Private browsing / storage disabled — fall back to light.
    }
    const initial: Theme = stored === "dark" ? "dark" : "light";
    setTheme(initial);
    document.documentElement.setAttribute("data-theme", initial);
  }, []);

  const isDark = theme === "dark";

  return (
    <button
      type="button"
      className="theme-toggle"
      aria-pressed={isDark}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title="Switch between light and dark mode. Your choice is remembered on this device."
      onClick={(event) => {
        event.stopPropagation();
        const next: Theme = isDark ? "light" : "dark";
        setTheme(next);
        document.documentElement.setAttribute("data-theme", next);
        try {
          window.localStorage.setItem(THEME_STORAGE_KEY, next);
        } catch {
          // Preference simply won't persist; the toggle still works.
        }
      }}
    >
      <span aria-hidden="true">{isDark ? "☀" : "☾"}</span>
    </button>
  );
}
