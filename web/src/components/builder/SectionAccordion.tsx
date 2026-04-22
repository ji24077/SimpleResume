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
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between rounded-t-2xl px-5 py-4 text-left transition hover:bg-zinc-900/70"
      >
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-200">{title}</h3>
          {typeof count === "number" && (
            <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">
              {count}
            </span>
          )}
        </div>
        <span className="text-zinc-500" aria-hidden>
          {open ? "▾" : "▸"}
        </span>
      </button>
      {open && <div className="border-t border-zinc-800 px-5 py-5">{children}</div>}
    </section>
  );
}
