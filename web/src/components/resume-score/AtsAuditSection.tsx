"use client";

import type { AtsAudit } from "@/lib/types";
import ScoreBadge from "./ScoreBadge";

const AUDIT_KEYS: { key: keyof Omit<AtsAudit, "issues">; label: string }[] = [
  { key: "parseability", label: "Parseability" },
  { key: "section_completeness", label: "Section Completeness" },
  { key: "format_consistency", label: "Format Consistency" },
  { key: "keyword_coverage", label: "Keyword Coverage" },
];

export default function AtsAuditSection({ audit }: { audit: AtsAudit }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        {AUDIT_KEYS.map(({ key, label }) => {
          const rubric = audit[key];
          return (
            <div
              key={key}
              className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4"
            >
              <div className="mb-3 flex items-center justify-between gap-2">
                <h3 className="text-sm font-medium text-zinc-200">{label}</h3>
                <ScoreBadge score={rubric.score} size="sm" />
              </div>
              <p className="text-sm leading-relaxed text-zinc-400">
                {rubric.reason}
              </p>
              {rubric.suggestion && (
                <p className="mt-2 text-xs leading-relaxed text-zinc-500">
                  💡 {rubric.suggestion}
                </p>
              )}
            </div>
          );
        })}
      </div>

      {audit.issues.length > 0 && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-amber-400">
            ATS Issues
          </h3>
          <ul className="space-y-2">
            {audit.issues.map((issue, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-zinc-400"
              >
                <span className="mt-0.5 text-amber-400">⚠</span>
                <span>{issue}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
