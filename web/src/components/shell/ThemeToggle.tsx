"use client";

import { useTheme } from "@/lib/theme";

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  return (
    <button type="button" className="nav-link" onClick={toggleTheme} aria-label="Toggle theme">
      {theme === "dusk" ? "☾ Dusk" : "☀ Ivy"}
    </button>
  );
}
