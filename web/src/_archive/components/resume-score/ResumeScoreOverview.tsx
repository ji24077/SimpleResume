"use client";

import type { ResumeScoreResponse } from "@/lib/types";
import ScoreBadge from "./ScoreBadge";

export default function ResumeScoreOverview({
  result,
}: {
  result: ResumeScoreResponse;
}) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
      <div className="flex flex-col items-start gap-6 sm:flex-row sm:items-center">
        <div className="flex flex-col items-center gap-2">
          <ScoreBadge score={result.overall_score} size="lg" />
          <span className="text-lg font-bold text-white">{result.grade}</span>
        </div>
        <div className="flex-1">
          <p className="text-sm leading-relaxed text-zinc-300">
            {result.summary}
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-emerald-400">
            Top Strengths
          </h3>
          <ul className="space-y-2">
            {result.top_strengths.slice(0, 3).map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                <span className="mt-0.5 text-emerald-400" aria-hidden>
                  ✓
                </span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-amber-400">
            Top Issues
          </h3>
          <ul className="space-y-2">
            {result.top_issues.slice(0, 3).map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                <span className="mt-0.5 text-amber-400" aria-hidden>
                  ⚠
                </span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
