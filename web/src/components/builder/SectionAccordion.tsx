"use client";

import { ReactNode, useState } from "react";

type SectionAccordionProps = {
  title: string;
  count?: number;
  defaultOpen?: boolean;
  children: ReactNode;
};

export default function SectionAccordion({
  title,
  count,
  defaultOpen = true,
  children,
}: SectionAccordionProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section
      className="rounded-lg"
      style={{ border: "1px solid var(--border)", background: "var(--surface-1)" }}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between rounded-t-lg px-5 py-4 text-left transition"
        style={{ background: "transparent" }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-hover)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
      >
        <div className="flex items-center gap-3">
          <h3 className="t-label" style={{ fontSize: 12, color: "var(--fg-2)" }}>
            {title}
          </h3>
          {typeof count === "number" && (
            <span
              className="font-mono"
              style={{
                background: "var(--surface-2)",
                color: "var(--fg-4)",
                fontSize: 11,
                padding: "2px 8px",
                borderRadius: 999,
              }}
            >
              {count}
            </span>
          )}
        </div>
        <span style={{ color: "var(--fg-4)" }} aria-hidden>
          {open ? "▾" : "▸"}
        </span>
      </button>
      {open && (
        <div className="px-5 py-5" style={{ borderTop: "1px solid var(--border)" }}>
          {children}
        </div>
      )}
    </section>
  );
}
