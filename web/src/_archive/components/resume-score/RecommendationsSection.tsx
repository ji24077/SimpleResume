"use client";

import type { Recommendation } from "@/lib/types";

const PRIORITY_COLOR: Record<string, string> = {
  high: "border-red-700/50 bg-red-950/30 text-red-300",
  medium: "border-amber-700/50 bg-amber-950/30 text-amber-300",
  low: "border-zinc-600/50 bg-zinc-800/40 text-zinc-400",
};

function priorityColor(priority: string): string {
  return PRIORITY_COLOR[priority.toLowerCase()] ?? PRIORITY_COLOR.low;
}

const CATEGORY_ORDER = [
  "Highest Impact Fixes",
  "Easy Wins",
  "ATS Fixes",
  "Bullet Improvements",
  "Missing Information",
];

export default function RecommendationsSection({
  recommendations,
}: {
  recommendations: Recommendation[];
}) {
  if (!recommendations.length) {
    return (
      <p className="text-sm text-zinc-500">No recommendations available.</p>
    );
  }

  const grouped = new Map<string, Recommendation[]>();
  for (const rec of recommendations) {
    const arr = grouped.get(rec.category) ?? [];
    arr.push(rec);
    grouped.set(rec.category, arr);
  }

  const sortedCategories = Array.from(grouped.keys()).sort((a, b) => {
    const ai = CATEGORY_ORDER.indexOf(a);
    const bi = CATEGORY_ORDER.indexOf(b);
    return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
  });

  return (
    <div className="space-y-6">
      {sortedCategories.map((category) => {
        const recs = grouped.get(category)!;
        return (
          <div key={category}>
            <h3 className="mb-3 text-sm font-medium text-zinc-200">
              {category}
            </h3>
            <div className="space-y-2">
              {recs.map((rec, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 rounded-xl border border-zinc-800 bg-zinc-900/40 px-4 py-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-zinc-300">{rec.text}</p>
                    {rec.expected_gain > 0 && (
                      <p className="mt-1 text-xs text-zinc-500">
                        Expected gain: +{rec.expected_gain.toFixed(1)} pts
                      </p>
                    )}
                  </div>
                  <span
                    className={`shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${priorityColor(rec.priority)}`}
                  >
                    {rec.priority}
                  </span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
