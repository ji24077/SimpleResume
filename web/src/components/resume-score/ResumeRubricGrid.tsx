"use client";

import type { RubricScore } from "@/lib/types";
import ScoreBadge from "./ScoreBadge";

function formatLabel(key: string): string {
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function ResumeRubricGrid({
  rubrics,
}: {
  rubrics: Record<string, RubricScore>;
}) {
  const entries = Object.entries(rubrics);

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {entries.map(([key, rubric]) => (
        <div
          key={key}
          className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4"
        >
          <div className="mb-3 flex items-center justify-between gap-2">
            <h3 className="text-sm font-medium text-zinc-200">
              {formatLabel(key)}
            </h3>
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
      ))}
    </div>
  );
}
