"use client";

import { useState } from "react";
import type { CredibilityInfo } from "@/lib/types";

const LEVEL_STYLES: Record<string, { bg: string; text: string; border: string; icon: string; label: string }> = {
  high: {
    bg: "bg-emerald-950/50",
    text: "text-emerald-400",
    border: "border-emerald-800/50",
    icon: "✓",
    label: "High Credibility",
  },
  medium: {
    bg: "bg-amber-950/50",
    text: "text-amber-400",
    border: "border-amber-800/50",
    icon: "~",
    label: "Medium Credibility",
  },
  low: {
    bg: "bg-red-950/50",
    text: "text-red-400",
    border: "border-red-800/50",
    icon: "!",
    label: "Low Credibility",
  },
};

export default function CredibilityBadge({ credibility }: { credibility: CredibilityInfo }) {
  const [expanded, setExpanded] = useState(false);
  const style = LEVEL_STYLES[credibility.level] || LEVEL_STYLES.medium;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition hover:brightness-110 ${style.bg} ${style.text} ${style.border}`}
        aria-expanded={expanded}
        aria-label={`${style.label}. ${credibility.signals.length} signal(s). Click to expand.`}
      >
        <span className="text-sm font-bold" aria-hidden>{style.icon}</span>
        <span>{style.label}</span>
      </button>

      {expanded && (
        <div className="absolute left-0 top-full z-40 mt-2 w-64 rounded-lg border border-zinc-700 bg-zinc-900 p-3 shadow-xl">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
            Verification Strength
          </p>
          <ul className="space-y-1.5">
            {credibility.signals.map((signal, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-zinc-300">
                <span className={`mt-0.5 shrink-0 ${style.text}`} aria-hidden>•</span>
                <span>{signal}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[10px] text-zinc-600 italic">
            Credibility reflects verification strength, not a truth claim.
          </p>
        </div>
      )}
    </div>
  );
}
